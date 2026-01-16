# Architecture for Data Transformation

## Goal

Extend the pool scraping system to include contextual data (weather, holidays) and transform it into ML-ready datasets for Prophet-based occupancy predictions.

**Scope of this spec:** Data loading and transformation only. Prediction, serving, and monitoring will be addressed later.

---

## Architecture

All code and data lives in `swm_pool_data`:

```text
swm_pool_data/
├── pool_scrapes_raw/          # existing raw JSON (every 15 min)
├── weather_raw/               # hourly weather data
│   └── weather_YYYYMMDD.json  # one file per day
├── holidays/
│   ├── public_holidays.json   # German public holidays
│   └── school_holidays.json   # Bavarian school vacations
├── datasets/                  # transformed ML-ready data
│   └── occupancy_features.csv # single growing file, all history
├── src/
│   ├── loaders/
│   │   ├── weather_loader.py
│   │   └── holiday_loader.py
│   └── transform.py
└── .github/workflows/
    ├── scrape.yml             # existing, every 15 min
    ├── load_weather.yml       # daily at 05:00 UTC
    └── transform.yml          # daily at 06:00 UTC
```

This keeps data close to transformations and avoids cross-repo complexity.

---

## Key Decisions

| Decision | Choice | Rationale |
| -------- | ------ | --------- |
| Output format | CSV | Simpler, good ML tool compatibility |
| Historical backfill | No | Start fresh from implementation date |
| Data retention | Keep all | No rolling window, indefinite storage |
| School holidays | Manual JSON from official source | km.bayern.de is authoritative |
| Weather parameters | temperature, precipitation, weather_code, cloud_cover | Sufficient for occupancy correlation |
| File strategy | Single growing file | Simpler for ML consumption, easier deduplication |

---

## Data Sources

| Source | Frequency | Provider |
| ------ | --------- | -------- |
| Weather (historical + forecast) | Daily | Open-Meteo (free, no API key) |
| Bavarian school holidays | Yearly/static | Manual JSON from km.bayern.de |
| German public holidays | Yearly/static | `holidays` Python package |

Weather data will be **hourly** to align with pool occupancy patterns.

---

## Weather Data Loading

### Open-Meteo API

**Endpoint:** `https://api.open-meteo.com/v1/forecast`

**Location:** Munich city center

- Latitude: `48.1351`
- Longitude: `11.5820`

**Parameters:**

```text
?latitude=48.1351
&longitude=11.5820
&hourly=temperature_2m,precipitation,weather_code,cloud_cover
&timezone=Europe/Berlin
&past_days=7
&forecast_days=7
```

**Response fields used:**

| Field | Description | Unit |
| ----- | ----------- | ---- |
| `temperature_2m` | Air temperature at 2m | °C |
| `precipitation` | Total precipitation (rain + snow) | mm |
| `weather_code` | WMO weather code (0=clear, 61-67=rain, etc.) | code |
| `cloud_cover` | Total cloud cover | % |

### Weather File Schema

**File:** `weather_raw/weather_YYYYMMDD.json`

```json
{
  "fetched_at": "2026-01-16T06:00:00+01:00",
  "location": {
    "latitude": 48.1351,
    "longitude": 11.5820,
    "city": "Munich"
  },
  "hourly": [
    {
      "timestamp": "2026-01-16T00:00:00+01:00",
      "temperature_c": 2.5,
      "precipitation_mm": 0.0,
      "weather_code": 3,
      "cloud_cover_percent": 75
    }
  ]
}
```

**Retention:** Keep 90 days of weather files, then archive/delete older files.

### Weather Loader Script

```python
# src/loaders/weather_loader.py
def fetch_weather() -> dict:
    """Fetch 7 days historical + 7 days forecast from Open-Meteo."""
    pass

def save_weather(data: dict, output_dir: Path) -> Path:
    """Save weather data to weather_YYYYMMDD.json."""
    pass
```

---

## Holiday Data

### Public Holidays Schema

**File:** `holidays/public_holidays.json`

Generated using the `holidays` Python package for Bavaria (BY).

```json
{
  "generated_at": "2026-01-01T00:00:00+01:00",
  "region": "DE-BY",
  "years": [2025, 2026, 2027],
  "holidays": [
    {
      "date": "2026-01-01",
      "name": "Neujahr"
    },
    {
      "date": "2026-01-06",
      "name": "Heilige Drei Könige"
    }
  ]
}
```

**Update frequency:** Regenerate annually or when adding a new year.

### School Holidays Schema

**File:** `holidays/school_holidays.json`

**Source:** Bavarian Ministry of Education (https://www.km.bayern.de/ministerium/termine/ferientermine.html)

Bavarian school vacation periods, manually maintained from the official calendar. This is the authoritative source for Bavaria and is updated annually by the ministry.

```json
{
  "updated_at": "2026-01-16T00:00:00+01:00",
  "source": "https://www.km.bayern.de/ministerium/termine/ferientermine.html",
  "vacations": [
    {
      "name": "Winterferien",
      "start": "2026-02-14",
      "end": "2026-02-22"
    }
  ]
}
```

### Holiday Loader Script

```python
# src/loaders/holiday_loader.py
def generate_public_holidays(years: list[int]) -> dict:
    """Generate public holidays using holidays package."""
    pass

def load_school_holidays(path: Path) -> list[tuple[date, date]]:
    """Load school vacation date ranges."""
    pass

def is_holiday(dt: datetime) -> bool:
    """Check if datetime falls on a public holiday."""
    pass

def is_school_vacation(dt: datetime) -> bool:
    """Check if datetime falls within school vacation."""
    pass
```

---

## Transform Pipeline

### Schedule

**Runs:** Daily at 06:00 UTC via GitHub Actions (after weather load at 05:00 UTC)

### Input Files

| Source | Path Pattern | Format |
| ------ | ------------ | ------ |
| Pool occupancy | `pool_scrapes_raw/pool_data_*.json` | JSON (15-min intervals) |
| Weather | `weather_raw/weather_*.json` | JSON (hourly) |
| Public holidays | `holidays/public_holidays.json` | JSON |
| School holidays | `holidays/school_holidays.json` | JSON |

### Data Alignment Strategy

Pool data is recorded every 15 minutes; weather data is hourly.

**Approach:** Join pool records to the weather observation for the same hour.

```text
Pool timestamp: 2026-01-16T10:45:00 → Weather hour: 2026-01-16T10:00:00
Pool timestamp: 2026-01-16T11:15:00 → Weather hour: 2026-01-16T11:00:00
```

Implementation:

```python
def align_weather(pool_timestamp: datetime, weather_df: pd.DataFrame) -> dict:
    """Get weather data for the hour containing pool_timestamp."""
    hour_start = pool_timestamp.replace(minute=0, second=0, microsecond=0)
    return weather_df.loc[hour_start].to_dict()
```

**Missing weather data:** If weather is unavailable for a timestamp, set weather columns to `null`. The transform continues; downstream models handle missing values.

### Output Schema

**File:** `datasets/occupancy_features.csv` (single growing file, all historical data retained)

| Column | Type | Description |
| ------ | ---- | ----------- |
| `timestamp` | datetime | ISO 8601, Europe/Berlin timezone |
| `pool_name` | string | Facility name |
| `facility_type` | string | "pool" or "sauna" |
| `occupancy_percent` | float | 0-100, percent free capacity |
| `is_open` | int | 0 or 1 |
| `hour` | int | 0-23 |
| `day_of_week` | int | 0=Monday, 6=Sunday |
| `month` | int | 1-12 |
| `is_weekend` | int | 0 or 1 |
| `is_holiday` | int | 0 or 1 (public holiday) |
| `is_school_vacation` | int | 0 or 1 |
| `temperature_c` | float | Air temperature, nullable |
| `precipitation_mm` | float | Precipitation, nullable |
| `weather_code` | int | WMO code, nullable |
| `cloud_cover_percent` | int | Cloud cover, nullable |

**File strategy:** Single file, append new records daily. Deduplicate on `(timestamp, pool_name)`.

### Transform Script

```python
# src/transform.py
def load_pool_data(input_dir: Path, since: datetime = None) -> pd.DataFrame:
    """Load pool JSON files, optionally filtering by date."""
    pass

def load_weather_data(input_dir: Path) -> pd.DataFrame:
    """Load and combine weather JSON files into hourly DataFrame."""
    pass

def merge_features(pool_df: pd.DataFrame, weather_df: pd.DataFrame,
                   holidays: list, vacations: list) -> pd.DataFrame:
    """Join pool data with weather and holiday features."""
    pass

def transform(pool_dir: Path, weather_dir: Path, holiday_dir: Path,
              output_path: Path) -> None:
    """Main transform pipeline."""
    pass
```

---

## GitHub Actions Workflows

### Weather Loader Workflow

**File:** `.github/workflows/load_weather.yml`

```yaml
name: Load Weather Data

on:
  schedule:
    - cron: "0 5 * * *"  # Daily at 05:00 UTC (06:00 Berlin winter, 07:00 summer)
  workflow_dispatch:

permissions:
  contents: write

jobs:
  load-weather:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: pip install requests

      - name: Fetch weather data
        run: python src/loaders/weather_loader.py --output-dir weather_raw

      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add weather_raw/
          git diff --staged --quiet || git commit -m "Weather data $(date -u +%Y-%m-%d)"
          git push
```

### Transform Workflow

**File:** `.github/workflows/transform.yml`

```yaml
name: Transform Data

on:
  schedule:
    - cron: "0 6 * * *"  # Daily at 06:00 UTC (after weather load)
  workflow_dispatch:

permissions:
  contents: write

jobs:
  transform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: pip install pandas holidays

      - name: Run transform
        run: python src/transform.py

      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add datasets/
          git diff --staged --quiet || git commit -m "Transform $(date -u +%Y-%m-%d)"
          git push
```

---

## Error Handling

### Weather API Failures

- **Retry:** 3 attempts with exponential backoff (1s, 2s, 4s)
- **On failure:** Log error, exit with code 0 (don't fail the workflow). Weather data will be missing for that day; transform handles nulls.

### Transform Failures

- **Missing weather:** Continue with null weather columns
- **Invalid JSON:** Skip file, log warning, continue with remaining files
- **Empty pool data:** Exit early with warning (no data to transform)

### Data Validation

Before writing output:

- Assert `occupancy_percent` is in range [0, 100]
- Assert `timestamp` is valid ISO 8601
- Assert no duplicate `(timestamp, pool_name)` pairs

---

## Dependencies

**requirements.txt additions:**

```text
requests>=2.31.0
pandas>=2.0.0
holidays>=0.40
```

---

## Deferred Items

These will be addressed in future specs:

- **Prediction pipeline:** Prophet-based, 7-day horizon in 15-min slots
- **Serving layer:** How predictions are consumed
- **Monitoring:** Tracking prediction accuracy
- **Backfill:** Historical weather for existing pool data (decided: not doing backfill)
