"""
Static binding from (facility name, type) to the SWM page and heading where
its opening hours live.

Why a static table: facility names use umlauts/apostrophes, URL slugs are
inconsistent (`michaelibad-hallenbad`, `freibaeder-muenchen/dantebad`), and
shared pages host multiple facilities. The heading text is the stable
identifier for a facility's hours block on its page.

How the discovery was done (step 1 of the plan): the pool/sauna category
pages (`/baeder/hallenbaeder-muenchen`, `/baeder/saunen-muenchen`) list
per-facility links statically; the ice-rink page is `/baeder/eislaufen`.
Headings were read directly from each page's DOM.

For the ice rink, `heading` is None: the Prinzregentenstadion page exposes
opening hours only during ice season, and uses a different structural
pattern (not an `#oeffnungszeiten` anchor). The parser handles it via the
closed-for-season marker path; when ice season returns, the binding will
need a concrete heading.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .facilities import FACILITIES, FacilityType


@dataclass(frozen=True)
class PageBinding:
    url: str
    heading: Optional[str]


PAGE_BINDINGS: Dict[Tuple[str, FacilityType], PageBinding] = {
    # --- Pools ---
    ("Bad Giesing-Harlaching", FacilityType.POOL): PageBinding(
        "https://www.swm.de/baeder/bad-giesing-harlaching",
        "Öffnungszeiten Bad Giesing-Harlaching",
    ),
    ("Cosimawellenbad", FacilityType.POOL): PageBinding(
        "https://www.swm.de/baeder/cosimawellenbad",
        "Öffnungszeiten Hallenbad",
    ),
    ("Dante-Winter-Warmfreibad", FacilityType.POOL): PageBinding(
        "https://www.swm.de/baeder/freibaeder-muenchen/dantebad",
        "Öffnungszeiten Dante-Winter-Warmfreibad",
    ),
    ("Michaelibad", FacilityType.POOL): PageBinding(
        "https://www.swm.de/baeder/michaelibad-hallenbad",
        "Öffnungszeiten Hallenbad",
    ),
    ("Müller'sches Volksbad", FacilityType.POOL): PageBinding(
        "https://www.swm.de/baeder/muellersches-volksbad",
        "Öffnungszeiten Bad",
    ),
    ("Nordbad", FacilityType.POOL): PageBinding(
        "https://www.swm.de/baeder/nordbad",
        "Öffnungszeiten Hallenbad",
    ),
    ("Olympia-Schwimmhalle", FacilityType.POOL): PageBinding(
        "https://www.swm.de/baeder/olympia-schwimmhalle",
        "Öffnungszeiten Hallenbad",
    ),
    ("Südbad", FacilityType.POOL): PageBinding(
        "https://www.swm.de/baeder/suedbad",
        "Öffnungszeiten Hallenbad",
    ),
    ("Westbad", FacilityType.POOL): PageBinding(
        "https://www.swm.de/baeder/westbad-hallenbad",
        "Öffnungszeiten Hallenbad inklusive Saunalandschaft "
        "(Badebekleidung ist verpflichtend)",
    ),
    # --- Saunas ---
    ("Cosimawellenbad", FacilityType.SAUNA): PageBinding(
        "https://www.swm.de/baeder/cosimawellenbad",
        "Öffnungszeiten Sauna",
    ),
    ("Dantebad", FacilityType.SAUNA): PageBinding(
        "https://www.swm.de/baeder/freibaeder-muenchen/dantebad",
        "Öffnungszeiten Sauna",
    ),
    ("Michaelibad", FacilityType.SAUNA): PageBinding(
        "https://www.swm.de/baeder/michaelibad-hallenbad",
        "Öffnungszeiten Sauna",
    ),
    ("Müller'sches Volksbad", FacilityType.SAUNA): PageBinding(
        "https://www.swm.de/baeder/muellersches-volksbad",
        "Öffnungszeiten Sauna",
    ),
    ("Nordbad", FacilityType.SAUNA): PageBinding(
        "https://www.swm.de/baeder/nordbad",
        "Öffnungszeiten Sauna",
    ),
    ("Südbad", FacilityType.SAUNA): PageBinding(
        "https://www.swm.de/baeder/suedbad",
        "Öffnungszeiten Sauna",
    ),
    ("Westbad", FacilityType.SAUNA): PageBinding(
        "https://www.swm.de/baeder/westbad-hallenbad",
        "Öffnungszeiten Saunainsel (textilfrei)",
    ),
    # --- Ice rink ---
    ("Prinzregentenstadion - Eislaufbahn", FacilityType.ICE_RINK): PageBinding(
        "https://www.swm.de/baeder/eislaufen",
        None,
    ),
}


class UnknownBindingError(KeyError):
    pass


def get_binding(name: str, facility_type: FacilityType) -> PageBinding:
    try:
        return PAGE_BINDINGS[(name, facility_type)]
    except KeyError:
        raise UnknownBindingError(
            f"No PAGE_BINDINGS entry for ({name!r}, {facility_type.value}). "
            "Every facility in src/facilities.py must have a binding."
        )


def unique_urls() -> List[str]:
    return sorted({b.url for b in PAGE_BINDINGS.values()})


def assert_covers_facilities() -> None:
    """Raise if PAGE_BINDINGS and FACILITIES disagree on which facilities exist."""
    binding_keys = set(PAGE_BINDINGS.keys())
    facility_keys = set(FACILITIES.keys())
    missing = facility_keys - binding_keys
    orphan = binding_keys - facility_keys
    if missing or orphan:
        parts = []
        if missing:
            parts.append(f"missing bindings for {sorted(missing)}")
        if orphan:
            parts.append(f"orphan bindings for {sorted(orphan)}")
        raise AssertionError("; ".join(parts))
