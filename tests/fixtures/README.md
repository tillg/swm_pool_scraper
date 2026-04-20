# HTML fixtures

Snapshots of SWM facility pages used by opening-hours parser tests.

Files:

- `olympia-schwimmhalle.html` — pool-only page (Olympia is registered only as
  a pool; the page also shows a sauna subsection but we don't scrape it).
- `cosimawellenbad.html` — shared pool + sauna page.
- `westbad-hallenbad.html` — shared page with unusual sauna heading
  (`Öffnungszeiten Saunainsel (textilfrei)`).
- `dantebad.html` — pool + sauna under a nested URL slug, with an h2
  subsection hierarchy (not h3 like other shared pages).
- `eislaufen.html` — ice rink page captured during the off-season; contains
  the closed-for-season marker `"Die Eislaufsaison … ist beendet."` and does
  **not** include an `#oeffnungszeiten` anchor.

## Refreshing

When SWM changes the markup and the parser breaks:

```bash
for slug in olympia-schwimmhalle cosimawellenbad westbad-hallenbad eislaufen; do
  curl -sSL -A 'Mozilla/5.0' "https://www.swm.de/baeder/$slug" \
    > tests/fixtures/$slug.html
done
curl -sSL -A 'Mozilla/5.0' \
  "https://www.swm.de/baeder/freibaeder-muenchen/dantebad" \
  > tests/fixtures/dantebad.html
```

The ice-rink fixture is the expected steady state outside ice season. When
ice season returns and the page grows an `#oeffnungszeiten` anchor, capture
a second fixture (e.g. `eislaufen-open.html`) and add a parser test for it.
