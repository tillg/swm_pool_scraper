#!/usr/bin/env python3

import json
import csv
import argparse
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from src.models import PoolOccupancy


def load_json_file(json_file: Path) -> Dict[str, Any]:
    """Load a single JSON file"""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def json_to_pool_occupancy(pool_data: Dict[str, Any]) -> PoolOccupancy:
    """Convert JSON dict back to PoolOccupancy object"""
    pool = PoolOccupancy(
        pool_name=pool_data['pool_name'],
        occupancy_level=pool_data['occupancy_level'],
        timestamp=datetime.fromisoformat(pool_data['timestamp']),
        raw_occupancy=pool_data.get('raw_occupancy', '')
    )
    pool.facility_type = pool_data['facility_type']
    return pool


def convert_json_files_to_csv(json_files: List[Path], output_csv: Path):
    """Convert multiple JSON files to a single CSV file"""
    
    fieldnames = [
        'timestamp', 'pool_name', 'facility_type', 'occupancy_percent', 
        'is_open', 'hour', 'day_of_week', 'is_weekend', 'occupancy_text'
    ]
    
    total_records = 0
    
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for json_file in sorted(json_files):
            print(f"Processing {json_file.name}...")
            
            try:
                data = load_json_file(json_file)
                
                # Process pools
                for pool_data in data.get('pools', []):
                    pool = json_to_pool_occupancy(pool_data)
                    writer.writerow(pool.to_csv_row())
                    total_records += 1
                
                # Process saunas
                for sauna_data in data.get('saunas', []):
                    sauna = json_to_pool_occupancy(sauna_data)
                    writer.writerow(sauna.to_csv_row())
                    total_records += 1
                    
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
                continue
    
    print(f"✅ Converted {len(json_files)} JSON files → {total_records} CSV records")
    print(f"📄 Output: {output_csv}")


def main():
    parser = argparse.ArgumentParser(description="Convert JSON pool data files to CSV for Create ML")
    parser.add_argument("--input-dir", type=Path, help="Directory containing JSON files (default: scraped_data/)")
    parser.add_argument("--output", type=Path, help="Output CSV file (default: ml_data.csv)")
    parser.add_argument("--include-test-data", action="store_true", help="Also include test_data/ JSON files")
    
    args = parser.parse_args()
    
    # Set defaults
    if not args.input_dir:
        args.input_dir = Path("scraped_data")
    
    if not args.output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = Path(f"ml_data_{timestamp}.csv")
    
    # Collect JSON files
    json_files = []
    
    # Main data directory
    if args.input_dir.exists():
        json_files.extend(args.input_dir.glob("*.json"))
        print(f"Found {len(json_files)} JSON files in {args.input_dir}")
    else:
        print(f"⚠️  Directory {args.input_dir} not found")
    
    # Include test data if requested
    if args.include_test_data:
        test_dir = Path("test_data")
        if test_dir.exists():
            test_files = list(test_dir.glob("*.json"))
            json_files.extend(test_files)
            print(f"Added {len(test_files)} test JSON files")
    
    if not json_files:
        print("❌ No JSON files found to convert")
        return 1
    
    # Convert to CSV
    convert_json_files_to_csv(json_files, args.output)
    return 0


if __name__ == "__main__":
    exit(main())