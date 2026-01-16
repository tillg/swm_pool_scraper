# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python web scraping project for collecting pool occupancy data from Stadtwerke München (SWM). The scraper targets https://www.swm.de/baeder/auslastung to gather indoor pool capacity information for machine learning purposes.

## Architecture

- **API-based scraping**: Direct calls to `https://counter.ticos-systems.cloud/api/gates/counter`
- **Facility registry**: Manages organization ID to pool name mappings in `config/facilities.json`
- **Dual-mode operation**: API (primary) and Selenium (fallback) scraping methods
- **Monitoring system**: Automatic detection of new facilities and capacity changes
- **Modular design**: Separation of concerns with registry, scraper, and monitor components

## Tech Stack

- **Python 3.13** - Base language
- **Requests** - HTTP client for API calls
- **Selenium** - Browser automation (fallback mode)
- **Beautiful Soup** - HTML parsing for validation
- **JSON/CSV** - Data storage formats
- **Logging** - Error tracking and monitoring

## Key Technical Details

### API Discovery
The Ticos counter API was discovered by monitoring network traffic:
- Endpoint: `https://counter.ticos-systems.cloud/api/gates/counter`
- Parameter: `organizationUnitIds={org_id}`
- Response: `{"organizationUnitId": 30195, "personCount": 72, "maxPersonCount": 311}`
- No authentication required, but uses Origin/Referer headers

### Organization ID Mapping
Organization IDs are internal identifiers that must be mapped to pool names:
- IDs are sequential (30184-30208 currently)
- Mappings stored in `config/facilities.json`
- Auto-updates capacity when changes detected
- Pool IDs: 30195, 30190, 30208, 30197, 30184, 30187, 30199
- Sauna IDs: 30191, 30200, 30203, 30185, 30188, 30207

## Usage

### Installation

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Scraper

```bash
# API mode (default, fast ~2s)
python scrape.py

# Selenium mode (fallback, ~10s)
python scrape.py --method selenium

# Monitor for new facilities
python scrape.py --monitor

# Validate API vs website
python scrape.py --validate

# Test mode (saves to test_data/)
python scrape.py --test

# With debug logging
python scrape.py --test --log-level DEBUG

# Custom output directory
python scrape.py --output-dir /path/to/output
```

### Converting to CSV for Create ML
```bash
# Convert all JSON files to CSV
python json_to_csv.py

# Include test data
python json_to_csv.py --include-test-data

# Specify custom output
python json_to_csv.py --output my_ml_data.csv

# Convert specific directory
python json_to_csv.py --input-dir path/to/json/files
```

### Testing the Scraper
```bash
# Run test script with visible browser
python test_scraper.py
```


### Current Data Extraction

The scraper successfully extracts real-time occupancy data with full Create ML optimization:

**Swimming Pools (Hallenbäder):**
- Bad Giesing-Harlaching
- Cosimawellenbad  
- Michaelibad
- Nordbad
- Südbad
- Westbad

**Saunas:**
- Cosimawellenbad
- Dantebad
- Michaelibad
- Nordbad
- Südbad
- Westbad

### Data Formats for Machine Learning

**CSV Format (Create ML Ready):**
```csv
timestamp,pool_name,facility_type,occupancy_percent,is_open,hour,day_of_week,is_weekend,occupancy_text
2025-08-31T10:51:32,Bad Giesing-Harlaching,pool,85.0,1,10,6,1,85 % frei
2025-08-31T10:51:32,Cosimawellenbad,sauna,100.0,1,10,6,1,100 % frei
```

**Features for ML Models:**
- `occupancy_percent`: Numeric target variable (0-100)
- `facility_type`: Categorical (pool/sauna)  
- `hour`: Time feature (0-23)
- `day_of_week`: Day feature (0-6, Monday=0)
- `is_weekend`: Boolean feature (0/1)
- `is_open`: Operational status (0/1)

**JSON Format (Rich Metadata):**
- Separated pools and saunas sections
- Summary statistics (averages, busiest/quietest facilities)
- Scrape timing and performance metrics
- Full feature extraction for each facility

## Data Collection Workflow

**Primary Usage (Recommended):**
```bash
# 1. Collect data regularly (creates timestamped JSON files)
python scrape.py

# 2. When ready for ML training, convert all historical data
python json_to_csv.py --include-test-data

# 3. Use the generated CSV with Apple's Create ML
# → Results in ml_data_YYYYMMDD_HHMMSS.csv
```

**Development/Testing:**
```bash
# Test mode (saves to test_data/, not tracked in git)
python scrape.py --test

# Debug with visible browser
python scrape.py --test --headless=false --log-level DEBUG
```

## Data Management

**Git Tracking:**
- ✅ `scraped_data/*.json` - Production data (tracked)
- ❌ `test_data/` - Development data (ignored)
- ❌ `*.csv` - Generated files (ignored, recreated from JSON)
- ❌ `*.log` - Log files (ignored)

**File Organization:**
- **JSON files**: Rich metadata, human-readable, version-controlled
- **CSV files**: ML-optimized, generated on-demand, not stored in git
- **Logs**: Debug info, rotating daily, ignored by git

## Project Structure

The project now contains a complete, functional web scraping implementation:

```
swm_pool_scraper/
├── config/
│   └── facilities.json     # Organization ID to pool name mappings
├── src/
│   ├── __init__.py
│   ├── api_scraper.py      # API-based scraper (primary method)
│   ├── scraper.py          # Selenium-based scraper (fallback)
│   ├── facility_registry.py # Facility management & discovery
│   ├── data_storage.py     # CSV/JSON file operations
│   ├── models.py           # PoolOccupancy data class
│   └── logger.py           # Logging configuration
├── test_data/              # Test mode scraped data
├── scraped_data/           # Production scraped data
├── logs/                   # Application logs
├── scrape.py               # CLI entry point with multiple modes
├── json_to_csv.py          # Convert JSON to ML-ready CSV
├── test_scraper.py         # Debug/test script
├── requirements.txt        # Python dependencies
├── config.py               # Configuration settings
├── .venv/                  # Python virtual environment
└── .gitignore             # Git ignore rules
```

## Monitoring for New Facilities

### Automatic Detection
Run `python scrape.py --monitor` to check for new facilities. This will:
1. Scrape website for all pool names
2. Compare with `config/facilities.json`
3. Report any unknown facilities
4. Check for capacity changes

### Manual Discovery Process
When a new facility is detected:

1. **Identify the new facility name** from monitoring output
2. **Find its organization ID** by probing nearby IDs:
   ```python
   from src.api_scraper import SWMAPIScraper
   scraper = SWMAPIScraper()
   for org_id in range(30210, 30220):
       data = scraper.fetch_occupancy(org_id)
       if data:
           print(f"Found: {org_id} - Capacity: {data['maxPersonCount']}")
   ```
3. **Update the registry** in `config/facilities.json`:
   ```json
   {
     "org_id": 30215,
     "name": "New Pool Name",
     "facility_type": "pool",
     "max_capacity": null,
     "active": true
   }
   ```
4. **Validate** with `python scrape.py --validate`

### Alert System
The system automatically:
- Logs warnings for new facilities
- Tracks capacity changes
- Creates `alerts.json` for historical record
- Can be extended to send email/Slack notifications