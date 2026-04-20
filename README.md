# SWM Pool Scraper

A production-ready web scraper for collecting real-time pool occupancy data from Stadtwerke München (SWM). The scraper targets https://www.swm.de/baeder/auslastung to gather indoor pool, sauna, and ice rink capacity information for machine learning applications.

## Resume next session (2026-04-20)

> Session handoff note. Delete this section once the opening-hours
> workflow is running daily in production.

The opening-hours scraper (`scrape_opening_hours.py`) is **shipped and
pushed** to `main`. Implementation is complete on this repo side.

**Blocking next step:** `tillg/swm_pool_data` needs to gain a
`Load Opening Hours` workflow that invokes the new CLI daily. A colleague
agent is working on that PR; the full handoff brief (drop-in workflow
YAML + directory README + verification commands) was shared in the
previous chat session.

**Pick up with:**

```bash
# 1. Has the colleague shipped the workflow?
gh api /repos/tillg/swm_pool_data/actions/workflows --jq '.workflows[].name'
# → look for "Load Opening Hours"

# 2. If yes, trigger the first run and stream logs:
gh workflow run load_opening_hours.yml -R tillg/swm_pool_data
gh run watch -R tillg/swm_pool_data

# 3. Verify the commit that should land on swm_pool_data/main:
gh api /repos/tillg/swm_pool_data/contents/facility_openings_raw \
  --jq '.[].name' | head
# → expect one facility_opening_YYYYMMDD_HHMMSS.json with
#   total_facilities:17, open_count≥16, ice rink closed_for_season.
```

If the first run fails with `ParseError`, SWM markup drifted — fix the
offending heading in `src/facility_pages.py` or the parser itself in
`src/opening_hours_parser.py`, push, and re-run.

**Follow-ups (not urgent, not yet on a spec):**

- Join `facility_opening_*.json` into `swm_pool_data/transform.py` so ML
  rows carry an `is_scheduled_open` feature.
- Capture seasonal/special schedules (Frauenbadetag, Wellenzeiten, …) as
  structured date-range overrides instead of free-form `special_notes`.
- Optional CSV view of opening hours parallel to the occupancy CSV.

## Features

- **API-based scraping** - Direct access to Ticos counter API (fast and reliable)
- **Real-time data collection** - Monitors occupancy for 9 pools, 7 saunas, and 1 ice rink
- **ML-optimized output** - Rich JSON data with Create ML-ready CSV conversion
- **Time-based features** - Hour, day-of-week, weekend indicators for temporal modeling
- **Analytics ready** - Summary statistics and metadata included
- **Dual-mode operation** - API (fast) or Selenium (fallback) scraping methods

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Scrape data (saves to scraped_data/)
python scrape.py

# Convert to CSV for Create ML
python json_to_csv.py --include-test-data
```

## Architecture

**Data Collection Methods:**
1. **API Mode (Default)** - Direct calls to `counter.ticos-systems.cloud` API
2. **Selenium Mode (Fallback)** - Browser automation if API changes

**Project Structure:**
```
swm_pool_scraper/
├── scrape.py              # Main scraper CLI
├── json_to_csv.py         # CSV converter for Create ML
├── src/
│   ├── facilities.py      # Facility name to org_id mappings
│   ├── api_scraper.py     # API-based scraping (fast)
│   ├── scraper.py         # Selenium-based scraping (fallback)
│   ├── facility_registry.py # Facility registry wrapper
│   ├── models.py          # Data models with ML features
│   ├── data_storage.py    # JSON/CSV output handling
│   └── logger.py          # Logging configuration
├── scraped_data/          # Production JSON data (tracked in git)
└── test_data/             # Development data (ignored)
```

## Data Format

**JSON Output** (Rich metadata):
```json
{
  "scrape_timestamp": "2026-01-19T08:28:51.215664+01:00",
  "scrape_metadata": {
    "total_facilities": 17,
    "pools_count": 9,
    "saunas_count": 7,
    "method": "api"
  },
  "pools": [
    {
      "pool_name": "Nordbad",
      "facility_type": "pool",
      "occupancy_percent": 78.0,
      "is_weekend": false,
      "hour": 8
    }
  ],
  "saunas": [...],
  "summary": {
    "avg_pool_occupancy": 85.2,
    "busiest_pool": "Cosimawellenbad"
  }
}
```

**CSV Output** (Create ML Ready):

```csv
timestamp,pool_name,facility_type,occupancy_percent,hour,day_of_week,is_weekend
2026-01-19T08:28:47,Nordbad,pool,78.0,8,0,0
```

## Timestamp Handling

All timestamps use **Europe/Berlin local time** with the correct UTC offset (CET = `+01:00` in winter, CEST = `+02:00` in summer). This is intentional: pool usage patterns are driven by wall-clock time, not UTC.

**How it works:**

- A single timestamp is captured per scrape batch via `datetime.now(ZoneInfo("Europe/Berlin"))` (see `config.py`)
- All time-based features (`hour`, `day_of_week`, `is_weekend`) are derived from this timezone-aware datetime (see `src/models.py`)
- Output timestamps are serialized with `.isoformat()`, preserving the correct offset

**Example:** A scrape at 2 PM on a summer day produces:
```json
{
  "timestamp": "2026-07-15T14:00:00.123456+02:00",
  "hour": 14,
  "day_of_week": 2,
  "is_weekend": false
}
```

**For downstream consumers** (e.g., [swm_pool_data](https://github.com/tillg/swm_pool_data)): timestamps may contain mixed offsets across a DST boundary. Always parse with a UTC-first strategy (`pd.to_datetime(..., utc=True)`) and convert to Berlin time, rather than assuming a fixed offset.

## Tech Stack

- **Python 3.13** - Base language
- **Requests** - HTTP client for API calls
- **Selenium** - Browser automation (fallback mode)
- **Beautiful Soup** - HTML parsing
- **JSON/CSV** - Data storage formats

## Usage Examples

**Regular Data Collection:**
```bash
# API mode (fast, ~2 seconds)
python scrape.py

# Selenium mode (fallback, ~10 seconds)
python scrape.py --method selenium

# Test mode (saves to test_data/)
python scrape.py --test

# Custom output directory
python scrape.py --output-dir /path/to/output

# Run every 15 minutes via cron
*/15 * * * * cd /path/to/scraper && python scrape.py
```

**Opening Hours (daily):**
```bash
# Scrape published opening hours for all 17 facilities
python scrape_opening_hours.py

# Test mode (saves to test_data/)
python scrape_opening_hours.py --test

# Custom output directory (used by the swm_pool_data GH Actions workflow)
python scrape_opening_hours.py --output-dir facility_openings_raw
```

Output file: `facility_opening_YYYYMMDD_HHMMSS.json`, same directory
convention as the occupancy snapshots. Each entry carries a `status` of
`open` (weekly schedule populated) or `closed_for_season` (e.g. the ice
rink outside ice season). Any other parse failure is fatal — the scheduler
emails the operator so markup drift is noticed immediately.

Example entry:
```json
{
  "pool_name": "Cosimawellenbad",
  "facility_type": "pool",
  "status": "open",
  "url": "https://www.swm.de/baeder/cosimawellenbad",
  "heading": "Öffnungszeiten Hallenbad",
  "weekly_schedule": {
    "monday":   [{"open": "07:30", "close": "23:00"}],
    "saturday": [{"open": "07:30", "close": "23:00"}]
  },
  "special_notes": ["Kassenschluss: 30 Minuten vor Ende der Öffnungszeit"]
}
```

Pool + sauna at the same address (6 pool+sauna pages plus Dantebad) produce
two entries from a single fetched page, distinguished by
`(pool_name, facility_type)` and their respective `heading` text.

Adding a new facility: register it in `src/facilities.py` and add a
`PageBinding(url, heading)` entry to `src/facility_pages.py`. The heading
must match the facility's opening-hours heading on its SWM page verbatim.
Tests in `tests/test_facility_pages_coverage.py` enforce 1:1 coverage.

**Create ML Training:**
```bash
# Convert all historical data to CSV
python json_to_csv.py --include-test-data

# Train your model in Swift/Create ML
import CreateML
let dataTable = try MLDataTable(contentsOf: URL(fileURLWithPath: "ml_data.csv"))
let regressor = try MLRegressor(trainingData: dataTable, targetColumn: "occupancy_percent")
```

**Data Analysis:**
```bash
# View latest JSON data
python -m json.tool scraped_data/pool_data_*.json | tail -50
```

## Facility Management

The scraper uses a static facility registry in `src/facilities.py`. This maps facility names and types to their Ticos API organization IDs.

**Current facilities (17 total):**
- 9 swimming pools (Hallenbäder)
- 7 saunas
- 1 ice rink

**Adding new facilities:**
1. Find the new facility on the SWM website
2. Discover its org_id by probing the API (IDs are roughly sequential around 30xxx)
3. Add the mapping to `src/facilities.py`
4. Run tests to verify: `python -m pytest tests/test_facility_coverage.py -v`

**Note:** Facilities are never deleted from the registry. If a facility returns no data, it's likely closed — the scraper skips it gracefully.

## Testing

**Run All Tests:**
```bash
# Complete test suite
python -m pytest tests/ -v
```

**Run Specific Test Suites:**
```bash
# API scraper tests only
python -m pytest tests/test_api_scraper.py -v

# Data storage tests only
python -m pytest tests/test_data_storage.py -v

# Facility coverage tests (verify all facilities registered)
python -m pytest tests/test_facility_coverage.py -v
```

**Test Configuration:**
- Tests are configured via `pytest.ini`
- Test files follow the pattern `test_*.py` in the `tests/` directory
- Use `-v` flag for verbose output

**Facility Coverage Tests (`test_facility_coverage.py`):**
These tests verify the scraper's facility registry matches expected counts:
- `test_all_pools_are_registered` - Checks all 9 pools are registered
- `test_all_saunas_are_registered` - Checks all 7 saunas are registered
- `test_all_ice_rinks_are_registered` - Checks all ice rinks are registered
- `test_total_facility_count` - Verifies total count (17 facilities)

