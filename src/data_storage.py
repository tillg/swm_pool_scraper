import csv
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .models import PoolOccupancy
from config import DATA_CONFIG, TEST_DATA_DIR, SCRAPED_DATA_DIR


class DataStorage:
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.data_dir = TEST_DATA_DIR if test_mode else SCRAPED_DATA_DIR
        self.data_dir.mkdir(exist_ok=True)
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
    
    def save_to_json(self, pool_data: List[PoolOccupancy], filename: str = None, metadata: Dict[str, Any] = None) -> Path:
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"pool_data_{timestamp}.json"
        
        filepath = self.data_dir / filename
        
        # Separate pools and saunas for better organization
        pools = [p for p in pool_data if p.facility_type == 'pool']
        saunas = [p for p in pool_data if p.facility_type == 'sauna']
        unknown = [p for p in pool_data if p.facility_type == 'unknown']
        
        scrape_time = datetime.now()
        
        data = {
            'scrape_timestamp': scrape_time.isoformat(),
            'scrape_metadata': {
                'total_facilities': len(pool_data),
                'pools_count': len(pools),
                'saunas_count': len(saunas),
                'unknown_count': len(unknown),
                'scrape_duration_ms': metadata.get('duration_ms') if metadata else None,
                'hour': scrape_time.hour,
                'day_of_week': scrape_time.weekday(),
                'is_weekend': scrape_time.weekday() >= 5
            },
            'pools': [pool.to_dict() for pool in pools],
            'saunas': [sauna.to_dict() for sauna in saunas],
            'unknown_facilities': [u.to_dict() for u in unknown] if unknown else [],
            'summary': {
                'avg_pool_occupancy': sum(p.occupancy_percent or 0 for p in pools) / len(pools) if pools else 0,
                'avg_sauna_occupancy': sum(s.occupancy_percent or 0 for s in saunas) / len(saunas) if saunas else 0,
                'busiest_pool': max(pools, key=lambda x: x.occupancy_percent or 0).pool_name if pools else None,
                'quietest_pool': min(pools, key=lambda x: x.occupancy_percent or 100).pool_name if pools else None
            }
        }
        
        if metadata:
            data['scrape_metadata'].update(metadata)
        
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved {len(pool_data)} records to {filepath}")
        self.logger.info(f"  - {len(pools)} pools, {len(saunas)} saunas")
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