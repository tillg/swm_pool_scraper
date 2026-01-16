# Save Data to Separate Repository

## Goal

Store scraped pool data in a dedicated `tillg/swm_pool_data` repository and run automated scrapes every 15 minutes via GitHub Actions.

## Current State

- Scraper saves JSON files to local `scraped_data/`
- Entry point is `main.py`
- Manual runs only

## Target State

- Data stored in `tillg/swm_pool_data` repo under `pool_scrapes_raw/`
- Entry point renamed to `scrape.py` with `--output-dir` argument
- Automated scrapes every 15 minutes
- Clean separation: code repo vs data repo

---

## Architecture

**Repositories:**
- `tillg/swm_pool_scraper` — scraper code (public)
- `tillg/swm_pool_data` — scraped data storage

The GitHub Action lives in `swm_pool_data` (the data repo). Each run:

1. Checks out itself (data repo)
2. Checks out the scraper tool from `tillg/swm_pool_scraper`
3. Installs Python dependencies via `requirements.txt`
4. Runs `python scraper/scrape.py --output-dir pool_scrapes_raw`
5. Commits and pushes the new data file to itself

This approach is simplest because the workflow commits to its own repo using the built-in `GITHUB_TOKEN` — no cross-repo authentication needed. Since `tillg/swm_pool_scraper` is public, no additional tokens are required.

---

## Implementation

### 1. Rename Entry Point (swm_pool_scraper)

Rename `main.py` to `scrape.py` and ensure it supports:

```bash
python scrape.py --output-dir PATH    # Output directory (default: scraped_data/)
```

The existing `--output-dir` functionality should be preserved. The workflow handles git operations — the scraper just writes files.

### 2. Data Repo Structure (swm_pool_data)

```text
swm_pool_data/
├── .github/workflows/scrape.yml
├── pool_scrapes_raw/
│   └── pool_data_YYYYMMDD_HHMMSS.json
└── README.md
```

### 3. GitHub Action (swm_pool_data)

```yaml
# swm_pool_data/.github/workflows/scrape.yml
name: Scrape Pool Data

on:
  schedule:
    - cron: "*/15 * * * *"
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/checkout@v4
        with:
          repository: tillg/swm_pool_scraper
          path: scraper

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - run: pip install -r scraper/requirements.txt

      - run: python scraper/scrape.py --output-dir pool_scrapes_raw

      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add pool_scrapes_raw/
          git diff --staged --quiet || git commit -m "Scrape $(date -u +%Y-%m-%d\ %H:%M)"
          git push
```

---

## Notes

- **Schedule limits:** GitHub Actions minimum frequency is 5 minutes. Times are approximate under high load.
- **Inactivity:** Public repos auto-disable workflows after 60 days without activity.
- **Commit volume:** 15-min intervals = ~96 commits/day. This is fine for git.
