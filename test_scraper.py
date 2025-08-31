#!/usr/bin/env python3

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from src.scraper import SWMPoolScraper
from src.data_storage import DataStorage
from src.logger import setup_logging


def test_scraper():
    logger = setup_logging(log_level="DEBUG")
    logger.info("Testing SWM Pool Scraper")
    
    storage = DataStorage(test_mode=True)
    
    try:
        with SWMPoolScraper(headless=False) as scraper:
            logger.info("Scraping pool data...")
            pool_data = scraper.scrape_pool_data()
            
            logger.info(f"Scraped {len(pool_data)} pools")
            for pool in pool_data:
                logger.info(f"Pool: {pool.pool_name}")
                logger.info(f"  Occupancy: {pool.occupancy_level}")
                logger.info(f"  Raw data: {pool.raw_occupancy[:100]}...")
                logger.info("---")
            
            if pool_data:
                csv_path = storage.save_to_csv(pool_data)
                json_path = storage.save_to_json(pool_data)
                
                logger.info(f"Data saved to:")
                logger.info(f"  CSV: {csv_path}")
                logger.info(f"  JSON: {json_path}")
            else:
                logger.warning("No data to save")
    
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    test_scraper()