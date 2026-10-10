"""Check the data files before they are merged. Exits non-zero on any problem."""
import os
import re
import sys

from common import CONFIDENCE, DATA, FIELDS, GENERIC_EMAIL, norm, read_csv

URL = re.compile(r"^https?://[^\s/$.?#][^\s]*$", re.I)


def main():
    errors = []
    seen_names, seen_domains = {}, {}
    for fname in ("companies.csv", "unverified.csv"):
        path = os.path.join(DATA, fname)
        with open(path, encoding="utf-8") as f:
            header = f.readline().strip().split(",")
        if header != FIELDS:
            errors.append(f"{fname}: header must be {','.join(FIELDS)}")
            continue
        for i, r in enumerate(read_csv(path), start=2):
            where = f"{fname}:{i} ({r['name']})"
            if not r["name"].strip():
                errors.append(f"{where}: empty name")
            if r["confidence"] not in CONFIDENCE:
                errors.append(f"{where}: confidence must be one of {CONFIDENCE}")
            for col in ("website", "careers_page"):
                if r[col] and not URL.match(r[col]):
                    errors.append(f"{where}: {col} is not a URL")
            if r["github_devs"] and not r["github_devs"].isdigit():
                errors.append(f"{where}: github_devs must be a number")
            for e in filter(None, (x.strip() for x in r["email"].split(";"))):
                if not GENERIC_EMAIL.match(e):
                    errors.append(f"{where}: only role addresses (info@, careers@, ...) are allowed, not {e}")
            key = norm(r["name"])
            if key and key in seen_names:
                errors.append(f"{where}: duplicate of {seen_names[key]}")
            seen_names.setdefault(key, where)
            if r["domain"]:
                if r["domain"] in seen_domains:
                    errors.append(f"{where}: domain {r['domain']} already used by {seen_domains[r['domain']]}")
                seen_domains.setdefault(r["domain"], where)
    for e in errors:
        print(e)
    print(f"{len(errors)} problem(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
