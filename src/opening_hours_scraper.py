"""
Fetch each SWM facility page once, parse per-facility opening hours, and
return a list of FacilityOpeningHours entries.

Hard-fails (raises) on any fetch or parse error that isn't a recognised
closed-for-season state. The CLI turns that into a non-zero exit so the
scheduler (GitHub Actions in swm_pool_data) surfaces the failure via email.
"""

from __future__ import annotations

import logging
import socket
from datetime import datetime
from typing import Dict, List

import requests
import urllib3.util.connection as _urllib3_connection
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .facilities import FACILITIES
from .facility_pages import PAGE_BINDINGS, assert_covers_facilities, unique_urls
from .opening_hours_model import FacilityOpeningHours
from .opening_hours_parser import parse_opening_hours
from config import TIMEZONE

# Force IPv4 for all HTTP in this process. www.swm.de has both AAAA and A
# records; GitHub Actions runners resolve the AAAA but often have no IPv6
# egress, producing `[Errno 101] Network is unreachable` at connect() that
# urllib3 retries can't recover from (retries hit the same v6 address). See
# https://github.com/tillg/swm_pool_scraper/issues/1 for the evidence.
_urllib3_connection.allowed_gai_family = lambda: socket.AF_INET


class OpeningHoursScraper:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        # Aggressive retry policy: www.swm.de from GH Actions runners has
        # shown both Errno 101 (fixed by forcing IPv4 above) and v4 connect
        # timeouts lasting tens of seconds. 5 attempts with backoff_factor=2
        # buys ~2.5 minutes of total patience, enough to ride out most
        # transient transit/WAF hiccups without needing a workflow-level
        # re-run.
        retry = Retry(
            total=5, backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        })

    def _fetch(self, url: str) -> str:
        # (connect_timeout, read_timeout). Separate values let us fail fast
        # on reads while giving connect some slack for the GH-runner blips.
        response = self.session.get(url, timeout=(15, 30))
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"
        return response.text

    def scrape_opening_hours(self) -> List[FacilityOpeningHours]:
        # Coverage check up-front; a missing binding is a wiring bug.
        assert_covers_facilities()

        scraped_at = datetime.now(TIMEZONE)
        html_by_url: Dict[str, str] = {}
        for url in unique_urls():
            self.logger.info(f"GET {url}")
            html_by_url[url] = self._fetch(url)

        entries: List[FacilityOpeningHours] = []
        # Use the FACILITIES order so output is deterministic.
        for (name, facility_type), _org_id in FACILITIES.items():
            binding = PAGE_BINDINGS[(name, facility_type)]
            entry = parse_opening_hours(
                html_by_url[binding.url],
                binding,
                name,
                facility_type,
                scraped_at,
            )
            self.logger.debug(
                f"✓ {name} ({facility_type.value}): {entry.status}"
            )
            entries.append(entry)
        return entries


class ManagedOpeningHoursScraper:
    def __init__(self) -> None:
        self.scraper = OpeningHoursScraper()

    def __enter__(self) -> OpeningHoursScraper:
        return self.scraper

    def __exit__(self, *exc) -> None:
        self.scraper.session.close()
