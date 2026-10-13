"""Look up each company domain's email provider (MX records) and where its website is hosted (the network
that announces the website's IP address, via Team Cymru's public IP-to-ASN DNS service).

Uses `dig`, which is available on macOS and the Ubuntu runners. The country is that of the IP block's
registration, which is a good approximation of where a site is served from, not an exact location.
Output: build/dns.json ({domain: {"email_provider", "hosting", "hosting_country"}})

usage: python scripts/dns_signals.py [--workers 16] [--resolver 1.1.1.1]
"""

import argparse
import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from functools import cache

from common import BUILD, DATA, read_csv

RESOLVER = "1.1.1.1"
MAIL = [
    (r"google\.com|googlemail\.com", "Google Workspace"),
    (r"outlook\.com|office365|microsoft", "Microsoft 365"),
    (r"zoho\.", "Zoho Mail"),
    (r"secureserver\.net", "GoDaddy"),
    (r"titan\.email", "Titan"),
    (r"hostinger", "Hostinger"),
    (r"protonmail|proton\.me", "Proton"),
    (r"mimecast", "Mimecast"),
    (r"pphosted|ppe-hosted", "Proofpoint"),
    (r"yandex", "Yandex"),
    (r"mailgun|sendgrid|amazonses", "Transactional service"),
]
HOSTS = [
    (r"amazon", "Amazon (AWS)"),
    (r"oracle", "Oracle Cloud"),
    (r"google", "Google Cloud"),
    (r"microsoft", "Microsoft Azure"),
    (r"cloudflare", "Cloudflare"),
    (r"digitalocean", "DigitalOcean"),
    (r"hetzner", "Hetzner"),
    (r"\bovh", "OVHcloud"),
    (r"akamai|linode", "Akamai (Linode)"),
    (r"vultr|choopa|constant", "Vultr"),
    (r"contabo", "Contabo"),
    (r"hostinger", "Hostinger"),
    (r"godaddy|go-daddy|secureserver", "GoDaddy"),
    (r"namecheap", "Namecheap"),
    (r"a2hosting|a2 hosting", "A2 Hosting"),
    (r"unified-?layer|bluehost|newfold|endurance", "Bluehost / Newfold"),
    (r"automattic", "WordPress.com"),
    (r"wix", "Wix"),
    (r"squarespace", "Squarespace"),
    (r"shopify", "Shopify"),
    (r"fastly", "Fastly"),
    (r"github", "GitHub"),
    (r"vercel", "Vercel"),
    (r"netlify", "Netlify"),
    (r"mtn", "MTN"),
    (r"airtel", "Airtel"),
    (r"liquid", "Liquid"),
    (r"raxio", "Raxio"),
    (r"roke", "Roke Telkom"),
    (r"africa ?online", "Africa Online"),
    (r"nation media|\bntv\b", "Nation Media"),
    (r"\buccl|ucom|utl\b|uganda telecom", "Uganda Telecom"),
    (r"research and education network for uganda", "RENU"),
    (r"\bnita\b|national information technology", "NITA-U"),
    (r"renu", "RENU"),
    (r"smile", "Smile"),
    (r"xneelo|hetzner south africa", "xneelo"),
    (r"afrihost", "Afrihost"),
    (r"safaricom", "Safaricom"),
    (r"truehost|cloudoon", "Truehost"),
]


def dig(rtype, name, resolver):
    try:
        out = subprocess.run(
            ["dig", "+short", "+time=3", "+tries=2", f"@{resolver}", rtype, name],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    # dig prints its own errors (";; connection timed out ...") on stdout; those are not records
    return [line.strip().strip('"') for line in out.splitlines() if line.strip() and not line.startswith(";")]


def email_provider(domain, resolver):
    records = dig("MX", domain, resolver)
    hosts = " ".join(r.split()[-1].lower() for r in records if " " in r)
    if not hosts:
        return ""
    for pattern, name in MAIL:
        if re.search(pattern, hosts):
            return name
    return "Own or hosting-provider mail"


@cache
def asn_name(asn, resolver):
    txt = dig("TXT", f"AS{asn}.asn.cymru.com", resolver)
    return txt[0].split("|")[-1].strip() if txt else ""


def hosting(domain, resolver):
    ips = [x for x in dig("A", domain, resolver) if re.fullmatch(r"\d+(\.\d+){3}", x)]
    if not ips:
        ips = [x for x in dig("A", "www." + domain, resolver) if re.fullmatch(r"\d+(\.\d+){3}", x)]
    if not ips:
        return "", ""
    origin = dig("TXT", ".".join(reversed(ips[0].split("."))) + ".origin.asn.cymru.com", resolver)
    if not origin:
        return "", ""
    parts = [p.strip() for p in origin[0].split("|")]
    if len(parts) < 3 or not parts[0].split()[0].isdigit():
        return "", ""
    asn, country = parts[0].split()[0], parts[2]
    owner = asn_name(asn, resolver)
    for pattern, name in HOSTS:
        if re.search(pattern, owner, re.I):
            return name, "" if name == "Cloudflare" else country  # Cloudflare hides the real origin
    label = re.sub(r",\s*[A-Z]{2}$", "", owner.split(" - ", 1)[-1]).strip()
    return label or f"AS{asn}", country


def lookup(domain, resolver):
    host, country = hosting(domain, resolver)
    return domain, {"email_provider": email_provider(domain, resolver), "hosting": host, "hosting_country": country}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--resolver", default=RESOLVER)
    args = ap.parse_args()
    domains = sorted(
        {
            r["domain"]
            for f in ("companies.csv", "unverified.csv")
            for r in read_csv(os.path.join(DATA, f))
            if r["domain"]
        }
    )
    with ThreadPoolExecutor(args.workers) as pool:
        results = dict(pool.map(lambda d: lookup(d, args.resolver), domains))
    results = {d: v for d, v in results.items() if any(v.values())}
    os.makedirs(BUILD, exist_ok=True)
    with open(os.path.join(BUILD, "dns.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, sort_keys=True)
    print(f"domains: {len(domains)}, with DNS signals: {len(results)}")


if __name__ == "__main__":
    main()
