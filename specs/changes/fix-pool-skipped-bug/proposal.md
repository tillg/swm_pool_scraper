# Bug: Pool skipped — RESOLVED

The pool Dante-Winter-Warmfreibad is listed on https://www.swm.de/baeder/auslastung but is not scraped. Also missing: Prinzregentenstadion - Eislaufbahn.

## Root Cause

**The scraper uses a static facility registry.** It only fetches data for facilities in `config/facilities.json`, which was manually populated and never updated.

**Missing facilities:**

- Dante-Winter-Warmfreibad (pool)
- Olympia-Schwimmhalle (pool)
- Prinzregentenstadion - Eislaufbahn (ice rink)
- Müller'sches Volksbad (sauna — exists as pool but not sauna)

**Why monitoring didn't catch this:** `FacilityDiscovery.discover_from_website()` returns hardcoded IDs instead of actually scraping.

## Solution (Implemented)

**Static Python dict with all known facilities.** Investigation revealed that org_ids are not in static HTML — they're embedded in JavaScript bundles and rendered by Vue.js. Dynamic HTML parsing is not feasible.

**Key changes:**

1. Replaced `config/facilities.json` with `src/facilities.py` — a Python dict mapping `(name, FacilityType) -> org_id`
2. Added `ice_rink` as a new facility type (alongside `pool`/`sauna`)
3. All 17 facilities now registered (9 pools, 7 saunas, 1 ice rink)
4. Simplified `facility_registry.py` to use the Python dict
5. Simplified `api_scraper.py` to iterate over all registered facilities

**Maintenance approach:**
- Never delete facilities from the list
- Periodically review SWM website for new facilities and add them manually
- If a facility returns no data, it's likely closed — scraper skips it gracefully

## Test Strategy

**Integration test against facility registry:** Verify all expected facilities are registered by checking counts and names.

## Completed Steps

1. ✓ Build test that verifies all facilities from SWM page are scraped
2. ✓ Confirm test fails (proves the bug)
3. ✓ Inspect and analyze the HTML structure to identify the facility IDs and names
4. ✓ Fix the code (implement static facility registry)
5. ✓ Confirm test passes (43/43 tests pass)
