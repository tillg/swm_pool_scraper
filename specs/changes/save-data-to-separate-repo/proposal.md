# Save Data to Separate Repository

## Goal

Store scraped pool data in a dedicated `tillg/swm_pool_data` repository and run automated scrapes every 15 minutes via GitHub Actions.

## Architecture

**Repositories:**
- `tillg/swm_pool_scraper` — scraper code (public)
- `tillg/swm_pool_data` — scraped data storage

The GitHub Action lives in `swm_pool_data`. Each run:
1. Checks out itself (data repo)
2. Checks out the scraper from `tillg/swm_pool_scraper`
3. Installs dependencies and runs `python scraper/scrape.py --output-dir pool_scrapes_raw`
4. Commits and pushes the new JSON file

This approach uses the built-in `GITHUB_TOKEN` — no cross-repo auth needed.

---

## Changes Made

### swm_pool_scraper

- **Renamed** `main.py` → `scrape.py`
- **Added** `--output-dir` argument to specify output directory
- **Added** `Europe/Berlin` timezone for all timestamps (filenames and JSON content)

### swm_pool_data

- **Created** `.github/workflows/scrape.yml` — runs every 15 minutes
- **Created** `pool_scrapes_raw/` — stores JSON files
- **Created** `README.md` — documents the data format

---

## Key Details

**Workflow permissions:** The workflow requires `permissions: contents: write` to push commits.

**Timezone:** All timestamps use `Europe/Berlin` so filenames and data reflect Munich local time, regardless of where GitHub Actions runs.

**Schedule:** Cron `*/15 * * * *` runs at :00, :15, :30, :45. GitHub doesn't guarantee exact timing under load.

**Inactivity:** Public repos auto-disable workflows after 60 days without activity.
