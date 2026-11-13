# Third-party assets

Served from `/assets/`, so pages make no requests to CDNs or font services at
runtime. Map tiles, glyphs and sprites still come from OpenFreeMap.

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
