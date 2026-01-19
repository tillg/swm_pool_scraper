"""
Facility Registry - Simple wrapper around the facilities.py mappings

Provides facility lookup by name/type and org_id.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from .facilities import (
    FACILITIES,
    FacilityType,
    get_org_id,
    UnknownFacilityError,
)


@dataclass
class Facility:
    """Represents a facility with its org_id and metadata."""
    org_id: int
    name: str
    facility_type: FacilityType
    active: bool = True

    @property
    def type_value(self) -> str:
        """Get facility type as string."""
        return self.facility_type.value


class FacilityRegistry:
    """
    Central registry for facility mappings.
    Uses the static FACILITIES dict from facilities.py.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.facilities: Dict[int, Facility] = {}
        self._load_from_dict()

    def _load_from_dict(self):
        """Load facilities from the Python dict."""
        for (name, facility_type), org_id in FACILITIES.items():
            facility = Facility(
                org_id=org_id,
                name=name,
                facility_type=facility_type,
            )
            self.facilities[org_id] = facility
        self.logger.info(f"Loaded {len(self.facilities)} facilities from facilities.py")

    def get_facility(self, org_id: int) -> Optional[Facility]:
        """Get facility by organization ID."""
        return self.facilities.get(org_id)

    def get_facility_by_name(self, name: str, facility_type: FacilityType) -> Optional[Facility]:
        """Get facility by name and type."""
        org_id = get_org_id(name, facility_type)
        if org_id is not None:
            return self.facilities.get(org_id)
        return None

    def get_org_id(self, name: str, facility_type: FacilityType) -> int:
        """
        Get org_id for a facility. Raises UnknownFacilityError if not found.
        """
        org_id = get_org_id(name, facility_type)
        if org_id is None:
            raise UnknownFacilityError(name, facility_type)
        return org_id

    def get_all_facilities(self) -> List[Facility]:
        """Get all registered facilities."""
        return list(self.facilities.values())

    def get_facilities_by_type(self, facility_type: FacilityType) -> List[Facility]:
        """Get all facilities of a specific type."""
        return [f for f in self.facilities.values() if f.facility_type == facility_type]


# Re-export for backwards compatibility
__all__ = ['FacilityRegistry', 'Facility', 'FacilityType', 'UnknownFacilityError']
