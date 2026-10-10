# Uganda Tech Companies

An open, community-maintained directory of technology companies in Uganda: software houses,
fintechs, ISPs and hosting providers, IT services firms, AI and data startups, tech hubs, and the
in-house tech teams of banks and public bodies.

**Search it:** https://agaba-ed.github.io/uganda-tech-companies/
**Download it:** [`data/companies.csv`](data/companies.csv) · [`data/unverified.csv`](data/unverified.csv)

| File | Rows | What it is |
|---|---|---|
| `data/companies.csv` | 764 | High and medium confidence: strong tech website, several developers, or found in 2+ sources |
| `data/unverified.csv` | 4,485 | Low-confidence candidates |

There's no official register of tech companies in Uganda. This project aims to be the most complete
public list, and it only gets better if people who know the ecosystem correct and extend it.

## How it was built

Everything comes from public data. The scripts in [`scripts/`](scripts) are the full pipeline.

1. **Common Crawl.** Every `.ug` domain from recent web-crawl snapshots (about 3,100 domains).
   Government, university and school domains are skipped.
2. **OpenStreetMap.** Company, IT and telecom offices and computer shops mapped in Uganda.
3. **GitHub.** Organisations located in Uganda, plus the employers that ~10,700 developers located in
   Uganda list on their profiles. Only the employer name and a count are kept. No usernames or
   personal details are stored.
4. **Classification.** Each website's homepage is fetched and scored on tech keywords: positive for
   things like "software development", "payment gateway", "web hosting"; negative for hotels,
   schools, churches, betting. The score sets the sector and confidence.
5. **Merging.** Entries are de-duplicated by normalised name and domain. Entries seen in two or more
   independent sources are upgraded.

A **weekly GitHub Action** repeats steps 1–4 and opens a pull request with any new candidates. It
never merges on its own, and it never overwrites rows that people have corrected.

### Known gaps

- Companies on `.com` and other non-`.ug` domains are only found through GitHub and OpenStreetMap.
- Sites that only render with JavaScript can score too low and be missed.
- Many GitHub-only entries have no website yet. Adding one is the most useful contribution.
- Sector labels are keyword-based and sometimes wrong.

## Columns

See [`data/schema.md`](data/schema.md).

## Contributing

Corrections and additions are very welcome. See [CONTRIBUTING.md](CONTRIBUTING.md). The quickest
ways to help are:

- **Add a company:** open an [issue](../../issues/new/choose) or edit the CSV in a pull request.
- **Confirm unverified entries:** move them from `unverified.csv` to `companies.csv`.
- **Remove or correct your company:** open an issue. Removals are honoured and recorded in
  `state/removed.txt` so the entry is never re-added.

## Running the pipeline

Python 3.10+ only, no dependencies.

```bash
python scripts/harvest_commoncrawl.py --crawls 2
GITHUB_TOKEN=... python scripts/harvest_github.py
python scripts/harvest_osm.py
python scripts/prepare.py
python scripts/fetch_homepages.py build/to_fetch.txt
python scripts/classify.py
python scripts/update.py
python scripts/validate.py
```

## Licence

- **Data** (`data/`) is under the [Open Database License (ODbL) 1.0](DATA_LICENSE). You may use,
  share and adapt it, including commercially, if you attribute this project and share adapted
  databases under the same licence.
- **Code** (`scripts/`, `site/`, workflows) is under the [MIT License](LICENSE).

Attribution: "Uganda Tech Companies (github.com/Agaba-Ed/uganda-tech-companies)". The data also
contains information © OpenStreetMap contributors, and is derived from Common Crawl and public
GitHub profiles.

## Privacy

The dataset lists organisations, not people. Only role-based email addresses (info@, careers@,
hr@ …) are kept, and no phone numbers or personal details are stored. Entries that look like a
person's name rather than a business are filtered out. If you find personal data, please open an
issue and it will be removed.
