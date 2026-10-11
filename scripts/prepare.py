"""Work out which domains still need a homepage fetch.

Combines domains from Common Crawl, OpenStreetMap and GitHub orgs, drops ones already
evaluated (state/seen_domains.txt) or already in the dataset.
Output: build/to_fetch.txt, build/source_map.tsv
"""

import os

from common import BUILD, DATA, STATE, domain_of, read_csv

SKIP_HOSTS = (
    "github.io",
    "github.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "medium.com",
    "youtube.com",
    "instagram.com",
    "vercel.app",
    "netlify.app",
    "herokuapp.com",
    "blogspot.com",
    "wordpress.com",
    "google.com",
    "linktr.ee",
    "notion.site",
    "wixsite.com",
    "bit.ly",
)


def lines(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f]


def main():
    source = {}
    for d in lines(os.path.join(BUILD, "cc_domains.txt")):
        source.setdefault(d, "Common Crawl (.ug)")
    for r in read_csv(os.path.join(BUILD, "osm_candidates.csv")):
        if r["domain"]:
            source.setdefault(r["domain"], "OpenStreetMap")
    for line in lines(os.path.join(BUILD, "gh_orgs.tsv")):
        parts = line.split("\t")
        if len(parts) > 2 and parts[2]:
            source.setdefault(domain_of(parts[2]), "GitHub org")
    source = {d: s for d, s in source.items() if d and "." in d and not d.endswith(SKIP_HOSTS)}

    known = set(lines(os.path.join(STATE, "seen_domains.txt")))
    for f in ("companies.csv", "unverified.csv"):
        known |= {r["domain"] for r in read_csv(os.path.join(DATA, f)) if r["domain"]}
    todo = sorted(d for d in source if d not in known)

    os.makedirs(BUILD, exist_ok=True)
    with open(os.path.join(BUILD, "to_fetch.txt"), "w") as f:
        f.write("\n".join(todo))
    with open(os.path.join(BUILD, "source_map.tsv"), "w") as f:
        f.writelines(f"{d}\t{s}\n" for d, s in source.items())
    print(f"{len(source)} candidate domains, {len(todo)} not seen before")


if __name__ == "__main__":
    main()
