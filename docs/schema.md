# Record schema

Each trail has one record: `<id>/trail.toml`. The file is TOML. Field names are stable: tools read them, so fields are added, not renamed. Optional fields are marked "where present".

Example (shortened):

```toml
id = "long-trail"
name = "Long Trail (Vermont)"
short_name = "LT"
short_name_url = "https://www.greenmountainclub.org/"
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
| `short_name` | string, where present | Abbreviation the trail's holder or author uses for it, or, failing that, one in established use among hikers. Never made up: a trail nobody abbreviates has none. Written without full stops (`"AT"`, not `"A.T."`); hyphens and digits stay as the holder writes them. Two trails may truthfully share one, and both show it. | `"LT"` |
| `short_name_url` | string, with `short_name` | The page where the abbreviation was seen in use. Required when `short_name` is present; an error without it. An http(s) address. | `"https://www.greenmountainclub.org/"` |
| `country` | string | `US` or `CA`. | `"US"` |
| `regions` | array of strings | State, province or territory codes crossed. | `["VT"]` |
| `length_km` | integer | Published length in kilometres. A check value, not measured from the track. | `438` |
| `length_note` | string | Where the published length comes from. | `"272 mi published"` |
| `kind` | string, where present | `"route"` for a route: one that a hiker or a small group worked out and published. Absent means a designated trail: one that a land agency or a trail association designates. | `"route"` |
| `tier` | string | `national` (US National Scenic Trail), `regional` (80 km or more), `short` (well-known, 60-80 km), `deferred`, or `candidate`. The tiers apply to routes as well. | `"regional"` |
| `designation` | string | What makes it a long trail: statute, agency or association, or for a route the person and year it was published. | `"National Scenic Trail (1968)"` |
| `wave` | integer or string | `1` for trails in the first set; `"held"` where listing is undecided. | `1` |
| `wave_note` | string, where present | Why a held trail is held. | `"Held: no usable whole track exists."` |
| `inclusion` | string, where present | `nst-unconditional` for every National Scenic Trail; `candidate-decision-pending` for a candidate. Absent otherwise. | `"nst-unconditional"` |

## `[source]`: where the track comes from

The field and file names keep the word "line" (`line.geojson`, `line_file`, `line_policy`, `line_source`); they refer to the trail's track.

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `status` | string | `verified` (downloaded and measured), `found` (source located, not downloaded), `osm-only` (only an OpenStreetMap relation), or `none`. | `"osm-only"` |
| `publisher` | string | Who publishes the track. | `"Green Mountain Club"` |
| `publisher_url` | string, where present | The publisher's own page for the trail, kept when the included track comes from another source. | `"https://www.greenmountainclub.org/"` |
| `url` | string | Where to ask for the track: a layer or relation page, never a dated file name. | `"https://www.openstreetmap.org/relation/391736"` |
| `discovery` | string | How to tell whether the source has a newer release. | `"osm-relation-version: ..."` |
| `format` | string | What the source serves and how it is paged. | `"OpenStreetMap route relation"` |
| `crs` | string | Coordinate system the source stores. Published files are longitude/latitude (EPSG:4326). | `"EPSG:4326"` |
| `licence` | string | Licence id, from: `us-gov-public-domain`, `CC-BY-4.0`, `CC-BY`, `ODbL-1.0`, `stated-permission`, `CC-BY-NC-ND-4.0`, `none-stated`, `restricted`, `unknown`. | `"ODbL-1.0"` |
| `licence_text` | string | What the source actually says, with the page it was read on. Not legal advice. For `stated-permission` it says in a sentence or two what was asked and where the statement was read; the words, the speaker, the date and the address go in the four `permission_*` fields. | `"OpenStreetMap contributors, ODbL 1.0 ..."` |
| `permission_quote` | string, `stated-permission` only | The holder's words, exactly as written, with no licence named. Required for `stated-permission` and refused for any other licence. The trail page shows it as a quotation. | `"It's completely public and free to share."` |
| `permission_by` | string, `stated-permission` only | Who said it, by role, as it should read after "Said by". | `"the association's president"` |
| `permission_date` | string, `stated-permission` only | The day it was said, `YYYY-MM-DD`. | `"2026-11-16"` |
| `permission_url` | string, `stated-permission` only | An `http(s)` address of the page, issue or message thread where it was said. The trail page links to it. | `"https://github.com/swaits/longhikes/issues/2"` |
| `attribution` | string | The credit line to show, as the source asks. | `"OpenStreetMap contributors (ODbL)"` |
| `osm_only` | boolean | `true` when OpenStreetMap is the only source of the included track. | `true` |
| `mainline` | string | How the main track is told apart from alternates, connectors and side trails in this source. | `"One relation tagged complete."` |
| `decision` | string, where present | A settled inclusion question, stated neutrally. | `"included-named"` |
| `decision_text` | string, where present | What the decision settles, in one sentence. | `"Included with its name and logo."` |
| `source_checked` | string (date) | Date the source was last read, `YYYY-MM-DD`. | `"2026-11-08"` |
| `redistributable` | boolean | `true` when the source's terms allow its track to be passed on. Must be `true` for every included data file. | `true` |
| `line_source` | string | Short name of the included track's source, or `none (no line included)`. | `"OpenStreetMap"` |
| `line_file` | string | Included main track file, usually `"line.geojson"`, or `""` when no track is included. | `"line.geojson"` |
| `line_absent_reason` | string, where no line | Why no track is included. | `"Publisher's GIS data is not licensed for redistribution ..."` |
| `length_gap_note` | string, where present | Why the measured track differs from `length_km` by more than 15% (partly unbuilt, planned length, side trails counted, and so on). Required in that case. | `"The trail is not finished: built passages are what is mapped."` |

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
| `parts` | integer, where verified | Pieces left after joining track ends within 100 m. | `1` |
| `note` | string | What was found, including failures and gaps. | `"389.5 km in 12 parts against 480 km planned."` |

## `[hike]`: what a hiker asks first

Optional: a record without `[hike]` is valid. The table holds the facts a hiker wants before anything else: where the trail goes, what the country is like, how long it takes, when to go, where its own site is. Every fact is read on a page, and that page is named in `[[hike.source]]`. The first choice is a page of the trail's holder (the agency, the association, or for a route its author) or a government page. Where those say nothing, a fact may be read on an established hiking reference that covers the trail, such as a guide site, a hiking association's list of trails or a guidebook publisher's page; the source entry names that site as the publisher, so a reader can see where the fact came from and weigh it. Apps and pages that anyone can edit (AllTrails, forums, social media, wikis) are not sources. A fact found on no acceptable page is left out, never guessed. Where sources disagree, the managing body's figure is used. Wording is ours: nothing is copied from a source.

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `summary` | string | Two or three plain sentences: where the trail goes, what the country is like, what sets it apart. No sales language and no superlative that a source does not support. The first sentence stands alone, because the site uses it as a one-line description. | `"The Long Trail runs the length of Vermont along the Green Mountains, from the Massachusetts border to the Canadian border."` |
| `official_url` | string | The trail's own page from whoever manages or publishes it (agency, association, or the route's author). | `"https://www.greenmountainclub.org/the-long-trail/"` |
| `start`, `end` | string | The two ends as place names a hiker would recognise, in the usual direction of travel where there is one. For a loop, `start` is the usual trailhead and `end` is left out. | `"Springer Mountain, Georgia"` |
| `start_lonlat`, `end_lonlat` | array of two numbers, where present | The position of the place named in `start` (or `end`), as a gazetteer or the trail's holder gives it: longitude and latitude in decimal degrees, WGS84, longitude first, rounded to three decimals (about 100 m). It is the place, not a surveyed trailhead, and it is there so that a trail with no track can still be put on a map. A loop has `start_lonlat` only. The place name in `start` (or `end`) may be left out when the record has a track and the numbers are the ends of that track, with the track named as the source. The source of the numbers must allow republication and is named in `[[hike.source]]`, like every other fact. Where both are given, the straight distance between the two points cannot be longer than `length_km`, because a trail cannot be shorter than the distance between its ends; the validator checks this with a 2 per cent tolerance. | `[-83.927, 34.627]` |
| `shape` | string | `"point-to-point"`, `"loop"` or `"network"`. | `"point-to-point"` |
| `days` | array of two integers | The usual time to walk the whole trail in one go, `[fewest, most]`, in days, as a source states it. Weeks count 7 days, months 30. | `[150, 210]` |
| `season` | string | The months in which the whole trail is usually walked, as a short phrase. Not the dates a park or hut is open, unless those set the walking season. | `"July to September"` |
| `months` | array of integers | The same season as month numbers, 1 to 12, for filtering: every month in which the whole trail, or a usual start, is normally walked. A month counts when about half of it or more is in season. Given whenever `season` is. | `[7, 8, 9]` |
| `high_point` | string | Name of the highest point on the trail. | `"Mount Mansfield"` |
| `high_point_m` | integer | The elevation of the highest point in metres, rounded to the nearest metre (converted from feet where the source gives feet). May be given without `high_point` where a source states the elevation but not a name. | `1340` |
| `terrain` | array of strings | One to three of `alpine`, `forest`, `desert`, `coast`, `prairie`, `canyon`, `tundra`, `lakes`, `farmland`: the main kinds of country only. | `["forest"]` |
| `travel` | string | What the walking is, as the sources describe it. `"trail"`: on built or maintained trail for all or nearly all of the way. `"trail-and-road"`: trail with long stretches on roads. `"some-cross-country"`: mostly trail or road, with stretches that have no trail. `"mostly-cross-country"`: no trail for most of the way. | `"trail"` |
| `permit` | string | One plain sentence on whether a permit or reservation is needed to walk the whole trail, and from whom. Left out when no source says. | `"Individual hikers need no permit."` |
| `unfinished` | string | Only where the trail is not complete on the ground: one sentence saying how much exists, as a source states it. | `"About 400 of the planned 700 miles are built."` |
| `caution` | string | Only where a source says so: a few plain sentences a hiker should know before choosing the trail that no other field holds, such as long sections that are unofficial, unmaintained or on roads. Not current conditions or closures, which change. A loss of access that a publisher has reported in writing may go here, worded as that publisher's report and naming its page in `[[hike.source]]`. | `"About a third of the route is unofficial and not maintained."` |
| `checked` | string (date) | Required when `[hike]` is present. The date the facts were read, `YYYY-MM-DD`. | `"2026-11-13"` |

## `[[hike.source]]`: where the `[hike]` facts were read

An array of tables, and at least one when `[hike]` is present. Every fact field in `[hike]` (every field except `checked`) must be named in the `facts` of at least one source. `summary` and `terrain` are our own wording and judgement, but each still names the page or pages it was drawn from.

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `url` | string | The page a fact was read on. | `"https://www.greenmountainclub.org/the-long-trail/"` |
| `publisher` | string | Who publishes that page. | `"Green Mountain Club"` |
| `facts` | array of strings | The `[hike]` field names this page supports. `"high_point"` covers both `high_point` and `high_point_m`. | `["start", "end", "high_point"]` |

## `[route]`: the author and the track policy

Present only when `kind = "route"`. A route is a high route, a traverse or a loop of linked trails that a hiker or a small group worked out and published.

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `creator` | string | The route's author: the person, people or group who worked the route out. | `"Steve Roper"` |
| `year` | integer, where known | The year the route was first published or first walked, as the source states it. Absent when no page read states one. | `1970` |
| `line_policy` | string | `open` (the author publishes the track freely), `sold` (the route is got by buying a guide or map set), `withheld` (the author chooses not to publish a track), or `unclear` (not settled). | `"sold"` |
| `creator_words` | string, where found | The author's own words on sharing the track, quoted exactly. | `"There is no route, so you must create one on your own."` |
| `creator_words_url` | string, where `creator_words` is present | The page the words were read on. | `"https://andrewskurka.com/adventures/great-western-loop/route-description/"` |
| `creator_words_by` | string, where the words are another person's | Whose words `creator_words` quotes, when they are not the author's. | `"Andrew Skurka"` |
| `note` | string, where present | Anything else about the route's tracks: when it was first walked, what it links, what is still missing. | `"The guidebook's maps are the track."` |

## `[[guide]]`: where the route is got from

An array of tables, one per guide, and at least one for every route. A guide is the book, map set or page that gives the route.

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `title` | string | The guide's title or the page's name. | `"Sierra High Route, 2nd Edition"` |
| `author` | string | Who wrote or published it. | `"Steve Roper"` |
| `access` | string | `"free"` or `"purchase"`. | `"purchase"` |
| `url` | string | The author's or publisher's own page for the guide. | `"https://www.mountaineers.org/books/books/sierra-high-route-2nd-edition-traversing-timberline-country"` |
| `format` | string | What the guide is: book, map set, web page, GPX file, and so on. | `"book"` |
| `price` | string, where known | The price exactly as the page states it, with the date read in `price_checked`. | `"$24.95"` |
| `price_checked` | string (date), where `price` is present | Date the price was read, `YYYY-MM-DD`. | `"2026-11-10"` |
| `publisher` | string, where known | The publisher, where it is not the author. | `"Mountaineers Books"` |
| `isbn` | string, where known | The book's ISBN. | `"978-0-89886-506-6"` |

## `[[link]]`: other pages about the trail

Optional: an array of tables, one per page. A link is a page about this one trail from someone other than its manager: a wiki article, an encyclopedia article, a second organisation that shares the trail. The trail's page shows them under "More about this trail". It is not for a site's home page, a shop or an app listing.

The trail's own page belongs in `hike.official_url`, not here, and the publisher's page in `source.publisher_url`; a link that repeats either is an error. A link is not a source: a fact still needs its `[[hike.source]]`.

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `title` | string | The page's own title, or the trail's name as that site gives it. Plain text. | `"Appalachian Trail"` |
| `publisher` | string | Who publishes the page. | `"LongTrailsWiki"` |
| `url` | string | The page's address, `http` or `https`. No two links in a record share one. | `"https://www.longtrailswiki.net/wiki/Appalachian_Trail"` |
| `note` | string, where needed | One short plain sentence on what the page offers, where that is not obvious. | `"Trip reports and resupply notes."` |

## Files beside the record

| File | Meaning |
| --- | --- |
| `line.geojson` | The main track (FeatureCollection, longitude/latitude). Present only when `source.line_file` names it. |
| `alternates.geojson` | Alternate or connector tracks the source serves separately, where present. |
| `line-<source>.geojson` | One source's own extract, where the main track combines sources (for example `line-usfs.geojson`). |
| `release.txt` | Source, licence and date the track files came from. Present when a track is included. |
| `shield.svg`, `shield.png` | The trail's logo. Present only when `shield.logo_file` names it. See NOTICE.md. |
| `elevation.json` | The trail's elevation facts and profile, computed from `line.geojson` and a public elevation model. Present for every trail with a track. See below. |

## `elevation.json`: elevation facts and profile

Computed by `python3 tools/elevation.py` from the trail's track (`line.geojson`) and the Terrain Tiles open elevation data. It is not read from any trail page. The file is one line of compact JSON. The same track gives the same file.

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `highest`, `lowest` | object | `m` (whole metres), `lon` and `lat` (5 decimals) of the highest and the lowest sample on the track. | `{"lat":36.57843,"lon":-118.29247,"m":4009}` |
| `ascent_m`, `descent_m` | integer | Total climbing and total descending along the track, in metres, by the method below. For a trail that is not a loop, they are for the direction in `orientation`. Walking the other way swaps them. | `124343` |
| `track_km` | number | Length sampled, in kilometres. It is the length of the track, not the published length. | `4269.9` |
| `published_km` | integer | The record's `length_km`. | `4265` |
| `coverage` | number | `track_km` divided by `published_km`. Below about 0.85 the track is partial, and every figure here describes the track, not the whole trail. Above 1 the track is longer than the published length. | `1.001` |
| `parts` | integer | Number of separate parts the track falls into once pieces whose ends are within 100 m are joined. It is the number the site's own joining gives, and can be larger than `verification.parts`, which was counted with another joining rule. | `1` |
| `part_starts_km` | array of numbers, where `parts` is more than 1 | The profile distance at which each part after the first begins. | `[102.4, 250.1]` |
| `orientation` | string | `"south-to-north"` or `"west-to-east"`: the direction the track is walked for `ascent_m`, `descent_m` and the profile. A part that is a loop keeps the direction it has. | `"south-to-north"` |
| `profile` | array | Pairs `[distance_km, elevation_m]`, at most 700, thinned so that a drawn line follows the full profile. The distance is along the sampled track. The first point of a part repeats the distance of the last point of the part before it, so a chart must not draw a line between them (use `part_starts_km`). The highest and lowest points are always in the profile. | `[[0,1222],[0.03,1225]]` |
| `source` | object | What the numbers come from and how: `model`, `url`, `attribution` (the credit to show), `zoom`, `ground_m_per_pixel_at_40n`, `sample_spacing_m`, `smoothing`, `limits`, `method_version`, `computed` (the date). | `{"zoom":12,...}` |

### Method

1. Pieces of the track whose ends are within 100 m are joined into parts. Parts are never joined to each other. No climb is counted across a gap.
2. Each part is walked from its start and a point is taken every 30 m along it, and at its end.
3. The elevation at each point is read from the elevation tiles by interpolating between the four nearest grid cells. The tiles used are Terrain Tiles "terrarium" tiles at zoom 12, about 29 m per cell at 40 degrees north. Cells that are far out of line with their neighbours are tile-making errors and are replaced, and values below sea level are set to 0.
4. `highest` and `lowest` are the largest and smallest of these values.
5. For `ascent_m` and `descent_m` the profile is first smoothed with a moving average over 90 m (three points). Then a climb or a descent counts only after the profile has moved more than 5 m against the last high or low point. Without that, noise in the model adds a great deal of climbing that is not there.
6. The smoothing and the 5 m threshold were chosen once, to match published figures for ten well-known trails, and then left fixed for every trail. They are in `tools/elevation.py`.

### Limits

- These are computed values, not measurements. Where a published figure exists, it may differ. For ten well-known trails the computed climbing is within about 15% of the published figure, and the published figures themselves differ by about as much from one source to another.
- The elevation model is a grid. A narrow summit can be missed by up to 15 m of position and so read a little low. Highest and lowest are the model's values at the samples, not surveyed benchmarks. Values below sea level are set to 0, because beside a coast the model carries the depth of the sea and none of these trails goes below sea level.
- The model's own accuracy varies. In the United States it is built from 10 m surveys; in Canada it is coarser (20 m to 400 m, depending on the place), so a Canadian trail's ascent is likely to be low.
- Ascent and descent depend on the method's settings. They are comparable between trails in this dataset, which all use the same settings. They are not the figure a GPS watch or another site would show.
- The profile follows the track as it is stored. Where the track is partial, joined in the wrong order, or includes side trails or alternates, the facts follow it. Check `coverage` and `parts` first.
- The direction is a convention, chosen to make the output repeatable. It is not the trail's usual direction.
