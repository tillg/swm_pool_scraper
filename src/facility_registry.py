"""
Facility Registry - Source of truth for pool/sauna mappings
Includes automatic discovery and validation
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass, asdict
import requests
from enum import Enum


class FacilityType(Enum):
    POOL = "pool"
    SAUNA = "sauna"
    UNKNOWN = "unknown"


@dataclass
class Facility:
    org_id: int
    name: str
    facility_type: FacilityType
    max_capacity: Optional[int] = None
    last_seen: Optional[datetime] = None
    first_seen: Optional[datetime] = None
    active: bool = True
    auto_discovered: bool = False
    
    def to_dict(self):
        d = asdict(self)
        d['facility_type'] = self.facility_type.value
        if self.last_seen:
            d['last_seen'] = self.last_seen.isoformat()
        if self.first_seen:
            d['first_seen'] = self.first_seen.isoformat()
        return d


class FacilityRegistry:
    """
    Central registry for facility mappings
    Stores in both JSON file and can sync with database
    """
    
    def __init__(self, config_path: Path = None):
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path or Path("config/facilities.json")
        self.facilities: Dict[int, Facility] = {}
        self.load()
    
    def load(self):
        """Load facility mappings from file"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                for item in data.get('facilities', []):
                    facility = Facility(
                        org_id=item['org_id'],
                        name=item['name'],
                        facility_type=FacilityType(item['facility_type']),
                        max_capacity=item.get('max_capacity'),
                        last_seen=datetime.fromisoformat(item['last_seen']) if item.get('last_seen') else None,
                        first_seen=datetime.fromisoformat(item['first_seen']) if item.get('first_seen') else None,
                        active=item.get('active', True),
                        auto_discovered=item.get('auto_discovered', False)
                    )
                    self.facilities[facility.org_id] = facility
            self.logger.info(f"Loaded {len(self.facilities)} facilities from {self.config_path}")
        else:
            self.logger.info("No existing facility config found, starting with defaults")
            self._load_defaults()
    
    def _load_defaults(self):
        """Load known facility mappings"""
        # These are the ones we've discovered so far
        defaults = [
            Facility(30195, "Bad Giesing-Harlaching", FacilityType.POOL),
            Facility(30190, "Cosimawellenbad", FacilityType.POOL),
            Facility(30208, "Michaelibad", FacilityType.POOL),
            Facility(30197, "Nordbad", FacilityType.POOL),
            Facility(30184, "Südbad", FacilityType.POOL),
            Facility(30187, "Westbad", FacilityType.POOL),
            Facility(30199, "Müller'sches Volksbad", FacilityType.POOL),
            # Saunas (guessing based on IDs being close)
            Facility(30191, "Cosimawellenbad Sauna", FacilityType.SAUNA),
            Facility(30200, "Dantebad Sauna", FacilityType.SAUNA),
            Facility(30203, "Michaelibad Sauna", FacilityType.SAUNA),
            Facility(30185, "Nordbad Sauna", FacilityType.SAUNA),
            Facility(30188, "Südbad Sauna", FacilityType.SAUNA),
            Facility(30207, "Westbad Sauna", FacilityType.SAUNA),
        ]
        
        for facility in defaults:
            facility.first_seen = datetime.now()
            self.facilities[facility.org_id] = facility
    
    def save(self):
        """Persist facility mappings to file"""
        self.config_path.parent.mkdir(exist_ok=True)
        
        data = {
            'last_updated': datetime.now().isoformat(),
            'total_facilities': len(self.facilities),
            'active_facilities': len([f for f in self.facilities.values() if f.active]),
            'facilities': [f.to_dict() for f in self.facilities.values()]
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.logger.info(f"Saved {len(self.facilities)} facilities to {self.config_path}")
    
    def get_facility(self, org_id: int) -> Optional[Facility]:
        """Get facility by organization ID"""
        return self.facilities.get(org_id)
    
    def add_facility(self, facility: Facility, auto_discovered: bool = False):
        """Add or update a facility"""
        facility.auto_discovered = auto_discovered
        if org_id not in self.facilities:
            facility.first_seen = datetime.now()
            self.logger.info(f"New facility discovered: {facility.name} (ID: {facility.org_id})")
        
        facility.last_seen = datetime.now()
        self.facilities[facility.org_id] = facility
        self.save()
    
    def get_unknown_org_ids(self, discovered_ids: List[int]) -> List[int]:
        """Find organization IDs we haven't seen before"""
        known_ids = set(self.facilities.keys())
        discovered = set(discovered_ids)
        return list(discovered - known_ids)
    
    def mark_inactive(self, org_id: int):
        """Mark a facility as inactive (no longer appearing in API)"""
        if org_id in self.facilities:
            self.facilities[org_id].active = False
            self.logger.warning(f"Facility {self.facilities[org_id].name} marked as inactive")
            self.save()


class FacilityDiscovery:
    """
    Automatic discovery of new facilities
    Runs periodically to check for changes
    """
    
    def __init__(self, registry: FacilityRegistry):
        self.registry = registry
        self.logger = logging.getLogger(__name__)
        self.api_base = "https://counter.ticos-systems.cloud/api/gates/counter"
    
    def discover_from_website(self) -> List[int]:
        """
        Scrape the website to find all organization IDs being used
        This would run the browser automation to capture network traffic
        """
        # This would use our api_discovery.py logic
        # For now, return known IDs
        return [30195, 30190, 30208, 30197, 30184, 30187, 
                30199, 30191, 30200, 30203, 30185, 30188, 30207]
    
    def probe_org_id(self, org_id: int) -> Optional[Dict]:
        """Test if an organization ID is valid"""
        url = f"{self.api_base}?organizationUnitIds={org_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json',
            'Origin': 'https://www.swm.de',
            'Referer': 'https://www.swm.de/',
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0]
        except Exception as e:
            self.logger.debug(f"Failed to probe org_id {org_id}: {e}")
        
        return None
    
    def scan_id_range(self, start: int = 30180, end: int = 30220) -> List[int]:
        """
        Scan a range of IDs to find valid facilities
        Use sparingly to avoid rate limiting
        """
        valid_ids = []
        
        for org_id in range(start, end):
            if org_id in self.registry.facilities:
                continue  # Skip known IDs
            
            data = self.probe_org_id(org_id)
            if data:
                valid_ids.append(org_id)
                self.logger.info(f"Found new valid org_id: {org_id} (capacity: {data.get('maxPersonCount')})")
                
                # Add to registry as unknown facility
                facility = Facility(
                    org_id=org_id,
                    name=f"Unknown Facility {org_id}",
                    facility_type=FacilityType.UNKNOWN,
                    max_capacity=data.get('maxPersonCount'),
                    auto_discovered=True
                )
                self.registry.add_facility(facility, auto_discovered=True)
        
        return valid_ids
    
    def check_for_changes(self) -> Dict:
        """
        Main discovery method - checks for new facilities and changes
        Returns a report of what was found
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'new_facilities': [],
            'missing_facilities': [],
            'capacity_changes': []
        }
        
        # Get current IDs from website
        current_ids = self.discover_from_website()
        
        # Check for new IDs
        new_ids = self.registry.get_unknown_org_ids(current_ids)
        if new_ids:
            self.logger.warning(f"Found {len(new_ids)} new organization IDs: {new_ids}")
            report['new_facilities'] = new_ids
            
            # Try to get info about new facilities
            for org_id in new_ids:
                data = self.probe_org_id(org_id)
                if data:
                    facility = Facility(
                        org_id=org_id,
                        name=f"New Facility {org_id}",
                        facility_type=FacilityType.UNKNOWN,
                        max_capacity=data.get('maxPersonCount'),
                        auto_discovered=True
                    )
                    self.registry.add_facility(facility, auto_discovered=True)
        
        # Check for missing IDs (facilities that might be closed)
        known_active = [f.org_id for f in self.registry.facilities.values() if f.active]
        missing_ids = set(known_active) - set(current_ids)
        if missing_ids:
            self.logger.warning(f"Facilities not found in current data: {missing_ids}")
            report['missing_facilities'] = list(missing_ids)
            for org_id in missing_ids:
                self.registry.mark_inactive(org_id)
        
        # Check for capacity changes
        for org_id in current_ids:
            if org_id in self.registry.facilities:
                data = self.probe_org_id(org_id)
                if data:
                    facility = self.registry.get_facility(org_id)
                    new_capacity = data.get('maxPersonCount')
                    if facility.max_capacity and facility.max_capacity != new_capacity:
                        self.logger.info(f"Capacity change for {facility.name}: {facility.max_capacity} -> {new_capacity}")
                        report['capacity_changes'].append({
                            'facility': facility.name,
                            'old_capacity': facility.max_capacity,
                            'new_capacity': new_capacity
                        })
                        facility.max_capacity = new_capacity
                        self.registry.save()
        
        return report


class AlertSystem:
    """
    Send alerts when new facilities are discovered or issues detected
    """
    
    def __init__(self, config: Dict = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
    
    def send_alert(self, alert_type: str, message: str, details: Dict = None):
        """Send an alert through configured channels"""
        
        # Log the alert
        self.logger.warning(f"ALERT [{alert_type}]: {message}")
        if details:
            self.logger.warning(f"Details: {json.dumps(details, indent=2)}")
        
        # Write to alert file
        alert_file = Path("alerts.json")
        alert_data = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'message': message,
            'details': details
        }
        
        # Append to alerts file
        alerts = []
        if alert_file.exists():
            with open(alert_file, 'r') as f:
                alerts = json.load(f)
        
        alerts.append(alert_data)
        
        # Keep only last 100 alerts
        alerts = alerts[-100:]
        
        with open(alert_file, 'w') as f:
            json.dump(alerts, f, indent=2)
        
        # Could also send to:
        # - Email
        # - Slack/Discord webhook
        # - Push notification
        # - SMS via Twilio
        # - PagerDuty for critical alerts
    
    def check_discovery_report(self, report: Dict):
        """Check discovery report and send appropriate alerts"""
        
        if report.get('new_facilities'):
            self.send_alert(
                'NEW_FACILITIES',
                f"Discovered {len(report['new_facilities'])} new facilities",
                report
            )
        
        if report.get('missing_facilities'):
            self.send_alert(
                'MISSING_FACILITIES',
                f"{len(report['missing_facilities'])} facilities are no longer available",
                report
            )
        
        if report.get('capacity_changes'):
            self.send_alert(
                'CAPACITY_CHANGE',
                f"Capacity changed for {len(report['capacity_changes'])} facilities",
                report
            )


# Usage example
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize registry
    registry = FacilityRegistry(Path("config/facilities.json"))
    
    # Run discovery
    discovery = FacilityDiscovery(registry)
    report = discovery.check_for_changes()
    
    # Send alerts if needed
    alerts = AlertSystem()
    alerts.check_discovery_report(report)
    
    # Show current facilities
    print("\nCurrent Facility Registry:")
    for facility in registry.facilities.values():
        status = "✅" if facility.active else "❌"
        auto = "🤖" if facility.auto_discovered else "👤"
        print(f"{status} {auto} {facility.org_id}: {facility.name} ({facility.facility_type.value}) - Capacity: {facility.max_capacity}")