# SWM Pool Scraper

A production-ready web scraper for collecting real-time pool occupancy data from Stadtwerke München (SWM). The scraper targets https://www.swm.de/baeder/auslastung to gather indoor pool and sauna capacity information for machine learning applications.

## Features

- 🚀 **API-based scraping** - Direct access to Ticos counter API (10x faster than web scraping)
- 🏊‍♂️ **Real-time data collection** - Monitors occupancy for 7 pools and 6 saunas
- 📊 **ML-optimized output** - Rich JSON data with Create ML-ready CSV conversion
- 🕐 **Time-based features** - Hour, day-of-week, weekend indicators for temporal modeling  
- 🔍 **Automatic monitoring** - Detects new facilities and capacity changes
- 📈 **Analytics ready** - Summary statistics and metadata included
- 🔄 **Dual-mode operation** - API (fast) or Selenium (fallback) scraping methods

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Scrape data (saves to scraped_data/)
python main.py

# Convert to CSV for Create ML
python json_to_csv.py --include-test-data
```

## Architecture

**Data Collection Methods:**
1. **API Mode (Default)** - Direct calls to `counter.ticos-systems.cloud` API
2. **Selenium Mode (Fallback)** - Browser automation if API changes
3. **Monitoring Mode** - Checks for new facilities and changes
4. **Validation Mode** - Compares API data with website display

**Project Structure:**
```
swm_pool_scraper/
├── main.py                # Main scraper with multiple modes
├── json_to_csv.py         # CSV converter for Create ML
├── config/
│   └── facilities.json    # Organization ID to pool name mappings
├── src/
│   ├── api_scraper.py     # API-based scraping (fast)
│   ├── scraper.py         # Selenium-based scraping (fallback)
│   ├── facility_registry.py # Facility management & discovery
│   ├── models.py          # Data models with ML features
│   ├── data_storage.py    # JSON/CSV output handling
│   └── logger.py          # Logging configuration
├── scraped_data/          # Production JSON data (tracked in git)
└── test_data/            # Development data (ignored)
```

## Data Format

**JSON Output** (Rich metadata):
```json
{
  "scrape_timestamp": "2025-08-31T13:01:14.168",
  "scrape_metadata": {
    "pools_count": 6,
    "saunas_count": 6,
    "avg_pool_occupancy": 60.17,
    "busiest_pool": "Bad Giesing-Harlaching"
  },
  "pools": [
    {
      "pool_name": "Nordbad",
      "occupancy_percent": 36.0,
      "is_weekend": true,
      "hour": 13
    }
  ]
}
```

**CSV Output** (Create ML Ready):

```csv
timestamp,pool_name,facility_type,occupancy_percent,hour,day_of_week,is_weekend
2025-08-31T13:01:14,Nordbad,pool,36.0,13,6,1
```

## Tech Stack

- **Python 3.13** - Base language
- **Selenium** - Browser automation for dynamic content
- **Beautiful Soup** - HTML parsing
- **Chrome WebDriver** - Automated browser control
- **JSON/CSV** - Data storage formats

## Monitoring for New Facilities

The scraper includes automatic monitoring to detect when SWM adds new pools or saunas:

**Check for New Facilities:**
```bash
# Run monitoring check
python main.py --monitor

# This will:
# 1. Check the website for unknown pool names
# 2. Compare with config/facilities.json
# 3. Report any new facilities found
```

**Validate API vs Website:**
```bash
# Ensure API data matches website display
python main.py --validate

# Reports any mismatches between API and website
```

**Manual Discovery Process:**
1. Check monitoring report for unknown facilities
2. Look for patterns in organization IDs (they're sequential)
3. Update `config/facilities.json` with new mappings
4. Test with `python main.py --method api`

**Automatic Alerts:**
- New facilities are logged as warnings
- Capacity changes are tracked automatically
- Check `alerts.json` for historical changes

## Usage Examples

**Regular Data Collection:**
```bash
# API mode (fast, ~2 seconds)
python main.py

# Selenium mode (fallback, ~10 seconds)
python main.py --method selenium

# Run every 15 minutes via cron
*/15 * * * * cd /path/to/scraper && python main.py
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

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.