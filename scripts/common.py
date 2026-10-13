"""Shared constants and helpers for the Uganda tech companies pipeline."""

import csv
import os
import re
from urllib.parse import urljoin

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
BUILD = os.path.join(ROOT, "build")
STATE = os.path.join(ROOT, "state")

FIELDS = [
    "name",
    "website",
    "domain",
    "sector",
    "confidence",
    "github_devs",
    "description",
    "careers_page",
    "email",
    "location",
    "stack_mentions",
    "sources",
]
CONFIDENCE = ("high", "medium", "low")

_SUFFIX = re.compile(
    r"\b(limited|ltd|llc|inc|plc|co|company|smc|u|uganda|ug|group|africa|east africa|"
    r"technologies|technology|tech|solutions|systems|labs?|labz|hq|studios?)\b\.?",
    re.I,
)

# Page titles that mean "this is not a real company site" (parked domains, server defaults, errors).
JUNK_NAME = re.compile(
    r"^(https?:?|github\.com|n/?a|home|other|no company|founder|remote|management|marketing|mining|education|"
    r"environment|imaging|security|investment ltd|open to opportunities|api|com|db|a\.?i|plug|pencil|the word|"
    r"index of.*|welcome.*|untitled.*|coming soon.*|under construction.*|maintenance.*|403.*|404.*|"
    r"account suspended.*|site not found.*|page not found.*)$"
    r"|future home of|apache http server|test page|default (web )?page|parallels plesk|cpanel|dns resolution error|"
    r"domain registered at|hugedomains|domain (is )?for sale|this domain|buy this domain|a microsoft certified partner|"
    r"secure web hosting that grows",
    re.I,
)
# Businesses the homepage classifier sometimes mistakes for tech.
NON_TECH = re.compile(
    r"church|hospital|safari|poultry|estates?\b|property manag|cargo|bible|diocese|parish|"
    r"hotel|lodge|tours?\b|salon|restaurant|real estate|cinema|bet(ting|bonus)?\b|casino",
    re.I,
)
SPAM = re.compile(
    r"illuminati|spell ?caster|love spell|\bwitch|black magic|sugar mummy|hack(er)? for hire|"
    r"porn|escort|casino|betting|loan shark|fake (money|notes)|counterfeit|maxwin|slot gacor|\bdepo\b|\btogel\b",
    re.I,
)
PUBLIC_SECTOR = re.compile(
    r"ministry|authority|commission|uganda police|judiciary|bureau of statistics|"
    r"\bnita\b|nita-u|\bnira\b|\bura\b|\bucc\b|\bnfa\b|\bnssf\b|uetcl|national (water|forestry|"
    r"cert|meteorological|mining)|government of uganda|electoral|bank of uganda|posta uganda|"
    r"registration authority|\.go\.ug",
    re.I,
)
BANK = re.compile(
    r"\bbank\b|absa|stanbic|centenary|dfcu|equity bank|exim|finance trust|sacco|microfinance|ugafode", re.I
)
# Map ad-hoc labels onto the fixed sector list in data/schema.md.
SECTOR_ALIASES = {
    "software house": "Software house / Agency",
    "software": "Software house / Agency",
    "sme tech": "Software house / Agency",
    "fintech": "Fintech / Payments",
    "fintech / lending": "Fintech / Payments",
    "fintech / telco": "Fintech / Payments",
    "fintech / energy": "Fintech / Payments",
    "fintech / fuel": "Fintech / Payments",
    "fintech / asset finance": "Fintech / Payments",
    "fintech / investment": "Fintech / Payments",
    "microfinance tech": "Fintech / Payments",
    "insurtech": "Fintech / Payments",
    "tech hub": "Tech hub / Training",
    "tech training": "Tech hub / Training",
    "talent network": "Tech hub / Training",
    "it services": "IT services / Systems integration",
    "it services / bpo": "IT services / Systems integration",
    "systems integration": "IT services / Systems integration",
    "web / it services": "IT services / Systems integration",
    "telco / cloud": "Hosting / Cloud / ISP / Telecom",
    "infrastructure": "Hosting / Cloud / ISP / Telecom",
    "govtech / data": "AI / Data",
    "ai": "AI / Data",
    "healthtech / software": "Healthtech",
    "agritech / fintech": "Agritech",
    "edtech / robotics": "Edtech",
    "energy / iot": "Energy / Mobility / IoT",
    "e-mobility / iot": "Energy / Mobility / IoT",
    "energy / fintech": "Energy / Mobility / IoT",
    "mobility / ticketing": "Energy / Mobility / IoT",
    "delivery": "E-commerce / Marketplace",
    "logistics": "E-commerce / Marketplace",
    "ngo tech": "Tech (general)",
}
GENERIC_EMAIL = re.compile(
    r"^(info|contact|contacts|hello|hi|sales|support|careers|career|jobs|hr|admin|office|enquiries|enquiry|"
    r"inquiries|inquiry|mail|team|recruitment|business|marketing|help|customercare|customerservice|care|service|"
    r"services|general|reception|ict|it|tech|dev|partnerships|press|media|accounts|billing|noc|helpdesk)@",
    re.I,
)


_PHONE = re.compile(r"(?:\+?256|\b0)[\s-]?\(?[2-9]\d{2}\)?[\s-]?\d{3}[\s-]?\d{3}")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def norm(name):
    """Normalised key used for de-duplication."""
    n = (name or "").lower().strip().lstrip("@")
    n = re.sub(r"https?://|www\.", "", n)
    n = re.sub(r"\.(co\.ug|ug|com|org|io|africa|net|co)$", "", n)
    n = _SUFFIX.sub(" ", n)
    return re.sub(r"[^a-z0-9]+", "", n)


def domain_of(url):
    if not url:
        return ""
    url = url.strip()
    if "://" not in url:
        url = "http://" + url
    host = re.sub(r"^[a-z]+://", "", url, flags=re.I).split("/")[0].split(":")[0].lower()
    return host.removeprefix("www.")


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields=FIELDS):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def clean_row(row):
    """Apply privacy and quality rules. Returns None when the row should be dropped."""
    name = re.sub(r"\s+", " ", row.get("name", "")).strip(" |-\u2013\u2014")
    if not name or JUNK_NAME.search(name) or JUNK_NAME.search(row.get("description", "")[:80]):
        return None
    if _EMAIL.search(name) or _PHONE.search(name) or re.search(r"\d{9,}", name) or SPAM.search(name):
        return None
    if NON_TECH.search(name) or looks_personal(name, row.get("website", ""), row.get("sources", "")):
        return None
    row = dict(row)
    row["name"] = name[:100]
    emails = [e.strip() for e in re.split(r"[;,\s]+", row.get("email") or row.get("emails") or "") if e.strip()]
    row["email"] = "; ".join(e for e in emails if GENERIC_EMAIL.match(e))  # only role addresses, never personal ones
    website = (row.get("website") or "").strip()
    if website and not re.match(r"https?://", website, re.I):
        website = "https://" + website.lstrip("/")
    row["website"] = website if re.match(r"https?://[^\s/$.?#][^\s]*$", website, re.I) else ""
    row["domain"] = row.get("domain") or domain_of(row["website"])
    careers = (row.get("careers_page") or "").strip()
    if re.search(r"wa\.me|whatsapp|mailto:|tel:|javascript:", careers, re.I):
        careers = ""
    elif careers and not re.match(r"https?://", careers, re.I):
        careers = urljoin(row["website"] + "/", careers) if row["website"] else ""
    row["careers_page"] = careers if re.match(r"https?://[^\s/$.?#][^\s]*$", careers, re.I) else ""
    desc = _PHONE.sub("", row.get("description", ""))
    desc = _EMAIL.sub("", desc)
    desc = re.sub(r"\s+", " ", desc).strip(" ,;|-")[:300]
    row["description"] = "" if re.search(r"lorem ipsum|dolor sit amet", desc, re.I) else desc  # template text
    parts = [SECTOR_ALIASES.get(x.strip().lower(), x.strip()) for x in row.get("sector", "").split(" · ") if x.strip()]
    sector = " · ".join(dict.fromkeys(parts))
    if PUBLIC_SECTOR.search(name + " " + row.get("domain", "")):
        sector = "Public sector (in-house tech)"
    elif BANK.search(name) and not sector.startswith("Fintech"):
        sector = "Bank / Financial institution (in-house tech)"
    row["sector"] = sector
    # "kampala" and "KAMPALA" are the same place; mixed-case names are left as written
    places = [p.strip() for p in (row.get("location") or "").split(",") if p.strip()]
    row["location"] = ", ".join(p.title() if p.isupper() or p.islower() else p for p in places)
    row["stack_mentions"] = ", ".join(
        dict.fromkeys(x.strip().lower() for x in (row.get("stack_mentions") or "").split(",") if x.strip())
    )
    return row


# Technologies looked for in job ads and careers pages, as display name -> pattern.
TECH_TERMS = {
    name: re.compile(pattern, re.I)
    for name, pattern in {
        "JavaScript": r"\bjavascript\b",
        "TypeScript": r"\btypescript\b",
        "React": r"\breact(\.js|js)?\b(?! native)",
        "React Native": r"\breact native\b",
        "Angular": r"\bangular\b",
        "Vue": r"\bvue(\.js|js)?\b",
        "Next.js": r"\bnext\.?js\b",
        "Node.js": r"\bnode(\.js|js)?\b",
        "Python": r"\bpython\b",
        "Django": r"\bdjango\b",
        "Flask": r"\bflask\b",
        "FastAPI": r"\bfastapi\b",
        "PHP": r"\bphp\b",
        "Laravel": r"\blaravel\b",
        "Java": r"\bjava\b(?!script)",
        "Spring": r"\bspring( boot)?\b",
        "Kotlin": r"\bkotlin\b",
        "Swift": r"\bswift(ui)?\b",
        "Flutter": r"\bflutter\b",
        "Dart": r"\bdart\b",
        "C#": r"(?<!\w)c#|(?<![\w/])\.net\b|\basp\.net\b",
        "Go": r"\bgolang\b|\bgo (developer|engineer)\b",
        "Ruby": r"ruby on rails|\bruby\b(?= (developer|engineer|programming))|\brails\b",
        "SQL": r"\bsql\b",
        "PostgreSQL": r"\bpostgres(ql)?\b",
        "MySQL": r"\bmysql\b",
        "MongoDB": r"\bmongo(db)?\b",
        "AWS": r"\baws\b|amazon web services",
        "Azure": r"\bazure\b",
        "Google Cloud": r"\bgcp\b|google cloud",
        "Docker": r"\bdocker\b",
        "Kubernetes": r"\bkubernetes\b|\bk8s\b",
        "Linux": r"\blinux\b",
        "Odoo": r"\bodoo\b",
        "Salesforce": r"\bsalesforce\b",
        "Power BI": r"\bpower ?bi\b",
        "Machine learning": r"machine learning|\bml engineer\b|\bdata scien",
    }.items()
}


def tech_terms(text):
    return [name for name, rx in TECH_TERMS.items() if rx.search(text)]


# Developers sometimes put their own name in GitHub's "company" field. Entries that come only from
# that field, have no website and contain a common given name are treated as personal and dropped.
_GIVEN = set(
    [
        "aaron",
        "abdul",
        "abel",
        "abraham",
        "adam",
        "adrian",
        "agnes",
        "ahmed",
        "alan",
        "albert",
        "alex",
        "alexander",
        "alfred",
        "ali",
        "alice",
        "allan",
        "allen",
        "alvin",
        "amos",
        "andrew",
        "angela",
        "ann",
        "anna",
        "annet",
        "anthony",
        "arnold",
        "arthur",
        "asha",
        "baldwin",
        "barbara",
        "ben",
        "benjamin",
        "bernard",
        "betty",
        "bonny",
        "brian",
        "bruce",
        "caleb",
        "calvin",
        "carol",
        "caroline",
        "charles",
        "christine",
        "christopher",
        "collins",
        "dan",
        "daniel",
        "david",
        "davis",
        "dennis",
        "denis",
        "derrick",
        "dickson",
        "donald",
        "douglas",
        "edgar",
        "edith",
        "edward",
        "edwin",
        "elijah",
        "elizabeth",
        "ellen",
        "emmanuel",
        "eric",
        "esther",
        "evans",
        "faith",
        "felix",
        "francis",
        "frank",
        "fred",
        "gabriel",
        "geoffrey",
        "george",
        "gerald",
        "gideon",
        "gilbert",
        "godfrey",
        "grace",
        "hannah",
        "harriet",
        "henry",
        "herbert",
        "hilda",
        "ian",
        "immaculate",
        "innocent",
        "irene",
        "isaac",
        "isah",
        "isaiah",
        "israel",
        "ivan",
        "jacob",
        "james",
        "jane",
        "janet",
        "jason",
        "joan",
        "joel",
        "john",
        "johnson",
        "jonathan",
        "joseph",
        "joshua",
        "josephine",
        "judith",
        "julius",
        "kenneth",
        "kevin",
        "lawrence",
        "linda",
        "lucy",
        "mark",
        "martin",
        "mary",
        "matthew",
        "michael",
        "moses",
        "nathan",
        "nicholas",
        "noah",
        "norah",
        "oscar",
        "patience",
        "patrick",
        "paul",
        "peter",
        "philip",
        "phillip",
        "prossy",
        "rachel",
        "raymond",
        "rebecca",
        "richard",
        "robert",
        "ronald",
        "rose",
        "ruth",
        "samuel",
        "sandra",
        "sarah",
        "simon",
        "solomon",
        "stella",
        "stephen",
        "steven",
        "susan",
        "timothy",
        "titus",
        "tom",
        "tony",
        "tonny",
        "victor",
        "vincent",
        "violet",
        "wilson",
        "winnie",
        "yusuf",
    ]
)
_BIZWORD = re.compile(
    r"ltd|limited|tech|soft|solution|system|consult|digital|labs?\b|hub|group|agency|studio|media|"
    r"global|enterprise|services|company|\binc\b|data|code|dev|web|\bapps?\b|innov|cloud|pay|works|"
    r"foundation|network|holdings|ventures|creative|design|ministr|house|records|music|collection",
    re.I,
)


def looks_personal(name, website, sources):
    if website or sources != "GitHub developers" or _BIZWORD.search(name):
        return False
    words = re.findall(r"[a-z]+", name.lower())
    return 2 <= len(words) <= 3 and any(w in _GIVEN for w in words)
