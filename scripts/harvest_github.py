"""Collect tech employers from GitHub: organisations located in Uganda, and the "company" field of
users located in Uganda.

Only aggregate employer counts are written. No usernames or personal details are stored.
Needs GITHUB_TOKEN (or GH_TOKEN) in the environment.
Output: build/gh_employers.tsv (employer, developer_count), build/gh_orgs.tsv
"""
import datetime as dt
import json
import os
import re
import time
import urllib.request
from collections import Counter

from common import BUILD

TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
LOCATIONS = ["Uganda", "Kampala", "Entebbe", "Mbarara", "Gulu", "Jinja", "Wakiso", "Mukono", "Mbale", "Lira",
             "Fort Portal", "Masaka", "Arua"]
USER_Q = """query($q:String!,$after:String){search(query:$q,type:USER,first:100,after:$after){userCount
pageInfo{hasNextPage endCursor} nodes{... on User{login company}}}}"""
ORG_Q = """query($q:String!,$after:String){search(query:$q,type:USER,first:100,after:$after){userCount
pageInfo{hasNextPage endCursor} nodes{... on Organization{login name websiteUrl description location
repositories(privacy:PUBLIC){totalCount}}}}}"""

# employer strings that are not companies
NOISE = re.compile(
    r"^(n/?a|none|nil|no|non|null|self|private|home|student|students|me|myself|independent|unemployed|uganda|"
    r"kampala|freelanc\w*|free ?lancer?|self[- ]?employed.*|open to work|looking.*|available.*|personal|hobby\w*|"
    r".*developer|.*engineer|.*programmer|.*designer|.*student.*|software|web|github|https?:?|github\.com|research|"
    r"individual|travel|sponsor|sql|own start ?up|it solutions|consultant|consulting|company|business|startup|tech|"
    r"technology|.*\.github\.io|-|\.|\?)$", re.I)
EDU = re.compile(r"byu|pathway|universit|college|school|institute of|academy\b|polytechnic|\bkiu\b|\bmubs\b|"
                 r"\bucu\b|\bmust\b|\bslau\b|\bisbat\b|\bmak\b|makerere|kyambogo|\balx\b|microverse|holberton", re.I)


def gql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body,
                                 headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            if "errors" in data and not data.get("data"):
                raise RuntimeError(data["errors"])
            return data["data"]["search"]
        except Exception:
            time.sleep(15 * (attempt + 1))
    raise RuntimeError("GitHub GraphQL failed repeatedly")


def search_all(query, q, start, end, sink):
    """Search splits by account creation date so each slice stays under GitHub's 1000-result cap."""
    rng = f"{q} created:{start:%Y-%m-%d}..{end:%Y-%m-%d}"
    page = gql(query, {"q": rng, "after": None})
    if page["userCount"] > 1000 and (end - start).days > 1:
        mid = start + (end - start) / 2
        search_all(query, q, start, mid, sink)
        search_all(query, q, mid + dt.timedelta(days=1), end, sink)
        return
    while True:
        for n in page["nodes"]:
            if n and n.get("login"):
                sink[n["login"]] = n
        if not page["pageInfo"]["hasNextPage"]:
            return
        page = gql(query, {"q": rng, "after": page["pageInfo"]["endCursor"]})
        time.sleep(0.5)


def main():
    if not TOKEN:
        raise SystemExit("set GITHUB_TOKEN")
    start, end = dt.date(2008, 1, 1), dt.date.today()
    users, orgs = {}, {}
    for loc in LOCATIONS:
        search_all(USER_Q, f'location:"{loc}" type:user', start, end, users)
        search_all(ORG_Q, f'location:"{loc}" type:org', start, end, orgs)
        print(f"{loc}: {len(users)} users, {len(orgs)} orgs", flush=True)

    employers, display = Counter(), {}
    for u in users.values():
        for part in re.split(r"\s*[,/|&]\s*|\s+and\s+", u.get("company") or ""):
            part = re.sub(r"\s+", " ", part.strip().lstrip("@").strip(" .-"))
            if not part or len(part) > 60 or NOISE.match(part) or EDU.search(part):
                continue
            key = part.lower()
            employers[key] += 1
            display.setdefault(key, part)

    os.makedirs(BUILD, exist_ok=True)
    with open(os.path.join(BUILD, "gh_employers.tsv"), "w") as f:
        for key, n in employers.most_common():
            f.write(f"{display[key]}\t{n}\n")
    with open(os.path.join(BUILD, "gh_orgs.tsv"), "w") as f:
        for o in orgs.values():
            if EDU.search(f"{o.get('name') or ''} {o.get('description') or ''}"):
                continue
            row = [o["login"], o.get("name") or "", o.get("websiteUrl") or "", o.get("description") or "",
                   o.get("location") or "", str(o.get("repositories", {}).get("totalCount", 0))]
            f.write("\t".join(c.replace("\t", " ").replace("\n", " ") for c in row) + "\n")
    print(f"employers: {len(employers)}, orgs: {len(orgs)}")


if __name__ == "__main__":
    main()
