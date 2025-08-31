"""
Unit tests for PoolOccupancy model
Tests data parsing, property calculations, and data export formats
"""

import pytest
from datetime import datetime
from src.models import PoolOccupancy


class TestPoolOccupancy:
    
    def test_basic_initialization(self):
        timestamp = datetime(2025, 8, 31, 14, 30, 0)
        pool = PoolOccupancy(
            pool_name="Test Pool",
            occupancy_level="75 % frei",
            timestamp=timestamp,
            raw_occupancy="25/100 persons"
        )
        
        assert pool.pool_name == "Test Pool"
        assert pool.occupancy_level == "75 % frei"
        assert pool.timestamp == timestamp
        assert pool.raw_occupancy == "25/100 persons"
    
    def test_occupancy_percent_extraction(self):
        timestamp = datetime.now()
        
        # Test various percentage formats
        test_cases = [
            ("85 % frei", 85.0),
            ("100% frei", 100.0),
            ("0 % frei", 0.0),
            ("50% verfügbar", 50.0),
            ("geschlossen", None),
            ("no percentage here", None),
            ("", None),
        ]
        
        for occupancy_text, expected_percent in test_cases:
            pool = PoolOccupancy("Test", occupancy_text, timestamp)
            assert pool.occupancy_percent == expected_percent
    
    def test_facility_type_property(self):
        pool = PoolOccupancy("Test", "50 % frei", datetime.now())
        
        # Default should be unknown
        assert pool.facility_type == "unknown"
        
        # Should be settable
        pool.facility_type = "pool"
        assert pool.facility_type == "pool"
        
        pool.facility_type = "sauna"
        assert pool.facility_type == "sauna"
    
    def test_is_open_property(self):
        timestamp = datetime.now()
        
        # Test open cases
        open_cases = [
            "85 % frei",
            "100 % verfügbar",
            "50% available",
        ]
        
        for occupancy_text in open_cases:
            pool = PoolOccupancy("Test", occupancy_text, timestamp)
            assert pool.is_open is True
        
        # Test closed cases
        closed_cases = [
            "geschlossen",
            "closed",
            "derzeit zu",
            "GESCHLOSSEN",
        ]
        
        for occupancy_text in closed_cases:
            pool = PoolOccupancy("Test", occupancy_text, timestamp)
            assert pool.is_open is False
        
        # Test empty/None
        pool_empty = PoolOccupancy("Test", "", timestamp)
        assert pool_empty.is_open is False
    
    def test_time_properties(self):
        # Test specific datetime for predictable results
        timestamp = datetime(2025, 8, 31, 14, 30, 0)  # Sunday, 2:30 PM (2025-08-31 is a Sunday)
        pool = PoolOccupancy("Test", "50 % frei", timestamp)
        
        assert pool.hour == 14
        assert pool.day_of_week == 6  # Sunday (0=Monday, 6=Sunday)
        assert pool.day_name == "Sunday"
        assert pool.is_weekend is True
        
        # Test weekday
        weekday_timestamp = datetime(2025, 9, 1, 10, 0, 0)  # Monday, 10:00 AM
        weekday_pool = PoolOccupancy("Test", "50 % frei", weekday_timestamp)
        
        assert weekday_pool.hour == 10
        assert weekday_pool.day_of_week == 0  # Monday
        assert weekday_pool.day_name == "Monday"
        assert weekday_pool.is_weekend is False
    
    def test_to_dict_method(self):
        timestamp = datetime(2025, 8, 31, 14, 30, 0)
        pool = PoolOccupancy(
            pool_name="Bad Giesing-Harlaching",
            occupancy_level="75 % frei",
            timestamp=timestamp,
            raw_occupancy="78/311 persons"
        )
        pool.facility_type = "pool"
        
        result = pool.to_dict()
        
        expected_keys = {
            'pool_name', 'facility_type', 'occupancy_level', 'occupancy_percent',
            'is_open', 'timestamp', 'hour', 'day_of_week', 'day_name', 
            'is_weekend', 'raw_occupancy'
        }
        
        assert set(result.keys()) == expected_keys
        assert result['pool_name'] == "Bad Giesing-Harlaching"
        assert result['facility_type'] == "pool"
        assert result['occupancy_level'] == "75 % frei"
        assert result['occupancy_percent'] == 75.0
        assert result['is_open'] is True
        assert result['timestamp'] == timestamp.isoformat()
        assert result['hour'] == 14
        assert result['day_of_week'] == 6
        assert result['day_name'] == "Sunday"
        assert result['is_weekend'] is True
        assert result['raw_occupancy'] == "78/311 persons"
    
    def test_to_csv_row_method(self):
        timestamp = datetime(2025, 8, 31, 14, 30, 0)
        pool = PoolOccupancy(
            pool_name="Cosimawellenbad",
            occupancy_level="90 % frei",
            timestamp=timestamp
        )
        pool.facility_type = "pool"
        
        result = pool.to_csv_row()
        
        expected_keys = {
            'timestamp', 'pool_name', 'facility_type', 'occupancy_percent',
            'is_open', 'hour', 'day_of_week', 'is_weekend', 'occupancy_text'
        }
        
        assert set(result.keys()) == expected_keys
        assert result['timestamp'] == timestamp.isoformat()
        assert result['pool_name'] == "Cosimawellenbad"
        assert result['facility_type'] == "pool"
        assert result['occupancy_percent'] == 90.0
        assert result['is_open'] == 1  # Boolean converted to int for ML
        assert result['hour'] == 14
        assert result['day_of_week'] == 6
        assert result['is_weekend'] == 1  # Boolean converted to int for ML
        assert result['occupancy_text'] == "90 % frei"
    
    def test_csv_row_closed_facility(self):
        timestamp = datetime.now()
        closed_pool = PoolOccupancy("Test", "geschlossen", timestamp)
        closed_pool.facility_type = "sauna"
        
        result = closed_pool.to_csv_row()
        
        assert result['is_open'] == 0  # Closed facility
        assert result['occupancy_percent'] is None
        assert result['facility_type'] == "sauna"
    
    def test_weekend_detection(self):
        # Test all days of the week
        weekdays = [
            (0, False),  # Monday
            (1, False),  # Tuesday
            (2, False),  # Wednesday
            (3, False),  # Thursday
            (4, False),  # Friday
            (5, True),   # Saturday
            (6, True),   # Sunday
        ]
        
        for day_of_week, expected_weekend in weekdays:
            # Create datetime with specific weekday
            # 2025-09-01 is a Monday, so add days to get desired weekday
            base_date = datetime(2025, 9, 1)  # Monday
            test_date = base_date.replace(day=1 + day_of_week)
            
            pool = PoolOccupancy("Test", "50 % frei", test_date)
            assert pool.is_weekend == expected_weekend, f"Day {day_of_week} weekend detection failed"
    
    def test_edge_cases(self):
        timestamp = datetime.now()
        
        # Test with special characters in pool name
        pool = PoolOccupancy("Müller'sches Volksbad", "85 % frei", timestamp)
        assert pool.pool_name == "Müller'sches Volksbad"
        
        # Test with None raw_occupancy
        pool_no_raw = PoolOccupancy("Test", "50 % frei", timestamp, None)
        assert pool_no_raw.raw_occupancy is None
        
        # Test occupancy parsing edge cases
        edge_cases = [
            ("99% frei", 99.0),
            ("1 % frei", 1.0),
            ("  75 %  frei  ", 75.0),  # Whitespace handling
        ]
        
        for occupancy_text, expected_percent in edge_cases:
            pool = PoolOccupancy("Test", occupancy_text, timestamp)
            assert pool.occupancy_percent == expected_percent