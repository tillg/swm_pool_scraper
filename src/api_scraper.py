"""
API-based scraper for SWM pool occupancy data

Scraping flow:
1. Load known facilities from facilities.py
2. Fetch occupancy data from Ticos API for each facility
"""

import logging
import time
from datetime import datetime
from typing import List, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import PoolOccupancy
from .facility_registry import FacilityRegistry
from config import TIMEZONE


class APIError(Exception):
    """Custom exception for API-related errors"""
    pass


class SWMAPIScraper:
    """
    Scraper for SWM pool/sauna occupancy data.

    Uses static facility list from facilities.py and fetches data from Ticos API.
    """

    API_BASE = "https://counter.ticos-systems.cloud/api/gates/counter"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.registry = FacilityRegistry()

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
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://www.swm.de',
            'Referer': 'https://www.swm.de/',
        })

    def fetch_occupancy(self, org_id: int) -> Optional[Dict]:
        """
        Fetch occupancy data for a single facility from Ticos API.
        Returns None if request fails or facility is closed.
        """
        url = f"{self.API_BASE}?organizationUnitIds={org_id}"

        try:
            response = self.session.get(url, timeout=5)
            response.raise_for_status()

            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                return data[0]

            # Empty response means facility is closed or no data
            return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch org_id {org_id}: {e}")
            return None

    def scrape_pool_data(self) -> List[PoolOccupancy]:
        """
        Main scraping method.

        Fetches occupancy data from Ticos API for all known facilities.
        Uses the static facility list from facilities.py.

        Returns list of PoolOccupancy objects.
        """
        timestamp = datetime.now(TIMEZONE)
        pool_data = []

        # Get all facilities from our static registry
        all_facilities = self.registry.get_all_facilities()
        self.logger.info(f"Fetching data for {len(all_facilities)} facilities")

        # Fetch occupancy data for each facility
        for facility in all_facilities:
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

                pool_occupancy = PoolOccupancy(
                    pool_name=facility.name,
                    occupancy_level=f"{occupancy_percent} % frei",
                    timestamp=timestamp,
                    raw_occupancy=f"{current_count}/{max_count} persons"
                )
                pool_occupancy.facility_type = facility.facility_type.value
                pool_data.append(pool_occupancy)

                self.logger.debug(
                    f"✓ {facility.name}: {occupancy_percent}% free "
                    f"({current_count}/{max_count})"
                )
            else:
                # No data - facility might be closed, skip it
                self.logger.debug(
                    f"✗ No data for {facility.name} (ID: {facility.org_id}) - "
                    "might be closed"
                )

        self.logger.info(
            f"Successfully fetched {len(pool_data)}/{len(all_facilities)} facilities"
        )
        return pool_data


# Context manager for clean resource handling
class ManagedAPIScraper:
    """Context manager wrapper for API scraper"""

    def __init__(self):
        self.scraper = SWMAPIScraper()

    def __enter__(self):
        return self.scraper

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Close session cleanly
        self.scraper.session.close()
