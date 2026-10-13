"""Download the homepage of each domain (first 1 MB) so it can be classified.

usage: python scripts/fetch_homepages.py <domains.txt> [--workers 32]
Output: build/html/<domain>.html and build/fetch_log.tsv (domain, status, final_url)
"""

import argparse
import http.client
import logging
import os
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from common import BUILD

LOG = logging.getLogger(__name__)

HTML = os.path.join(BUILD, "html")
UA = "Mozilla/5.0 (compatible; uganda-tech-companies/1.0; +https://github.com/Agaba-Ed/uganda-tech-companies)"
# Many small Ugandan sites have expired or self-signed certificates. Verified TLS is always tried
# first; the unverified context is only a fallback for reading a public homepage, and nothing is sent.
INSECURE = ssl.create_default_context()
INSECURE.check_hostname = False
INSECURE.verify_mode = ssl.CERT_NONE


def fetch(domain):
    path = os.path.join(HTML, domain + ".html")
    if os.path.exists(path) and os.path.getsize(path):
        return domain, "200", ""
    attempts = [(f"https://{host}/", ctx) for host in (domain, f"www.{domain}") for ctx in (None, INSECURE)]
    attempts += [(f"http://{host}/", None) for host in (domain, f"www.{domain}")]
    for url, ctx in attempts:
        result = try_fetch(url, ctx, path)
        if result:
            return (domain, *result)
    return domain, "000", ""


def open_url(url, ctx=None, limit=1_000_000, timeout=20):
    """(status, final_url, headers, body) or None. Pass ctx=INSECURE only as a fallback."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return str(r.status), r.geturl(), r.headers, r.read(limit)
    except (OSError, ValueError, http.client.HTTPException) as e:  # URLError, TLS and socket errors are OSErrors
        LOG.debug("%s: %s", url, e)
        return None


def try_fetch(url, ctx, path):
    got = open_url(url, ctx)
    if not got:
        return None
    status, final, _, body = got
    with open(path, "wb") as f:
        f.write(body)
    return status, final


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("domains")
    ap.add_argument("--workers", type=int, default=32)
    args = ap.parse_args()
    os.makedirs(HTML, exist_ok=True)
    with open(args.domains, encoding="utf-8") as f:
        domains = [d.strip() for d in f if d.strip()]
    ok = 0
    with ThreadPoolExecutor(args.workers) as pool, open(os.path.join(BUILD, "fetch_log.tsv"), "a") as log:
        for domain, status, final in pool.map(fetch, domains):
            log.write(f"{domain}\t{status}\t{final}\n")
            ok += status != "000"
    print(f"fetched {ok}/{len(domains)}")


if __name__ == "__main__":
    main()
