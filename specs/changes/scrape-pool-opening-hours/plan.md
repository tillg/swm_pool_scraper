# Implementation Plan: Facility Opening Hours Scraper

Ordered, checkbox tasks. Each should be small enough to implement and verify
in one pass.

## 1. Discover URLs and section ids

- [x] ~Fetch `/baeder/auslastung` and extract links~ — overview page is
      JS-rendered; the category pages `/baeder/hallenbaeder-muenchen`,
      `/baeder/saunen-muenchen`, and `/baeder/eislaufen` list facility links
      statically.
- [x] Open each URL and record the **heading** used by the pool and sauna
      subsections. Discovery outcome: `id="oeffnungszeiten"` is an anchor
      separator; actual hours live in **sibling `<section>` modules
      identified by heading text**. Binding shape updated to
      `(url, heading)` in architecture.md.
- [x] Dantebad (sauna) and Dante-Winter-Warmfreibad (pool) share one page
      (`/baeder/freibaeder-muenchen/dantebad`) — **7 shared pages, not 6**.
- [x] Ice rink lives at `/baeder/eislaufen`. Currently **closed for season**
      (no `oeffnungszeiten` anchor present), marker text:
      `"Die Eislaufsaison 2025/2026 ist beendet."`.
- [x] Initial `CLOSED_SEASON_MARKERS` derived:
      `"Eislaufsaison"` + `"beendet"`, plus the generic keywords
      `"Saison beendet"`, `"Winterpause"`, `"Sommerpause"`.
- [x] `(name, FacilityType) → (url, heading)` recorded; see
      `PAGE_BINDINGS` populated in step 2.

## 2. Add `src/facility_pages.py`

- [x] Create a frozen `PageBinding` dataclass (`url`, `heading`).
- [x] Populate `PAGE_BINDINGS: Dict[Tuple[str, FacilityType], PageBinding]`
      with all 17 entries from step 1.
- [x] Add helpers: `get_binding(name, type)` (raises on missing) and
      `unique_urls()` for deduplicated fetching.

## 3. Add `FACILITY_PAGE_BASE_URL` to `config.py`

- [x] Add the base URL constant alongside the existing `SWM_URL`.

## 4. Enforce coverage invariant

- [x] `tests/test_facility_pages_coverage.py`:
  - [x] Every `FACILITIES` key has a `PAGE_BINDINGS` entry.
  - [x] Every `PAGE_BINDINGS` key exists in `FACILITIES`.
  - [x] Shared-page facilities have identical `url` but distinct `heading`.

## 5. Define the data model

- [x] `src/opening_hours_model.py` with `FacilityOpeningHours` dataclass:
      `pool_name`, `facility_type`, `status` (`"open" | "closed_for_season"`),
      `url`, `heading`, `weekly_schedule`, `special_notes`, `raw_section`,
      `scraped_at`.
- [x] Implement `to_dict()` producing the per-facility JSON shape from
      `architecture.md`.

## 6. Capture fixture HTML

- [x] Save fixtures to `tests/fixtures/` for all 10 unique pages:
  - [x] `olympia-schwimmhalle.html` — pool-only, open.
  - [x] `cosimawellenbad.html` — shared pool + sauna, both open.
  - [x] `eislaufen.html` — ice rink, currently closed for season.
  - [x] `dantebad.html` — shared page, pool uses split Mo/Mi/Fr vs
        Di/Do/Sa/So pattern.
  - [x] `westbad-hallenbad.html` — sauna has unusual heading
        ("Öffnungszeiten Saunainsel (textilfrei)").
  - [x] Plus `bad-giesing-harlaching`, `michaelibad-hallenbad`,
        `muellersches-volksbad`, `nordbad`, `suedbad`.
- [x] Brief README in `tests/fixtures/` describing how to refresh them.

## 7. Implement the HTML parser

- [x] `src/opening_hours_parser.py` exposing
      `parse_opening_hours(html, binding, pool_name, facility_type,
      scraped_at) -> FacilityOpeningHours`.
- [x] `CLOSED_SEASON_MARKERS` populated from step 1 (case-insensitive
      substring match).
- [x] Locate heading via `soup.find_all('h{2,3,4}')` + exact text match;
      content block is the parent `<div class="text-plus__col">`.
- [x] Extract weekly schedule into `weekday → [{open, close}]`. Accept
      short/long German weekday names (Mo/Montag...); support range ("Mo
      bis So"), list ("Mo, Mi, Fr"), wrap-around ("Samstag bis Montag"),
      and multiple intervals per day ("... und ...").
- [x] Outcome logic:
  - [x] At least one interval parsed → `status = "open"`.
  - [x] No heading found AND page text hits `CLOSED_SEASON_MARKERS` →
        `status = "closed_for_season"`, empty schedule, marker captured
        in `special_notes`.
  - [x] Otherwise → raise `ParseError`.
- [x] `Kassenschluss`/`Badeschluss`/`Saunaschluss` info lines pass through
      without stopping schedule parsing; any other non-match after the
      main schedule stops parsing and remaining lines become
      `special_notes` (prevents Wellenzeiten/Damentag sub-schedules from
      leaking into the main weekly_schedule).

## 8. Unit-test the parser

- [x] `tests/test_opening_hours_parser.py` (14 tests):
  - [x] Pool fixture parses the expected weekdays.
  - [x] Shared-page fixture yields distinct schedules for pool vs sauna.
  - [x] Wellenzeiten sub-block does NOT leak into schedule but DOES land
        in notes.
  - [x] Kassenschluss passes through as note without breaking parsing.
  - [x] Split weekday groups parse correctly (Dantebad pool).
  - [x] Westbad sauna parses the unusual heading.
  - [x] Ice rink fixture yields `closed_for_season` with marker.
  - [x] Missing heading + no marker raises `ParseError`.
  - [x] Heading present but no parseable intervals raises.
  - [x] Day tokenization: range, wrap-around, list, full names.

## 9. Implement the scraper

- [x] `src/opening_hours_scraper.py` with `OpeningHoursScraper`:
  - [x] `requests.Session` with the same `Retry` strategy as `SWMAPIScraper`
        (3 retries, backoff 1).
  - [x] `assert_covers_facilities()` at the top of the run — coverage bug
        fails fast.
  - [x] Fetches each URL from `unique_urls()` once and caches the HTML.
  - [x] Iterates `FACILITIES` in declaration order; any parse error
        propagates as an exception.
- [x] Add `ManagedOpeningHoursScraper` context manager, mirroring
      `ManagedAPIScraper`.

## 10. Extend `DataStorage`

- [x] Add `save_opening_hours(entries, metadata)` that writes
      `facility_opening_YYYYMMDD_HHMMSS.json` using the same directory
      resolution (`test_mode` / `output_dir`) as `save_to_json`.
- [x] Emit per-type counts, `unique_pages_fetched`, `open_count`,
      `closed_for_season_count` in `scrape_metadata`.

## 11. Add the CLI

- [x] `scrape_opening_hours.py` at the repo root, same argument conventions
      as `scrape.py`:
  - [x] Args: `--test`, `--log-level`, `--output-dir`.
  - [x] On any exception: log, exit non-zero, **no snapshot written**.
  - [x] On success: call `save_opening_hours` and exit 0.
  - [x] Compact per-facility summary showing `status`.

## 12. Integration test

- [x] `tests/test_opening_hours_scraper.py` (4 tests) monkey-patches
      `OpeningHoursScraper._fetch` to return fixture HTML and verifies:
  - [x] Happy path returns 17 entries and writes the snapshot with correct
        per-type and per-status counts.
  - [x] A single-facility hard parse failure raises and **no file is
        written**.
  - [x] Shared pages yield two entries with distinct `facility_type`.

## 13. Wire up the daily schedule (in `swm_pool_data`)

> This step is a PR against the `swm_pool_data` repo, not this one.
> **Not done from here** — it needs to be implemented against that repo.

- [ ] Add `.github/workflows/load_opening_hours.yml`, modeled on the existing
      `scrape.yml`:
  - [ ] Schedule: once per day, early-morning Berlin time (e.g. 03:00 UTC).
  - [ ] Checkout both `swm_pool_data` and `swm_pool_scraper`.
  - [ ] `pip install -r scraper/requirements.txt`.
  - [ ] Run `python scraper/scrape_opening_hours.py --output-dir facility_openings_raw`.
  - [ ] Commit and push on success.
  - [ ] `permissions: contents: write`; default GH Actions email on failure
        reaches the operator (verify notification settings).
- [ ] Create directory `facility_openings_raw/` in `swm_pool_data` with a
      short `README.md` explaining the file format.

## 14. Update documentation (in this repo)

- [x] `README.md`: added an "Opening Hours (daily)" usage block with an
      example JSON entry and a note on adding new facilities.
- [x] `CLAUDE.md`: added a two-cadence table up front; listed the new file
      prefix and `tmp/` ignore under Data Management.

## 15. First production run & verification

- [x] Run `python scrape_opening_hours.py --test` locally — 17 entries
      scraped in ~1 second, all pools/saunas `open`, ice rink
      `closed_for_season`.
- [x] Spot-check Cosimawellenbad: pool = 07:30–23:00, sauna = 09:00–23:00
      (distinct schedules from a single fetched page — shared-page
      behaviour verified).
- [x] Spot-check ice rink: `status = closed_for_season`,
      `special_notes = ["Eislaufsaison 2025/2026 ist beendet."]`.
- [ ] Trigger the GH Actions workflow manually (`workflow_dispatch`) —
      blocked on step 13.

## 16. Post-launch follow-ups (out of scope)

- [ ] Optional CSV view of opening hours for ML joins.
- [ ] Structured capture of special schedules (school blocks, women-only
      sessions) beyond free-form `special_notes`.
- [ ] Replace free-form `special_notes` with structured date-range overrides
      once the shape becomes clear.
