# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python web scraping project for collecting pool occupancy data from Stadtwerke München (SWM). The scraper targets https://www.swm.de/baeder/auslastung to gather indoor pool capacity information for machine learning purposes.

## Architecture

- **Simple Python script**: Single-execution scraper that fetches data and appends to a file
- **Modular design**: Proper Python modules structure planned
- **Test data storage**: Save scraped data to `./test_data/` for development and tuning

## Tech Stack

- **Python 3.13** - Base language
- **Selenium** - Browser automation for JavaScript-rendered content
- **Beautiful Soup** - HTML parsing after page load
- **Requests** - HTTP requests (fallback)
- **CSV/JSON** - Data storage formats
- **Logging** - Error tracking and monitoring

## Development Plan

**Key Finding**: The SWM website loads occupancy data dynamically via JavaScript, requiring browser automation rather than simple HTTP requests.

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
# Basic usage (saves JSON to scraped_data/)
python main.py

# Test mode (saves JSON to test_data/)
python main.py --test

# Force CSV format if needed
python main.py --format csv

# Non-headless browser (for debugging)
python main.py --test --headless=false

# With debug logging
python main.py --test --log-level DEBUG
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
python main.py

# 2. When ready for ML training, convert all historical data
python json_to_csv.py --include-test-data

# 3. Use the generated CSV with Apple's Create ML
# → Results in ml_data_YYYYMMDD_HHMMSS.csv
```

**Development/Testing:**
```bash
# Test mode (saves to test_data/, not tracked in git)
python main.py --test

# Debug with visible browser
python main.py --test --headless=false --log-level DEBUG
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
├── src/
│   ├── __init__.py
│   ├── scraper.py          # Selenium-based scraper with fallback parsing
│   ├── data_storage.py     # CSV/JSON file operations
│   ├── models.py           # PoolOccupancy data class
│   └── logger.py           # Logging configuration
├── test_data/              # Test mode scraped data
├── scraped_data/           # Production scraped data
├── logs/                   # Application logs
├── main.py                 # CLI entry point
├── test_scraper.py         # Debug/test script
├── requirements.txt        # Python dependencies
├── config.py               # Configuration settings
├── .venv/                  # Python virtual environment
└── .gitignore             # Git ignore rules
```