# Third-party assets

Served from the site's own address (the build writes each file as
`/immutable/<name>.<hash>.<ext>`, see `web/olt/fingerprint.py`), so pages make
no requests to CDNs or font services at runtime. Map tiles, glyphs and sprites still come from OpenFreeMap, and the
trail maps' elevation tiles from Terrain Tiles on AWS.

## MapLibre GL JS

| File | Package | Version | Licence |
| --- | --- | --- | --- |
| `maplibre-gl/maplibre-gl.js`, `maplibre-gl/maplibre-gl.css` | maplibre-gl | 4.7.1 | BSD-3-Clause, `maplibre-gl/LICENSE.txt` |

Downloaded unchanged from `https://unpkg.com/maplibre-gl@4.7.1/dist/` on
2026-11-10. SHA-256:

```text
be9633c4d870e26fb37f1cfe5c5a77181667114003ea16207ac7850d8da8add1  maplibre-gl.js
576b085fdd9487a65a19215328c1e086c07ce5bf6da09b666b3806d3d008dae9  maplibre-gl.css
```

The standard build runs its worker from a `blob:` URL, which the site's
Content-Security-Policy allows (`worker-src blob:`). The bundle's last line
names a source map that is not vendored.

To upgrade: download `dist/maplibre-gl.js`, `dist/maplibre-gl.css` and
`LICENSE.txt` of the new version into `maplibre-gl/`, update this file, and
check that the trail maps still draw.

## maplibre-contour

| File | Package | Version | Licence |
| --- | --- | --- | --- |
| `maplibre-contour/maplibre-contour.js` | maplibre-contour | 0.1.1 | BSD-3-Clause (with code from d3-contour, ISC, and vt-pbf, MIT), `maplibre-contour/LICENSE.txt` |

Draws the contour lines of the trail pages' outdoor map in the browser, from
the same elevation tiles as the relief. `maplibre-contour.js` is the package's
`dist/index.min.js` and `LICENSE.txt` its `LICENSE`, unchanged, from the npm
tarball `https://registry.npmjs.org/maplibre-contour/-/maplibre-contour-0.1.1.tgz`
(SHA-1 `d8aa3e3b62c8d097fc4eacb3d849635a0b662ede`, as the registry lists it),
downloaded 2026-11-15; unpkg serves the same bytes. SHA-256:

```text
055e45d0a76aaeaaf5a96765b8ce524abba3272456be75e715081e235ebd1262  maplibre-contour.js
b4a3261f4af65db24e6a2ca23093ac25619e6fe0b5ca5ec75fb09a49817b5c8d  LICENSE.txt
```

It defines `window.mlcontour`. Only trail pages load it (deferred, after
MapLibre; `olt/layout.py` `outdoor=True`), and `app.js` draws the map without
contours when it is missing. It runs its work in a worker made from a `blob:`
URL (`worker-src blob:`) and fetches the elevation tiles there with `fetch()`
(`connect-src` names the tiles' path). No `eval`, no source map.

To upgrade: put `dist/index.min.js` of the new version here as
`maplibre-contour.js`, with its `LICENSE`, update this file, and check the
contours and the relief on a trail page in Firefox and in Chromium.

## Outdoor map style (`../map/`)

`outdoor.json` is this site's own style for the trail pages' outdoor map,
derived from OpenFreeMap's Liberty style (MIT), a fork of OSM Liberty and OSM
Bright (BSD-3-Clause code, CC BY 4.0 design). `LICENSE.txt` beside it keeps
their notices; the design credit, "© OpenMapTiles", is in the corner of every
map. The style keeps OpenFreeMap's tiles, glyphs and sprites. Its elevation
source is Terrain Tiles on AWS, the data `tools/elevation.py` uses, credited
under every trail map (`olt/common.py` `TRAIL_MAP_CREDIT`).

## Web fonts (`../fonts/`)

Latin subset only, as served by Google Fonts on 2026-11-10. Characters outside
it fall back to the system serif or sans. The `@font-face` rules are at the top
of `../style.css`.

| File | Family | Weights | Licence |
| --- | --- | --- | --- |
| `source-serif-4-latin.woff2` | Source Serif 4, roman | variable 400-700 | SIL OFL 1.1, `OFL-source-serif-4.txt` |
| `source-serif-4-italic-latin.woff2` | Source Serif 4, italic | variable 400-600 | SIL OFL 1.1, `OFL-source-serif-4.txt` |
| `ibm-plex-sans-condensed-{400,500,600}-latin.woff2` | IBM Plex Sans Condensed | 400, 500, 600 | SIL OFL 1.1, `OFL-ibm-plex-sans-condensed.txt` |

Source Serif 4 is the weight-only variable font (no optical-size axis): 51 KB
instead of 122 KB.
