# SWM Pool Scraper

A production-ready web scraper for collecting real-time pool occupancy data from Stadtwerke München (SWM). The scraper targets https://www.swm.de/baeder/auslastung to gather indoor pool, sauna, and ice rink capacity information for machine learning applications.

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
