# Field Kit

Offline survival / tactical / emergency PWA for a Samsung Galaxy S22 Ultra.
Live: https://jordanmcnulty3-max.github.io/field-kit/ (GitHub Pages, branch `main`, folder `/`).

This repo is the single source of truth: source **and** the deployed build live here.
Each release is one commit tagged `vN` (versions are `N` or dotted `N.M`, for example `v7` or `v7.1`).

## Layout

| Path | What it is |
|---|---|
| `src/shell.html` | Page shell + all CSS. The Survival section is a placeholder filled from `src/survival.html`. |
| `src/survival.html` | Empty Survival tab (home, page and live-region containers); `survival.js` draws everything in it. |
| `src/survival/*.json`, `src/checklists/*.json` | Survival topics and checklists, one JSON file each. A topic's diagrams are `fig` blocks naming a diagram in `figs/`. |
| `src/tooldata/*.json` | Numbers a Survival tool works from, one JSON file per tool (`water.json`: the Water planner's amounts and conversions, with sources) |
| `src/protocols/*.json` | Emergency protocols, one JSON file each |
| `src/geo.js` | UTM / MGRS / DMS parsing, distance, bearing |
| `src/ballistics.js` | Point-mass G1/G7 solver |
| `src/app.js` | Navigation, GPS, compass, waypoints, ballistics UI, emergency tools, backup/restore, update banner. `APP_VERSION` lives here. Exposes `window.FK`. |
| `src/map.js` | Leaflet map, USGS offline tiles (Cache Storage `fk-tiles`), tracks, GPX export |
| `src/survival.js`, `src/survival-tools.js` | Survival home (Where / When filters, pinned, recent, topics by category), topic and checklist pages, tools (SOS light, Daylight and moon, Water planner), tap-to-enlarge diagrams |
| `src/sw.js` | Service worker. Cache name `VERSION = 'fieldkit-vN'` lives here. |
| `src/manifest.json` | PWA manifest |
| `figs/figs.py`, `figs/rope.py` | All diagrams, drawn as SVG in Python (later `svg()` calls override earlier ones) |
| `figs/figs.css`, `figs/markers.html` | Diagram styles and arrowhead markers |
| `vendor/` | Leaflet 1.9.4 (unchanged upstream files) |
| `build.py` | Builds the root files below from everything above |
| `index.html`, `sw.js`, `manifest.json`, `leaflet.js`, `leaflet.css` | **Build output, served by Pages. Never edit by hand.** |
| `icon-*.png` | App icons (static) |

## Release

```
git clone https://github.com/jordanmcnulty3-max/field-kit && cd field-kit
# edit src/ or figs/
# bump APP_VERSION in src/app.js and VERSION in src/sw.js to the same N (or N.M)
python3 build.py --release    # refuses if the two versions differ, or if any protocol, topic, checklist, tool data or report wording is still draft
git add -A && git commit -m "vN: what changed" && git tag vN
git push && git push --tags   # needs a token with Contents: write on this repo
```

Phones pick up the new version on the next open (update banner) because the service-worker cache name changed.
To roll back: `git checkout vOLD -- src figs vendor`, set both version numbers to a new, higher N, rebuild, commit and tag vN.
(Reusing an old version number would leave installed phones on their cached copy.)

## Checks

Every push to any branch runs `.github/workflows/checks.yml` (results on the repo's Actions tab):

- **Build and tests (Chromium):** builds, fails if the committed root files differ from a fresh build of `src/`, runs the full test suite. On `main` and tags it also runs the `--release` draft check.
- **iPhone engine (WebKit) layout:** the sheet, screen and button-size tests in WebKit, Safari's engine (catches the kind of bug the first iPhone test found).
- **Lighthouse:** audits Survival, Tactical map and Emergency as a phone. Accessibility below 95 fails; the reports are kept as a download on the run.

Run them locally:

```
pip install -r requirements-dev.txt && python3 -m playwright install chromium webkit
python3 -m pytest -q -n auto                      # Chromium
FK_BROWSER=webkit python3 -m pytest -q tests/test_sheet.py tests/test_tactical_layout.py
python3 build.py _site && npx @lhci/cli@0.16.1 autorun
```
