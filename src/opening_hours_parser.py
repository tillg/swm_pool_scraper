"""
Parse a facility's opening hours from its SWM page HTML.

The parser locates the heading element matching `binding.heading`, reads the
surrounding content block (`<div class="text-plus__col">`), and extracts a
weekly schedule from weekday-annotated time lines.

Outcome rules (D4 in architecture.md):
  - at least one weekday interval parsed           -> status = "open"
  - no heading found AND page text contains a
    closed-for-season marker                       -> status = "closed_for_season"
  - anything else                                  -> raise ParseError

The set of closed-for-season markers lives in CLOSED_SEASON_MARKERS; extending
it is a one-line change.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from .facilities import FacilityType
from .facility_pages import PageBinding
from .opening_hours_model import (
    STATUS_CLOSED_FOR_SEASON,
    STATUS_OPEN,
    WEEKDAYS,
    FacilityOpeningHours,
)


class ParseError(RuntimeError):
    pass


CLOSED_SEASON_MARKERS: Tuple[str, ...] = (
    "Eislaufsaison",          # "Die Eislaufsaison ... ist beendet."
    "Saison beendet",
    "Saison ist beendet",
    "Winterpause",
    "Sommerpause",
    "Derzeit geschlossen",
)

# Day tokens (short and long, German)
_DAY_MAP = {
    "mo": "monday",     "montag": "monday",
    "di": "tuesday",    "dienstag": "tuesday",
    "mi": "wednesday",  "mittwoch": "wednesday",
    "do": "thursday",   "donnerstag": "thursday",
    "fr": "friday",     "freitag": "friday",
    "sa": "saturday",   "samstag": "saturday",
    "so": "sunday",     "sonntag": "sunday",
}

# "7 bis 23 Uhr" / "7.30 bis 23 Uhr" / "7.30 bis 9.30 Uhr"
_TIME_RE = r"(\d{1,2})(?:[.:](\d{2}))?"
_INTERVAL_RE = re.compile(
    rf"{_TIME_RE}\s*bis\s*{_TIME_RE}\s*Uhr",
    flags=re.IGNORECASE,
)

# Lines like "Kassenschluss: ..." are informational and do not disrupt the
# main weekday block — we skip them without stopping the scan.
_INFO_PREFIXES = (
    "kassenschluss",
    "badeschluss",
    "bade- und saunaschluss",
    "bade- und badeschluss",
    "saunaschluss",
)


def _tokenize_days(lhs: str) -> List[str]:
    """Return weekday keys for an LHS like 'Mo bis So' or 'Mo, Mi, Fr' or 'Dienstag'."""
    lhs = lhs.strip().rstrip(":").strip()
    # range form
    m = re.match(r"^(.+?)\s+bis\s+(.+?)$", lhs, re.IGNORECASE)
    if m:
        a = _DAY_MAP.get(m.group(1).strip().lower())
        b = _DAY_MAP.get(m.group(2).strip().lower())
        if not a or not b:
            return []
        i, j = WEEKDAYS.index(a), WEEKDAYS.index(b)
        if i <= j:
            return list(WEEKDAYS[i : j + 1])
        # cyclic wrap-around (e.g. "Samstag bis Montag")
        return list(WEEKDAYS[i:]) + list(WEEKDAYS[: j + 1])
    # list form
    days: List[str] = []
    for part in re.split(r"[,/]|\s+und\s+", lhs):
        key = _DAY_MAP.get(part.strip().lower())
        if key:
            days.append(key)
    return days


def _parse_intervals(rhs: str) -> List[Dict[str, str]]:
    intervals: List[Dict[str, str]] = []
    # An RHS may carry multiple intervals joined by "und": "7.30 bis 9.30 Uhr und 17.30 bis 20.30 Uhr"
    for m in _INTERVAL_RE.finditer(rhs):
        h1, m1, h2, m2 = m.groups()
        intervals.append(
            {
                "open": f"{int(h1):02d}:{m1 or '00'}",
                "close": f"{int(h2):02d}:{m2 or '00'}",
            }
        )
    return intervals


def _parse_line(line: str) -> Optional[List[Tuple[str, Dict[str, str]]]]:
    """Return (day, interval) pairs if line is a weekday-hours line, else None."""
    if ":" not in line:
        return None
    lhs, rhs = line.split(":", 1)
    if not rhs.strip():
        return None
    days = _tokenize_days(lhs)
    if not days:
        return None
    intervals = _parse_intervals(rhs)
    if not intervals:
        return None
    return [(d, iv) for d in days for iv in intervals]


def _find_heading(soup: BeautifulSoup, heading: str) -> Optional[Tag]:
    for tag_name in ("h2", "h3", "h4"):
        for h in soup.find_all(tag_name):
            if h.get_text(strip=True) == heading:
                return h
    return None


def _content_block(heading_el: Tag) -> Tag:
    """Return the facility's content container. SWM wraps each heading+content
    in a div.text-plus__col; fall back to the immediate parent otherwise."""
    parent = heading_el.parent
    if parent and parent.name == "div" and "text-plus__col" in (parent.get("class") or []):
        return parent
    return parent if parent is not None else heading_el


def _is_info_line(line: str) -> bool:
    lower = line.lower().rstrip(":").strip()
    return any(lower.startswith(p) for p in _INFO_PREFIXES)


def _extract_schedule_and_notes(
    content_text: str,
) -> Tuple[Dict[str, List[Dict[str, str]]], List[str]]:
    schedule: Dict[str, List[Dict[str, str]]] = {}
    notes: List[str] = []

    lines = [ln.strip() for ln in content_text.splitlines() if ln.strip()]
    started = False
    stopped = False
    for line in lines:
        if stopped:
            if line:
                notes.append(line)
            continue
        parsed = _parse_line(line)
        if parsed is not None:
            started = True
            for day, iv in parsed:
                schedule.setdefault(day, []).append(iv)
            continue
        # Non-matching line
        if _is_info_line(line):
            notes.append(line)
            continue
        if started:
            # first real breaker after main schedule — stop parsing schedule lines
            stopped = True
            notes.append(line)
        # else: pre-schedule noise (e.g. the heading text itself) — ignore
    return schedule, notes


def _detect_closed_for_season(page_text: str) -> Optional[str]:
    for marker in CLOSED_SEASON_MARKERS:
        if marker.lower() in page_text.lower():
            # return a short snippet around the marker for special_notes
            idx = page_text.lower().index(marker.lower())
            # Capture up to the end of the sentence
            tail = page_text[idx : idx + 200]
            end = len(tail)
            for punct in (". ", "\n"):
                p = tail.find(punct)
                if p != -1 and p < end:
                    end = p + len(punct.rstrip())
            return tail[:end].strip()
    return None


def parse_opening_hours(
    html: str,
    binding: PageBinding,
    pool_name: str,
    facility_type: FacilityType,
    scraped_at: datetime,
) -> FacilityOpeningHours:
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(separator="\n", strip=True)

    # Heading-less facilities (currently: the ice rink, which only publishes
    # opening hours during ice season). Treat presence of a closed-season
    # marker on the page as a successful closed_for_season outcome.
    if binding.heading is None:
        marker = _detect_closed_for_season(page_text)
        if marker is None:
            raise ParseError(
                f"{pool_name} ({facility_type.value}): binding.heading is None but "
                "no closed-for-season marker was found on the page. The page may "
                "have a live schedule now — add a heading to PAGE_BINDINGS."
            )
        return FacilityOpeningHours(
            pool_name=pool_name,
            facility_type=facility_type.value,
            status=STATUS_CLOSED_FOR_SEASON,
            url=binding.url,
            heading=None,
            weekly_schedule={},
            special_notes=[marker],
            raw_section=marker,
            scraped_at=scraped_at,
        )

    heading_el = _find_heading(soup, binding.heading)
    if heading_el is None:
        # Heading missing: the facility may be closed for season, or markup drifted.
        marker = _detect_closed_for_season(page_text)
        if marker is not None:
            return FacilityOpeningHours(
                pool_name=pool_name,
                facility_type=facility_type.value,
                status=STATUS_CLOSED_FOR_SEASON,
                url=binding.url,
                heading=binding.heading,
                weekly_schedule={},
                special_notes=[marker],
                raw_section=marker,
                scraped_at=scraped_at,
            )
        raise ParseError(
            f"{pool_name} ({facility_type.value}): heading {binding.heading!r} "
            f"not found in {binding.url} and no closed-for-season marker present."
        )

    block = _content_block(heading_el)
    raw_section = block.get_text(separator="\n", strip=True)
    schedule, notes = _extract_schedule_and_notes(raw_section)

    if not schedule:
        # Found heading but couldn't parse a single weekday — unexpected, fail.
        raise ParseError(
            f"{pool_name} ({facility_type.value}): no weekday intervals parsed "
            f"under heading {binding.heading!r} at {binding.url}. Raw section "
            f"begins: {raw_section[:200]!r}"
        )

    return FacilityOpeningHours(
        pool_name=pool_name,
        facility_type=facility_type.value,
        status=STATUS_OPEN,
        url=binding.url,
        heading=binding.heading,
        weekly_schedule=schedule,
        special_notes=notes,
        raw_section=raw_section,
        scraped_at=scraped_at,
    )
