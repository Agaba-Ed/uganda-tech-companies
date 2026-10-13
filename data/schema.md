# Data schema

Both `companies.csv` and `unverified.csv` use the same columns. Files are UTF-8 with a header row,
sorted by name. Multiple values in one cell are separated by `; ` or `, `.

| Column | Description |
|---|---|
| `name` | Company or organisation name |
| `website` | Homepage URL (`https://…`), when known |
| `domain` | Registrable domain of the website, used for de-duplication |
| `sector` | Up to two labels, e.g. `Fintech / Payments · Software house / Agency`. Empty when unknown |
| `confidence` | `high`, `medium` or `low`: how sure we are this is a real, active tech organisation in Uganda |
| `github_devs` | Number of GitHub users located in Uganda who name this company as their employer on their profile (not a headcount) |
| `description` | The site's own meta description or opening text (max 300 characters) |
| `careers_page` | Link to a careers or jobs page, if one was found on the homepage |
| `email` | Role-based contact addresses only (info@, careers@, hr@ …) |
| `location` | Street and city, when known (mostly from OpenStreetMap) |
| `stack_mentions` | Technologies mentioned on the homepage (react, django, aws …) |
| `sources` | Where the entry came from: `Common Crawl (.ug)`, `OpenStreetMap`, `GitHub org`, `GitHub developers`, `yellow.ug directory`, `Curated (<list it came from>)` |

## Technology signals: `tech.csv`

One row per company with any signal, joined to the files above by `name`. Multiple values are separated by `; `.

| Column | Description |
|---|---|
| `name`, `domain` | As in `companies.csv` / `unverified.csv` |
| `github_languages` | Main languages of public repositories pushed in the last two years, with counts, e.g. `TypeScript:7; Python:4`. Counts are developers who name the company plus repositories of its GitHub organisation. No usernames are stored |
| `web_tech` | Platform, frameworks, servers and widgets detected on the homepage (`WordPress; Elementor; Cloudflare`) |
| `email_provider` | From MX records: `Google Workspace`, `Microsoft 365`, `Zoho Mail`, … or `Own or hosting-provider mail` |
| `hosting` | Network announcing the website's IP address. `Cloudflare` means the real host is hidden |
| `hosting_country` | Country the IP block is registered in (two-letter code). An approximation of where the site is served from |
| `careers_tech` | Technologies named on the company's careers page |

`insights.json` holds the aggregated numbers shown on the Insights page. Every breakdown has `n`, the number of
companies in `companies.csv` it is based on, and `items`, a ranked list of `{label, count}`.

## Confidence

- **high:** homepage scores strongly as tech, or 3+ developers name the company, or found in 2+ sources.
- **medium:** homepage scores moderately, or 2 developers name the company.
- **low:** a single weak signal. These live in `unverified.csv`.

## Sectors

`Fintech / Payments`, `Software house / Agency`, `Hosting / Cloud / ISP / Telecom`,
`IT services / Systems integration`, `Cybersecurity`, `AI / Data`, `Healthtech`, `Edtech`, `Agritech`,
`E-commerce / Marketplace`, `Messaging / SMS / USSD`, `Tech hub / Training`, `Energy / Mobility / IoT`,
`Bank / Financial institution (in-house tech)`, `Public sector (in-house tech)`, `Tech (general)`.
