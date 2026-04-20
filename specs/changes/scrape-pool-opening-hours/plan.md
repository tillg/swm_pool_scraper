# Implementation Plan: Facility Opening Hours Scraper

Ordered, checkbox tasks. Each should be small enough to implement and verify
in one pass.

## 1. Discover URLs and section ids

- [ ] Fetch `https://www.swm.de/baeder/auslastung` and extract the per-facility
      links — this gives us the URL for each of the 17 facilities.
- [ ] Open each URL and record the section id(s) where opening hours live.
      For the six shared pages (Cosimawellenbad, Michaelibad, Nordbad, Südbad,
      Westbad, Müller'sches Volksbad) capture **two** section ids — pool and
      sauna.
- [ ] Confirm Dantebad (sauna-only) and Dante-Winter-Warmfreibad (pool-only)
      are separate pages.
- [ ] Confirm the ice-rink URL and section id for Prinzregentenstadion.
- [ ] Record each `(name, FacilityType) → (url, section_id)` in a scratch
      note. Escalate if any facility has no discoverable page or section.

## 2. Add `src/facility_pages.py`

- [ ] Create a frozen `PageBinding` dataclass (`url`, `section_id`).
- [ ] Populate `PAGE_BINDINGS: Dict[Tuple[str, FacilityType], PageBinding]`
      with all 17 entries from step 1.
- [ ] Add helpers: `get_binding(name, type)` (raises on missing) and
      `unique_urls()` for deduplicated fetching.

## 3. Add `FACILITY_PAGE_BASE_URL` to `config.py`

- [ ] Add the base URL constant alongside the existing `SWM_URL`.

## 4. Enforce coverage invariant

- [ ] `tests/test_facility_pages_coverage.py`:
  - [ ] Every `FACILITIES` key has a `PAGE_BINDINGS` entry.
  - [ ] Every `PAGE_BINDINGS` key exists in `FACILITIES`.
  - [ ] Shared-page facilities have identical `url` but distinct `section_id`.

## 5. Define the data model

- [ ] `src/opening_hours_model.py` with `FacilityOpeningHours` dataclass
      (`pool_name`, `facility_type`, `url`, `section_id`, `weekly_schedule`,
      `special_notes`, `raw_section`, `scraped_at`) and `to_dict()` producing
      the shape in `architecture.md`.

## 6. Capture fixture HTML

- [ ] Save three fixtures to `tests/fixtures/`:
  - [ ] `olympia_schwimmhalle.html` (pool-only).
  - [ ] `cosimawellenbad.html` (shared pool + sauna).
  - [ ] `prinzregentenstadion.html` (ice rink).
- [ ] Brief README in `tests/fixtures/` describing how to refresh them.

## 7. Implement the HTML parser

- [ ] `src/opening_hours_parser.py` exposing a pure function
      `parse_opening_hours(html, binding, pool_name, facility_type)
      -> FacilityOpeningHours`.
- [ ] Locate `binding.section_id` via BeautifulSoup.
- [ ] Parse weekly schedule into `weekday → [{open, close}]`. Accept `-` and
      `–`; map German weekday names (Montag..Sonntag) to English keys.
- [ ] Capture free-form notes into `special_notes`; preserve section text
      in `raw_section`.
- [ ] On missing section or unparseable schedule, **raise** — no partial
      results (per D4 hard-fail policy).

## 8. Unit-test the parser

- [ ] `tests/test_opening_hours_parser.py`:
  - [ ] Pool fixture parses the expected weekdays.
  - [ ] Shared-page fixture yields distinct schedules for pool vs sauna.
  - [ ] Ice-rink fixture parses.
  - [ ] Missing section id raises with a descriptive message.
  - [ ] German weekday names map to English keys.

## 9. Implement the scraper

- [ ] `src/opening_hours_scraper.py` with `OpeningHoursScraper`:
  - [ ] `requests.Session` with the same `Retry` strategy as `SWMAPIScraper`
        (3 retries, backoff).
  - [ ] Fetches each URL from `unique_urls()` once and caches the HTML.
  - [ ] For each `(name, type)` in `FACILITIES`, looks up the binding and
        calls `parse_opening_hours`.
  - [ ] Any fetch failure, missing section, or parse error propagates as an
        exception (hard fail).
  - [ ] Returns `List[FacilityOpeningHours]` of length 17 on success.
- [ ] Add `ManagedOpeningHoursScraper` context manager, mirroring
      `ManagedAPIScraper`.

## 10. Extend `DataStorage`

- [ ] Add `save_opening_hours(entries, metadata)` that writes
      `facility_opening_YYYYMMDD_HHMMSS.json` using the same directory
      resolution (`test_mode` / `output_dir`) as `save_to_json`.
- [ ] Emit the top-level shape from `architecture.md` (scrape_timestamp,
      per-type counts, `unique_pages_fetched`, `facilities` list).

## 11. Add the CLI

- [ ] `scrape_opening_hours.py` at the repo root:
  - [ ] Args: `--test`, `--log-level`, `--output-dir`.
  - [ ] Runs the scraper; on any exception log and exit non-zero **without
        writing a snapshot**.
  - [ ] On success, call `save_opening_hours` and exit 0.
  - [ ] Print a compact per-facility summary.

## 12. Integration test

- [ ] `tests/test_opening_hours_scraper.py` monkey-patches
      `requests.Session.get` to return fixture HTML per URL and verifies:
  - [ ] Happy path returns 17 entries and writes the snapshot.
  - [ ] A single-facility parse failure raises and **no file is written**.
  - [ ] Shared pages yield two entries with distinct `facility_type`.

## 13. Wire up the daily schedule

- [ ] Match whatever already schedules `scrape.py`. Default to a GitHub
      Actions workflow (simpler to configure email on failure).
- [ ] Run `python scrape_opening_hours.py` once per day, early-morning
      Berlin time (e.g. 04:00 local).
- [ ] Configure failure notifications so the operator gets an email on any
      non-zero exit.

## 14. Update documentation

- [ ] `README.md`: document the two cadences, show a `facility_opening_*.json`
      example (including a shared-page case), and note how to re-confirm
      bindings when a facility is added.
- [ ] `CLAUDE.md`: mention the `facility_opening_*.json` prefix under Data
      Management and the daily cadence.

## 15. First production run & verification

- [ ] Run `python scrape_opening_hours.py --test` locally; inspect the file.
- [ ] Spot-check Cosimawellenbad: pool and sauna must have different
      schedules.
- [ ] Run without `--test`; confirm the file lands in `scraped_data/` and
      commit it (matches existing policy of tracking production JSON).

## 16. Post-launch follow-ups (out of scope)

- [ ] Optional CSV view of opening hours for ML joins.
- [ ] Structured capture of special schedules (school blocks, women-only
      sessions) beyond free-form `special_notes`.
