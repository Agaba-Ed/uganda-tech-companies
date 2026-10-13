"""Summarise the dataset into data/insights.json for the Insights page and anyone reusing the numbers.

Breakdowns cover the confident list (data/companies.csv). Each one carries `n`, the number of companies it
is based on, so a reader can tell how much of the list the numbers describe.
"""

import datetime as dt
import json
import os
from collections import Counter

from common import DATA, read_csv

CMS = ["WordPress", "Wix", "Joomla", "Drupal", "Shopify", "Webflow", "Squarespace", "Blogger"]
FRAMEWORKS = [
    "Next.js",
    "React",
    "Nuxt",
    "Vue",
    "Angular",
    "Gatsby",
    "Svelte",
    "Laravel",
    "Django",
    "ASP.NET",
    "Express",
]
DELIVERY = ["Cloudflare", "nginx", "Apache", "LiteSpeed", "Microsoft IIS", "Vercel", "Netlify", "Amazon CloudFront"]
ANALYTICS = ["Google Analytics", "Google Tag Manager", "Meta Pixel", "Tawk.to", "Hotjar"]
TOP = 12


def split(value, sep="; "):
    return [x for x in (value or "").split(sep) if x]


def ranked(counter, top=TOP):
    return [{"label": k, "count": v} for k, v in counter.most_common(top)]


def breakdown(counter, n, top=TOP):
    return {"n": n, "items": ranked(counter, top)}


def domain_kind(domain):
    if not domain:
        return "No website"
    if domain.endswith(".ug"):
        return ".ug"
    if domain.endswith(".com"):
        return ".com"
    return "Other"


def city(location):
    place = location.split(", ")[-1].strip() if location else ""
    return "" if place.lower() in ("", "uganda") else place


def web_section(sites):
    n = len(sites)
    used = Counter(t for techs in sites for t in techs)
    has_cms = Counter(next((c for c in CMS if c in techs), "Custom-built / other") for techs in sites)
    return {
        "n": n,
        "platform": breakdown(has_cms, n),
        "frameworks": breakdown(Counter({k: used[k] for k in FRAMEWORKS if used[k]}), n),
        "delivery": breakdown(Counter({k: used[k] for k in DELIVERY if used[k]}), n),
        "analytics": breakdown(Counter({k: used[k] for k in ANALYTICS if used[k]}), n),
    }


def hosting_section(rows):
    hosted = [r for r in rows if r["hosting"]]
    where = Counter(
        "Behind Cloudflare"
        if r["hosting"] == "Cloudflare"
        else "In Uganda"
        if r["hosting_country"] == "UG"
        else "Abroad"
        for r in hosted
    )
    countries = Counter(r["hosting_country"] for r in hosted if r["hosting_country"] and r["hosting_country"] != "UG")
    return {
        "n": len(hosted),
        "where": breakdown(where, len(hosted)),
        "hosts": breakdown(Counter(r["hosting"] for r in hosted), len(hosted)),
        "countries_abroad": breakdown(countries, sum(countries.values())),
    }


def languages_section(rows):
    with_langs = [dict(x.rsplit(":", 1) for x in split(r["github_languages"])) for r in rows if r["github_languages"]]
    by_company = Counter(lang for langs in with_langs for lang in langs)
    by_developers = Counter()
    for langs in with_langs:
        for lang, count in langs.items():
            by_developers[lang] += int(count)
    return {
        "n": len(with_langs),
        "by_company": breakdown(by_company, len(with_langs)),
        "by_usage": breakdown(by_developers, len(with_langs)),
    }


def main():
    companies = read_csv(os.path.join(DATA, "companies.csv"))
    unverified = read_csv(os.path.join(DATA, "unverified.csv"))
    names = {r["name"] for r in companies}
    tech = [r for r in read_csv(os.path.join(DATA, "tech.csv")) if r["name"] in names]
    web = {r["name"]: split(r["web_tech"]) for r in tech if r["web_tech"]}
    n = len(companies)

    sectors = Counter(s for r in companies for s in r["sector"].split(" · ") if s)
    cities = Counter(c for r in companies if (c := city(r["location"])))
    careers = [r for r in tech if r["careers_tech"]]
    mail = [r for r in tech if r["email_provider"]]
    insights = {
        "generated_at": dt.date.today().isoformat(),
        "totals": {
            "companies": n,
            "unverified": len(unverified),
            "with_website": sum(1 for r in companies if r["website"]),
            "with_careers_page": sum(1 for r in companies if r["careers_page"]),
            "on_github": sum(1 for r in companies if r["github_devs"]),
            "github_profiles": sum(int(r["github_devs"] or 0) for r in companies),
        },
        "sectors": breakdown(sectors, sum(1 for r in companies if r["sector"]), top=20),
        "cities": breakdown(cities, sum(1 for r in companies if city(r["location"]))),
        "domains": breakdown(Counter(domain_kind(r["domain"]) for r in companies), n),
        "github_languages": languages_section(tech),
        "web": web_section(list(web.values())),
        "email": breakdown(Counter(r["email_provider"] for r in mail), len(mail)),
        "hosting": hosting_section(tech),
        "careers_tech": breakdown(Counter(t for r in careers for t in split(r["careers_tech"])), len(careers)),
    }
    with open(os.path.join(DATA, "insights.json"), "w", encoding="utf-8") as f:
        json.dump(insights, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"insights.json: {n} companies, {len(tech)} with technology signals")


if __name__ == "__main__":
    main()
