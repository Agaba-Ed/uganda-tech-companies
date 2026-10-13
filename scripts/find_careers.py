"""Find a careers page for every company that has a website but no careers_page yet.

Looks for a careers/jobs link (or a hosted job board) on the homepage, then tries common paths
such as /careers. A probed path only counts if it is not redirected away and reads like a jobs page.
Updates data/companies.csv and data/unverified.csv in place.

usage: python scripts/find_careers.py [--workers 32]
"""

import argparse
import html
import http.client
import logging
import os
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlsplit

from common import DATA, clean_row, read_csv, write_csv
from fetch_homepages import INSECURE, UA

LOG = logging.getLogger(__name__)

ANCHOR = re.compile(r"<a\b[^>]*?href=[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", re.I | re.S)
# the last part of the link's path must itself be a careers page name, not a blog post that mentions careers
CAREER_SLUG = re.compile(
    r"^(careers?|jobs?|vacanc(y|ies)|join-?us|join-?our-?team|work-?with-?us|we-?are-?hiring|hiring|"
    r"opportunities|careers?-?(and|&)-?jobs|current-?(openings|vacancies)|open-?positions)(\.\w{2,5})?$",
    re.I,
)
CAREER_TEXT = re.compile(
    r"^\s*(careers?|jobs?|vacanc(y|ies)|join (us|our team)|work with us|we.?re hiring|open (roles|positions))\b", re.I
)
JOB_BOARD = re.compile(
    r"lever\.co|greenhouse\.io|workable\.com|bamboohr\.com|zohorecruit|breezy\.hr|recruitee\.com|"
    r"teamtailor\.com|smartrecruiters\.com|myworkdayjobs\.com|ashbyhq\.com|personio\.",
    re.I,
)
SOCIAL = re.compile(r"facebook\.|twitter\.|x\.com|instagram\.|youtube\.|tiktok\.|wa\.me|whatsapp|mailto:|tel:", re.I)
PATHS = ["/careers", "/careers/", "/jobs", "/vacancies", "/join-us", "/work-with-us"]
JOBS_PAGE = re.compile(r"career|job|vacanc|opening|position|join (us|our team)|hiring|recruit", re.I)


def get(url):
    """(final_url, html) or None. Verified TLS first, unverified only as a fallback."""
    for ctx in (None, INSECURE):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
                return r.geturl(), r.read(500_000).decode("utf-8", errors="ignore")
        except (OSError, ValueError, http.client.HTTPException) as e:
            LOG.debug("%s: %s", url, e)
    return None


def same_site(url, base):
    host, site = (urlsplit(u).netloc.lower().removeprefix("www.") for u in (url, base))
    return host == site or host.endswith("." + site)


def careers_link(url, label, base):
    """True if a homepage link points at the company's own careers page or its hosted job board."""
    if JOB_BOARD.search(urlsplit(url).netloc):
        return True
    if not same_site(url, base):
        return False
    slug = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]
    host = urlsplit(url).netloc.lower()
    return bool(CAREER_SLUG.match(slug) or (host.startswith(("careers.", "jobs.")) and slug == "")) or (
        bool(CAREER_TEXT.search(label)) and bool(CAREER_SLUG.match(slug) or re.search(r"career|job|vacanc", url, re.I))
    )


def link_on_homepage(base, page):
    for raw, label in ANCHOR.findall(page):
        href = html.unescape(raw.strip())
        if SOCIAL.search(href):
            continue
        url = urljoin(base, href)
        if careers_link(url, re.sub(r"<[^>]+>|\s+", " ", label), base):
            return url
    return ""


def probe_paths(base):
    host = urlsplit(base).netloc.removeprefix("www.")
    for path in PATHS:
        got = get(urljoin(base, path))
        if not got:
            continue
        final, page = got
        moved = urlsplit(final)
        if moved.netloc.removeprefix("www.") != host or moved.path.strip("/") == "":
            continue  # redirected to the homepage or another site
        title = re.search(r"(?is)<title[^>]*>(.*?)</title>", page)
        heading = re.search(r"(?is)<h1[^>]*>(.*?)</h1>", page)
        text = " ".join(m.group(1) for m in (title, heading) if m)
        if JOBS_PAGE.search(text) and not re.search(r"not found|404|page.{0,20}exist", text, re.I):
            return final
    return ""


def find(website):
    got = get(website)
    if not got:
        return ""
    base, page = got
    return link_on_homepage(base, page) or probe_paths(base)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=32)
    args = ap.parse_args()
    files = {f: read_csv(os.path.join(DATA, f)) for f in ("companies.csv", "unverified.csv")}
    todo = [r for rows in files.values() for r in rows if r["website"] and not r["careers_page"]]
    with ThreadPoolExecutor(args.workers) as pool:
        for row, url in zip(todo, pool.map(lambda r: find(r["website"]), todo), strict=True):
            row["careers_page"] = url
    for fname, rows in files.items():
        for r in rows:
            clean_row(r)
        write_csv(os.path.join(DATA, fname), rows)
    found = sum(1 for r in todo if r["careers_page"])
    print(f"checked {len(todo)} websites, found {found} new careers pages")


if __name__ == "__main__":
    main()
