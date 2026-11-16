# Changelog

## 2026-11-16 - Emblems for 81 trails, a history on every record, and a page of what was left out

- 81 trails now show an emblem, up from 41. Each is the trail's own crest, badge or roundel, alone. Where the holder only publishes a larger logo, the emblem was cropped out of it and the lettering or organisation name beside it was cut off. Where the emblem sat on a white surround that could be removed cleanly, the surround was made transparent. 72 are PNG and 9 are SVG.
- 123 records have no emblem file. 101 say the trail has no emblem of its own (`no-logo-exists`), and 22 say an emblem exists or may exist but no usable artwork was found at a source the dataset allows (`logo-not-found`). Each says in its logo note which pages were checked. The Pinhoti Trail's file was removed, because it was the Alabama Trails Foundation's wordmark and not the trail's emblem.
- `tools/validate.py` now rejects a `shield.status` that is not one of the three values, a `use-real-logo` record with no logo file, a logo file on a record that says it has none, and a record with no file and no note. A trail page says "No emblem of its own" or "Emblem not found" for the two states, and the Logos page counts and explains each.
- Every record has a `[[history]]` list: what changed or was asked for, the fields it concerns, the page it was read on, who asked (by role) and whether it was applied or declined. Each trail page shows it under "History of this record", beside "About this data". The records that changed in the last release, and the ones whose logo changed today, have an entry for each change.
- `tools/check_history.py` fails when a fact about a trail or its track changed with no new history entry. The logo counts as a fact. It prints the earlier entries about each changed field, and flags a declined request or one made by someone other than the dataset's own check. It runs on every push and pull request. `tools/validate.py` checks the shape of each entry.
- A new page, "Considered and left out", lists the 35 trails and routes that were looked at and not included, with the reason, the page that shows it and the date. It comes from `left-out.toml` and is linked from the footer.
- The Hoosier Heritage Trail record now says the longest stretch between legal forest campsites is 13.3 miles, as its association's president wrote on the issue tracker. Its length note no longer says the association's site disagrees with itself, because the home page now gives 161 miles throughout. The association's free 2026 guide and map set is linked from the trail page under "Maps and guides". Any trail may now list its holder's own guide or map set in `[[guide]]`, not only a route. The trail's emblem is the roundel from the file the association's president sent, shown alone.
- A new tool, `tools/gpx_track.py`, turns a GPX file sent by a holder or a hiker into a record's track files. It keeps the geometry only, reports gaps between segments, and refuses a file that is not GPX.
- A track shared by stated permission now shows the quoted words, who said them, when and where, in the credit box of the download panel as well, and its note no longer says the quotation is below when it is not.

## 2026-11-16 - 19 trails added, seven tracks added, and the C&O Canal Towpath removed

- A deeper search of the web, region by region, added 14 official trails: the Land Between the Lakes North/South Trail, the Bristol Hills Trail, the Shenipsit Trail, the Midland to Mackinac Trail, the Middle Fork Trail, the Boundary Trail in the Pasayten Wilderness, the Wyoming Range National Recreation Trail, the Solitude Loop Trail, Alpine Trail #7, Boundary Trail #1 at Mount St. Helens, the Dän Zhùr (Donjek) Route, the Koroc River and Palmer River Loop, the Western Uplands Backpacking Trail and the Stein Valley Traverse. It also added 4 routes: the Northern Colorado Trail, the Teton Crest Route, the Big Bend 100 and the Georgia Loop.
- Eleven of those 18 came with a track. Eight tracks came from OpenStreetMap, for the Land Between the Lakes North/South Trail, the Bristol Hills Trail, the Shenipsit Trail, the Boundary Trail in the Pasayten Wilderness, the Wyoming Range National Recreation Trail, Boundary Trail #1 at Mount St. Helens, the Western Uplands Backpacking Trail and the Stein Valley Traverse. Three came from the Forest Service's open trail data, for the Middle Fork Trail, the Solitude Loop Trail and Alpine Trail #7. The other new trails and routes were records only.
- The Pasayten track from OpenStreetMap had run about 18 miles (29 km) past the end of the trail, onto ways named for the Castle Pass, Three Fools Creek and Pacific Crest trails. It was rebuilt without them and measured 69.8 miles (112.3 km) against the published 73 miles (117 km), in one part.
- The Hoosier Heritage Trail was added at its association's request, made through the issue tracker, with the association's own track. The association's president said in writing that the track was free to share. A new licence value, `stated-permission`, recorded such permission with the quoted words, who gave them, when and where.
- The C&O Canal Towpath was removed, because the inclusion rule leaves out canal towpaths.
- The Grand Enchantment Trail is now recorded as a route by its author, Brett Tucker. It has no track, because his map set is sold.
- Tracks from OpenStreetMap, with elevation, were added for the Great Eastern Trail, the International Appalachian Trail in Newfoundland and Labrador, the Timberline Trail, the Kekekabic Trail, the Pukaskwa Coastal Hiking Trail, the West Coast Trail and the Chuck Keiper Trail.
- Four records were corrected. The Finger Lakes Trail was given as 580 miles for the main trail. The Ozark Highlands Trail was given as about 325 miles planned and about 290 built, with its unbuilt gaps stated. The Eastern Continental Trail's length note was rewritten from the author's pages. The Knobstone record was extended to the 160-mile Knobstone Hiking Trail.
- The Knobstone record also carried what the Hoosier Heritage Trail Association reported about the Pioneer section, and that the Knobstone Hiking Trail Association's site still listed it. Each of the two trails linked to the other, as a separate trail over a similar corridor.
- 204 trails in all, 147 designated trails and 57 routes. 126 have a track and 78 are records only.

## 2026-11-16 - Permission shown with its quote, and two switches kept in step

- A trail page shared by stated permission showed the quoted words, who said them and when, and a link to where. The GPX file's description carried the quote and the address. The data page counted such tracks as "Tracks shared with permission".
- A list page's own miles and kilometres switch was removed. The one in the header was the only switch left.
- The Outdoor and Plain map switch stayed in step with the page when the choice changed while the map was loading, in another tab, or after Back.
- A length range given in an address with the shortest and longest swapped showed the shorter one first in its controls.

## 2026-11-15 - The Tonto Trail, the Maricopa Trail and the Across Utah Route added

- The Tonto Trail was added at 95 miles (153 km), with a track and elevation from OpenStreetMap.
- The Maricopa Trail was added at more than 315 miles (507 km), with a track and elevation from OpenStreetMap and its side routes kept as alternates. The county data was not used because its terms forbid commercial reuse.
- The Across Utah Route was added as a route by author Jamal Green, at about 700 miles. It has no track and its record points to the author's pages.
- 186 trails in all, 134 designated trails and 52 routes. 107 have a track and 79 are records only.

## 2026-11-15 - Saved trails added, and the units and theme switches moved

- A visitor could save trails with a star in a list or a Save button on a trail page. The saved list is kept in the visitor's browser and shown on its own page with a map of those trails.
- A saved list could be carried in a page address for bookmarking or sending to another person or device. A list opened from such an address did not overwrite the visitor's own list.
- The miles and theme switches moved from the foot of the page to the header on every page, beside a saved count.
- Fixes kept the filters, the switches, the sort and the saved stars showing the right values after Back, a reload, a change in another tab, and clearing the search and filters. A length given in the other unit in the address took the nearest step instead of being dropped.
- The home page headline and subtitle were shortened.

## 2026-11-15 - Trail pages got an outdoor map

- Maps on trail pages opened on an outdoor style with hill shading, contour lines, woods, water, footpaths, and peaks with their heights. Heights and contours followed the visitor's choice of units.
- A switch on the map returned to the plain map and was remembered. The home page overview map was unchanged.
- The map still loaded when the elevation tiles or the contour add-on failed.

## 2026-11-15 - The Eastern Sierra High Route and three tracks added

- The Eastern Sierra High Route was added as a route by author Dan Stenziano, at 65 to 70 miles. The author sells the route, so the record has no track.
- Tracks from OpenStreetMap, with elevation, were added for the Thames Valley Trail, the Grand Valley Trail and the Sentier Nepisiguit Mi'gmaq Trail.
- The Boreal Trail stayed a record only. OpenStreetMap held only three short pieces of it, and its record said so.
- 183 trails in all, 132 designated trails and 51 routes. 105 had a track and 78 were records only.

## 2026-11-15 - Abbreviations kept only where one is in real use

- Every record had carried an abbreviation because the schema required one, and many were invented. An abbreviation was now recorded only where the trail's holder or author used it or it was in settled use among hikers.
- 104 abbreviations were kept, each with the page where it was seen, and 13 of them were corrected to the form in use. 78 were removed.
- Abbreviations were written without full stops, as AT, and two trails could share one where that was the truth. The validator enforced the rule.
- On the site a trail page and a list row showed the abbreviation only where the record had one. A search for a shared abbreviation listed every trail that used it, and a trail with no logo and no abbreviation got a plain mark in place of made up letters.
- HST was restored for the High Sierra Trail, resting on a hiking guide page that used it. The source pages for FLT and LSHT were replaced with pages that could be read.

## 2026-11-14 - Lists checked again, five trails removed, and other links shown

- Two lists on LongTrailsWiki, 188 entries on one and 573 on the other, were checked against the inclusion rule for the United States and Canada. Seven missing trails were added from that check: the Prescott Circle Trail, the High Country Pathway, the Guadalupe Ridge Trail, the Toiyabe Crest National Recreation Trail, the General George Crook National Recreation Trail, and as routes the Condor Trail and the Mojave-Sonoran Trail. Four of the seven had a track.
- The Black Canyon National Recreation Trail and Montana Trail 406 were also added. The Black Canyon record included a track, and Montana Trail 406 was a record only.
- Five were removed as not walking trails: the Great Trail (Trans Canada Trail), the Great Western Trail, and the Iditarod, Nez Perce and Overmountain Victory National Historic Trails.
- A record could now carry links to other pages about the trail, each with a title, a publisher and an address, separate from the official site. 97 trails linked to their LongTrailsWiki page.
- Missing facts were filled on six trails. The Colorado Trail high point was corrected to 13,271 feet, and the East Coast Trail was corrected to one linear trail rather than a network.
- On the site a trail page listed its other links as "More about this trail" under the main buttons. A trail with no official site put its first other link in the main button place, named by its publisher, without repeating it in the list. The About page showed the section naming the other lists of long trails that this dataset had been checked against.
- 182 trails in all, 132 designated trails and 50 routes. 102 had a track and 80 were records only.

## 2026-11-14 - The filter panel stayed reachable

- The filter panel beside the trail list stayed beside the list at any window height and was never taller than the window. When its fields did not fit it scrolled on its own, with "Clear search and filters" kept at its foot.
- Extra filters beside the list were set in one column. Each choice fit in one row with its count on the right, and some names were shortened.
- A later fix let the mouse wheel scroll the page again when it was over the filters and the panel itself had nothing left to scroll.

## 2026-11-14 - Miles and feet put first, and the site given its mark

- Miles and feet came first unless a visitor chose kilometres and metres. That held for paired figures, the time estimate, the elevation profile, page descriptions and the map scale.
- The length filter and the length scale used round mile steps for a reader in miles and round kilometre steps for a reader in kilometres. The lists defined by length became "Under 100 miles" and "The longest" at 1,000 miles or more, and the old address for the short list redirected to the new one. The records themselves stayed metric.
- The tab icon became a mountain with a trail up it, with the sizes browsers and phones need. The home page opened with the mark, the name and what the site offered, and link previews got a real image that other sites and message apps could draw.
- The decorative contour drawing on the home page stayed inside the content column and thinned out on every side.

## 2026-11-14 - 41 trails added from other lists, and the Fundy Footpath removed

- Other lists of long trails were checked against the inclusion rule, and 41 missing trails were added. 28 were designated trails and 13 were routes, and 12 had a track.
- The designated trails added were the Akshayuk Pass, the American Discovery Trail, the Bay Area Ridge Trail, the Boreal Trail, the Chuck Keiper Trail, the Conestoga Trail, the Conservation Trail, the Cottonwood Trail, the East Beach Trail (Naikoon), the Fremont National Recreation Trail, the Grand Valley Trail, the Highline National Recreation Trail, the International Appalachian Trail in Maine and in Newfoundland and Labrador, the Iron Belle Trail hiking route, the Itijjagiaq Trail, the Knobstone Trail, the Lost Coast Trail, the Massanutten Trail, the Sentier Nepisiguit Mi'gmaq Trail, the North Umpqua Trail, the Ocean to Lake Hiking Trail, the Ottawa-Temiskaming Highland Trail, the Paumanok Path, the Ring the Peak Trail, the Shawangunk Ridge Trail, the Thames Valley Trail and the Warrior Trail.
- The routes added were the Appalachian High Route, the Basin and Range Trail, the Bigfoot Trail, the Bitterroots 80-mile Route, the Desert Winter Thru-Hike, the Grand-Moab Route, the Lowest to Highest Route, the San Diego Trans County Trail, the Santa Fe to Taos Thru-Hike, the Southeastern Serpentine Trail, the Southwestern Horseshoe, the Teton Range Traverse and the Vancouver Island Backbone.
- Each new record checked the length and the holder on the holder's own page and carried sourced hiker facts. Five were marked held where a question stayed open. The American Discovery Trail record said how much of it was road and shared path.
- The Fundy Footpath was removed. At about 25 miles (41 km) it fell below the 50-mile floor, which stayed as it was.
- The rule now said plainly that paths made mainly for cycling, such as gravel rail trails and canal towpaths, and historic trails that are mainly driving routes, were not listed.
- A hiker fact could now be read on an established hiking site where the holder and government pages said nothing, with that site named as the source. The holder's figure still won a disagreement.
- Two corrections were made: the Deseret Hiking Route also ran through Idaho, and the Vagabond Loop linked to its author's live page instead of an archived copy.
- Tracks for the Thames Valley, Grand Valley, Sentier Nepisiguit Mi'gmaq and Boreal trails were still to be fetched. The OpenStreetMap query servers could not be reached.
- 178 trails in all, 131 designated trails and 47 routes. 97 had a track and 81 were records only.

## 2026-11-14 - Every list of trails could be sorted, and trails without a track joined the map

- Every list of trails got a "Sort by" menu for name, length, time and climb, in either direction. Lists opened by name, A to Z, except the lists defined by length or time. The chosen order was kept in the page address, and the pages were right without JavaScript.
- A trail with no track but a known start and end was drawn on the map as a dotted straight link between the two places with a ring at each. A trail with only one known place was drawn as a ring. The text on and under the map said the dotted mark was not the trail's path.
- Such a trail followed the filters, the row highlight and the map popup like any other, and its own page showed the map in place of an empty frame. It gave no download and no elevation.

## 2026-11-14 - Start and end positions added for trails with no track

- Records could give the position of the place named as the start or the end, so a trail with no track could still be put on a map. 32 of the 53 trails with no track got at least one position, 45 points in all.
- Each point named its source, and only public domain sources were used. A point was the named place, not a surveyed trailhead, and an end that was only a border, a whole park or a mountain range got no point.
- The Eastern Continental Trail start was set to Key West as its author's page said, and the Brazeau Loop got its start, the Nigel Creek trailhead.

## 2026-11-14 - The site was rebuilt for browsing trails

- The site was rebuilt around finding and reading about trails. The navigation became Trails, Places and About, and a route was presented as a kind of trail, explained where the word first appeared.
- The home page became the catalogue, with filters for where, length, time, season, terrain, kind, walking, shape and GPX. A filter was offered only when at least a third of the trails had a value for it.
- The site got lists such as National Scenic Trails and Routes, and a Places page grouping states and provinces into regions. A trail page led with the summary, an at a glance box, the map, the downloads and the elevation profile, and the dataset fields moved into a folded "About this data" section.
- The trail list became a compact card on phones and beside the filters, and a column table where it had the full page width.

## 2026-11-14 - Hiker facts and elevation added to the records

- Records gained a table of hiker facts: a one sentence summary, the official page, where the trail started and ended, its shape, how many days it took, the season, the high point, the terrain, how much was off trail, and whether a permit was needed. 137 of the 138 records had the table, and every fact named its source.
- Each of the 85 trails with a track gained elevation figures: the highest and lowest points, the total climb and descent, and a profile.
- The wording was settled across the README, the contributing guide and the schema: a route for a route, its author for its author, and a track for a trail's geometry.
- Three corrections were made. The Bartram Trail official link moved to the Forest Service page because the old domain served spam. The Eastern Continental Trail ended at Cap Gaspé and Newfoundland came out of its regions. The Wind River High Route record named both of its authors.

## 2026-11-13 - Logos finished for 15 trails

- Seven trails gained their logo from the holder's own site: the California Coastal Trail, the Fundy Footpath, the Grand Enchantment Trail, the Great Eastern Trail, the Great Trail (Trans Canada Trail), and the Nez Perce and Overmountain Victory National Historic Trails.
- Four were recorded as having no logo of their own, only their agency's mark: Pukaskwa Coastal, Teton Crest, Timberline and West Coast Trail.
- Four had an emblem but no clean copy was found on the holder's site: Iditarod, Kekekabic, Oregon Desert and Great Western. Each record said what was looked at.
- Trail pages stopped saying a logo had been taken from a page when no logo was included. The link now said the logo was not included, and the Logo section said who held it and that no copy was in the dataset.

## 2026-11-13 - Corrections invited on every page, and changes checked before publishing

- Each trail page offered "Report a problem" with the record already filled in, plus "Edit this record" and "History". The home page, the footer and the About page linked to forms for a wrong record and a missing trail, and the Logos page linked to a form for a steward or an author who wanted a track or a logo removed or given a different credit.
- Three issue forms and a pull request checklist were added for contributors.
- Each proposed change was checked by the validator and the site tests, and the site was rebuilt only after those checks passed on the main branch. A failing record or page was therefore not published.
- Changes merged in the public copy of the repository were passed on to the main copy automatically, and the contributing guide named the main copy.

## 2026-11-13 - The dataset took the name Long Hikes

- The dataset and the README took the name Long Hikes, after the site. The README pointed readers to the public repository for issues and proposed changes.
- The contributing guide gained a section on how to send a change, covering the form on each trail page, editing a record in a copy of the repository, and the checks each proposed change got.
- The route table column and the schema heading said "track policy".

## 2026-11-13 - A trail's geometry became a track in the documents and on the site

- The site stopped calling a trail's geometry by the old word and called it a track. Download links named the formats they offered.
- The documents and the notes in the records made the same change. File and field names, quoted words, attribution strings and trail names were left as they were.

## 2026-11-13 - The Long Hikes site opened

- The site Long Hikes opened at longhikes.org, built from the records. It had a page for each of the 138 trails, a finder on the home page with a map of the 85 tracks, region and route lists, and the documents from the repository as pages.
- Each track was offered as GeoJSON and as GPX, with two archives holding everything.
- At that point the dataset held 138 trails, 104 designated trails and 34 routes. 85 had a track and 53 were records only.

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
