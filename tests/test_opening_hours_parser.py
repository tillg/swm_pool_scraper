"""Unit tests for src/opening_hours_parser.py."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.facilities import FacilityType
from src.facility_pages import PAGE_BINDINGS
from src.opening_hours_parser import (
    CLOSED_SEASON_MARKERS,
    ParseError,
    parse_opening_hours,
)
from src.opening_hours_model import STATUS_CLOSED_FOR_SEASON, STATUS_OPEN

FIXTURES = Path(__file__).parent / "fixtures"
T0 = datetime(2026, 4, 20, 4, 0, tzinfo=timezone.utc)


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _parse(fixture: str, pool_name: str, facility_type: FacilityType):
    binding = PAGE_BINDINGS[(pool_name, facility_type)]
    return parse_opening_hours(
        _load(fixture), binding, pool_name, facility_type, T0
    )


# --- Happy paths -----------------------------------------------------------


def test_pool_only_page_parses():
    r = _parse("olympia-schwimmhalle.html", "Olympia-Schwimmhalle", FacilityType.POOL)
    assert r.status == STATUS_OPEN
    # Monday through Sunday, all 07:00–23:00
    for day in ("monday", "wednesday", "saturday", "sunday"):
        assert r.weekly_schedule[day] == [{"open": "07:00", "close": "23:00"}]


def test_shared_page_pool_and_sauna_have_distinct_schedules():
    pool = _parse("cosimawellenbad.html", "Cosimawellenbad", FacilityType.POOL)
    sauna = _parse("cosimawellenbad.html", "Cosimawellenbad", FacilityType.SAUNA)
    assert pool.status == STATUS_OPEN and sauna.status == STATUS_OPEN
    assert pool.weekly_schedule["monday"] == [
        {"open": "07:30", "close": "23:00"}
    ]
    assert sauna.weekly_schedule["monday"] == [
        {"open": "09:00", "close": "23:00"}
    ]


def test_split_weekday_groups_parse_correctly():
    # Dante-Winter-Warmfreibad has "Mo, Mi, Fr: 7 bis 23" and "Di, Do, Sa, So: 7.30 bis 23".
    r = _parse("dantebad.html", "Dante-Winter-Warmfreibad", FacilityType.POOL)
    assert r.weekly_schedule["monday"] == [{"open": "07:00", "close": "23:00"}]
    assert r.weekly_schedule["wednesday"] == [{"open": "07:00", "close": "23:00"}]
    assert r.weekly_schedule["friday"] == [{"open": "07:00", "close": "23:00"}]
    assert r.weekly_schedule["tuesday"] == [{"open": "07:30", "close": "23:00"}]
    assert r.weekly_schedule["sunday"] == [{"open": "07:30", "close": "23:00"}]


def test_westbad_sauna_unusual_heading_parses():
    r = _parse("westbad-hallenbad.html", "Westbad", FacilityType.SAUNA)
    assert r.status == STATUS_OPEN
    assert r.heading == "Öffnungszeiten Saunainsel (textilfrei)"
    assert r.weekly_schedule["monday"] == [
        {"open": "07:30", "close": "23:00"}
    ]


def test_wellenzeiten_lines_do_not_leak_into_schedule():
    # Cosimawellenbad pool block includes Wellenzeiten with "Freitag: 15 bis 17 Uhr*"
    # which must NOT become a second Friday interval.
    r = _parse("cosimawellenbad.html", "Cosimawellenbad", FacilityType.POOL)
    assert r.weekly_schedule["friday"] == [
        {"open": "07:30", "close": "23:00"}
    ]
    # But the Wellenzeiten text should be captured as notes.
    joined = "\n".join(r.special_notes)
    assert "Wellenzeiten" in joined
    assert "Freitag: 15 bis 17 Uhr" in joined


def test_kassenschluss_lines_become_notes_not_breakers():
    r = _parse("cosimawellenbad.html", "Cosimawellenbad", FacilityType.POOL)
    # Kassenschluss appears AFTER the Mo-So line and before Wellenzeiten —
    # it must not stop schedule parsing; it should appear in notes.
    assert any("Kassenschluss" in n for n in r.special_notes)


# --- Closed-for-season -----------------------------------------------------


def test_ice_rink_closed_for_season():
    r = _parse(
        "eislaufen.html",
        "Prinzregentenstadion - Eislaufbahn",
        FacilityType.ICE_RINK,
    )
    assert r.status == STATUS_CLOSED_FOR_SEASON
    assert r.weekly_schedule == {}
    assert any("Eislaufsaison" in n for n in r.special_notes)


def test_closed_season_markers_is_not_empty():
    # Sanity — the constant is populated so the detector can fire.
    assert len(CLOSED_SEASON_MARKERS) >= 3


# --- Hard failures ---------------------------------------------------------


def test_missing_heading_without_closed_marker_raises():
    # Build a minimal HTML that lacks the heading AND has no closed-season text.
    from src.facility_pages import PageBinding

    html = "<html><body><h2>Nope</h2><p>Contact us.</p></body></html>"
    binding = PageBinding(url="https://example", heading="Öffnungszeiten Sauna")
    with pytest.raises(ParseError):
        parse_opening_hours(
            html, binding, "Test", FacilityType.SAUNA, T0
        )


def test_heading_present_but_no_intervals_raises():
    from src.facility_pages import PageBinding

    html = (
        "<html><body>"
        "<div class='text-plus__col'>"
        "<h3>Öffnungszeiten Test</h3>"
        "<p>Kassenschluss: 30 Minuten vor Ende der Öffnungszeit</p>"
        "</div>"
        "</body></html>"
    )
    binding = PageBinding(url="https://example", heading="Öffnungszeiten Test")
    with pytest.raises(ParseError):
        parse_opening_hours(html, binding, "Test", FacilityType.POOL, T0)


# --- Day tokenization ------------------------------------------------------


def test_range_parses_monday_to_sunday():
    from src.opening_hours_parser import _tokenize_days

    assert _tokenize_days("Mo bis So") == [
        "monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday",
    ]


def test_range_wraps_around():
    from src.opening_hours_parser import _tokenize_days

    # "Samstag bis Montag" = Sa, So, Mo
    assert _tokenize_days("Samstag bis Montag") == [
        "saturday", "sunday", "monday",
    ]


def test_list_form_parses():
    from src.opening_hours_parser import _tokenize_days

    assert _tokenize_days("Mo, Mi, Fr") == ["monday", "wednesday", "friday"]


def test_full_day_names_map_to_english():
    from src.opening_hours_parser import _tokenize_days

    assert _tokenize_days("Dienstag") == ["tuesday"]
    assert _tokenize_days("Sonntag") == ["sunday"]
