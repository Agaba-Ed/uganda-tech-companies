"""Collect every .ug domain seen in recent Common Crawl snapshots.

Reads the snapshot's cluster.idx (the secondary index), finds the blocks whose keys start with
"ug," and downloads only those blocks of the CDX index. Output: build/cc_domains.txt

usage: python scripts/harvest_commoncrawl.py [--crawls 2]
"""
import argparse
import gzip
import json
import os
import urllib.request

from common import BUILD

BASE = "https://data.commoncrawl.org/cc-index/collections"
SKIP_SLD = (".go.ug", ".ac.ug", ".sc.ug", ".mil.ug")  # government, universities, schools
SLD = {"co", "ac", "or", "go", "ne", "sc", "com", "org", "mil"}
UA = {"User-Agent": "uganda-tech-companies (+https://github.com/Agaba-Ed/uganda-tech-companies)"}


def get(url, byte_range=None, timeout=300):
    headers = dict(UA)
    if byte_range:
        headers["Range"] = "bytes=%d-%d" % byte_range
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
        return r.read()


def registrable(surt_host):
    parts = list(reversed(surt_host.split(",")))
    if len(parts) >= 3 and parts[-2] in SLD:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def harvest(crawl):
    lines = get(f"{BASE}/{crawl}/indexes/cluster.idx", timeout=900).decode().splitlines()
    idx = [i for i, l in enumerate(lines) if l.startswith(("ug,", "ug)"))]
    if not idx:
        return set()
    hosts = set()
    for line in lines[max(idx[0] - 1, 0): idx[-1] + 1]:
        _, cdx_file, offset, length, _ = line.split("\t")
        raw = get(f"{BASE}/{crawl}/indexes/{cdx_file}", (int(offset), int(offset) + int(length) - 1))
        for rec in gzip.decompress(raw).decode(errors="ignore").splitlines():
            key = rec.split(" ", 1)[0]
            if key.startswith(("ug,", "ug)")):
                hosts.add(key.split(")", 1)[0])
    return {registrable(h) for h in hosts if "," in h}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crawls", type=int, default=2, help="how many of the latest snapshots to read")
    args = ap.parse_args()
    crawls = [c["id"] for c in json.loads(get("https://index.commoncrawl.org/collinfo.json", timeout=60))][: args.crawls]
    domains = set()
    for c in crawls:
        try:
            found = harvest(c)
        except Exception as e:  # one bad snapshot should not sink the run
            print(f"{c}: failed ({e})")
            continue
        print(f"{c}: {len(found)} domains")
        domains |= found
    domains = sorted(d for d in domains if not d.endswith(SKIP_SLD))
    os.makedirs(BUILD, exist_ok=True)
    with open(os.path.join(BUILD, "cc_domains.txt"), "w") as f:
        f.write("\n".join(domains))
    print(f"total commercial .ug domains: {len(domains)}")


if __name__ == "__main__":
    main()
