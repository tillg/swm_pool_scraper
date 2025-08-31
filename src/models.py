from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import re


@dataclass
class PoolOccupancy:
    pool_name: str
    occupancy_level: str
    timestamp: datetime
    raw_occupancy: Optional[str] = None
    
    @property
    def facility_type(self) -> str:
        """Determine if this is a pool or sauna based on context"""
        # We'll need to determine this from the scraping context
        # For now, return 'unknown' - will be set during scraping
        return getattr(self, '_facility_type', 'unknown')
    
    @facility_type.setter
    def facility_type(self, value: str):
        self._facility_type = value
    
    @property
    def occupancy_percent(self) -> Optional[float]:
        """Extract numeric percentage from occupancy_level"""
        if not self.occupancy_level:
            return None
        
        match = re.search(r'(\d+)\s*%', self.occupancy_level)
        if match:
            return float(match.group(1))
        return None
    
    @property
    def is_open(self) -> bool:
        """Determine if facility is open based on occupancy text"""
        if not self.occupancy_level:
            return False
        
        closed_keywords = ['geschlossen', 'closed', 'zu']
        return not any(keyword in self.occupancy_level.lower() for keyword in closed_keywords)
    
    @property
    def hour(self) -> int:
        """Hour of the day (0-23) for time-based ML features"""
        return self.timestamp.hour
    
    @property
    def day_of_week(self) -> int:
        """Day of week (0=Monday, 6=Sunday) for ML features"""
        return self.timestamp.weekday()
    
    @property
    def day_name(self) -> str:
        """Day name for readability"""
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return days[self.day_of_week]
    
    @property
    def is_weekend(self) -> bool:
        """Weekend indicator for ML features"""
        return self.day_of_week >= 5  # Saturday=5, Sunday=6
    
    def to_dict(self) -> dict:
        """Full dictionary representation with all features"""
        return {
            'pool_name': self.pool_name,
            'facility_type': self.facility_type,
            'occupancy_level': self.occupancy_level,
            'occupancy_percent': self.occupancy_percent,
            'is_open': self.is_open,
            'timestamp': self.timestamp.isoformat(),
            'hour': self.hour,
            'day_of_week': self.day_of_week,
            'day_name': self.day_name,
            'is_weekend': self.is_weekend,
            'raw_occupancy': self.raw_occupancy
        }
    
    def to_csv_row(self) -> dict:
        """CSV-optimized representation for Create ML"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'pool_name': self.pool_name,
            'facility_type': self.facility_type,
            'occupancy_percent': self.occupancy_percent,
            'is_open': 1 if self.is_open else 0,
            'hour': self.hour,
            'day_of_week': self.day_of_week,
            'is_weekend': 1 if self.is_weekend else 0,
            'occupancy_text': self.occupancy_level
        }