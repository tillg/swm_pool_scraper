"""
Unit tests for data storage functionality
Tests CSV/JSON file operations, directory handling, and data formats
"""

import pytest
import json
import csv
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock

from src.data_storage import DataStorage
from src.models import PoolOccupancy


class TestDataStorage:
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_pool_data(self):
        """Sample pool data for testing"""
        timestamp = datetime(2025, 8, 31, 14, 30, 0)
        pools = [
            PoolOccupancy(
                pool_name="Bad Giesing-Harlaching",
                occupancy_level="75 % frei",
                timestamp=timestamp,
                raw_occupancy="78/311 persons"
            ),
            PoolOccupancy(
                pool_name="Cosimawellenbad",
                occupancy_level="85 % frei", 
                timestamp=timestamp,
                raw_occupancy="80/530 persons"
            ),
            PoolOccupancy(
                pool_name="Westbad Sauna",
                occupancy_level="90 % frei",
                timestamp=timestamp,
                raw_occupancy="6/60 persons"
            )
        ]
        
        # Set facility types
        pools[0].facility_type = "pool"
        pools[1].facility_type = "pool" 
        pools[2].facility_type = "sauna"
        
        return pools
    
    def test_initialization_production_mode(self, temp_dir):
        """Test DataStorage initialization in production mode"""
        with patch('src.data_storage.SCRAPED_DATA_DIR', temp_dir / "scraped"):
            storage = DataStorage(test_mode=False)
            
            assert storage.test_mode is False
            assert storage.data_dir == temp_dir / "scraped"
            assert storage.data_dir.exists()
    
    def test_initialization_test_mode(self, temp_dir):
        """Test DataStorage initialization in test mode"""
        with patch('src.data_storage.TEST_DATA_DIR', temp_dir / "test"):
            storage = DataStorage(test_mode=True)
            
            assert storage.test_mode is True
            assert storage.data_dir == temp_dir / "test"
            assert storage.data_dir.exists()
    
    def test_save_to_csv_new_file(self, temp_dir, sample_pool_data):
        """Test saving to CSV creates new file with headers"""
        with patch('src.data_storage.SCRAPED_DATA_DIR', temp_dir):
            storage = DataStorage(test_mode=False)
            
            filepath = storage.save_to_csv(sample_pool_data, "test_output.csv")
            
            assert filepath.exists()
            assert filepath.name == "test_output.csv"
            
            # Check CSV content
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                assert len(rows) == 3
                
                # Check headers
                expected_headers = {
                    'timestamp', 'pool_name', 'facility_type', 'occupancy_percent',
                    'is_open', 'hour', 'day_of_week', 'is_weekend', 'occupancy_text'
                }
                assert set(reader.fieldnames) == expected_headers
                
                # Check first row data
                first_row = rows[0]
                assert first_row['pool_name'] == "Bad Giesing-Harlaching"
                assert first_row['facility_type'] == "pool"
                assert first_row['occupancy_percent'] == "75.0"
                assert first_row['is_open'] == "1"
                assert first_row['hour'] == "14"
                assert first_row['day_of_week'] == "6"  # Sunday
                assert first_row['is_weekend'] == "1"
                assert first_row['occupancy_text'] == "75 % frei"
    
    def test_save_to_csv_append_mode(self, temp_dir, sample_pool_data):
        """Test saving to CSV appends to existing file"""
        with patch('src.data_storage.SCRAPED_DATA_DIR', temp_dir):
            storage = DataStorage(test_mode=False)
            
            # First save
            filepath = storage.save_to_csv(sample_pool_data[:2], "append_test.csv")
            
            # Second save (should append)
            storage.save_to_csv(sample_pool_data[2:], "append_test.csv")
            
            # Check total content
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                assert len(rows) == 3  # 2 + 1
                
                # Should only have headers once
                content = filepath.read_text()
                header_count = content.count('timestamp,pool_name')
                assert header_count == 1
    
    def test_save_to_csv_default_filename(self, temp_dir, sample_pool_data):
        """Test saving to CSV with default filename"""
        with patch('src.data_storage.SCRAPED_DATA_DIR', temp_dir):
            with patch('src.data_storage.DATA_CONFIG', {"csv_filename": "default.csv"}):
                storage = DataStorage(test_mode=False)
                
                filepath = storage.save_to_csv(sample_pool_data)
                
                assert filepath.name == "default.csv"
    
    def test_save_to_json_with_filename(self, temp_dir, sample_pool_data):
        """Test saving to JSON with specific filename"""
        # Mock datetime.now() to return the same time as the fixture's timestamp
        mock_time = datetime(2025, 8, 31, 14, 30, 0)
        with patch('src.data_storage.SCRAPED_DATA_DIR', temp_dir):
            with patch('src.data_storage.datetime') as mock_dt:
                mock_dt.now.return_value = mock_time
                storage = DataStorage(test_mode=False)

                metadata = {'duration_ms': 1500, 'method': 'api'}
                filepath = storage.save_to_json(sample_pool_data, "specific.json", metadata)
            
            assert filepath.exists()
            assert filepath.name == "specific.json"
            
            # Check JSON content
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                assert 'scrape_timestamp' in data
                assert 'scrape_metadata' in data
                assert 'pools' in data
                assert 'saunas' in data
                assert 'summary' in data
                
                # Check metadata
                metadata_section = data['scrape_metadata']
                assert metadata_section['total_facilities'] == 3
                assert metadata_section['pools_count'] == 2
                assert metadata_section['saunas_count'] == 1
                assert metadata_section['duration_ms'] == 1500
                assert metadata_section['hour'] == 14
                assert metadata_section['day_of_week'] == 6  # Sunday
                assert metadata_section['is_weekend'] is True
                
                # Check facility separation
                assert len(data['pools']) == 2
                assert len(data['saunas']) == 1
                assert len(data.get('unknown_facilities', [])) == 0
                
                # Check summary stats
                summary = data['summary']
                assert summary['avg_pool_occupancy'] == 80.0  # (75+85)/2
                assert summary['avg_sauna_occupancy'] == 90.0
                assert summary['busiest_pool'] == "Cosimawellenbad"
                assert summary['quietest_pool'] == "Bad Giesing-Harlaching"
    
    def test_save_to_json_auto_timestamp_filename(self, temp_dir, sample_pool_data):
        """Test saving to JSON with auto-generated timestamp filename"""
        with patch('src.data_storage.SCRAPED_DATA_DIR', temp_dir):
            storage = DataStorage(test_mode=False)
            
            with patch('src.data_storage.datetime') as mock_dt:
                mock_now = datetime(2025, 8, 31, 15, 45, 30)
                mock_dt.now.return_value = mock_now
                mock_dt.strftime = datetime.strftime  # Keep strftime working
                
                filepath = storage.save_to_json(sample_pool_data)
                
                expected_name = "pool_data_20250831_154530.json"
                assert filepath.name == expected_name
    
    def test_save_to_json_with_unknown_facilities(self, temp_dir):
        """Test JSON saving handles unknown facility types"""
        with patch('src.data_storage.SCRAPED_DATA_DIR', temp_dir):
            storage = DataStorage(test_mode=False)
            
            timestamp = datetime.now()
            unknown_pool = PoolOccupancy("Unknown Pool", "50 % frei", timestamp)
            unknown_pool.facility_type = "unknown"
            
            filepath = storage.save_to_json([unknown_pool])
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                assert len(data['pools']) == 0
                assert len(data['saunas']) == 0
                assert len(data['unknown_facilities']) == 1
                assert data['unknown_facilities'][0]['pool_name'] == "Unknown Pool"
    
    def test_save_to_json_empty_pool_list(self, temp_dir):
        """Test JSON saving with empty pool list"""
        with patch('src.data_storage.SCRAPED_DATA_DIR', temp_dir):
            storage = DataStorage(test_mode=False)
            
            filepath = storage.save_to_json([])
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                assert data['scrape_metadata']['total_facilities'] == 0
                assert data['scrape_metadata']['pools_count'] == 0
                assert data['scrape_metadata']['saunas_count'] == 0
                assert len(data['pools']) == 0
                assert len(data['saunas']) == 0
                assert data['summary']['avg_pool_occupancy'] == 0
                assert data['summary']['avg_sauna_occupancy'] == 0
                assert data['summary']['busiest_pool'] is None
                assert data['summary']['quietest_pool'] is None
    
    def test_load_from_csv_existing_file(self, temp_dir, sample_pool_data):
        """Test loading from existing CSV file"""
        with patch('src.data_storage.SCRAPED_DATA_DIR', temp_dir):
            storage = DataStorage(test_mode=False)
            
            # First create a CSV file
            storage.save_to_csv(sample_pool_data, "load_test.csv")
            
            # Then load it
            loaded_data = storage.load_from_csv("load_test.csv")
            
            assert len(loaded_data) == 3
            assert loaded_data[0]['pool_name'] == "Bad Giesing-Harlaching"
            assert loaded_data[0]['facility_type'] == "pool"
            assert loaded_data[2]['pool_name'] == "Westbad Sauna"
            assert loaded_data[2]['facility_type'] == "sauna"
    
    def test_load_from_csv_nonexistent_file(self, temp_dir):
        """Test loading from non-existent CSV file"""
        with patch('src.data_storage.SCRAPED_DATA_DIR', temp_dir):
            storage = DataStorage(test_mode=False)
            
            loaded_data = storage.load_from_csv("nonexistent.csv")
            
            assert loaded_data == []
    
    def test_load_from_csv_default_filename(self, temp_dir):
        """Test loading from CSV with default filename"""
        with patch('src.data_storage.SCRAPED_DATA_DIR', temp_dir):
            with patch('src.data_storage.DATA_CONFIG', {"csv_filename": "default.csv"}):
                storage = DataStorage(test_mode=False)
                
                # This should look for default.csv (which doesn't exist)
                loaded_data = storage.load_from_csv()
                
                assert loaded_data == []
    
    def test_get_latest_json_file(self, temp_dir, sample_pool_data):
        """Test getting the latest JSON file by modification time"""
        with patch('src.data_storage.SCRAPED_DATA_DIR', temp_dir):
            storage = DataStorage(test_mode=False)
            
            # Create multiple JSON files with different timestamps
            import time
            
            storage.save_to_json(sample_pool_data, "pool_data_20250831_100000.json")
            time.sleep(0.01)  # Small delay to ensure different modification times
            storage.save_to_json(sample_pool_data, "pool_data_20250831_120000.json") 
            time.sleep(0.01)
            storage.save_to_json(sample_pool_data, "pool_data_20250831_140000.json")
            
            latest_file = storage.get_latest_json_file()
            
            assert latest_file.name == "pool_data_20250831_140000.json"
    
    def test_get_latest_json_file_no_files(self, temp_dir):
        """Test getting latest JSON file when none exist"""
        with patch('src.data_storage.SCRAPED_DATA_DIR', temp_dir):
            storage = DataStorage(test_mode=False)
            
            with pytest.raises(FileNotFoundError, match="No JSON files found"):
                storage.get_latest_json_file()
    
    def test_list_data_files(self, temp_dir, sample_pool_data):
        """Test listing all data files by type"""
        with patch('src.data_storage.SCRAPED_DATA_DIR', temp_dir):
            storage = DataStorage(test_mode=False)
            
            # Create various file types
            storage.save_to_csv(sample_pool_data, "test1.csv")
            storage.save_to_csv(sample_pool_data, "test2.csv")
            storage.save_to_json(sample_pool_data, "test1.json")
            
            # Create a fake HTML file
            (temp_dir / "debug.html").write_text("<html>test</html>")
            
            file_list = storage.list_data_files()
            
            assert 'csv' in file_list
            assert 'json' in file_list
            assert 'html' in file_list
            
            assert len(file_list['csv']) == 2
            assert len(file_list['json']) == 1
            assert len(file_list['html']) == 1
            
            # Check file names
            csv_names = [f.name for f in file_list['csv']]
            assert "test1.csv" in csv_names
            assert "test2.csv" in csv_names
            
            assert file_list['json'][0].name == "test1.json"
            assert file_list['html'][0].name == "debug.html"
    
    def test_unicode_handling(self, temp_dir):
        """Test proper Unicode handling in file operations"""
        with patch('src.data_storage.SCRAPED_DATA_DIR', temp_dir):
            storage = DataStorage(test_mode=False)
            
            timestamp = datetime.now()
            unicode_pool = PoolOccupancy(
                pool_name="Müller'sches Volksbad",
                occupancy_level="85 % frei",
                timestamp=timestamp
            )
            unicode_pool.facility_type = "pool"
            
            # Test CSV
            csv_path = storage.save_to_csv([unicode_pool], "unicode_test.csv")
            loaded_csv = storage.load_from_csv("unicode_test.csv")
            assert loaded_csv[0]['pool_name'] == "Müller'sches Volksbad"
            
            # Test JSON  
            json_path = storage.save_to_json([unicode_pool], "unicode_test.json")
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert data['pools'][0]['pool_name'] == "Müller'sches Volksbad"
    
    def test_edge_case_facility_types(self, temp_dir):
        """Test handling of various facility type combinations"""
        with patch('src.data_storage.SCRAPED_DATA_DIR', temp_dir):
            storage = DataStorage(test_mode=False)
            
            timestamp = datetime.now()
            mixed_facilities = []
            
            # Create facilities with different types
            types_and_names = [
                ("pool", "Regular Pool"),
                ("sauna", "Regular Sauna"),
                ("unknown", "Mystery Facility"),
                ("", "Empty Type"),
                (None, "None Type")
            ]
            
            for facility_type, name in types_and_names:
                facility = PoolOccupancy(name, "50 % frei", timestamp)
                if facility_type is not None and facility_type != "":
                    facility.facility_type = facility_type
                mixed_facilities.append(facility)
            
            filepath = storage.save_to_json(mixed_facilities)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Check categorization
                pool_names = [p['pool_name'] for p in data['pools']]
                sauna_names = [s['pool_name'] for s in data['saunas']]
                unknown_names = [u['pool_name'] for u in data['unknown_facilities']]
                
                assert "Regular Pool" in pool_names
                assert "Regular Sauna" in sauna_names
                
                # Empty/None/unknown should go to unknown_facilities  
                # Note: "Empty Type" will have default facility_type="unknown"
                unknown_expected = {"Mystery Facility", "Empty Type", "None Type"}
                assert set(unknown_names) == unknown_expected