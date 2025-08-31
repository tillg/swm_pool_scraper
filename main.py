#!/usr/bin/env python3

import sys
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from src.scraper import SWMPoolScraper
from src.data_storage import DataStorage
from src.logger import setup_logging


def main():
    parser = argparse.ArgumentParser(description="SWM Pool Occupancy Scraper")
    parser.add_argument("--test", action="store_true", help="Run in test mode (save to test_data/)")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser in headless mode")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--format", choices=["csv", "json", "both"], default="json", help="Output format")
    
    args = parser.parse_args()
    
    logger = setup_logging(log_level=args.log_level)
    logger.info("Starting SWM Pool Scraper")
    
    try:
        import time
        start_time = time.time()
        
        storage = DataStorage(test_mode=args.test)
        
        with SWMPoolScraper(headless=args.headless) as scraper:
            pool_data = scraper.scrape_pool_data()
            
            if not pool_data:
                logger.warning("No pool data scraped")
                return 1
            
            scrape_duration = (time.time() - start_time) * 1000  # milliseconds
            metadata = {'duration_ms': scrape_duration}
            
            if args.format in ["csv", "both"]:
                storage.save_to_csv(pool_data)
            
            if args.format in ["json", "both"]:
                storage.save_to_json(pool_data, metadata=metadata)
            
            # Enhanced logging with facility types
            pools = [p for p in pool_data if p.facility_type == 'pool']
            saunas = [p for p in pool_data if p.facility_type == 'sauna']
            
            logger.info(f"Successfully scraped data: {len(pools)} pools, {len(saunas)} saunas ({scrape_duration:.0f}ms)")
            
            for pool in pools:
                logger.info(f"  Pool {pool.pool_name}: {pool.occupancy_percent}% free")
            for sauna in saunas:
                logger.info(f"  Sauna {sauna.pool_name}: {sauna.occupancy_percent}% free")
        
        return 0
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())