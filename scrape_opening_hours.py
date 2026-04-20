#!/usr/bin/env python3
"""Daily CLI: scrape opening hours for every SWM facility.

Operated exactly like scrape.py (see CLAUDE.md / README):
  swm_pool_data's GH Actions workflow invokes
    python scraper/scrape_opening_hours.py --output-dir facility_openings_raw

On success, exits 0 after writing a single facility_opening_*.json.
On any failure, exits non-zero and does NOT write a file — the scheduler
surfaces the failure via its default non-zero-exit email.
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from src.data_storage import DataStorage
from src.logger import setup_logging
from src.opening_hours_scraper import ManagedOpeningHoursScraper


def main() -> int:
    parser = argparse.ArgumentParser(description="SWM Facility Opening Hours Scraper")
    parser.add_argument("--test", action="store_true",
                        help="Run in test mode (save to test_data/)")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--output-dir", type=str,
                        help="Output directory (default: scraped_data/ or test_data/)")
    args = parser.parse_args()

    logger = setup_logging(log_level=args.log_level)
    logger.info("Starting SWM Opening Hours Scraper")

    start = time.time()
    try:
        with ManagedOpeningHoursScraper() as scraper:
            entries = scraper.scrape_opening_hours()
    except Exception as e:
        logger.error(f"Scrape failed: {e}")
        return 1

    duration_ms = (time.time() - start) * 1000
    storage = DataStorage(test_mode=args.test, output_dir=args.output_dir)
    try:
        storage.save_opening_hours(entries, metadata={"duration_ms": duration_ms})
    except Exception as e:
        logger.error(f"Save failed: {e}")
        return 1

    # Compact summary
    print("\nOpening hours:")
    for e in entries:
        flag = "✓" if e.status == "open" else "❄"
        print(f"  {flag} {e.pool_name} ({e.facility_type}): {e.status}")
    print(f"\nCompleted in {duration_ms:.0f}ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
