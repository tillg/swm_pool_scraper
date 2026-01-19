import csv
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .models import PoolOccupancy
from config import DATA_CONFIG, TEST_DATA_DIR, SCRAPED_DATA_DIR, TIMEZONE


class DataStorage:
    def __init__(self, test_mode: bool = False, output_dir: Optional[Path] = None):
        self.test_mode = test_mode
        if output_dir:
            self.data_dir = Path(output_dir)
        else:
            self.data_dir = TEST_DATA_DIR if test_mode else SCRAPED_DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def save_to_csv(self, pool_data: List[PoolOccupancy], filename: str = None) -> Path:
        if not filename:
            filename = DATA_CONFIG["csv_filename"]
        
        filepath = self.data_dir / filename
        file_exists = filepath.exists()
        
        # Create ML-optimized CSV format
        fieldnames = [
            'timestamp', 'pool_name', 'facility_type', 'occupancy_percent', 
            'is_open', 'hour', 'day_of_week', 'is_weekend', 'occupancy_text'
        ]
        
        with open(filepath, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
                self.logger.info(f"Created new Create ML optimized CSV file: {filepath}")
            
            for pool in pool_data:
                writer.writerow(pool.to_csv_row())
        
        self.logger.info(f"Appended {len(pool_data)} records to {filepath}")
        return filepath
    
    def save_to_json(
        self,
        pool_data: List[PoolOccupancy],
        filename: str = None,
        metadata: Dict[str, Any] = None
    ) -> Path:
        if not filename:
            timestamp = datetime.now(TIMEZONE).strftime('%Y%m%d_%H%M%S')
            filename = f"pool_data_{timestamp}.json"

        filepath = self.data_dir / filename

        # Group facilities by type dynamically
        by_type = defaultdict(list)
        for facility in pool_data:
            by_type[facility.facility_type].append(facility)

        scrape_time = datetime.now(TIMEZONE)

        # Build metadata with counts for each type
        scrape_metadata = {
            'total_facilities': len(pool_data),
            'hour': scrape_time.hour,
            'day_of_week': scrape_time.weekday(),
            'is_weekend': scrape_time.weekday() >= 5
        }
        for facility_type, facilities in by_type.items():
            scrape_metadata[f'{facility_type}_count'] = len(facilities)

        if metadata:
            scrape_metadata.update(metadata)

        # Build facilities section with all types
        facilities_by_type = {}
        for facility_type, facilities in sorted(by_type.items()):
            key = f'{facility_type}s'  # pluralize: pool -> pools
            facilities_by_type[key] = [f.to_dict() for f in facilities]

        # Build summary (pools get special treatment for backwards compat)
        pools = by_type.get('pool', [])
        summary = {}
        if pools:
            summary['avg_pool_occupancy'] = (
                sum(p.occupancy_percent or 0 for p in pools) / len(pools)
            )
            summary['busiest_pool'] = max(
                pools, key=lambda x: x.occupancy_percent or 0
            ).pool_name
            summary['quietest_pool'] = min(
                pools, key=lambda x: x.occupancy_percent or 100
            ).pool_name

        data = {
            'scrape_timestamp': scrape_time.isoformat(),
            'scrape_metadata': scrape_metadata,
            **facilities_by_type,
            'summary': summary
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Log counts
        counts = ', '.join(f"{len(v)} {k}" for k, v in sorted(by_type.items()))
        self.logger.info(f"Saved {len(pool_data)} records to {filepath}")
        self.logger.info(f"  - {counts}")
        return filepath
    
    def load_from_csv(self, filename: str = None) -> List[Dict[str, Any]]:
        if not filename:
            filename = DATA_CONFIG["csv_filename"]
        
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            self.logger.warning(f"CSV file not found: {filepath}")
            return []
        
        with open(filepath, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            data = list(reader)
        
        self.logger.info(f"Loaded {len(data)} records from {filepath}")
        return data
    
    def get_latest_json_file(self) -> Path:
        json_files = list(self.data_dir.glob("pool_data_*.json"))
        if not json_files:
            raise FileNotFoundError("No JSON files found")
        
        return max(json_files, key=lambda f: f.stat().st_mtime)
    
    def list_data_files(self) -> Dict[str, List[Path]]:
        return {
            'csv': list(self.data_dir.glob("*.csv")),
            'json': list(self.data_dir.glob("*.json")),
            'html': list(self.data_dir.glob("*.html"))
        }