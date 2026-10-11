"""Score each fetched homepage for how strongly it reads as a tech company.

usage: python scripts/classify.py
Reads build/html/, build/fetch_log.tsv and build/source_map.tsv (domain -> source).
Output: build/tech_web.csv (pages scoring >= 7, with confidence high >= 14, medium >= 10, low >= 7)
"""

import csv
import html as htmllib
import os
import re
from collections import Counter

from common import BUILD

HTML_DIR = os.path.join(BUILD, "html")
LOG = os.path.join(BUILD, "fetch_log.tsv")
OUT = os.path.join(BUILD, "tech_web.csv")
os.makedirs(HTML_DIR, exist_ok=True)

# Strong signals: the business itself is tech. Weight 3.
STRONG = [
    "software development",
    "software company",
    "software solutions",
    "web development",
    "mobile app development",
    "app development",
    "custom software",
    "saas",
    "fintech",
    "payment gateway",
    "payment solutions",
    "digital payments",
    "mobile money api",
    "api integration",
    "cloud hosting",
    "web hosting",
    "domain registration",
    "data center",
    "data centre",
    "cybersecurity",
    "cyber security",
    "it solutions",
    "it services",
    "ict solutions",
    "ict services",
    "systems integration",
    "system integrator",
    "erp",
    "machine learning",
    "artificial intelligence",
    "data analytics",
    "data science",
    "digital transformation",
    "managed services",
    "network solutions",
    "internet service provider",
    "isp",
    "fibre",
    "fiber optic",
    "telecom",
    "edtech",
    "healthtech",
    "agritech",
    "insurtech",
    "proptech",
    "e-commerce platform",
    "point of sale",
    "pos system",
    "school management system",
    "hospital management system",
    "sacco software",
    "microfinance software",
    "core banking",
    "ussd",
    "sms gateway",
    "bulk sms",
    "devops",
    "ui/ux",
    "ux design",
    "product design",
    "digital agency",
    "mobile money",
    "telecommunications",
    "internet bundles",
    "data bundles",
    "kyc",
    "identity verification",
    "tech startup",
    "technology company",
    "tech company",
    "innovation hub",
]
# Weaker signals: common on tech sites but also elsewhere. Weight 1.
WEAK = [
    "software",
    "technology",
    "technologies",
    "digital",
    "platform",
    "app",
    "developers",
    "website",
    "cloud",
    "api",
    "automation",
    "online",
    "innovation",
    "solutions",
    "ict",
    "computer",
    "network",
    "data",
    "systems",
    "it ",
    "tech",
    "startup",
    "android",
    "ios",
]
# Signals that the page is something else (schools, churches, hotels, NGOs etc). Weight -2.
NEGATIVE = [
    "hotel",
    "lodge",
    "safari",
    "tour",
    "church",
    "ministry of",
    "primary school",
    "secondary school",
    "nursery school",
    "high school",
    "college",
    "university",
    "admissions",
    "restaurant",
    "real estate",
    "apartments",
    "hardware store",
    "pharmacy",
    "clinic",
    "hospital",
    "farm",
    "law firm",
    "advocates",
    "solicitors",
    "insurance company",
    "sacco limited",
    "parish",
    "diocese",
    "foundation",
    "orphan",
    "charity",
    "ngo",
    "travel",
    "car hire",
    "salon",
    "fashion",
]
GAMBLING = ["betting", "casino", "sportsbook", "jackpot", "odds", "slots", "1xbet", "22bet", "1win"]
SECTORS = {
    "Fintech / Payments": [
        "fintech",
        "payment",
        "mobile money",
        "wallet",
        "lending",
        "loan",
        "remittance",
        "core banking",
        "sacco software",
        "microfinance software",
    ],
    "Software house / Agency": [
        "software development",
        "custom software",
        "web development",
        "app development",
        "digital agency",
        "web design",
        "mobile app",
    ],
    "Hosting / Cloud / ISP / Telecom": [
        "hosting",
        "domain",
        "cloud",
        "internet service",
        "isp",
        "fibre",
        "fiber",
        "telecom",
        "data center",
        "data centre",
        "bandwidth",
    ],
    "IT services / Systems integration": [
        "it solutions",
        "it services",
        "ict",
        "systems integration",
        "networking",
        "cctv",
        "managed services",
        "erp",
    ],
    "Cybersecurity": ["cybersecurity", "cyber security", "penetration", "infosec"],
    "AI / Data": ["machine learning", "artificial intelligence", " ai ", "data analytics", "data science"],
    "Healthtech": ["healthtech", "telemedicine", "hospital management", "health app", "ehr", "emr"],
    "Edtech": ["edtech", "e-learning", "elearning", "school management", "lms"],
    "Agritech": ["agritech", "agtech", "farmers app", "precision agriculture"],
    "E-commerce / Marketplace": ["e-commerce", "ecommerce", "online shop", "marketplace", "delivery app"],
    "Messaging / SMS / USSD": ["bulk sms", "sms gateway", "ussd", "short code"],
    "Tech hub / Training": ["innovation hub", "incubat", "accelerat", "coding bootcamp", "tech training"],
}
CAREER_RE = re.compile(
    r'href=["\']([^"\']*(?:career|jobs|vacanc|join-us|joinus|work-with-us|hiring)[^"\']*)["\']', re.I
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?256|0)[\s-]?[37]\d{2}[\s-]?\d{3}[\s-]?\d{3}")
STACK = [
    "react",
    "angular",
    "vue",
    "next.js",
    "django",
    "laravel",
    "spring",
    "node.js",
    "flutter",
    "kotlin",
    "swift",
    "python",
    "java",
    "php",
    "aws",
    "azure",
    "docker",
    "kubernetes",
    "postgres",
]


def meta(doc, *names):
    for n in names:
        m = re.search(
            rf'<meta[^>]+(?:name|property)=["\']{re.escape(n)}["\'][^>]*content=["\']([^"\']*)', doc, re.I
        ) or re.search(
            rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:name|property)=["\']{re.escape(n)}["\']', doc, re.I
        )
        if m and m.group(1).strip():
            return htmllib.unescape(m.group(1).strip())
    return ""


def visible_text(doc):
    doc = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", doc)
    doc = re.sub(r"(?s)<[^>]+>", " ", doc)
    return re.sub(r"\s+", " ", htmllib.unescape(doc)).strip()


def score(text):
    t = " " + text.lower() + " "
    s = sum(3 for k in STRONG if k in t) + sum(1 for k in WEAK if k in t) - sum(2 for k in NEGATIVE if k in t)
    if any(k in t for k in GAMBLING):
        s -= 50
    return s


def sector(text):
    t = " " + text.lower() + " "
    hits = Counter({name: sum(t.count(k) for k in kws) for name, kws in SECTORS.items()})
    best = [n for n, c in hits.most_common(2) if c > 0]
    return " · ".join(best) or "Tech (general)"


def read_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


log = {}
for line in read_lines(LOG):
    p = line.split("\t")
    if len(p) >= 2:
        log[p[0]] = (p[1], p[2] if len(p) > 2 else "")

for fn in os.listdir(HTML_DIR):
    if fn.endswith(".html"):
        log.setdefault(fn[:-5], ("200", ""))

SOURCE = {}
for line in read_lines(os.path.join(BUILD, "source_map.tsv")):
    d, _, src = line.partition("\t")
    SOURCE.setdefault(d, src)

rows = []
for d, (code, final) in log.items():
    path = os.path.join(HTML_DIR, d + ".html")
    if code == "000" or not os.path.exists(path):
        continue
    with open(path, encoding="utf-8", errors="ignore") as f:
        doc = f.read()
    title_m = re.search(r"(?is)<title[^>]*>(.*?)</title>", doc)
    title = re.sub(r"\s+", " ", htmllib.unescape(title_m.group(1))).strip() if title_m else ""
    desc = meta(doc, "description", "og:description")
    name = meta(doc, "og:site_name") or re.split(r"\s[|\-\u2013\u2014:]\s", title)[0].strip() or d
    body = visible_text(doc)
    blob = " ".join([title, desc, body[:6000]])
    s = score(blob)
    if s < 7:
        continue
    confidence = "high" if s >= 14 else "medium" if s >= 10 else "low"
    careers = ""
    m = CAREER_RE.search(doc)
    if m:
        careers = m.group(1)
        if careers.startswith("/"):
            careers = (final or f"https://{d}").split("/", 3)[:3] and "/".join(
                (final or f"https://{d}/").split("/")[:3]
            ) + careers
    emails = sorted({e for e in EMAIL_RE.findall(body) if not e.lower().endswith((".png", ".jpg", ".webp"))})[:3]
    phones = sorted({re.sub(r"[\s-]", "", p) for p in PHONE_RE.findall(body)})[:2]
    stack = [k for k in STACK if k in blob.lower()]
    rows.append(
        {
            "name": name[:80],
            "domain": d,
            "website": final or f"https://{d}",
            "sector": sector(blob),
            "tech_score": s,
            "confidence": confidence,
            "description": (desc or body[:200])[:300],
            "careers_page": careers,
            "emails": "; ".join(emails),
            "phones": "; ".join(phones),
            "stack_mentions": ", ".join(stack),
            "source": SOURCE.get(d, "Common Crawl (.ug)"),
        }
    )

rows.sort(key=lambda r: -r["tech_score"])
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["name"])
    w.writeheader()
    w.writerows(rows)
print(f"fetched={sum(1 for v in log.values() if v[0] != '000')} tech={len(rows)}")
print(Counter(r["confidence"] for r in rows))
print(Counter(r["sector"].split(" · ")[0] for r in rows).most_common())
