"""Check the data files before they are merged. Exits non-zero on any problem."""

import os
import re
import sys

from build_tech import TECH_FIELDS
from common import CONFIDENCE, DATA, FIELDS, GENERIC_EMAIL, norm, read_csv

URL = re.compile(r"^https?://[^\s/$.?#][^\s]*$", re.I)


def check_row(r):
    """Problems with a single row, independent of the rest of the data."""
    problems = []
    if not r["name"].strip():
        problems.append("empty name")
    if r["confidence"] not in CONFIDENCE:
        problems.append(f"confidence must be one of {CONFIDENCE}")
    problems += [f"{col} is not a URL" for col in ("website", "careers_page") if r[col] and not URL.match(r[col])]
    if r["github_devs"] and not r["github_devs"].isdigit():
        problems.append("github_devs must be a number")
    problems += [
        f"only role addresses (info@, careers@, ...) are allowed, not {e}"
        for e in filter(None, (x.strip() for x in r["email"].split(";")))
        if not GENERIC_EMAIL.match(e)
    ]
    return problems


def check_file(fname, seen_names, seen_domains):
    path = os.path.join(DATA, fname)
    with open(path, encoding="utf-8") as f:
        header = f.readline().strip().split(",")
    if header != FIELDS:
        return [f"{fname}: header must be {','.join(FIELDS)}"]
    errors = []
    for i, r in enumerate(read_csv(path), start=2):
        where = f"{fname}:{i} ({r['name']})"
        errors += [f"{where}: {p}" for p in check_row(r)]
        key = norm(r["name"])
        if key in seen_names:
            errors.append(f"{where}: duplicate of {seen_names[key]}")
        if r["domain"] in seen_domains:
            errors.append(f"{where}: domain {r['domain']} already used by {seen_domains[r['domain']]}")
        if key:
            seen_names.setdefault(key, where)
        if r["domain"]:
            seen_domains.setdefault(r["domain"], where)
    return errors


def check_tech(names):
    """tech.csv must have the expected header and only describe companies that are in the data files."""
    path = os.path.join(DATA, "tech.csv")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        if f.readline().strip().split(",") != TECH_FIELDS:
            return [f"tech.csv: header must be {','.join(TECH_FIELDS)}"]
    return [
        f"tech.csv:{i} ({r['name']}): not in companies.csv or unverified.csv"
        for i, r in enumerate(read_csv(path), start=2)
        if r["name"] not in names
    ]


def main():
    seen_names, seen_domains = {}, {}
    errors = [e for fname in ("companies.csv", "unverified.csv") for e in check_file(fname, seen_names, seen_domains)]
    names = {r["name"] for fname in ("companies.csv", "unverified.csv") for r in read_csv(os.path.join(DATA, fname))}
    errors += check_tech(names)
    for e in errors:
        print(e)
    print(f"{len(errors)} problem(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
