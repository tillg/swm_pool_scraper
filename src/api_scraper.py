"""
API-based scraper for SWM pool occupancy data
Uses direct API calls instead of browser automation
"""

import logging
import time
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import PoolOccupancy
from .facility_registry import FacilityRegistry, Facility


class APIError(Exception):
    """Custom exception for API-related errors"""
    pass


class SWMAPIScraper:
    """
    Direct API scraper for SWM pool data
    10x faster than Selenium, more reliable
    """
    
    def __init__(self, config_path: Path = None):
        self.logger = logging.getLogger(__name__)
        self.api_base = "https://counter.ticos-systems.cloud/api/gates/counter"
        self.registry = FacilityRegistry(config_path or Path("config/facilities.json"))
        
        # Setup session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Headers to mimic browser request
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://www.swm.de',
            'Referer': 'https://www.swm.de/',
        })
    
    def fetch_occupancy(self, org_id: int) -> Optional[Dict]:
        """
        Fetch occupancy data for a single facility
        Returns None if request fails
        """
        url = f"{self.api_base}?organizationUnitIds={org_id}"
        
        try:
            response = self.session.get(url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                return data[0]
            
            self.logger.warning(f"Empty response for org_id {org_id}")
            return None
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch org_id {org_id}: {e}")
            return None
    
    def scrape_pool_data(self) -> List[PoolOccupancy]:
        """
        Main scraping method - fetches all pool data via API
        Returns list of PoolOccupancy objects
        """
        timestamp = datetime.now()
        pool_data = []
        
        active_facilities = [f for f in self.registry.facilities.values() if f.active]
        self.logger.info(f"Fetching data for {len(active_facilities)} facilities")
        
        for facility in active_facilities:
            # Rate limiting - be respectful
            time.sleep(0.1)
            
            data = self.fetch_occupancy(facility.org_id)
            
            if data:
                # Calculate percentage (inverse of what API returns)
                current_count = data.get('personCount', 0)
                max_count = data.get('maxPersonCount', 1)
                
                # API gives current people, we want % free
                if max_count > 0:
                    occupancy_percent = round((1 - current_count / max_count) * 100)
                else:
                    occupancy_percent = 0
                
                # Update facility's max capacity if we have new info
                if max_count and facility.max_capacity != max_count:
                    self.logger.info(f"Updating capacity for {facility.name}: {facility.max_capacity} -> {max_count}")
                    facility.max_capacity = max_count
                    facility.last_seen = timestamp
                    self.registry.save()
                
                pool_occupancy = PoolOccupancy(
                    pool_name=facility.name,
                    occupancy_level=f"{occupancy_percent} % frei",
                    timestamp=timestamp,
                    raw_occupancy=f"{current_count}/{max_count} persons"
                )
                pool_occupancy.facility_type = facility.facility_type.value
                pool_data.append(pool_occupancy)
                
                self.logger.debug(f"✓ {facility.name}: {occupancy_percent}% free ({current_count}/{max_count})")
            else:
                self.logger.warning(f"✗ No data for {facility.name} (ID: {facility.org_id})")
        
        self.logger.info(f"Successfully fetched {len(pool_data)}/{len(active_facilities)} facilities")
        return pool_data
    
    def validate_against_website(self) -> Dict:
        """
        Compare API data with website display to ensure accuracy
        Returns validation report
        """
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        from bs4 import BeautifulSoup
        import re
        
        self.logger.info("Starting validation against website...")
        
        # Get API data
        api_data = self.scrape_pool_data()
        api_by_name = {p.pool_name: p for p in api_data}
        
        # Setup headless browser
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        validation_report = {
            'timestamp': datetime.now().isoformat(),
            'api_facilities': len(api_data),
            'website_facilities': 0,
            'matches': [],
            'mismatches': [],
            'missing_from_api': [],
            'missing_from_website': []
        }
        
        try:
            driver.get("https://www.swm.de/baeder/auslastung")
            time.sleep(5)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            text = soup.get_text()
            
            # Extract occupancy from website
            pattern = r'(Bad Giesing-Harlaching|Cosimawellenbad|Michaelibad|Nordbad|Südbad|Westbad|Müller\'sches Volksbad|Dantebad)\s*(?:Mehr Infos)?\s*(\d+\s*%\s*frei)'
            
            website_data = {}
            for match in re.finditer(pattern, text):
                name = match.group(1)
                occupancy = match.group(2)
                website_data[name] = occupancy
            
            validation_report['website_facilities'] = len(website_data)
            
            # Compare data
            for name, website_occupancy in website_data.items():
                if name in api_by_name:
                    api_occupancy = api_by_name[name].occupancy_level
                    if api_occupancy == website_occupancy:
                        validation_report['matches'].append({
                            'name': name,
                            'occupancy': api_occupancy
                        })
                    else:
                        validation_report['mismatches'].append({
                            'name': name,
                            'api': api_occupancy,
                            'website': website_occupancy
                        })
                else:
                    validation_report['missing_from_api'].append(name)
            
            for name in api_by_name:
                if name not in website_data:
                    validation_report['missing_from_website'].append(name)
            
        finally:
            driver.quit()
        
        # Log validation results
        if validation_report['mismatches']:
            self.logger.warning(f"Found {len(validation_report['mismatches'])} mismatches between API and website")
        
        if validation_report['missing_from_api']:
            self.logger.error(f"Facilities on website but not in API: {validation_report['missing_from_api']}")
        
        return validation_report


class PoolMonitor:
    """
    Monitors for new pools and changes in facility configuration
    """
    
    def __init__(self, scraper: SWMAPIScraper):
        self.scraper = scraper
        self.logger = logging.getLogger(__name__)
    
    def check_for_new_facilities(self) -> List[str]:
        """
        Check website for pool names not in our registry
        Returns list of unknown pool names
        """
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        from bs4 import BeautifulSoup
        import re
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        new_facilities = []
        
        try:
            driver.get("https://www.swm.de/baeder/auslastung")
            time.sleep(5)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            text = soup.get_text()
            
            # Look for all pool/sauna names
            known_names = {f.name for f in self.scraper.registry.facilities.values()}
            
            # Extended pattern to catch more facility names
            pattern = r'([A-Z][a-zäöüß]+(?:[-\s][A-Za-zäöüß]+)*bad|Sauna\s+[A-Za-zäöüß]+)\s*(?:Mehr Infos)?\s*\d+\s*%\s*frei'
            
            for match in re.finditer(pattern, text):
                name = match.group(1).strip()
                if name not in known_names and name not in new_facilities:
                    new_facilities.append(name)
                    self.logger.warning(f"Found unknown facility: {name}")
        
        finally:
            driver.quit()
        
        return new_facilities
    
    def probe_id_range(self, start: int = 30180, end: int = 30220) -> List[int]:
        """
        Probe a range of org IDs to find new valid facilities
        """
        new_ids = []
        known_ids = set(self.scraper.registry.facilities.keys())
        
        for org_id in range(start, end):
            if org_id in known_ids:
                continue
            
            time.sleep(0.2)  # Rate limiting
            data = self.scraper.fetch_occupancy(org_id)
            
            if data:
                new_ids.append(org_id)
                self.logger.info(f"Found new valid org_id: {org_id} (capacity: {data.get('maxPersonCount')})")
                
                # Add to registry as unknown
                facility = Facility(
                    org_id=org_id,
                    name=f"Unknown Facility {org_id}",
                    facility_type="unknown",
                    max_capacity=data.get('maxPersonCount'),
                    auto_discovered=True
                )
                self.scraper.registry.add_facility(facility, auto_discovered=True)
        
        return new_ids
    
    def generate_monitoring_report(self) -> Dict:
        """
        Generate comprehensive monitoring report
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'registry_status': {
                'total_facilities': len(self.scraper.registry.facilities),
                'active': len([f for f in self.scraper.registry.facilities.values() if f.active]),
                'auto_discovered': len([f for f in self.scraper.registry.facilities.values() if f.auto_discovered])
            },
            'new_facilities': self.check_for_new_facilities(),
            'validation': self.scraper.validate_against_website()
        }
        
        return report


# Context manager for clean resource handling
class ManagedAPIScraper:
    """Context manager wrapper for API scraper"""
    
    def __init__(self, config_path: Path = None):
        self.scraper = SWMAPIScraper(config_path)
    
    def __enter__(self):
        return self.scraper
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Close session cleanly
        self.scraper.session.close()