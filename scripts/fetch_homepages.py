"""Download the homepage of each domain (first 1 MB) so it can be classified.

usage: python scripts/fetch_homepages.py <domains.txt> [--workers 32]
Output: build/html/<domain>.html and build/fetch_log.tsv (domain, status, final_url)
"""
import argparse
import os
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from common import BUILD

HTML = os.path.join(BUILD, "html")
UA = "Mozilla/5.0 (compatible; uganda-tech-companies/1.0; +https://github.com/Agaba-Ed/uganda-tech-companies)"
# Many small Ugandan sites have expired or self-signed certificates; we only read public homepages.
INSECURE = ssl.create_default_context()
INSECURE.check_hostname = False
INSECURE.verify_mode = ssl.CERT_NONE


def fetch(domain):
    path = os.path.join(HTML, domain + ".html")
    if os.path.exists(path) and os.path.getsize(path):
        return domain, "200", ""
    for url in (f"https://{domain}/", f"https://www.{domain}/", f"http://{domain}/", f"http://www.{domain}/"):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20, context=INSECURE) as r:
                body = r.read(1_000_000)
                with open(path, "wb") as f:
                    f.write(body)
                return domain, str(r.status), r.geturl()
        except Exception:
            continue
    return domain, "000", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("domains")
    ap.add_argument("--workers", type=int, default=32)
    args = ap.parse_args()
    os.makedirs(HTML, exist_ok=True)
    domains = [d.strip() for d in open(args.domains) if d.strip()]
    ok = 0
    with ThreadPoolExecutor(args.workers) as pool, open(os.path.join(BUILD, "fetch_log.tsv"), "a") as log:
        for domain, status, final in pool.map(fetch, domains):
            log.write(f"{domain}\t{status}\t{final}\n")
            ok += status != "000"
    print(f"fetched {ok}/{len(domains)}")


if __name__ == "__main__":
    main()
