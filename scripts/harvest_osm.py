"""Collect company, IT and telecom offices and computer shops in Uganda from OpenStreetMap.

OpenStreetMap data is © OpenStreetMap contributors, available under the ODbL.
Output: build/osm_candidates.csv
"""

import json
import os
import re
import urllib.parse
import urllib.request

from common import BUILD, domain_of, write_csv

ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter"]
QUERY = """[out:json][timeout:170];area["ISO3166-1"="UG"]->.a;
(nwr["office"](area.a);nwr["shop"="computer"](area.a););out tags center;"""
KEEP_OFFICE = {
    "company",
    "it",
    "telecommunication",
    "yes",
    "consulting",
    "financial",
    "coworking",
    "research",
    "engineer",
}
TECH_NAME = re.compile(
    r"tech|soft|digital|\bict\b|\bit\b|system|comput|data|cyber|network|telecom|cloud|web|"
    r"\bapps?\b|innovat|electronic|hub|labs?\b|code|dev",
    re.I,
)
FIELDS = ["name", "website", "domain", "office", "email", "location", "tech_named"]


def fetch():
    data = urllib.parse.urlencode({"data": QUERY}).encode()
    for url in ENDPOINTS:
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "uganda-tech-companies"})
            with urllib.request.urlopen(req, timeout=200) as r:
                return json.loads(r.read())["elements"]
        except Exception as e:
            print(f"{url}: {e}")
    raise SystemExit("all Overpass endpoints failed")


def main():
    rows = []
    for el in fetch():
        t = el.get("tags", {})
        office, shop, name = t.get("office", ""), t.get("shop", ""), t.get("name", "").strip()
        if not name or not (office in KEEP_OFFICE or shop == "computer"):
            continue
        web = t.get("website") or t.get("contact:website") or ""
        techy = bool(TECH_NAME.search(name)) or office in ("it", "telecommunication") or shop == "computer"
        if not (techy or web):
            continue
        rows.append(
            {
                "name": name,
                "website": web,
                "domain": domain_of(web),
                "office": office or f"shop={shop}",
                "email": t.get("email") or t.get("contact:email") or "",
                "location": ", ".join(x for x in (t.get("addr:street", ""), t.get("addr:city", "")) if x),
                "tech_named": "yes" if techy else "",
            }
        )
    write_csv(os.path.join(BUILD, "osm_candidates.csv"), rows, FIELDS)
    print(f"osm candidates: {len(rows)}")


if __name__ == "__main__":
    main()
