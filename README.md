# Field Kit

Offline survival / tactical / emergency PWA for a Samsung Galaxy S22 Ultra.
Live: https://jordanmcnulty3-max.github.io/field-kit/ (GitHub Pages, branch `main`, folder `/`).

This repo is the single source of truth: source **and** the deployed build live here.
Each release is one commit tagged `vN`.

## Layout

| Path | What it is |
|---|---|
| `src/shell.html` | Page shell + all CSS. The Survival section is a placeholder filled from `src/survival.html`. |
| `src/survival.html` | Survival content. `{{fig:name\|caption}}` placeholders become diagrams. |
| `src/geo.js` | UTM / MGRS / DMS parsing, distance, bearing |
| `src/ballistics.js` | Point-mass G1/G7 solver |
| `src/app.js` | Navigation, GPS, compass, waypoints, ballistics UI, emergency tools, backup/restore, update banner. `APP_VERSION` lives here. Exposes `window.FK`. |
| `src/map.js` | Leaflet map, USGS offline tiles (Cache Storage `fk-tiles`), tracks, GPX export |
| `src/survival.js` | Region picker, topic search, tap-to-enlarge diagrams |
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
# bump APP_VERSION in src/app.js and VERSION in src/sw.js to the same N
python3 build.py              # refuses to build if the two versions differ
git add -A && git commit -m "vN: what changed" && git tag vN
git push && git push --tags   # needs a token with Contents: write on this repo
```

Phones pick up the new version on the next open (update banner) because the service-worker cache name changed.
To roll back: `git checkout vOLD -- src figs vendor`, set both version numbers to a new, higher N, rebuild, commit and tag vN.
(Reusing an old version number would leave installed phones on their cached copy.)
