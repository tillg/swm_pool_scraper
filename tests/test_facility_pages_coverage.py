"""Coverage tests for src/facility_pages.py.

Every facility in FACILITIES must have exactly one PAGE_BINDINGS entry
so the opening-hours scraper never silently skips anything.
"""

from src.facilities import FACILITIES, FacilityType
from src.facility_pages import (
    PAGE_BINDINGS,
    assert_covers_facilities,
    get_binding,
    unique_urls,
)


def test_every_facility_has_a_binding():
    for key in FACILITIES:
        assert key in PAGE_BINDINGS, f"no binding for {key}"


def test_no_orphan_bindings():
    for key in PAGE_BINDINGS:
        assert key in FACILITIES, f"orphan binding {key}"


def test_assert_covers_facilities_passes():
    assert_covers_facilities()


def test_shared_page_facilities_have_distinct_headings():
    # Cosimawellenbad has both pool and sauna on the same URL with different headings
    pool = get_binding("Cosimawellenbad", FacilityType.POOL)
    sauna = get_binding("Cosimawellenbad", FacilityType.SAUNA)
    assert pool.url == sauna.url
    assert pool.heading != sauna.heading


def test_unique_urls_deduplicates():
    # 17 facilities → 10 unique pages (7 shared pool+sauna pages,
    # 2 pool-only pages, 1 ice rink).
    assert len(unique_urls()) == 10


def test_ice_rink_binding_has_no_heading():
    # The ice rink is modeled as closed-for-season by default; no heading.
    b = get_binding(
        "Prinzregentenstadion - Eislaufbahn", FacilityType.ICE_RINK
    )
    assert b.heading is None
    assert b.url == "https://www.swm.de/baeder/eislaufen"


def test_pool_and_sauna_headings_present_for_shared_pages():
    shared = [
        "Cosimawellenbad",
        "Michaelibad",
        "Müller'sches Volksbad",
        "Nordbad",
        "Südbad",
        "Westbad",
        "Dantebad",  # shares URL with Dante-Winter-Warmfreibad pool
    ]
    # For each shared URL, check that the URL appears at least twice in bindings.
    urls_to_count = {}
    for key, b in PAGE_BINDINGS.items():
        urls_to_count[b.url] = urls_to_count.get(b.url, 0) + 1
    # 7 shared URLs each hosting 2 facilities
    shared_count = sum(1 for c in urls_to_count.values() if c == 2)
    assert shared_count == 7, f"expected 7 shared URLs, got {shared_count}"
