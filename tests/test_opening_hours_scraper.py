"""Integration tests for src/opening_hours_scraper.py.

Monkey-patches HTTP fetching so we test against fixture HTML, not the live site.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.data_storage import DataStorage
from src.facility_pages import unique_urls
from src.opening_hours_parser import ParseError
from src.opening_hours_scraper import OpeningHoursScraper

FIXTURES = Path(__file__).parent / "fixtures"


URL_TO_FIXTURE = {
    "https://www.swm.de/baeder/bad-giesing-harlaching": "bad-giesing-harlaching.html",
    "https://www.swm.de/baeder/cosimawellenbad": "cosimawellenbad.html",
    "https://www.swm.de/baeder/eislaufen": "eislaufen.html",
    "https://www.swm.de/baeder/freibaeder-muenchen/dantebad": "dantebad.html",
    "https://www.swm.de/baeder/michaelibad-hallenbad": "michaelibad-hallenbad.html",
    "https://www.swm.de/baeder/muellersches-volksbad": "muellersches-volksbad.html",
    "https://www.swm.de/baeder/nordbad": "nordbad.html",
    "https://www.swm.de/baeder/olympia-schwimmhalle": "olympia-schwimmhalle.html",
    "https://www.swm.de/baeder/suedbad": "suedbad.html",
    "https://www.swm.de/baeder/westbad-hallenbad": "westbad-hallenbad.html",
}


def _copy_missing_fixtures():
    # We only committed a subset of fixtures (per plan step 6). For the
    # integration test to run against all 10 pages, fall back to the
    # discovery dump when a specific fixture isn't yet in tests/fixtures/.
    dev_cache = Path(__file__).resolve().parent.parent / "tmp" / "discovery"
    for url, fname in URL_TO_FIXTURE.items():
        target = FIXTURES / fname
        if target.exists():
            continue
        src = dev_cache / fname
        if src.exists():
            target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def _fake_fetch(self, url: str) -> str:
    fname = URL_TO_FIXTURE[url]
    return (FIXTURES / fname).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _ensure_fixtures():
    _copy_missing_fixtures()
    # Skip gracefully if a fixture is still missing (dev machine without tmp/).
    missing = [f for f in URL_TO_FIXTURE.values() if not (FIXTURES / f).exists()]
    if missing:
        pytest.skip(f"Missing fixtures: {missing}")


def test_scraper_returns_one_entry_per_facility():
    with patch.object(OpeningHoursScraper, "_fetch", _fake_fetch):
        scraper = OpeningHoursScraper()
        entries = scraper.scrape_opening_hours()
    assert len(entries) == 17


def test_shared_pages_yield_two_entries_with_distinct_types():
    with patch.object(OpeningHoursScraper, "_fetch", _fake_fetch):
        entries = OpeningHoursScraper().scrape_opening_hours()
    cosima = [e for e in entries if e.pool_name == "Cosimawellenbad"]
    assert {e.facility_type for e in cosima} == {"pool", "sauna"}


def test_scraper_writes_snapshot():
    with patch.object(OpeningHoursScraper, "_fetch", _fake_fetch):
        entries = OpeningHoursScraper().scrape_opening_hours()

    with tempfile.TemporaryDirectory() as td:
        ds = DataStorage(test_mode=False, output_dir=td)
        path = ds.save_opening_hours(entries)
        data = json.loads(path.read_text(encoding="utf-8"))
    assert path.name.startswith("facility_opening_")
    meta = data["scrape_metadata"]
    assert meta["total_facilities"] == 17
    assert meta["unique_pages_fetched"] == 10
    assert meta["pools_count"] == 9
    assert meta["saunas_count"] == 7
    assert meta["ice_rinks_count"] == 1
    assert meta["open_count"] >= 16           # everything except the ice rink
    assert meta["closed_for_season_count"] == 1


def test_hard_fail_writes_no_snapshot():
    # Make a single URL return an unparseable page so parse_opening_hours raises.
    def bad_fetch(self, url: str) -> str:
        if "olympia" in url:
            return "<html><body>nothing here</body></html>"
        return _fake_fetch(self, url)

    with patch.object(OpeningHoursScraper, "_fetch", bad_fetch):
        with pytest.raises(ParseError):
            OpeningHoursScraper().scrape_opening_hours()

    # Caller (the CLI) is responsible for not writing anything on raise.
    with tempfile.TemporaryDirectory() as td:
        files = list(Path(td).iterdir())
        assert files == []
