"""
Facility mappings: (name, type) -> org_id

This is the source of truth for mapping facility names to their Ticos API organization IDs.
The org_ids were discovered by inspecting network traffic on https://www.swm.de/baeder/auslastung

Maintenance:
- Add new facilities when discovered (scraper will fail with clear error if unknown facility found)
- Never delete entries - obsolete facilities simply return no data from the API
- Review periodically (monthly) by checking the SWM website for new facilities

Last updated: 2026-01-19
"""

from enum import Enum
from typing import Dict, Tuple, Optional


class FacilityType(Enum):
    POOL = "pool"
    SAUNA = "sauna"
    ICE_RINK = "ice_rink"


# Mapping: (facility_name, facility_type) -> org_id
# Names must match exactly what appears on the SWM website
FACILITIES: Dict[Tuple[str, FacilityType], int] = {
    # === POOLS (9) ===
    ("Bad Giesing-Harlaching", FacilityType.POOL): 30195,
    ("Cosimawellenbad", FacilityType.POOL): 30190,
    ("Dante-Winter-Warmfreibad", FacilityType.POOL): 129,
    ("Michaelibad", FacilityType.POOL): 30208,
    ("Müller'sches Volksbad", FacilityType.POOL): 30197,
    ("Nordbad", FacilityType.POOL): 30184,
    ("Olympia-Schwimmhalle", FacilityType.POOL): 30182,
    ("Südbad", FacilityType.POOL): 30187,
    ("Westbad", FacilityType.POOL): 30199,

    # === SAUNAS (7) ===
    ("Cosimawellenbad", FacilityType.SAUNA): 30191,
    ("Dantebad", FacilityType.SAUNA): 30200,
    ("Michaelibad", FacilityType.SAUNA): 30203,
    ("Müller'sches Volksbad", FacilityType.SAUNA): 30204,
    ("Nordbad", FacilityType.SAUNA): 30185,
    ("Südbad", FacilityType.SAUNA): 30188,
    ("Westbad", FacilityType.SAUNA): 30207,

    # === ICE RINKS (1) ===
    ("Prinzregentenstadion - Eislaufbahn", FacilityType.ICE_RINK): 30356,
}


def get_org_id(name: str, facility_type: FacilityType) -> Optional[int]:
    """Get org_id for a facility by name and type."""
    return FACILITIES.get((name, facility_type))


def get_all_facilities() -> Dict[Tuple[str, FacilityType], int]:
    """Get all facility mappings."""
    return FACILITIES.copy()


def get_facilities_by_type(facility_type: FacilityType) -> Dict[str, int]:
    """Get all facilities of a specific type as {name: org_id}."""
    return {
        name: org_id
        for (name, ftype), org_id in FACILITIES.items()
        if ftype == facility_type
    }


class UnknownFacilityError(Exception):
    """Raised when a facility is discovered on the website but not in our mapping."""

    def __init__(self, name: str, facility_type: FacilityType):
        self.name = name
        self.facility_type = facility_type
        super().__init__(
            f"Unknown facility discovered: '{name}' (type: {facility_type.value})\n"
            f"This facility exists on the SWM website but is not in src/facilities.py.\n"
            f"Please add it to the FACILITIES dict with the correct org_id.\n"
            f"To find the org_id, inspect network traffic on https://www.swm.de/baeder/auslastung"
        )
