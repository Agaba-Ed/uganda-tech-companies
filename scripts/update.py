"""Merge everything the harvesters found into the data files.

- state/curated.csv (official licence lists, sector research) always lands in data/companies.csv.
- New finds go to data/companies.csv when they are medium/high confidence with a website, otherwise
  to data/unverified.csv.
- Existing rows are only enriched (empty fields filled, sources and GitHub counts updated), never
  overwritten, because people correct them by hand. Curated names are the one exception.
- Anything in state/removed.txt is never (re-)added, and every evaluated domain is recorded in
  state/seen_domains.txt so it is not fetched again.
"""

import os
import re

from common import BUILD, DATA, FIELDS, STATE, clean_row, domain_of, norm, read_csv, write_csv

TECHY = re.compile(
    r"tech|soft|digital|\bict\b|\bit\b|system|comput|data|cyber|network|telecom|cloud|web|\bapps?\b|"
    r"innovat|code|coder|dev|labs?\b|\bai\b|bytes?|hub|pay|fin|mobile|robot|iot|smart|logic",
    re.I,
)
RANK = {"high": 0, "medium": 1, "low": 2}


def lines(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def add_source(row, source):
    row["sources"] = "; ".join(dict.fromkeys(filter(None, [*row["sources"].split("; "), source])))


def merge_into(winner, row):
    for col in FIELDS:
        if col == "github_devs":
            winner[col] = str(max(int(winner[col] or 0), int(row[col] or 0)) or "")
        elif col == "sources":
            for source in row[col].split("; "):
                add_source(winner, source)
        elif not winner.get(col):
            winner[col] = row[col]


def dedupe(companies, unverified):
    """Merge rows sharing a normalised name or a domain; the verified, higher-confidence row wins."""
    tagged = [(r, True) for r in companies] + [(r, False) for r in unverified]
    tagged.sort(key=lambda t: (not t[1], RANK.get(t[0]["confidence"], 3)))
    by_key, kept = {}, []
    for row, verified in tagged:
        keys = [k for k in (norm(row["name"]), row["domain"] and "d:" + row["domain"]) if k]
        winner = next((by_key[k] for k in keys if k in by_key), None)
        if winner is None:
            kept.append((row, verified))
            winner = row
        else:
            merge_into(winner, row)
        for k in keys:
            by_key.setdefault(k, winner)
    return [r for r, v in kept if v], [r for r, v in kept if not v]


class Dataset:
    def __init__(self):
        self.companies, self.unverified = dedupe(
            read_csv(os.path.join(DATA, "companies.csv")), read_csv(os.path.join(DATA, "unverified.csv"))
        )
        self.removed = {norm(x) for x in lines(os.path.join(STATE, "removed.txt")) if x and not x.startswith("#")}
        self.by_name = {norm(r["name"]): r for r in self.companies + self.unverified}
        self.by_domain = {r["domain"]: r for r in self.companies + self.unverified if r["domain"]}
        self.added = []

    def find(self, name, domain=""):
        return self.by_name.get(norm(name)) or (self.by_domain.get(domain) if domain else None)

    def is_removed(self, name, domain=""):
        return norm(name) in self.removed or bool(domain and norm(domain) in self.removed)

    def add(self, row, verified=None):
        row = clean_row({**dict.fromkeys(FIELDS, ""), **row})
        if not row or self.is_removed(row["name"], row["domain"]) or self.find(row["name"], row["domain"]):
            return None
        row["confidence"] = row["confidence"] or "low"
        if verified is None:
            verified = row["confidence"] in ("high", "medium") and bool(row["website"])
        (self.companies if verified else self.unverified).append(row)
        self.added.append(row)
        self.by_name[norm(row["name"])] = row
        if row["domain"]:
            self.by_domain[row["domain"]] = row
        return row

    def promote(self, row):
        if row in self.unverified:
            self.unverified.remove(row)
            self.companies.append(row)

    # --- sources -------------------------------------------------------------------------------

    def add_curated(self, rows):
        for r in rows:
            d = domain_of(r["website"])
            source = f"Curated ({r['source']})"
            if self.is_removed(r["name"], d):
                continue
            existing = self.find(r["name"], d)
            if existing is None:
                self.add(
                    {
                        "name": r["name"],
                        "website": r["website"],
                        "domain": d,
                        "sector": r["sector"],
                        "confidence": "high",
                        "sources": source,
                    },
                    verified=True,
                )
                continue
            self.promote(existing)
            existing["confidence"] = "high"
            existing["name"] = r["name"]  # curated names are checked by hand
            if not existing["website"] and r["website"]:
                existing["website"], existing["domain"] = r["website"], d
            if r["sector"] and existing["sector"] in ("", "Tech (general)"):
                existing["sector"] = r["sector"]
            existing["sources"] = "; ".join(x for x in existing["sources"].split("; ") if x != "Curated")
            add_source(existing, source)

    def add_web(self, rows):
        for r in rows:
            name = r["name"] if r["name"] and r["name"] != r["domain"] else r["domain"]
            self.add(
                {
                    "name": name,
                    "website": r["website"],
                    "domain": r["domain"],
                    "sector": r["sector"],
                    "confidence": r["confidence"],
                    "description": r["description"],
                    "careers_page": r["careers_page"],
                    "email": r["emails"],
                    "stack_mentions": r["stack_mentions"],
                    "sources": r["source"],
                }
            )

    def add_directory(self, rows):
        for r in rows:
            existing = self.find(r["name"], r["domain"])
            if existing is not None:
                add_source(existing, "yellow.ug directory")
                existing["location"] = existing["location"] or r["city"]
                continue
            self.add(
                {
                    "name": r["name"],
                    "website": r["website"],
                    "domain": r["domain"],
                    "description": r["tagline"],
                    "location": r["city"],
                    # a directory listing alone is weak evidence: medium only if it also looks like tech
                    "confidence": "medium" if r["website"] and TECHY.search(f"{r['name']} {r['tagline']}") else "low",
                    "sources": "yellow.ug directory",
                }
            )

    def add_employers(self, rows):
        for line in rows:
            name, _, count = line.partition("\t")
            count = int(count or 0)
            existing = self.find(name)
            if existing is not None:
                existing["github_devs"] = str(max(int(existing["github_devs"] or 0), count))
            elif count >= 2 or TECHY.search(name):
                self.add(
                    {
                        "name": name,
                        "github_devs": str(count),
                        "confidence": "medium" if count >= 2 else "low",
                        "sources": "GitHub developers",
                    },
                    verified=False,
                )

    def add_orgs(self, rows):
        for line in rows:
            login, name, web, desc, loc, repos = (line.split("\t") + [""] * 6)[:6]
            if int(repos or 0) >= 2:
                self.add(
                    {
                        "name": name or login,
                        "website": web,
                        "domain": domain_of(web),
                        "description": desc,
                        "location": loc,
                        "sources": "GitHub org",
                    }
                )

    def add_osm(self, rows):
        for r in rows:
            if r["tech_named"]:
                self.add(
                    {
                        "name": r["name"],
                        "website": r["website"],
                        "domain": r["domain"],
                        "email": r["email"],
                        "location": r["location"],
                        "sources": "OpenStreetMap",
                    }
                )

    # --- output --------------------------------------------------------------------------------

    def save(self):
        by_name = lambda r: r["name"].lower()  # noqa: E731
        write_csv(os.path.join(DATA, "companies.csv"), sorted(self.companies, key=by_name))
        write_csv(os.path.join(DATA, "unverified.csv"), sorted(self.unverified, key=by_name))

        seen = set(lines(os.path.join(STATE, "seen_domains.txt"))) | set(lines(os.path.join(BUILD, "to_fetch.txt")))
        os.makedirs(STATE, exist_ok=True)
        with open(os.path.join(STATE, "seen_domains.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(d for d in seen if d)) + "\n")

        os.makedirs(BUILD, exist_ok=True)
        with open(os.path.join(BUILD, "summary.md"), "w", encoding="utf-8") as f:
            f.write(f"Weekly refresh found **{len(self.added)}** new companies.\n\n")
            for r in self.added[:200]:
                f.write(f"- {r['name']}" + (f" ({r['website']})" if r["website"] else "") + f" · {r['sources']}\n")


def main():
    ds = Dataset()
    ds.add_curated(read_csv(os.path.join(STATE, "curated.csv")))
    ds.add_web(read_csv(os.path.join(BUILD, "tech_web.csv")))
    ds.add_directory(read_csv(os.path.join(BUILD, "yellow_candidates.csv")))
    ds.add_employers(lines(os.path.join(BUILD, "gh_employers.tsv")))
    ds.add_orgs(lines(os.path.join(BUILD, "gh_orgs.tsv")))
    ds.add_osm(read_csv(os.path.join(BUILD, "osm_candidates.csv")))
    ds.save()
    print(f"added {len(ds.added)} new companies")


if __name__ == "__main__":
    main()
