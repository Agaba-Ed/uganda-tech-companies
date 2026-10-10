# Contributing

Thanks for helping map Uganda's tech ecosystem. Every correction makes the directory more useful.

## Without touching CSV files

Open an issue using one of the templates:

- **Add a company**
- **Correct or remove a company**

A maintainer will make the change.

## Editing the data directly

1. Edit `data/companies.csv` or `data/unverified.csv`. GitHub's web editor is fine for small changes.
2. Keep the header and column order unchanged (see [`data/schema.md`](data/schema.md)).
3. Open a pull request. The **Validate data** check must pass.

What the check enforces:

- `confidence` is `high`, `medium` or `low`
- `website` and `careers_page` are full URLs starting with `http://` or `https://`
- no duplicate names or domains across both files
- `email` contains only role addresses (info@, careers@, hr@ …), never a person's address

You can run it locally with `python scripts/validate.py`.

## Promoting an unverified entry

If you know a company in `unverified.csv` is real and does tech work in Uganda, move its row to
`companies.csv` and set `confidence` to `medium` or `high`. Adding the website is a big help.

## Removing an entry

Delete the row and add the company name (or domain) to `state/removed.txt`, so the weekly refresh
never adds it back. Removal requests from the company itself are always honoured.

## Ground rules

- Organisations only, never individuals.
- Public information only.
- Be accurate rather than generous. A wrong entry is worse than a missing one.
