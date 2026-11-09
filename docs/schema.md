# Record schema

Each trail has one record: `<id>/trail.toml`. The file is TOML. Field names are stable: tools read them, so fields are added, not renamed. Optional fields are marked "where present".

Example (shortened):

```toml
id = "long-trail"
name = "Long Trail (Vermont)"
short_name = "LT"
country = "US"
regions = ["VT"]
length_km = 438
length_note = "272 mi published"
tier = "regional"
designation = "Green Mountain Club; oldest long-distance trail in the US"
wave = 1

[source]
status = "osm-only"
publisher = "Green Mountain Club (publishes the trail)"
url = "https://www.openstreetmap.org/relation/391736"
licence = "ODbL-1.0"
attribution = "OpenStreetMap contributors (ODbL)"
osm_only = true
line_file = "line.geojson"
```

## Top level

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `id` | string | Stable identifier. Equals the directory name. Never changes. | `"long-trail"` |
| `name` | string | The trail's own name. | `"Long Trail (Vermont)"` |
| `short_name` | string | Abbreviation, as carried on the trail's shield. | `"LT"` |
| `country` | string | `US` or `CA`. | `"US"` |
| `regions` | array of strings | State, province or territory codes crossed. | `["VT"]` |
| `length_km` | integer | Published length in kilometres. A check value, not measured from the line. | `438` |
| `length_note` | string | Where the published length comes from. | `"272 mi published"` |
| `tier` | string | `national` (US National Scenic Trail), `regional` (100 km or more), `short` (well-known, 60-100 km), `deferred`, or `candidate`. | `"regional"` |
| `designation` | string | What makes it a long trail: statute, agency or association. | `"National Scenic Trail (1968)"` |
| `wave` | integer or string | `1` for trails in the first set; `"held"` where listing is undecided. | `1` |
| `wave_note` | string, where present | Why a held trail is held. | `"Held: no usable whole line exists."` |
| `inclusion` | string, where present | `nst-unconditional` for every National Scenic Trail; `candidate-decision-pending` for a candidate. Absent otherwise. | `"nst-unconditional"` |

## `[source]`: where the line comes from

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `status` | string | `verified` (downloaded and measured), `found` (source located, not downloaded), `osm-only` (only an OpenStreetMap relation), or `none`. | `"osm-only"` |
| `publisher` | string | Who publishes the line. | `"Green Mountain Club"` |
| `url` | string | Where to ask for the line: a layer or relation page, never a dated file name. | `"https://www.openstreetmap.org/relation/391736"` |
| `discovery` | string | How to tell whether the source has a newer release. | `"osm-relation-version: ..."` |
| `format` | string | What the source serves and how it is paged. | `"OpenStreetMap route relation"` |
| `crs` | string | Coordinate system the source stores. Published files are longitude/latitude (EPSG:4326). | `"EPSG:4326"` |
| `licence` | string | Licence id, from: `us-gov-public-domain`, `CC-BY-4.0`, `CC-BY`, `ODbL-1.0`, `CC-BY-NC-ND-4.0`, `none-stated`, `restricted`, `unknown`. | `"ODbL-1.0"` |
| `licence_text` | string | What the source actually says, with the page it was read on. Not legal advice. | `"OpenStreetMap contributors, ODbL 1.0 ..."` |
| `attribution` | string | The credit line to show, as the source asks. | `"OpenStreetMap contributors (ODbL)"` |
| `osm_only` | boolean | `true` when OpenStreetMap is the only source of the included line. | `true` |
| `mainline` | string | How the main line is told apart from alternates, connectors and side trails in this source. | `"One relation tagged complete."` |
| `decision` | string, where present | A settled inclusion question, stated neutrally. | `"included-named"` |
| `decision_text` | string, where present | What the decision settles, in one sentence. | `"Included with its name and logo."` |
| `source_checked` | string (date) | Date the source was last read, `YYYY-MM-DD`. | `"2026-11-08"` |
| `redistributable` | boolean | `true` when the source's terms allow its line to be passed on. Must be `true` for every included data file. | `true` |
| `line_source` | string | Short name of the included line's source, or `none (no line included)`. | `"OpenStreetMap"` |
| `line_file` | string | Included main line file, usually `"line.geojson"`, or `""` when no line is included. | `"line.geojson"` |
| `line_absent_reason` | string, where no line | Why no line is included. | `"Publisher's GIS data is not licensed for redistribution ..."` |
| `length_gap_note` | string, where present | Why the measured line differs from `length_km` by more than 15% (partly unbuilt, planned length, side trails counted, and so on). Required in that case. | `"The trail is not finished: built passages are what is mapped."` |

## `[osm]`: the OpenStreetMap relation

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `relation` | integer | Best OpenStreetMap relation id, or `0` for none found or not searched. | `391736` |
| `note` | string | What is in OpenStreetMap for this trail. | `"OSM 391736 has a 437.7 km distance tag."` |

## `[shield]`: the logo

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `status` | string | `use-real-logo`, `no-logo-exists`, or `logo-not-found`. | `"use-real-logo"` |
| `logo_source` | string | Where the logo art was taken from, when known. | `"https://www.greenmountainclub.org/"` |
| `contact` | string | Who holds the emblem or mark. | `"Green Mountain Club"` |
| `note` | string | What is known about the logo and its terms. | `"No logo or shield policy found."` |
| `logo_file` | string | Included logo file (`"shield.svg"` or `"shield.png"`), or `""` when none is included. | `"shield.svg"` |
| `logo_owner` | string | The logo's holder, named whenever a logo file is included. | `"Green Mountain Club"` |

## `[verification]`: what was checked

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `verified` | boolean | `true` when geometry was downloaded and measured. | `true` |
| `date` | string (date), where verified | Date of the check. | `"2026-11-08"` |
| `measured_km` | number, where verified | Measured (geodesic) length in kilometres. | `400.9` |
| `difference_percent` | number, where verified | Measured length minus published length, as a percent of published length. | `-8.5` |
| `parts` | integer, where verified | Pieces left after joining line ends within 100 m. | `1` |
| `note` | string | What was found, including failures and gaps. | `"389.5 km in 12 parts against 480 km planned."` |

## Files beside the record

| File | Meaning |
| --- | --- |
| `line.geojson` | The main line (FeatureCollection, longitude/latitude). Present only when `source.line_file` names it. |
| `alternates.geojson` | Alternate or connector lines the source serves separately, where present. |
| `line-<source>.geojson` | One source's own extract, where the main line combines sources (for example `line-usfs.geojson`). |
| `release.txt` | Source, licence and date the line files came from. Present when a line is included. |
| `shield.svg`, `shield.png` | The trail's logo. Present only when `shield.logo_file` names it. See NOTICE.md. |
