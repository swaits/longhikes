# Changelog

## 2026-11-10 - Floor lowered to 50 miles, and 40 trails added

- The inclusion rule is now 50 miles (80 km) instead of 100 km, in README.md, CONTRIBUTING.md and the tier definitions in docs/schema.md. The reason is the owner's: "It's basically multi day wilderness backpacking."
- 40 designated trails added, each with its steward, the page the length was read on, and its designation. 35 have a line built from the trail's OpenStreetMap route relation; 5 are records only, with the reason stated, because OpenStreetMap has no route relation for them.
- The new trails cover Pennsylvania (10), New England and New York (8), New Jersey and the Highlands (2), the southern Appalachians and the Ozarks (3), the Mid-Atlantic (1), the northern plains and the Black Hills (2), California and Oregon (2), and Canada (12).
- 104 trail records now; 84 ship a line and 20 are records only.

## 2026-11-09 - Lines for nine trails from OpenStreetMap

- Added lines from OpenStreetMap (ODbL-1.0) for nine trails that shipped as records only: Arizona, Florida, Ice Age, North Country, Great Divide Trail, Idaho Centennial, Long Path, Mid State and Superior Hiking. Each record names its relation, the measured length and the gap from the published length.
- The four National Scenic Trails among them (Arizona, Florida, Ice Age, North Country) now have a line that may be passed on.
- 49 trails of 64 now ship a line; 15 are records only. The Idaho Centennial Trail line is the west half only (about 20% of the trail) and says so.

## 2026-11-09 - First public release

- 64 trail records (United States and Canada).
- 40 trails with an included line; 24 records only, each saying why no line is included.
- Lines from OpenStreetMap, United States federal agencies, the Pacific Crest Trail Association and the Continental Divide Trail Coalition, each under the terms in its record.
- 38 trail logos, each naming its holder in the record.
- Tools: `tools/validate.py` and `tools/build_index.py` (Python 3, standard library only).
- Generated files: `trails.csv`, `index.geojson`, and the trail table in README.md.
