#!/usr/bin/env python3

import sys
import argparse
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from src.api_scraper import ManagedAPIScraper, PoolMonitor
from src.scraper import SWMPoolScraper
from src.data_storage import DataStorage
from src.logger import setup_logging


def main():
    parser = argparse.ArgumentParser(description="SWM Pool Occupancy Scraper")
    parser.add_argument("--test", action="store_true", help="Run in test mode (save to test_data/)")
    parser.add_argument("--method", choices=["api", "selenium"], default="api", help="Scraping method (default: api)")
    parser.add_argument("--validate", action="store_true", help="Validate API data against website")
    parser.add_argument("--monitor", action="store_true", help="Check for new facilities")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser in headless mode (selenium only)")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--format", choices=["csv", "json", "both"], default="json", help="Output format")
    
    args = parser.parse_args()
    
    logger = setup_logging(log_level=args.log_level)
    logger.info("Starting SWM Pool Scraper")
    
    try:
        start_time = time.time()
        storage = DataStorage(test_mode=args.test)
        
        # Choose scraping method
        if args.method == "api":
            logger.info("Using API-based scraping (fast & reliable)")
            
            with ManagedAPIScraper() as scraper:
                # Monitor mode
                if args.monitor:
                    logger.info("Running facility monitoring...")
                    monitor = PoolMonitor(scraper)
                    report = monitor.generate_monitoring_report()
                    
                    print("\n📊 Monitoring Report:")
                    print("-" * 40)
                    print(f"Total facilities: {report['registry_status']['total_facilities']}")
                    print(f"Active facilities: {report['registry_status']['active']}")
                    
                    if report['new_facilities']:
                        print(f"\n⚠️ Found {len(report['new_facilities'])} unknown facilities:")
                        for name in report['new_facilities']:
                            print(f"  • {name}")
                    
                    return 0
                
                # Validation mode
                if args.validate:
                    logger.info("Validating API data against website...")
                    validation = scraper.validate_against_website()
                    
                    print("\n✅ Validation Results:")
                    print(f"  • API facilities: {validation['api_facilities']}")
                    print(f"  • Website facilities: {validation['website_facilities']}")
                    print(f"  • Matches: {len(validation['matches'])}")
                    
                    if validation['mismatches']:
                        print("\n⚠️ Mismatches found:")
                        for mismatch in validation['mismatches']:
                            print(f"  • {mismatch['name']}: API={mismatch['api']}, Website={mismatch['website']}")
                
                # Regular scraping
                pool_data = scraper.scrape_pool_data()
        
        else:  # selenium method (fallback)
            logger.info("Using Selenium-based scraping (slower but reliable)")
            
            with SWMPoolScraper(headless=args.headless) as scraper:
                pool_data = scraper.scrape_pool_data()
        
        if not pool_data:
            logger.warning("No pool data scraped")
            return 1
        
        scrape_duration = (time.time() - start_time) * 1000  # milliseconds
        metadata = {
            'duration_ms': scrape_duration,
            'method': args.method
        }
        
        # Save data
        if args.format in ["csv", "both"]:
            storage.save_to_csv(pool_data)
        
        if args.format in ["json", "both"]:
            storage.save_to_json(pool_data, metadata=metadata)
        
        # Enhanced output
        pools = [p for p in pool_data if p.facility_type == 'pool']
        saunas = [p for p in pool_data if p.facility_type == 'sauna']
        
        logger.info(f"Successfully scraped {len(pool_data)} facilities in {scrape_duration:.0f}ms")
        
        print("\n📊 Current Pool Occupancy:")
        print("-" * 40)
        
        if pools:
            print("\n🏊 Swimming Pools:")
            for pool in sorted(pools, key=lambda x: x.pool_name):
                percent = pool.occupancy_percent
                status = "🟢" if percent and percent > 50 else "🟡" if percent and percent > 20 else "🔴"
                print(f"  {status} {pool.pool_name}: {pool.occupancy_level}")
        
        if saunas:
            print("\n🧖 Saunas:")
            for sauna in sorted(saunas, key=lambda x: x.pool_name):
                percent = sauna.occupancy_percent
                status = "🟢" if percent and percent > 50 else "🟡" if percent and percent > 20 else "🔴"
                print(f"  {status} {sauna.pool_name}: {sauna.occupancy_level}")
        
        print(f"\n⏱️ Completed in {scrape_duration:.0f}ms using {args.method.upper()}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())