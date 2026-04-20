"""Data model for one facility's opening hours at one point in time."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday")

# status values
STATUS_OPEN = "open"
STATUS_CLOSED_FOR_SEASON = "closed_for_season"


@dataclass
class FacilityOpeningHours:
    pool_name: str
    facility_type: str                    # "pool" | "sauna" | "ice_rink"
    status: str                           # STATUS_OPEN | STATUS_CLOSED_FOR_SEASON
    url: str
    heading: Optional[str]
    weekly_schedule: Dict[str, List[Dict[str, str]]]
    special_notes: List[str]
    raw_section: str
    scraped_at: datetime

    def to_dict(self) -> dict:
        return {
            "pool_name": self.pool_name,
            "facility_type": self.facility_type,
            "status": self.status,
            "url": self.url,
            "heading": self.heading,
            "weekly_schedule": self.weekly_schedule,
            "special_notes": list(self.special_notes),
            "raw_section": self.raw_section,
            "scraped_at": self.scraped_at.isoformat(),
        }
