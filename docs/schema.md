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
| `common_name` | string, where present | The name hikers use, where it differs from `name`: `"Appalachian Trail"` for `"Appalachian National Scenic Trail"`. Only where the trail's holder or author (or the agency that manages it) uses that name on a page; the page goes in the `basis_url` of the `[[history]]` entry that adds it. Never made up, and never the same as `name`. The site puts it in the page title, the heading and the search; `name` stays on the page. | `"Appalachian Trail"` |
| `short_name` | string, where present | Abbreviation the trail's holder or author uses for it, or, failing that, one in established use among hikers. Never made up: a trail nobody abbreviates has none. Written without full stops (`"AT"`, not `"A.T."`); hyphens and digits stay as the holder writes them. Two trails may truthfully share one, and both show it. | `"LT"` |
| `short_name_url` | string, with `short_name` | The page where the abbreviation was seen in use. Required when `short_name` is present; an error without it. An http(s) address. | `"https://www.greenmountainclub.org/"` |
| `country` | string | `US` or `CA`; for reason `outside-us-canada`, the trail's own two letter country code. | `"US"` |
| `regions` | array of strings | State, province or territory codes crossed. | `["VT"]` |
| `length_km` | integer | The end-to-end length of the trail's canonical path, in kilometres, as the trail's holder or author states it. A check value, not measured from the track. See "What `length_km` counts" below. | `438` |
| `length_note` | string | Where the length was read, and any disagreement between pages. | `"272 mi published"` |
| `system_km` | integer, where present | The larger figure the holder publishes for the whole trail system or the planned total, in kilometres. It must be greater than `length_km`, and `system_note` must say what it counts. Shown beside the length with its note; never used for lists, bands, filters or time estimates. See below. | `2549` |
| `system_note` | string, with `system_km` | What the larger figure counts, as a phrase that follows the word "counting" ("counting both corridors and connectors"). Required when `system_km` is present and refused without it. The site shows it as "Whole system: 1,584 mi, counting ...". | `"all designated trail, official side trail and connecting roadwalks"` |
| `built_km` | integer, where present | Only on an unfinished trail (one whose `hike.unfinished` is present): the length already built, in kilometres, as the holder states it. It cannot exceed `length_km`. The site shows it beneath the length ("290 mi built"). | `467` |
| `kind` | string, where present | `"route"` for a route: one that a hiker or a small group worked out and published. Absent means a designated trail: one that a land agency or a trail association designates. | `"route"` |
| `tier` | string | `national` (US National Scenic Trail), `regional` (80 km or more), `short` (under 50 miles, listed for a stated reason; 60-80 km), `deferred`, or `candidate`. The tiers apply to routes as well. | `"regional"` |
| `designation` | string | What makes it a long trail: statute, agency or association, or for a route the person and year it was published. | `"National Scenic Trail (1968)"` |
| `wave` | integer or string | `1` for trails in the first set; `"held"` where listing is undecided. | `1` |
| `wave_note` | string, where present | Why a held trail is held. | `"Held: no usable whole track exists."` |
| `inclusion` | string, where present | `nst-unconditional` for every National Scenic Trail that is listed; `candidate-decision-pending` for a candidate. Absent otherwise. | `"nst-unconditional"` |
| `short_reason` | string, with `length_km` under 80 | One plain sentence saying why a trail under the 50 mile (80 km) floor is listed, by the owner's test: it has real cross-country travel, it genuinely takes a fit, experienced party five or more days because the ground is hard (the days a managing body, an author or a guidebook prints do not decide this), or it is very well known and popular. It rests on what the record already says. Required on every record with `length_km` under 80, and refused on any other. A trail whose record can give none of the three reasons is not listed. | `"BC Parks says most of the route is marked by cairns, that hikers find the way from cairn to cairn, and that creek crossings can be difficult in high water."` |
| `places_checked` | string (date) | The day the record's `[[place]]` tables were last measured against the published outlines, or reviewed by hand where the trail has no track. Present once the record's places have been settled, including when the answer is no park, range or wilderness at all. Not a fact: changing it alone needs no `[[history]]` entry. | `"2026-11-20"` |
| `places_track` | string | The first 16 hex digits of the SHA-256 of the record's `line.geojson` bytes, as they were when the places were measured. Present on every record with a track once its places are settled, and refused on a record with no track. The validator fails a record whose track has changed since, so a new track cannot ship unmeasured. Not a fact. | `"0123456789abcdef"` |

### What `length_km` counts

`length_km` is the end-to-end length of the trail's canonical path: the way one person walks the trail from one end to the other. One branch is taken at a split, side trails are left out, and a system total is never used. The length is the holder's or the author's own figure for that path, and the floor is tested on the length with no stretch counted twice, so an out-and-back is judged one way. A loop reached by a stem is shown at the published figure, which walks the stem both ways, and `length_note` says which stretch is walked out and back, without stating any shorter length; where only a system total is published, the record does not use it as the length (see below).

A trail must also be walkable from one end to the other today. A trail that cannot be, because it is published in separate pieces or has gaps with no way across, is not listed and goes in `left-out.toml`. Road links that the holder publishes as the way through count as walkable, and so does evidence that people have walked it end to end. A ferry, shuttle or bus link across water or a closed stretch, named by the holder or the route's author as the way through, does not rule a trail out: the record says how each such link is made, and the track has a gap there, with no line drawn across. This is a judgement the maintainer makes case by case, not a mechanical test. Every trail or route needs a published length, and a route with no stated length is not listed. The length rule is at least 50 miles (80 km). A trail or route under 50 miles (80 km) is listed only when it is still reasonably long and at least one of these is true: it has real cross-country travel; it genuinely takes a fit, experienced party five or more days because the ground is hard: there is no trail, or the going is rough, unmaintained or needs route finding, with fords or thick brush (the number of days a managing body, an author or a guidebook prints does not decide this, and an itinerary that spreads a walk on ordinary built trail over five or more days at an easy pace does not count); or it is very well known and popular, as the Rae Lakes Loop is. Each such record gives its reason in `short_reason`. Being close to 50 miles is never a reason. The days never replace a published length. A trail with its own name and its own published length is listed even where it lies on a longer listed trail, as the John Muir Trail lies on the Pacific Crest Trail. A guidebook's cut of a longer trail is not listed. The climbing rule is that nothing harder than Class 3 may be required, apart from a few short Class 4 scrambles. A route that needs a rope, a belay or rock-climbing skill is not listed, unless that section is optional and the record says so. A trail that can be walked through but is partly unbuilt stays: its `length_km` is the holder's end-to-end route, `built_km` states the built part, and `hike.unfinished` says how the gaps are crossed.

A larger figure that the holder publishes (a system total, or a planned total) is kept as its own labelled fact in `system_km` and `system_note`. A planned total is the same thing: it is `system_km`, and the note says it is planned. There is no separate field for it.

Worked examples:

- The Florida Trail. The holder's figure of about 1,500 miles counts both branches at two splits, plus connectors. One walk from end to end, the Eastern Corridor by the east side of Lake Okeechobee, is 1,130 miles (1,818 km), so `length_km = 1818`. The holder's larger figure goes in `system_km = 2549`, with `system_note = "all designated trail, official side trail and connecting roadwalks"`.
- An unfinished trail. The Ozark Highlands Trail route is about 325 miles (523 km) from end to end, of which about 290 miles (467 km) are built. `length_km = 523`, `built_km = 467`, and `hike.unfinished` says what is unbuilt and how a hiker crosses it.

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
| `status` | string | `use-real-logo`: a logo file is included (`logo_file` names it). `no-logo-exists`: the trail has no emblem of its own, and the note says which pages were checked. `logo-not-found`: an emblem exists or may exist, but no usable artwork of it was found at an allowed source, and the note says where it was looked for or seen. The validator rejects any other value, a `use-real-logo` record with no file, and a file with either of the other two. | `"use-real-logo"` |
| `logo_source` | string | Where the logo art was taken from, when known. | `"https://www.greenmountainclub.org/"` |
| `contact` | string | Who holds the emblem or mark. | `"Green Mountain Club"` |
| `note` | string | What is known about the logo and its terms. Required when no file is included: it says where an emblem was looked for. | `"No logo or shield policy found."` |
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

Optional: a record without `[hike]` is valid. The table holds the facts a hiker wants before anything else: where the trail goes, what the country is like, how long it takes, when to go, where its own site is. Every fact is read on a page, and that page is named in `[[hike.source]]`. The first choice is a page of the trail's holder (the agency, the association, or for a route its author) or a government page. Where those say nothing, a fact may be read on an established hiking reference that covers the trail, such as a guide site, a hiking association's list of trails or a guidebook publisher's page; the source entry names that site as the publisher, so a reader can see where the fact came from and weigh it. Apps and pages that anyone can edit (AllTrails, forums, social media, wikis) are not sources. A fact found on no acceptable page is left out, never guessed, except season, which may be estimated and must then say so. Typical time is estimated at page-build time and never stored, while an estimated season is stored on the record. Where sources disagree, the managing body's figure is used; where none of them manages the trail, is its association or is its route author, the season is set by judgement from all the pages and the climate estimate, and `season_method` says so. Wording is ours: nothing is copied from a source.

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `summary` | string | Two or three plain sentences: where the trail goes, what the country is like, what sets it apart. No sales language and no superlative that a source does not support. The first sentence stands alone, because the site uses it as a one-line description. | `"The Long Trail runs the length of Vermont along the Green Mountains, from the Massachusetts border to the Canadian border."` |
| `official_url` | string | The trail's own page from whoever manages or publishes it (agency, association, or the route's author). | `"https://www.greenmountainclub.org/the-long-trail/"` |
| `start`, `end` | string | The two ends as place names a hiker would recognise, in the usual direction of travel where there is one. For a loop, `start` is the usual trailhead and `end` is left out. | `"Springer Mountain, Georgia"` |
| `start_lonlat`, `end_lonlat` | array of two numbers, where present | The position of the place named in `start` (or `end`), as a gazetteer or the trail's holder gives it: longitude and latitude in decimal degrees, WGS84, longitude first, rounded to three decimals (about 100 m). It is the place, not a surveyed trailhead, and it is there so that a trail with no track can still be put on a map. A loop has `start_lonlat` only. The place name in `start` (or `end`) may be left out when the record has a track and the numbers are the ends of that track, with the track named as the source. The source of the numbers must allow republication and is named in `[[hike.source]]`, like every other fact. Where both are given, the straight distance between the two points cannot be longer than `length_km`, because a trail cannot be shorter than the distance between its ends; the validator checks this with a 2 per cent tolerance. | `[-83.927, 34.627]` |
| `shape` | string | `"point-to-point"`, `"loop"` or `"network"`. | `"point-to-point"` |
| `days` | array of two integers | The usual time to walk the whole trail in one go, `[fewest, most]`, in days, as a source states it. Weeks count 7 days, months 30. | `[150, 210]` |
| `season` | string | The months in which the whole trail is usually walked, as a short phrase. Not the dates a park or hut is open, unless those set the walking season. `season` and `months` come together: one is never given without the other. For an estimated season (`season_basis = "estimate"`) the phrase is built from the months. | `"July to September"` |
| `months` | array of integers | The same season as month numbers, 1 to 12, for filtering: every month in which the whole trail, or a usual start, is normally walked. A month counts when about half of it or more is in season. Given whenever `season` is, and never without it. | `[7, 8, 9]` |
| `season_basis` | string | Required whenever `season` is present, and refused without it. Where the season came from, one of: `primary` (the page is published by the body that manages the trail, the trail's own association, or, for a route worked out by a hiker, that route's author); `sources` (no primary page, but two or more pages from different publishers agree on the season); `source` (one page that is not a primary one); `estimate` (no page states a season, so it is worked out from climate). A route author's stated season counts as `primary`. An `estimate` has no page that states a season: its one `[[hike.source]]` names both `season` and `months` and cites the climate data (CHELSA, with ETOPO), and any ordinary page naming the season makes the basis wrong. An estimate is worked out by a reviewer from the trail's location, elevation, monthly climate normals, a machine estimate and the most similar sourced trails (`tools/season_judge.py`); the method was tested blind against the seasons that pages state, and the result is in `tools/season_blind_test.json`. | `"primary"` |
| `season_method` | string | Required with `season_basis = "estimate"`, where it is one or two plain sentences saying how the season was set and what sets it there, ending "Confidence: high.", "Confidence: medium." or "Confidence: low.". Allowed with `sources`, where it says how the season was settled when the pages differ and must also end with a confidence; `sources` with a method needs pages from at least two different publishers naming the season (a page that contradicts itself, or two pages from one publisher, is an `estimate`); a season with a method was set by judgement and is shown as an estimate, not as a page's statement. Refused with `primary` and `source`. | `"Snow keeps the high passes closed until late June and returns in October. Confidence: high."` |
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

An array of tables, one per guide, and at least one for every route. A guide is the book, map set or page that gives the route. A guide that is bought must say exactly what it is: at least one of `isbn`, `edition` or `link_is`. Where the publisher now sells a newer edition than the one the record was read from, `url` is a library record of the edition read (`link_is = "library"`), and a second guide entry names the newer edition at the publisher's page, with a `where` that says the trip may be numbered differently. Any other trail may have one too: its holder's own guide or map set, shown as "Maps and guides".

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `title` | string | The guide's title or the page's name. | `"Sierra High Route, 2nd Edition"` |
| `author` | string | Who wrote or published it. | `"Steve Roper"` |
| `access` | string | `"free"` or `"purchase"`. | `"purchase"` |
| `url` | string | The author's or publisher's own page for the guide. | `"https://www.mountaineers.org/books/books/sierra-high-route-2nd-edition-traversing-timberline-country"` |
| `format` | string | What the guide is as a thing: book, map set, web page, GPX file, and so on. The edition and the place in it go in `edition` and `where`. | `"book"` |
| `price` | string, where known | The price exactly as the page states it, with the date read in `price_checked`. | `"$24.95"` |
| `price_checked` | string (date), where `price` is present | Date the price was read, `YYYY-MM-DD`. | `"2026-11-10"` |
| `publisher` | string, where known | The publisher, where it is not the author. | `"Mountaineers Books"` |
| `isbn` | string, where known | The book's ISBN. | `"978-0-89886-506-6"` |
| `edition` | string, where known | The edition and year the record's facts were read from; for a guide that is not a book, its version or year where the author states one. | `"9th edition, 2021"` |
| `where` | string, where the record says | Where in the guide this route is, in a few words. Left out when no source says. | `"Trip 25, page 149"` |
| `link_is` | string, where known | What `url` points at: `publisher` (the publisher's page for this exact title), `author` (the author's own page or shop page for this exact guide), `library` (a library catalogue record, for a title that is out of print or has no publisher's page for this edition), or `seller` (a bookseller, only where the author sells only there). | `"publisher"` |

## `[[link]]`: other pages about the trail

Optional: an array of tables, one per page. A link is a page about this one trail from someone other than its manager: a wiki article, an encyclopedia article, a second organisation that shares the trail. The trail's page shows them under "More about this trail". It is not for a site's home page, a shop or an app listing.

The trail's own page belongs in `hike.official_url`, not here, and the publisher's page in `source.publisher_url`; a link that repeats either is an error. A link is not a source: a fact still needs its `[[hike.source]]`.

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `title` | string | The page's own title, or the trail's name as that site gives it. Plain text. | `"Appalachian Trail"` |
| `publisher` | string | Who publishes the page. | `"LongTrailsWiki"` |
| `url` | string | The page's address, `http` or `https`. No two links in a record share one. | `"https://www.longtrailswiki.net/wiki/Appalachian_Trail"` |
| `note` | string, where needed | One short plain sentence on what the page offers, where that is not obvious. | `"Trip reports and resupply notes."` |

## `[[place]]`: the parks, ranges and wilderness areas the trail is in

Optional: an array of tables, one per place, written by `tools/place_trails.py` or, for a trail with no track, entered by hand from a cited source. Every entry names a place in `places.toml` by `kind` and `slug` together (slugs are unique within a kind, not across kinds). A trail is in a place when at least 1 mile (1.6 km) of its main track lies inside the published outline; alternates do not count. A record never names a parent place from `within`: the site works out parent membership itself. Adding or removing a `[[place]]` entry is a fact change and needs a `[[history]]` entry naming `place`; the measured `km` is not a fact, and it is never shown anywhere, including in history text.

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `kind` | string | `park`, `range` or `wilderness`. | `"range"` |
| `slug` | string | The place's slug in `places.toml`, within its kind. | `"wind-river-range"` |
| `basis` | string | `track`: measured from the track against the outline; only on a record with a track. `stated`: the trail has no track and a cited source puts it in the place. A trail later given a track must be re-measured, which the `places_track` check forces. | `"track"` |
| `km` | number, with `basis` `track` | The measured length of the main track inside the outline, in kilometres. Recorded so the 1 mile threshold can be audited; never shown anywhere. Required with `track` and refused with `stated`. Not a fact. | `142.3` |
| `source` | string, with `basis` `stated` | The address of the page that puts this trail in this place. Required with `stated` and refused with `track`. | `"https://example.org/trail"` |

## `[[history]]`: who asked for what, and on what evidence

Required: every record has at least one entry. An array of tables, oldest first, added to and never rewritten. Git keeps the diffs. The history keeps what git does not: the reason for each change, who asked for it, and the requests that were turned down, so that a later request that conflicts with an earlier one is easy to notice and settle.

The first entry is the one that adds the record, with `fields = ["record"]`. Every later entry names the fields it concerns.

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `date` | string (date) | The day the change was made, or the request was answered, `YYYY-MM-DD`. Not before the entry above it. | `"2026-11-16"` |
| `change` | string | One or two plain sentences: what changed, or what was asked for and declined. | `"The length was changed from 270 miles (435 km) to about 325 miles (523 km) planned."` |
| `fields` | array of strings | The record fields it concerns, named as this page names them (`length_km`, `source.licence`, `hike.caution`). A table name (`source`, `guide`, `hike.source`) names every field in it. `["record"]` for the entry that adds the record, and for no other. | `["length_km", "length_note"]` |
| `basis` | string | A sentence saying on what evidence: which page said what. | `"The association's page for the trail gives about 325 miles planned."` |
| `basis_url` | string | The page that was read, or the address of the issue or pull request. An `http(s)` address. Required, except for the entry that adds a record where the record's own `[source]` is the basis. | `"https://ozarkhighlandstrail.com/trail/"` |
| `asked_by` | string | Who asked, by role and never by a private person's name: `"the dataset's own check"`, `"the trail association's president"`, `"a hiker"`, `"the route's author"`. | `"a hiker"` |
| `outcome` | string | `applied` (the record was changed) or `declined` (it was not, and `basis` says why). | `"declined"` |

Settling a conflict:

- The holder's or the author's own current page wins. A fact on such a page is the one the record gives.
- Where two requests conflict, the earlier decision stands unless the later one brings new evidence from such a page.
- The request that loses is recorded as `declined`, with its reason in `basis`, so that it is not argued again.

### The check

`python3 tools/check_history.py` compares your work with the base revision (`origin/main`, then `main`; `--base REV` for another). Run it before you send a change. The workflow runs it for every push and pull request. For every `trail.toml` that differs (and every changed track file) it

- fails when a fact changed and no new entry with the outcome `applied` names the field, and says which record and which fields;
- fails when an entry that was already there was changed or removed;
- prints, for each changed fact, the earlier entries about the same field, and prints `!!` lines where an earlier entry was `declined`, or was asked for by someone other than the dataset's own check. That is where two requests may conflict: read the entry before you change the field again.

**Facts**, which need an entry when they change: `name`, `common_name`, `short_name`, `short_name_url`, `country`, `regions`, `length_km`, `length_note`, `system_km`, `system_note`, `built_km`, `kind`, `tier`, `designation`, `inclusion`; everything in `[source]` except the fields below, which includes the track's source, licence and permission; `osm.relation`; everything in `[shield]` except `note` (the logo); everything in `[hike]` except `summary`, `checked` and the sources (the ends, official page, days, season, months, season_basis, season_method, terrain, travel, high point, permit, unfinished and caution); `[route]` except `note` (the author and the track policy); `[[guide]]` except the price; `[[place]]` except the measured `km`. A replaced track file counts as a change to `source.line_file`.

**Not facts**, which need none: `[[history]]` itself; all of `[verification]`, which the tools refresh; `source.source_checked`, `source.discovery`, `source.format`, `source.crs`, `source.mainline` and `source.length_gap_note`; `hike.summary` (our wording), `hike.checked` and `[[hike.source]]`; `guide.price` and `guide.price_checked`; the notes `osm.note`, `shield.note` and `route.note`; `[[link]]`; `wave` and `wave_note`; `places_checked`, `places_track` and the measured `place.km`, which `tools/place_trails.py` refreshes. A field that is in neither list is a fact. The lists are `FACTS_TEXT` and `NOT_FACTS` in `tools/trail_history.py`, and `python3 tools/check_history.py --facts` prints them.

The site shows the history of each record under "History of this record".

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

## `left-out.toml`: trails considered and left out

One file at the top level, `left-out.toml`, holds the trails and routes that were looked at and left out, a few of which were listed here once and later removed. The site shows it as the "Considered and left out" page, so that a trail is not suggested and argued over again from nothing. An entry is not a judgement on the trail. It says only why the trail does not meet the inclusion rule in README.md.

The file holds one `[[trail]]` table per trail, sorted by `name`. No entry may match a trail in the dataset, by `id` or by `name`: if a left out trail comes to be listed, its entry leaves this file when its record is added. `tools/validate.py` checks the file in `check_left_out_entries` and `check_left_out`.

Example:

```toml
[[trail]]
id = "example-trail"
name = "Example Trail"
country = "US"
regions = ["PA"]
length_mi = 42.0
length_km = 68
reason = "below-floor"
note = "The holder gives it as 42 miles, below the 50 mile floor."
source_url = "https://example.org/example-trail"
decided = "2026-11-14"
was_listed = false
```

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `id` | string | Stable identifier for the entry: lower case words joined by hyphens, as a record `id` is written. A trail that was listed and removed keeps the `id` its record had. | `"fundy-footpath"` |
| `name` | string | The trail's own name. Where another trail in the dataset carries the same name, the name here says which one this is, as record names do. | `"Highline National Recreation Trail (Bear River Range)"` |
| `country` | string | `US` or `CA`. | `"US"` |
| `regions` | array of strings | State, province or territory codes crossed, as the records write them. A trail that spans a whole country uses a plain phrase instead, as the records use `"all provinces and territories"`. | `["MD", "DC", "WV"]` |
| `length_mi` | number, where known | The length its holder or author states, in miles. Left out where no page states one; never guessed. Given with `length_km`, and the two must agree. | `184.5` |
| `length_km` | number, where known | That length in kilometres, converted where the holder stated miles (or the reverse). | `297` |
| `length_note` | string, where needed | The length in words where a pair of numbers would mislead: a planned length, an "over 100 miles", two separate sections, a total for a whole network. Where present it is what the site shows. | `"120 miles planned"` |
| `reason` | string | Why it is left out, from the fixed set in the table below. One reason per entry: where two apply, the one that decided it, with the other said in `note`. | `"below-floor"` |
| `note` | string | One or two plain sentences giving the specific fact that decided it, read on the page in `source_url`. Neutral wording: these are good trails that do not fit this list's rule. | `"Pennsylvania DCNR give this loop as 42.1 miles."` |
| `source_url` | string | The holder's, author's or a government page that shows the deciding fact. Left out only where truly no page exists, and then the `note` says that no page exists. | `"https://www.nps.gov/ovvi/index.htm"` |
| `decided` | string (date) | The day the decision was made, `YYYY-MM-DD`. | `"2026-11-14"` |
| `was_listed` | boolean | `true` where the trail was once in the dataset and was removed. The site marks these in plain words. | `true` |
| `waiting_for` | string, `waiting` only | What would change the decision. Required when `reason` is `waiting` and refused for every other reason. | `"It is designated a National Scenic Trail."` |

The `reason` values mirror the inclusion rule:

| Value | Meaning |
| --- | --- |
| `below-floor` | Shorter than the 50 mile (80 km) floor, and meeting none of the conditions for a shorter trail: no real cross-country travel, no genuine five or more days on hard ground, and not very well known and popular. |
| `rail-trail-or-towpath` | A gravel rail trail or a canal towpath. |
| `driving-route` | Mainly a driving or motor route, as most National Historic Trails are, with at most short walkable pieces. |
| `not-mainly-walking` | Made mainly for bikes, horses or motor vehicles. |
| `network` | A network of trails, not one named trail walked as one walk. |
| `cannot-be-walked-through` | Published in separate pieces, or blocked, so it cannot be walked through as one walk. |
| `mostly-unbuilt` | Mostly unbuilt or still proposed. |
| `requires-climbing` | Requires roped or technical climbing: a route that needs a rope, a belay or rock-climbing skill, beyond a few short Class 4 scrambles, unless that section is optional. |
| `not-published-as-route` | A route its author has not published as a route, with a stated length, for others to follow (a route with no published length is left out under this reason); or a walk no land manager publishes as a named trail with a length. A published route of 50 miles or more that meets the climbing rule is listed even when every documented end-to-end completion is a single-push speed record and no multi-day walk of the whole line is published, without speed records and saying plainly how it has been done. |
| `outside-us-canada` | A trail outside the United States and Canada, which this list does not yet cover. The entry holds what is known about it so the data is ready if the area widens. `country` is then its own two letter code (not `US` or `CA`) and `regions` name its places in plain words. |
| `waiting` | Not left out for good. `waiting_for` says what would change the decision. |

## `glossary.toml`: the words this site uses

One file at the top level, `glossary.toml`, holds the trail terms the site uses, as it uses them. The site shows it as the Glossary page (`/glossary/`) and links each list or page to the terms that apply to it. The file holds one `[[term]]` table per term, in the order the page shows them. `tools/validate.py` checks it in `check_datafiles.py`.

A definition is short, plain and true of how this dataset uses the word. It states no fact about a particular trail, and it uses no dash as punctuation.

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `id` | string | Lower case words joined by hyphens. The anchor of the entry on the page. Unique. | `"high-route"` |
| `term` | string | The word as the page shows it. Unique, ignoring case. | `"High route"` |
| `definition` | string | One to three plain sentences, ending in a full stop. | `"A route through high country that links passes, ridges and basins, and may leave maintained trail to do it."` |
| `source_url` | string, where present | An `http(s)` address of a page that defines or describes the term, where one exists. | `"https://www.aldhawest.org/triple-crown"` |
| `see` | array of strings, where present | Site paths of the lists and pages where the term applies, each starting and ending with `/`. The entry links to each that exists, and each such page links back to the entry. | `["/lists/high-routes/"]` |

## `collections.toml`: named sets of trails

One file at the top level, `collections.toml`, names sets of trails that the site sets side by side on one page, such as the three trails of the Triple Crown. The page is at `/<id>/`. It shows each member's published length, states and provinces, usual time, high point, climb and season in one table, in the order of `members`. It does not rank or recommend.

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `id` | string | Lower case words joined by hyphens. The page's address. Unique. | `"triple-crown"` |
| `name` | string | The set's name as it is used. | `"Triple Crown"` |
| `members` | array of strings | The `id` of two or more records, in the order the definition names them. Each must be a record in the dataset. | `["appalachian", "pacific-crest", "continental-divide"]` |
| `definition` | string | What the set is, in a sentence, as its source states it. | `"The Triple Crown of Hiking is the award ..."` |
| `source_url` | string | An `http(s)` address of the page that states the definition. | `"https://www.aldhawest.org/triple-crown"` |
| `source_publisher` | string | Who publishes that page. | `"American Long Distance Hiking Association, West"` |

### `[[list]]`: which lists the home page shows

The same file also says which of the site's lists the home page offers under "Start from a list". The lists themselves are defined in `web/olt/browse.py` (each is a rule over the records); an entry here only places one on the home page. The row shows the marked lists in the order of `home`, each with its count, and then a link to every list (`/lists/`). A marked list that is not shown today is left out of the row: a list is shown when it holds at least 5 trails and no more than three quarters of all of them (a month's list needs 8).

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `key` | string | The key of a list in `browse.py`, which is the last part of its address under `/lists/` (`routes` for `/routes/`). Each key may appear once. | `"under-100-miles"` |
| `home` | integer | Its place in the home page's row, counting from 1. Unique among the entries. | `5` |

## `authors.toml`: who the route credits name

A route's author is the free text of its `route.creator`. One file at the top level, `authors.toml`, names the people and organisations those credits name, with every exact credit that names each. The site gives every route author a page of their own (`/authors/<name>/`), however many routes they have, and an author with no entry stands alone as written. An entry is needed where a person is credited in more than one form, where one credit names two or more people in full (the credit is listed under each, so the route is on each page and that route's row names who else is credited), where the page should be marked up as a person, and where a person (or a pair of people) is to carry a summary and a biography. A company or an association is left without an entry, or given one of kind `organisation`, and is not marked up as a person.

**The words about an author are for people only.** A summary, a biography, an "About" section and a leading place on `/authors/` are for human authors, never for an association, an agency, a government or any other organisation: their own sites are a link away from each trail's page. An organisation's page lists its routes and nothing more. An entry describes a person, not a route count: a person with no route on the site may have an entry, though the site builds pages only for authors of routes today.

An author's page opens with the name, the `summary` as its one sentence (or, with none, a plain sentence of how many routes and how long), and one line of the route count, their range in miles and the author's own site. The routes follow as rows beside the map; a route credited to others too says so in its own row ("With Ryan Jordan"). After the rows, under "About" and the name, comes the `bio`, with the sources and the date checked in small print.

`/authors/` opens with each person who has at least `PROMINENT_MIN` routes (3, set in `web/olt/authors.py`), with their summary and their routes as rows, most routes first, and lists the others below, alphabetically, each with their summary where there is one; organisations come last. Only people lead: an organisation, or a credit with no entry, never does, however many routes it has. A person whose routes reach the number moves up with no other change.

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `name` | string | The name as the credits write it. Unique. | `"Andrew Skurka"` |
| `credits` | array of strings | One or more exact `route.creator` values that credit this author. Each must be the `route.creator` of at least one route and contain the name. The same credit may be listed under each author it names. | `["Andrew Skurka", "Andrew Skurka and Ryan Jordan"]` |
| `kind` | string, optional | `person` (the default: one named person), `people` (human, but not one full name: a pair credited together, such as `"John and Monica Chapman"`, or a pair known by one name, such as `"Wilderness Mindset"`; `name` is then the credit as written), or `organisation`. Only a `person` page carries a schema.org `Person`. | `"people"` |
| `url` | string, optional | The author's own site or page, `http(s)`. Shown in the head of the author's page, and the `url` and `sameAs` of a `Person`. | `"https://andrewskurka.com/"` |
| `summary` | string, optional; people only | One sentence on one line, at most 160 characters, ending with a full stop, that says who this is. Begins with the name. No dash as punctuation. The page's sentence under the name, and its description for search engines. | `"Andrew Skurka is ..."` |
| `bio` | string, optional; people only | One paragraph of plain text on one line, 40 to 130 words, ending with a full stop. No dash as punctuation. Shown after the rows, under "About" and the name. Wording is ours: nothing is copied from a source. It uses the pronoun the cited sources use for the person; where none does, it repeats the surname. | |
| `checked` | date, with `summary` or `bio` | `YYYY-MM-DD`: when the summary and bio were last checked against their sources. Not in the future. Required with either; refused without. | `2026-11-17` |
| `[[author.source]]` | tables, with `summary` or `bio` | The pages the summary and bio were read on, each with `url` (`http(s)`) and `publisher` (who publishes the page). At least one is required with either; refused without; no page twice. | `url = "https://andrewskurka.com/about/"`, `publisher = "Andrew Skurka"` |

On an `organisation`, `summary`, `bio`, `checked` and `[[author.source]]` are refused; it may carry `url`. An unknown field is refused anywhere in an entry or a source. `tools/validate.py` runs these checks (`tools/check_datafiles.py`).

## `places.toml`: the parks, ranges and wilderness areas

One file at the top level, one `[[place]]` entry per place that at least one record names. It is the one spot where a place's display name, kind and source live. Entries are written by `tools/place_trails.py`, sorted by kind then slug, and checked by `tools/validate.py` (`tools/check_places.py`). Slugs are unique within a kind, not across kinds: a park and a wilderness area may share a slug. A page that joins two units, as Sequoia and Kings Canyon are joined, is one entry with two `source_id`s.

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `slug` | string | The place's slug, unique within its kind. | `"wind-river-range"` |
| `kind` | string | `park`, `range` or `wilderness`. | `"range"` |
| `name` | string | The display name. The slug is the slug of this name (`white-mountains-arizona` is the one stated exception, as the other White Mountains have the plain slug). | `"Wind River Range"` |
| `label` | string, where present | What kind of place it is, for the page's kicker. Defaults to the kind's own: `Park`, `Mountain range`, `Wilderness area`. Set it where that is wrong: `Plateau` for the Colorado Plateau, `National monument` for a national monument. | `"Plateau"` |
| `prep` | string, where present | The preposition a title or lede uses for the place: `in the` (the default for a range or a wilderness area), `in` (the default for a park), `on the`, `along the`. | `"on the"` |
| `where` | array of strings | The state or province codes the place is in, as records write them (`"WY"`, `"ON"`). Proposed by the tool from the `regions` codes shared by at least half of the place's measured trails, and confirmed by a reviewer. | `["WY"]` |
| `within` | array of strings, where present | The slugs of parent places, ranges within ranges. Each names an existing `range` entry, and the chains never circle. A trail in a nested range is also in every parent; records never store the parents. | `["rocky-mountains"]` |
| `source` | string | Which published outline set the boundary came from: `nps`, `wilderness-connect`, `cpcad` or `gmba-v2`. | `"gmba-v2"` |
| `source_id` | string, or array of strings | The publisher's own id for the outline (an array where one page joins units). | `"1234"` |
| `source_version` | string | The source's version, or the date the outline was downloaded, so a measurement can be re-derived from the same outline. | `"2026-11-20"` |
| `box` | array of numbers | The outline's bounding box as `[west, south, east, north]` in longitude and latitude, rounded to 2 decimals. A measurement, like `km`: the tool refreshes it, and the place's map opens on it. | `[-110.0, 42.5, -108.5, 43.5]` |

## `trail-numbers.txt`: a permanent number for every trail

One plain text file at the top level gives every trail a number that never changes and is never used again. It is one `id` per line, after a few `#` comment lines at the top. A trail's number is the zero-based index of its line among the `id` lines (the comments are not counted), so the first `id` is trail 0. The Saved page's short links are written in these numbers (see below).

Lines are only ever appended. A trail that is removed from the catalogue, or whose directory is renamed, keeps its line: the number is retired and no other trail gets it. `python3 tools/build_index.py`, which you run after adding a record, appends every record that has no line yet, in sorted order of the new `id`s, and says so; it never rewrites a line that is there. `tools/validate.py` fails when a record has no line, when an `id` is on two lines, or when a line is not a well-formed `id`; an `id` with no record is a retired number and is fine. `tools/check_history.py`, which CI runs against the base commit, fails when a line that was there is changed, moved or removed. The file was seeded with every record at the time, alphabetically by `id`.

### The short link to a saved list

The Saved page (`/saved/`) writes a list as `?t=<id>,<id>,...` while it holds ten trails or fewer (`SAVED_READABLE_MAX` in `web/assets/app.js`), and as `?s=<code>` when it holds more, so that the link does not grow with the list. The code is a set of trail numbers: bit N is 1 when the trail with number N is in the list. The bits are packed into bytes (bit 0 is the least significant bit of byte 0), trailing zero bytes are dropped, and the bytes are written in base64url without padding. The first character of the code is the format version, `1`, kept out of the base64url text, so that a later format can be told apart and old links keep opening; a code that starts with any other character is not understood and is shown as a link with no trails. A number that belongs to no trail on the site is ignored without a word. The page opens both forms for good; if an address has both `t` and `s`, `s` is used. A short link does not keep the order the trails were saved in: the list opens in A to Z order.
