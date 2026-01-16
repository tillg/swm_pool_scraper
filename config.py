import os
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).parent

# Timezone for Munich pools
TIMEZONE = ZoneInfo("Europe/Berlin")
TEST_DATA_DIR = BASE_DIR / "test_data"
SCRAPED_DATA_DIR = BASE_DIR / "scraped_data"

SWM_URL = "https://www.swm.de/baeder/auslastung"

SELENIUM_CONFIG = {
    "implicit_wait": 10,
    "page_load_timeout": 30,
    "headless": True,
}

DATA_CONFIG = {
    "csv_filename": "pool_occupancy.csv",
    "json_filename": "pool_occupancy.json",
}