"""Collect tech businesses from the yellow.ug business directory, category by category.

Starts from a few tech categories, follows related categories whose names look tech-related,
walks every results page, and reads each company's profile for its website. Respects robots.txt
(only /category/ and /company/ pages) and waits between requests.
Output: build/yellow_candidates.csv
"""

import argparse
import html
import os
import re
import time
import urllib.request

from common import BUILD, domain_of, write_csv

BASE = "https://www.yellow.ug"
UA = "Mozilla/5.0 (compatible; uganda-tech-companies/1.0; +https://github.com/Agaba-Ed/uganda-tech-companies)"
SEEDS = [
    "computers-internet",
    "communications",
    "sms-services",
    "software",
    "it-services",
    "internet-service-providers",
    "web-design",
    "web-hosting",
    "computer-software",
    "computer-services",
    "telecommunications",
    "mobile-money",
    "payment-solutions",
    "information-technology",
    "cyber-security",
    "data-centres",
    "digital-marketing",
]
TECH = re.compile(
    r"software|comput|internet|web|sms|telecom|network|data|cyber|digital|technolog|\bict\b|hosting|"
    r"\bapps?\b|mobile|payment|fintech|cctv|online|cloud|commerce|programm|ussd|\bisp\b|fib(re|er)|"
    r"satellite|gps|tracking|biometric|point-of-sale|\bpos\b|robot|artificial|wireless|gsm|"
    r"information|\bit\b|e-learning|electronic",
    re.I,
)
# categories that match the keywords above but are not tech businesses
SKIP = re.compile(
    r"broadcast|radio|television|tv-|newspaper|printing|stationery|repair|phone-shops|"
    r"mobile-phone-dealers|electronics-shop|electrical",
    re.I,
)
FIELDS = ["name", "website", "domain", "city", "tagline", "established", "category", "profile"]


def get(path, delay):
    time.sleep(delay)
    req = urllib.request.Request(BASE + path, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", errors="ignore")
        except Exception:
            time.sleep(5 * (attempt + 1))
    return ""


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def parse_listing(page, category):
    rows = []
    for block in re.split(r'<div class="company[ "]', page)[1:]:
        m = re.search(r'<h3>[^<]*<a href="(/company/\d+/[^"]+)">(.*?)</a>', block, re.S)
        if not m:
            continue
        city = re.search(r'<div class="address">(.*?)</div>', block, re.S)
        tag = re.search(r'<div class="tagline">(.*?)</div>', block, re.S)
        est = re.search(r"(\d{4}) Established", block)
        rows.append(
            {
                "name": text(m.group(2)),
                "profile": BASE + m.group(1),
                "category": category,
                "city": text(re.search(r"<b>(.*?)</b>", city.group(1)).group(1))
                if city and "<b>" in city.group(1)
                else "",
                "tagline": text(tag.group(1)) if tag else "",
                "established": est.group(1) if est else "",
            }
        )
    return rows


def related_categories(page, seen, queue):
    found = re.findall(r'href="/category/([a-z0-9-]+)"', page)
    return [
        c
        for c in dict.fromkeys(found)
        if c not in seen and c not in queue and TECH.search(c.replace("-", " ")) and not SKIP.search(c)
    ]


def crawl_category(cat, delay, companies):
    """Walk every results page of one category; return the related categories it links to."""
    related, page_no, path = [], 1, f"/category/{cat}"
    while path:
        page = get(path, delay)
        if not page:
            break
        for row in parse_listing(page, cat):
            companies.setdefault(row["profile"], row)
        related.append(page)
        page_no += 1
        path = f"/category/{cat}/{page_no}" if f'href="/category/{cat}/{page_no}"' in page else None
    return related


def crawl_categories(delay, max_categories):
    queue, seen, companies = list(SEEDS), set(), {}
    while queue and len(seen) < max_categories:
        cat = queue.pop(0)
        if cat in seen:
            continue
        seen.add(cat)
        for page in crawl_category(cat, delay, companies):
            queue += related_categories(page, seen, queue)
        print(f"{cat}: {len(companies)} companies so far", flush=True)
    return list(companies.values()), len(seen)


def profile_website(page):
    """The website is shown as plain text in the profile's contact block."""
    m = re.search(r'<div class="text weblinks">\s*<a[^>]*>([^<]+)</a>', page)
    if not m:
        return ""
    url = m.group(1).strip()
    return url if url.startswith("http") else "https://" + url


def add_websites(rows, delay):
    for i, row in enumerate(rows, 1):
        row["website"] = profile_website(get(row["profile"].removeprefix(BASE), delay))
        row["domain"] = domain_of(row["website"])
        if i % 50 == 0:
            print(f"profiles: {i}/{len(rows)}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--max-categories", type=int, default=80)
    ap.add_argument("--no-profiles", action="store_true", help="skip profile pages (no websites)")
    args = ap.parse_args()
    rows, n_categories = crawl_categories(args.delay, args.max_categories)
    if not args.no_profiles:
        add_websites(rows, args.delay)
    write_csv(os.path.join(BUILD, "yellow_candidates.csv"), rows, FIELDS)
    print(
        f"categories: {n_categories}, companies: {len(rows)}, with website: {sum(1 for r in rows if r.get('website'))}"
    )


if __name__ == "__main__":
    main()
