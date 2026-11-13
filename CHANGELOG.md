# Changelog

## 2026-11-10 - 34 person-defined routes added

- 34 person-defined routes added as records, each with its creator, the guide or page it is got from (free or for sale), and the creator's words on sharing the track.
- 1 has a track, from OpenStreetMap under the ODbL: the Big SEKI Loop (relation 11628437), 251.2 km against the published 249 km. 33 have no track, each saying why: 13 are sold as a guide, 2 are withheld by the creator, 3 are not settled, and 15 are open but have no licence that allows passing the track on and no OpenStreetMap route relation.
- The Vancouver Island Trail is already listed as `vancouver-island`, an association's trail with a track, and is unchanged.
- 138 records now; 85 ship a track and 53 are records only.

## 2026-11-10 - Person-defined routes added to the rule and the schema

- The inclusion rule now lists person-defined routes as well as designated trails: high routes, traverses and loops that a person or a small group worked out and published, at the same 50-mile floor. See README.md, section "Inclusion rule".
- The rule follows the creator's choice. Where the creator sells the route or chooses not to publish a track, the record has no track and no track is included from any source, OpenStreetMap included. Where the creator publishes the track freely, a track is included only where the creator's terms allow it or where OpenStreetMap carries the route as a relation.
- New record fields in docs/schema.md: `kind`, the `[route]` table (creator, year, track policy, the creator's words) and the `[[guide]]` array (what the route is got from, free or for sale, with price, publisher and ISBN where known).
- tools/validate.py checks the new fields and the track rule. tools/build_index.py carries `kind` and `line_policy` into trails.csv and index.geojson, and the README gets a second generated table for routes.
- NOTICE.md says a route's creator can ask for a record to be corrected or removed.

## 2026-11-10 - Floor lowered to 50 miles, and 40 trails added

- The inclusion rule is now 50 miles (80 km) instead of 100 km, in README.md, CONTRIBUTING.md and the tier definitions in docs/schema.md. The reason is the owner's: "It's basically multi day wilderness backpacking."
- 40 designated trails added, each with its steward, the page the length was read on, and its designation. 35 have a track built from the trail's OpenStreetMap route relation; 5 are records only, with the reason stated, because OpenStreetMap has no route relation for them.
- The new trails cover Pennsylvania (10), New England and New York (8), New Jersey and the Highlands (2), the southern Appalachians and the Ozarks (3), the Mid-Atlantic (1), the northern plains and the Black Hills (2), California and Oregon (2), and Canada (12).
- 104 trail records now; 84 ship a track and 20 are records only.

## 2026-11-09 - Tracks for nine trails from OpenStreetMap

- Added tracks from OpenStreetMap (ODbL-1.0) for nine trails that shipped as records only: Arizona, Florida, Ice Age, North Country, Great Divide Trail, Idaho Centennial, Long Path, Mid State and Superior Hiking. Each record names its relation, the measured length and the gap from the published length.
- The four National Scenic Trails among them (Arizona, Florida, Ice Age, North Country) now have a track that may be passed on.
- 49 trails of 64 now ship a track; 15 are records only. The Idaho Centennial Trail track is the west half only (about 20% of the trail) and says so.

## 2026-11-09 - First public release

- 64 trail records (United States and Canada).
- 40 trails with an included track; 24 records only, each saying why no track is included.
- Tracks from OpenStreetMap, United States federal agencies, the Pacific Crest Trail Association and the Continental Divide Trail Coalition, each under the terms in its record.
- 38 trail logos, each naming its holder in the record.
- Tools: `tools/validate.py` and `tools/build_index.py` (Python 3, standard library only).
- Generated files: `trails.csv`, `index.geojson`, and the trail table in README.md.
