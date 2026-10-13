"""Combine the technology signals into data/tech.csv, one row per company that has any.

Inputs (each optional, so a failed collector leaves the previous values in place):
  build/gh_languages.json (harvest_github.py), build/web_tech.json (fingerprint.py), build/dns.json (dns_signals.py)
"""

import json
import os

from common import BUILD, DATA, domain_of, norm, read_csv, write_csv

TECH_FIELDS = [
    "name",
    "domain",
    "github_languages",
    "web_tech",
    "email_provider",
    "hosting",
    "hosting_country",
    "careers_tech",
]


def load(name):
    path = os.path.join(BUILD, name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def counts(counter):
    """{"Python": 4, "PHP": 2} -> "Python:4; PHP:2" (most used first)."""
    return "; ".join(f"{k}:{v}" for k, v in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0])))


def github_languages(gh, companies):
    """Language -> developer count per company, plus repository counts from the company's own GitHub org."""
    by_key = {norm(r["name"]): r["name"] for r in companies}
    by_domain = {r["domain"]: r["name"] for r in companies if r["domain"]}
    out = {}
    for employer, langs in gh.get("employers", {}).items():
        name = by_key.get(norm(employer))
        if name:
            merged = out.setdefault(name, {})
            for lang, n in langs.items():
                merged[lang] = merged.get(lang, 0) + n
    for org in gh.get("orgs", []):
        name = by_domain.get(domain_of(org["website"])) or by_key.get(norm(org["name"]))
        if name:
            merged = out.setdefault(name, {})
            for lang, n in org["languages"].items():
                merged[lang] = max(merged.get(lang, 0), n)
    return {name: counts(langs) for name, langs in out.items()}


def main():
    companies = [r for f in ("companies.csv", "unverified.csv") for r in read_csv(os.path.join(DATA, f))]
    path = os.path.join(DATA, "tech.csv")
    previous = {r["name"]: r for r in read_csv(path)} if os.path.exists(path) else {}
    gh, web, dns = load("gh_languages.json"), load("web_tech.json"), load("dns.json")
    langs = github_languages(gh, companies) if gh is not None else None

    rows = []
    for c in companies:
        row = {
            **dict.fromkeys(TECH_FIELDS, ""),
            **previous.get(c["name"], {}),
            "name": c["name"],
            "domain": c["domain"],
        }
        if langs is not None:
            row["github_languages"] = langs.get(c["name"], "")
        if web is not None:
            w = web.get(c["domain"], {}) if c["domain"] else {}
            row["web_tech"] = "; ".join(w.get("web_tech", []))
            row["careers_tech"] = "; ".join(w.get("careers_tech", []))
        if dns is not None:
            d = dns.get(c["domain"], {}) if c["domain"] else {}
            for k in ("email_provider", "hosting", "hosting_country"):
                row[k] = d.get(k, "")
        if any(row[k] for k in TECH_FIELDS[2:]):
            rows.append(row)
    rows.sort(key=lambda r: r["name"].lower())
    write_csv(path, rows, TECH_FIELDS)
    print(f"tech.csv: {len(rows)} companies with signals")


if __name__ == "__main__":
    main()
