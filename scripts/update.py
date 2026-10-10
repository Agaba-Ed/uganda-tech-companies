"""Add newly discovered companies to data/unverified.csv and refresh GitHub developer counts.

Never edits names, sectors or descriptions that are already in the dataset (those may have been
corrected by hand), never re-adds anything listed in state/removed.txt, and records every evaluated
domain in state/seen_domains.txt so it is not fetched again.
"""
import os
import re

from common import BUILD, DATA, STATE, clean_row, domain_of, norm, read_csv, write_csv

TECHY = re.compile(r"tech|soft|digital|\bict\b|\bit\b|system|comput|data|cyber|network|telecom|cloud|web|\bapps?\b|"
                   r"innovat|code|coder|dev|labs?\b|\bai\b|bytes?|hub|pay|fin|mobile|robot|iot|smart|logic", re.I)


def lines(path):
    return [l.rstrip("\n") for l in open(path)] if os.path.exists(path) else []


def main():
    companies = read_csv(os.path.join(DATA, "companies.csv"))
    unverified = read_csv(os.path.join(DATA, "unverified.csv"))
    removed = {norm(l) for l in lines(os.path.join(STATE, "removed.txt")) if l and not l.startswith("#")}
    keys = {norm(r["name"]): r for r in companies + unverified}
    domains = {r["domain"]: r for r in companies + unverified if r["domain"]}
    added = []

    def known(name, domain):
        k = norm(name)
        return k in removed or norm(domain) in removed or k in keys or (domain and domain in domains)

    def add(row):
        row = clean_row({**dict.fromkeys(["website", "domain", "sector", "github_devs", "description", "careers_page",
                                          "email", "location", "stack_mentions"], ""), **row})
        if not row:
            return
        row["confidence"] = row.get("confidence") or "low"
        unverified.append(row)
        added.append(row)
        keys[norm(row["name"])] = row
        if row["domain"]:
            domains[row["domain"]] = row

    # 1. homepages that scored as tech
    for r in read_csv(os.path.join(BUILD, "tech_web.csv")):
        name = r["name"] if r["name"] and r["name"] != r["domain"] else r["domain"]
        if not known(name, r["domain"]):
            add({"name": name, "website": r["website"], "domain": r["domain"], "sector": r["sector"],
                 "confidence": r["confidence"], "description": r["description"], "careers_page": r["careers_page"],
                 "email": r["emails"], "stack_mentions": r["stack_mentions"], "sources": r["source"]})

    # 2. employers named by Ugandan GitHub developers: refresh counts, add new tech-sounding ones
    for line in lines(os.path.join(BUILD, "gh_employers.tsv")):
        name, _, n = line.partition("\t")
        n = int(n or 0)
        existing = keys.get(norm(name))
        if existing is not None:
            existing["github_devs"] = str(max(int(existing.get("github_devs") or 0), n))
        elif n >= 2 or TECHY.search(name):
            if not known(name, ""):
                add({"name": name, "github_devs": str(n), "confidence": "medium" if n >= 2 else "low",
                     "sources": "GitHub developers"})

    # 3. GitHub orgs located in Uganda without a scored website
    for line in lines(os.path.join(BUILD, "gh_orgs.tsv")):
        login, name, web, desc, loc, repos = (line.split("\t") + [""] * 6)[:6]
        d = domain_of(web)
        if int(repos or 0) >= 2 and not known(name or login, d):
            add({"name": name or login, "website": web, "domain": d, "description": desc, "location": loc,
                 "sources": "GitHub org"})

    # 4. tech-named OpenStreetMap offices without a scored website
    for r in read_csv(os.path.join(BUILD, "osm_candidates.csv")):
        if r["tech_named"] and not known(r["name"], r["domain"]):
            add({"name": r["name"], "website": r["website"], "domain": r["domain"], "email": r["email"],
                 "location": r["location"], "sources": "OpenStreetMap"})

    unverified.sort(key=lambda r: r["name"].lower())
    write_csv(os.path.join(DATA, "companies.csv"), sorted(companies, key=lambda r: r["name"].lower()))
    write_csv(os.path.join(DATA, "unverified.csv"), unverified)

    seen = set(lines(os.path.join(STATE, "seen_domains.txt"))) | set(lines(os.path.join(BUILD, "to_fetch.txt")))
    os.makedirs(STATE, exist_ok=True)
    with open(os.path.join(STATE, "seen_domains.txt"), "w") as f:
        f.write("\n".join(sorted(d for d in seen if d)) + "\n")

    with open(os.path.join(BUILD, "summary.md"), "w") as f:
        f.write(f"Weekly refresh found **{len(added)}** new candidates (added to `data/unverified.csv`).\n\n")
        for r in added[:200]:
            f.write(f"- {r['name']}" + (f" ({r['website']})" if r["website"] else "") + f" · {r['sources']}\n")
    print(f"added {len(added)} new candidates")


if __name__ == "__main__":
    main()
