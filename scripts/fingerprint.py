"""Detect what each company's website is built and served with, and which technologies its careers
page mentions.

Signatures are matched against the homepage HTML, response headers and cookies. They describe the public
website, which is not always the stack of the company's own products.
Output: build/web_tech.json ({domain: {"web_tech": [...], "https": bool, "careers_tech": [...]}})

usage: python scripts/fingerprint.py [--workers 32]
"""

import argparse
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor

from common import BUILD, DATA, read_csv, tech_terms
from fetch_homepages import INSECURE, open_url

# name -> (where, pattern); where is "html", "header" (all headers as "name: value" lines) or "cookie"
SIGNATURES = {
    # content management and site builders
    "WordPress": ("html", r"/wp-content/|/wp-includes/|<meta[^>]+generator[^>]+wordpress"),
    "WooCommerce": ("html", r"woocommerce"),
    "Elementor": ("html", r"elementor"),
    "Joomla": ("html", r"<meta[^>]+generator[^>]+joomla|/media/jui/|/components/com_"),
    "Drupal": ("html", r"<meta[^>]+generator[^>]+drupal|/sites/default/files/|drupal-settings-json"),
    "Wix": ("html", r"static\.wixstatic\.com|<meta[^>]+generator[^>]+wix\.com"),
    "Squarespace": ("html", r"static1\.squarespace\.com|squarespace-cdn"),
    "Webflow": ("html", r"<html[^>]+data-wf-(page|site)|assets\.website-files\.com"),
    "Shopify": ("html", r"cdn\.shopify\.com|shopify\.theme"),
    "Blogger": ("html", r"<meta[^>]+generator[^>]+blogger"),
    # frameworks
    "Next.js": ("html", r"__NEXT_DATA__|/_next/static/"),
    "Nuxt": ("html", r"__NUXT__|/_nuxt/"),
    "Gatsby": ("html", r"___gatsby|<meta[^>]+generator[^>]+gatsby"),
    "Angular": ("html", r"\sng-version=|<app-root"),
    "Vue": ("html", r"\sdata-v-[0-9a-f]{6,}|data-server-rendered"),
    "React": ("html", r"data-reactroot|react-dom(\.production)?(\.min)?\.js|id=\"root\"></div>"),
    "Svelte": ("html", r"svelte-[a-z0-9]{5,}|__sveltekit"),
    "Laravel": ("cookie", r"laravel_session"),
    "Django": ("cookie", r"\bcsrftoken="),
    "ASP.NET": ("header", r"x-aspnet-version|x-powered-by: asp\.net|asp\.net_sessionid"),
    "PHP": ("header", r"x-powered-by: php|phpsessid"),
    "Express": ("header", r"x-powered-by: express"),
    "Bootstrap": ("html", r"bootstrap(\.min)?\.(css|js)"),
    "Tailwind CSS": ("html", r"tailwindcss|tailwind(\.min)?\.css|--tw-"),
    # web servers, hosts and CDNs
    "Cloudflare": ("header", r"^cf-ray:|^server: cloudflare"),
    "Vercel": ("header", r"^x-vercel-id:|^server: vercel"),
    "Netlify": ("header", r"^x-nf-request-id:|^server: netlify"),
    "nginx": ("header", r"^server: nginx"),
    "Apache": ("header", r"^server: apache"),
    "LiteSpeed": ("header", r"^server: litespeed"),
    "Microsoft IIS": ("header", r"^server: microsoft-iis"),
    "Amazon CloudFront": ("header", r"^x-amz-cf-id:|^via: .*cloudfront"),
    "GitHub Pages": ("header", r"^server: github\.com"),
    # analytics and widgets
    "Google Analytics": ("html", r"googletagmanager\.com/gtag|google-analytics\.com|gtag\('config'"),
    "Google Tag Manager": ("html", r"googletagmanager\.com/gtm\.js"),
    "Meta Pixel": ("html", r"connect\.facebook\.net/[^\"']+/fbevents\.js"),
    "Tawk.to": ("html", r"embed\.tawk\.to"),
    "Hotjar": ("html", r"static\.hotjar\.com"),
}
COMPILED = {name: (where, re.compile(pattern, re.I | re.M)) for name, (where, pattern) in SIGNATURES.items()}


def get(url):
    for ctx in (None, INSECURE):
        got = open_url(url, ctx, limit=600_000, timeout=15)
        if got:
            return got
    return None


def detect(headers, html):
    header_text = "\n".join(f"{k.lower()}: {v.lower()}" for k, v in headers.items())
    cookies = " ".join(headers.get_all("Set-Cookie") or []).lower()
    found = [
        name
        for name, (where, rx) in COMPILED.items()
        if rx.search({"html": html, "header": header_text, "cookie": cookies}[where])
    ]
    if "Next.js" in found or "Gatsby" in found:
        found = [x for x in found if x != "React"]  # implied
    return found


def visible(html):
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def inspect(row):
    out = {}
    got = get(row["website"])
    if got:
        _, final, headers, body = got
        out["web_tech"] = detect(headers, body.decode("utf-8", errors="ignore"))
        out["https"] = final.lower().startswith("https://")
    if row["careers_page"]:
        page = get(row["careers_page"])
        if page:
            out["careers_tech"] = tech_terms(visible(page[3].decode("utf-8", errors="ignore")))
    return row["domain"], out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=32)
    args = ap.parse_args()
    rows = {
        r["domain"]: r
        for fname in ("companies.csv", "unverified.csv")
        for r in read_csv(os.path.join(DATA, fname))
        if r["website"] and r["domain"]
    }
    with ThreadPoolExecutor(args.workers) as pool:
        results = {d: out for d, out in pool.map(inspect, rows.values()) if out}
    os.makedirs(BUILD, exist_ok=True)
    with open(os.path.join(BUILD, "web_tech.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, sort_keys=True)
    reached = sum(1 for r in results.values() if "web_tech" in r)
    print(
        f"websites: {len(rows)}, reached: {reached}, careers pages read: {sum('careers_tech' in r for r in results.values())}"
    )


if __name__ == "__main__":
    main()
