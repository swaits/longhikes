# Sources

Each trail's record (`<id>/trail.toml`) names its source, the page to ask for the track, and the terms that apply. This file collects the distinct terms, the sentence that states them, the page they were read on, and the date read. Dates read: records were first read on 2026-11-08; the licence pages below were read again on 2026-11-09; 40 designated records and 34 person-defined routes were added and read on 2026-11-10.

A track is included in this repository only when its source's terms allow redistribution. Where they do not, the trail is a record only and `source.line_absent_reason` in its record says why.

## OpenStreetMap (ODbL-1.0)

Used by: 108 trails with an included track, and part of the Colorado Trail track (about 38 km; the rest is United States Forest Service data). Also named as the recorded source for 2 record-only trails, where no track was downloaded or none was usable. One of the person-defined routes has a track from OpenStreetMap (the Big SEKI Loop, relation 11628437); the other 49 name no source licence for a track.

Quoted terms: "You are free to copy, distribute, transmit and adapt our data, as long as you credit OpenStreetMap and its contributors."

Page: https://www.openstreetmap.org/copyright (read 2026-11-09). Full text: LICENSES/ODbL-1.0.txt. Credit required: "© OpenStreetMap contributors". Adapted tracks stay under the ODbL.

## United States federal agencies (public domain)

Publishers: National Park Service, USDA Forest Service and Bureau of Land Management services named in each record. Used by: 16 trails with an included track (Alpine Trail #7, Appalachian, Black Canyon, Colorado Trail in part, Fremont, General George Crook, Highline, Middle Fork Trail, Natchez Trace, New England, North Umpqua, Pacific Northwest, Potomac Heritage, Solitude Loop, Thorofare and South Boundary Trail, Toiyabe Crest).

Quoted terms: "Data and content created by government employees within the scope of their employment are not subject to domestic copyright protection under 17 U.S.C. 105."

Page: https://irma.nps.gov/DataStore/Reference/Profile/2311077 (read 2026-11-09). United States federal government work is public domain in the United States under 17 U.S.C. 105. Two included tracks were produced with partner associations (Appalachian and New England); the partners' share is not separately licensed in those services, and is noted in the records.

## Pacific Crest Trail Association (CC-BY-4.0)

Used by: 1 trail (Pacific Crest).

Quoted terms: "All of the data accessed through this page are licensed under the Creative Commons Attribution 4.0 International License."

Page: https://www.pcta.org/discover-the-trail/maps/pct-data/ (read 2026-11-09). Full text: LICENSES/CC-BY-4.0.txt. Credit required: Pacific Crest Trail Association.

## Continental Divide Trail Coalition (CC-BY, version not stated)

Used by: 1 trail (Continental Divide).

Quoted terms: the source item's licence field reads "CC BY" (no version stated).

Page: https://services8.arcgis.com/WyuHwdftppQLa5KO/arcgis/rest/services/Continental_Divide_Trail_2/FeatureServer/0 (read 2026-11-09). Treated here as Creative Commons Attribution, with credit to the Continental Divide Trail Coalition. The version should be confirmed with the Coalition before a use that needs a named version.

## A hiker who shares a track under CC BY 4.0 (CC-BY-4.0)

Used by: 2 trails (California Coastal Trail, Washington Coast Trail). The hiker's own GPX files, attached to this dataset's issue 1 on 2026-11-17, one of a walk of the whole California coast in eight section hikes and one of the Washington coast route the hiker worked out.

Quoted terms: for California, "CC BY 4.0 sounds good, and your idea for the source and link work for me." (https://github.com/swaits/longhikes/issues/1#issuecomment-6928214012, 2026-11-16); for Washington, "CC BY 4.0 is fine for this as well." (https://github.com/swaits/longhikes/issues/1#issuecomment-6935950983, 2026-11-17).

Credit required: Lauren Lake, PacificCoastalTrail blog (https://pacificcoastaltrail.wordpress.com), the name the blog gives the author. Full text of the licence: LICENSES/CC-BY-4.0.txt. The California track is one hiker's walk, not the official alignment, and the record says so.

## Holders who state permission in writing (stated-permission)

Used by: 1 trail with an included track (Hoosier Heritage Trail). The holder of the trail, the route's author or the person who recorded the track has stated in writing that the track may be shared, without naming a licence. Each record gives the statement in `source.permission_quote`, who made it by role in `source.permission_by`, when in `source.permission_date` and where in `source.permission_url`; the trail page shows them as a quotation with a link. This is not public domain and not a Creative Commons licence.

## Publishers with no stated licence (no track included)

Used by: the official trails marked "none-stated" and "record only" in the table below, none with an included track. Among them: the holders of the trails added on 2026-11-14 whose pages state no licence for a track.

Terms found: no licence stated on the items, and no licence found on the publishers' pages when read on 2026-11-09. The items carry disclaimers only. A disclaimer is not a licence, so these publishers' tracks are not redistributed here. Each record's `source.url` is the page to ask for the track, and `source.line_absent_reason` states this reason. Nine more records that were listed here had a track added from OpenStreetMap on 2026-11-09; their publishers' own tracks are still not used, and each record keeps the publisher and its page in `source.publisher` and `source.publisher_url`.

## Person-defined routes (creator's own pages, no track included)

Used by: the person-defined routes (`kind = "route"`). Each record names its creator and the guide the route is got from, in its `[[guide]]` tables, and `route.line_policy` says whether the creator shares the track.

Terms found: none. No route creator's page read on 2026-11-10 states a licence for the route's track. The record says where the track may be got from the creator, and `source.line_absent_reason` says why no track is included here: the route is sold as a guide, the creator withholds the track, the question is not settled, or the creator offers a download with no licence that allows passing it on. The Washington Coast Trail is the one person-defined route whose author shared the track directly, under CC BY 4.0 (see above). Where OpenStreetMap carries the route as a route relation and the creator publishes the track freely, the track comes from OpenStreetMap under the terms above.

Page: the creator's or publisher's own page for the guide, given in each record's first `[[guide]]` and quoted in `route.creator_words_url` where the creator's words are quoted.

## Every record's source


| Trail | Publisher | Page | Licence | Included |
| --- | --- | --- | --- | --- |
| across-utah-route | Jamal Green, Across Utah (publishes the route) | [source page](http://www.acrossutah.com/wordpress/master-map/) | none-stated | record only |
| akshayuk-pass | Parks Canada (Auyuittuq National Park) (publishes the trail) | [source page](https://www.parks.canada.ca/pn-np/nu/auyuittuq/activ/randonnee-hiking) | none-stated | record only |
| alexander-mackenzie | Province of British Columbia (BC Geographical Names record; no open geometry found) | [source page](https://www.openstreetmap.org/relation/2654551) | ODbL-1.0 | track |
| allegheny-trail | West Virginia Scenic Trails Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/1772789) | ODbL-1.0 | track |
| alpine-trail-7 | USDA Forest Service (National Forest System Trails, Enterprise Data Warehouse) | [source page](https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0) | us-gov-public-domain | track |
| american-discovery-trail | OpenStreetMap contributors (the American Discovery Trail Society holds the official route and gives its data by state, region or nationwide, but states no licence for it) | [source page](https://www.openstreetmap.org/relation/1544944) | ODbL-1.0 | track |
| appalachian | National Park Service Appalachian NST and Appalachian Trail Conservancy | [source page](https://services1.arcgis.com/fBc8EJBxQRMcHlei/ArcGIS/rest/services/ANST_Centerline/FeatureServer/0) | us-gov-public-domain | track |
| appalachian-high-route | Jake Blood and Jennifer Pharr Davis (publish the route) | [source page](https://jenniferpharrdavis.com/blog/hiking-appalachian-high-route) | none-stated | record only |
| arizona | Arizona Trail Association (AZTA) | [source page](https://www.openstreetmap.org/relation/2804113) | ODbL-1.0 | track |
| avon | Avon Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/3442182) | ODbL-1.0 | track |
| backbone | National Park Service, Santa Monica Mountains NRA | [source page](https://mapservices.nps.gov/arcgis/rest/services/NationalDatasets/NPS_Public_Trails_Geographic/FeatureServer/0) | ODbL-1.0 | track |
| baker | Rachel Carson Trails Conservancy (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/9078832) | ODbL-1.0 | track |
| bartram | Blue Ridge Bartram Trail Conservancy (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/9955138) | ODbL-1.0 | track |
| basin-and-range-trail | Eric Poulin (publishes the route) | [source page](https://basinandrangetrail.com/shop/) | none-stated | record only |
| batona | Batona Hiking Club (publishes the trail with the New Jersey State Park Service; no open geometry found) | [source page](https://www.openstreetmap.org/relation/4129027) | ODbL-1.0 | track |
| bay-circuit | Appalachian Mountain Club (leads the trail's partners; no open geometry found) | [source page](https://www.openstreetmap.org/relation/12779888) | ODbL-1.0 | track |
| bayou-state-trail | Bayou State Trail Association (publishes the trail) | [source page](https://www.bayoustatetrail.com/trails) | none-stated | record only |
| beartooth-high-route | Wilderness Mindset (publishes the route) | [source page](https://wildernessmindset.com/product/beartooth-high-route-map-pack/) | none-stated | record only |
| benton-mackaye | Benton MacKaye Trail Association (publishes the trail); the only other track, a Blue Ridge Forever ArcGIS item (2017), is restricted | [source page](https://www.openstreetmap.org/relation/1675439) | ODbL-1.0 | track |
| big-bend-100 | Ky Harkey and Anna Claire Eddington (the route's authors) | [source page](https://tpwmagazine.com/adventure-recreation/the-big-bend-100-a-hike-across-two-west-texas-parks/) | none-stated | record only |
| big-seki-loop | Amy and James (Doing Miles) (publishes the route) | [source page](https://www.openstreetmap.org/relation/11628437) | ODbL-1.0 | track |
| bigfoot-trail | Bigfoot Trail Alliance (publishes the route) | [source page](https://www.bigfoottrail.org/route/guidebook/) | none-stated | record only |
| bitterroots-80-mile-route | Wilderness Mindset (publishes the route) | [source page](https://wildernessmindset.com/product/bitterroots-80-mile-route-map-pack/) | none-stated | record only |
| black-canyon | Bureau of Land Management (Ground Transportation Linear Features) | [source page](https://gis.blm.gov/arcgis/rest/services/transportation/BLM_Natl_GTLF_Public_Display/MapServer/7) | us-gov-public-domain | track |
| blue-mountains-trail | Greater Hells Canyon Council (publishes the route) | [source page](https://www.hellscanyon.org/blue-mountains-trail/maps) | none-stated | record only |
| border-route | Border Route Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/5996078) | ODbL-1.0 | track |
| boreal-trail | Saskatchewan Provincial Parks (Meadow Lake Provincial Park) (publishes the trail) | [source page](https://saskparks.tourismsaskatchewan.com/media/media-library/pdfs/park-downloads/meadow-lake/meadow-lake-all.pdf) | none-stated | record only |
| boundary-trail-mount-st-helens | USDA Forest Service, Gifford Pinchot National Forest (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/5628775) | ODbL-1.0 | track |
| boundary-trail-pasayten | U.S. Forest Service, Okanogan-Wenatchee National Forest (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/5252516) | ODbL-1.0 | track |
| brazeau-loop | Parks Canada, Jasper National Park (publishes the trail) | [source page](https://parks.canada.ca/pn-np/ab/jasper/activ/passez-stay/arrierepays-backcountry/sugg-sentiers_trip-ideas) | none-stated | record only |
| bristol-hills-trail | CNY Hiking (describes the trail; no page of the trail's holder was read) | [source page](https://www.openstreetmap.org/relation/3630775) | ODbL-1.0 | track |
| brooks-range-traverse | Luc Mehl (publishes the route) | [source page](https://thingstolucat.com/brooks-range-traverse/) | none-stated | record only |
| bruce-trail | Bruce Trail Conservancy (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/3375262) | ODbL-1.0 | track |
| buckeye | Buckeye Trail Association (publishes the loop); the Ohio DNR MapServer requires a token | [source page](https://www.openstreetmap.org/relation/1738661) | ODbL-1.0 | track |
| california-coastal | California Coastal Commission; Coastal Trails Alliance (the track is a hiker's own, not theirs) | [source page](https://services9.arcgis.com/wwVnNW92ZHUIr0V0/arcgis/rest/services/California_Coastal_Trail_April_2021/FeatureServer) | CC-BY-4.0 | track |
| canol | Northwest Territories Parks (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/13591414) | ODbL-1.0 | track |
| centennial-sd | USDA Forest Service, Black Hills National Forest (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/7330792) | ODbL-1.0 | track |
| central-wind-rivers-loop | Wilderness Press (publishes the route in the guidebook) | [source page](https://shop.adventurewithkeen.com/product/backpacking-wyoming/) | none-stated | record only |
| chinese-wall-circuit | Wilderness Mindset (publishes the route) | [source page](https://wildernessmindset.com/bob-marshall-wilderness-chinese-wall-circuit/) | none-stated | record only |
| circle-of-solitude | Wilderness Press (publishes the route in the guidebook) | [source page](https://shop.adventurewithkeen.com/wilderness-press/) | none-stated | record only |
| cohos | Cohos Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/14765821) | ODbL-1.0 | track |
| colorado-trail | USDA Forest Service (EDW National Forest System trails), with OpenStreetMap where the Forest Service publishes no segment | [source page](https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0) | us-gov-public-domain | track |
| condor-trail | Condor Trail Association (publishes the route) | [source page](http://www.condortrail.com/maps-trail-descriptions/) | none-stated | record only |
| conestoga-trail | Lancaster Hiking Club (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/6827091) | ODbL-1.0 | track |
| conservation-trail | Foothills Trail Club of Western New York (built and maintains the trail) | [source page](https://sites.google.com/view/foothillstrailclub/about-the-trail) | none-stated | record only |
| continental-divide | Continental Divide Trail Coalition (CDTC) | [source page](https://services8.arcgis.com/WyuHwdftppQLa5KO/arcgis/rest/services/Continental_Divide_Trail_2/FeatureServer/0) | CC-BY | track |
| corvallis-to-the-sea | Corvallis-to-the-Sea Trail (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/14706511) | ODbL-1.0 | track |
| cottonwood-trail | Parks Canada (Kluane National Park and Reserve) (publishes the trail) | [source page](https://parks.canada.ca/pn-np/yt/kluane/activ/randonnee-hiking/cottonwood) | none-stated | record only |
| cranberry-lake-50 | Cranberry Lake 50 volunteer trail crew (publishes the loop; no open geometry found) | [source page](https://www.openstreetmap.org/relation/7580730) | ODbL-1.0 | track |
| cross-vermont | Cross Vermont Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/2750828) | ODbL-1.0 | track |
| dan-zhur-donjek | Parks Canada (Kluane National Park and Reserve) (publishes the trail) | [source page](https://parks.canada.ca/pn-np/yt/kluane/activ/randonnee-hiking/dan-zhur) | none-stated | record only |
| deadman-creek-loop | Wilderness Press (publishes the route in the guidebook) | [source page](https://shop.adventurewithkeen.com/product/backpacking-arizona/) | none-stated | record only |
| deseret-hiking-route | Kevin "LarryBoy" DeVries (publishes the route) | [source page](http://www.lbhikes.com/p/a-complete-guide-to-deseret-hiking-route.html) | none-stated | record only |
| desert-trail | Desert Trail Association, whose route was scouted by Russel Pengely, D. W. "Old Creosote" Tomer and Steve Tabor; the site is now run by Desert Survivors | [source page](https://deserttrail.net) | none-stated | record only |
| desert-winter-thru-hike | simBLISSity Ultralight Designs (Brett Tucker and partner; publish the route) | [source page](https://www.simblissity.net/desert-wth-mapset.shtml) | none-stated | record only |
| donut-hole | Keystone Trails Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/13780803) | ODbL-1.0 | track |
| east-beach-trail | BC Parks (Naikoon Provincial Park) (publishes the trail) | [source page](https://bcparks.ca/naikoon-park/) | none-stated | record only |
| east-coast-trail | East Coast Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/2199386) | ODbL-1.0 | track |
| eastern-continental-trail | M. J. Eberhart (trail name Nimblewill Nomad), who publishes the route | [source page](https://nimblewillnomad.com/books/) | none-stated | record only |
| eastern-sierra-high-route | Dan Stenziano (publishes the route) | [source page](https://danstenziano.com/products/eastern-sierra-high-route-guide) | none-stated | record only |
| finger-lakes | Finger Lakes Trail Conference (publishes the trail; the North Country Trail Association hosts its track as 'agol_flt') | [source page](https://www.openstreetmap.org/relation/12725656) | ODbL-1.0 | track |
| florida | Florida Trail Association with the USDA Forest Service Southern Region | [source page](https://www.openstreetmap.org/relation/14480287) | ODbL-1.0 | track |
| foothills | Foothills Trail Conservancy (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/4572989) | ODbL-1.0 | track |
| fremont | USDA Forest Service, National Forest System trails | [source page](https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0) | us-gov-public-domain | track |
| ganaraska | Ganaraska Hiking Trail Association (publishes the trail; no open track found) | [source page](https://www.openstreetmap.org/relation/3696751) | ODbL-1.0 | track |
| general-george-crook | USDA Forest Service, National Forest System trails | [source page](https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0) | us-gov-public-domain | track |
| georgia-loop | Benton MacKaye Trail Association (publishes the loop) | [source page](https://bmta.org/backpacking-hikes/) | none-stated | record only |
| grand-enchantment | Brett Tucker, simBLISSity Ultralight Designs (publishes the route and sells the mapset) | [source page](http://www.simblissity.net/get/) | none-stated | record only |
| grand-moab-route | Paul Mags, PMags.com (publishes the route) | [source page](https://pmags.com/the-grand-moab-route) | none-stated | record only |
| grand-sawtooth-loop | USDA Forest Service, National Forest System trails (no track included; the guides publish none) | [source page](https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0) | none-stated | record only |
| grand-valley-trail | Grand Valley Trails Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/3637768) | ODbL-1.0 | track |
| great-basin-trail | Ryan "Dirtmonger" Sylva, who publishes the route | [source page](https://www.gossamergear.com/blogs/our-blog/great-basin-trail) | none-stated | record only |
| great-colorado-route | Donovan "Iceman" Rice, who publishes the route | [source page](https://www.greatcoloradoroute.com/route) | none-stated | record only |
| great-divide-trail | Great Divide Trail Association (account 'GreatDivideTrail', public map) | [source page](https://www.openstreetmap.org/relation/8139599) | ODbL-1.0 | track |
| great-eastern | Great Eastern Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/1024490) | ODbL-1.0 | track |
| great-plains-trail | Steve Myers, Great Plains Trail Alliance (publishes the route) | [source page](https://www.greatplainstrail.org/gpt-map/) | none-stated | record only |
| great-western-divide-loop | Brian Lucido (publishes the route) | [source page](https://www.brianlucido.com/sequoia-great-western-divide-loop/) | none-stated | record only |
| great-western-loop | Andrew Skurka and Ryan Jordan (publish the route) | [source page](https://andrewskurka.com/adventures/great-western-loop/route-description/) | none-stated | record only |
| green-river-lakes-titcomb-basin-loop | Wilderness Press (publishes the route in the guidebook) | [source page](https://shop.adventurewithkeen.com/product/backpacking-wyoming/) | none-stated | record only |
| guadalupe-ridge-trail | National Park Service (publishes the trail) | [source page](https://mapservices.nps.gov/arcgis/rest/services/NationalDatasets/NPS_Public_Trails_Geographic/FeatureServer/0) | none-stated | record only |
| hayduke-trail | Joe Mitchell and Mike Coronella (publish the route) | [source page](https://uofupress.com/books/the-hayduke-trail/) | none-stated | record only |
| heart-lake-two-ocean-plateau-loop | Wilderness Press (publishes the route in the guidebook) | [source page](https://shop.adventurewithkeen.com/product/backpacking-wyoming/) | none-stated | record only |
| high-country-pathway | Michigan Department of Natural Resources (manages the land; no open geometry found) | [source page](https://www.openstreetmap.org/relation/2450544) | ODbL-1.0 | track |
| high-sierra | National Park Service, Sequoia and Kings Canyon National Parks (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/1714300) | ODbL-1.0 | track |
| highlands | New York-New Jersey Trail Conference (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/6335422) | ODbL-1.0 | track |
| highline | USDA Forest Service, National Forest System trails | [source page](https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0) | us-gov-public-domain | track |
| hoosier-heritage-trail | Hoosier Heritage Trail Association (publishes the trail) | [source page](https://hoosierheritagetrail.org/downloads/) | stated-permission | track |
| horse-shoe | Horse-Shoe Trail Conservancy (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/1596895) | ODbL-1.0 | track |
| hot-springs-trail | Aria Zoner (publishes the route) | [source page](https://www.amazon.com/Hot-Springs-Trail-Official-Guidebook/dp/1505613922) | none-stated | record only |
| iat-newfoundland-labrador | International Appalachian Trail Newfoundland and Labrador (publishes the trail) | [source page](https://www.openstreetmap.org/relation/15695142) | ODbL-1.0 | track |
| ice-age | Ice Age Trail Alliance for the National Park Service | [source page](https://www.openstreetmap.org/relation/2381423) | ODbL-1.0 | track |
| idaho-centennial | Idaho Department of Parks and Recreation | [source page](https://www.openstreetmap.org/relation/10758083) | ODbL-1.0 | track |
| international-appalachian-trail-maine | Maine Chapter of the International Appalachian Trail (maintains the trail) | [source page](https://maineiat.org/?p=412) | none-stated | record only |
| island-walk | Island Walk PEI Inc. (publishes the route; no open geometry found) | [source page](https://www.openstreetmap.org/relation/12307947) | ODbL-1.0 | track |
| itijjagiaq-trail | Nunavut Parks (Government of Nunavut) (publishes the trail) | [source page](https://nunavutparks.com/nunavut_parks/katannilik-territorial-park/) | none-stated | record only |
| john-muir | No single publisher: NPS Yosemite and Sequoia-Kings Canyon, USFS Inyo and Sierra National Forests | [source page](https://mapservices.nps.gov/arcgis/rest/services/NationalDatasets/NPS_Public_Trails_Geographic/FeatureServer/0) | ODbL-1.0 | track |
| kanab-canyon-loop | Wilderness Press (publishes the route in the guidebook) | [source page](https://shop.adventurewithkeen.com/product/backpacking-arizona/) | none-stated | record only |
| kekekabic | Kekekabic Trail Club; USFS (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/10831114) | ODbL-1.0 | track |
| kings-canyon-high-basin-route | Andrew Skurka (publishes the route) | [source page](https://andrewskurka.com/product/kings-canyon-high-basin-route-guide/) | none-stated | record only |
| knobstone | Indiana Department of Natural Resources (publishes the southern Knobstone section; no open geometry found) | [source page](https://www.openstreetmap.org/relation/4644135) | ODbL-1.0 | track |
| koroc-palmer-loop | Parks Canada (Torngat Mountains National Park) (publishes the trail) | [source page](https://parks.canada.ca/pn-np/nl/torngats/activ/randonee-hiking1/koroc) | none-stated | record only |
| la-cloche | Ontario Parks (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/14141941) | ODbL-1.0 | track |
| laurel-highlands | Keystone Trails Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/7192246) | ODbL-1.0 | track |
| lone-star | Lone Star Hiking Trail Club (publishes the trail; no open track found) | [source page](https://www.openstreetmap.org/relation/7014936) | ODbL-1.0 | track |
| long-path | New York-New Jersey Trail Conference (an ArcGIS item 'Long Path' under an ArcGIS account, 2025; provenance not confirmed) | [source page](https://www.openstreetmap.org/relation/919642) | ODbL-1.0 | track |
| long-trail | Green Mountain Club (publishes the trail); its ArcGIS 'TRAIL_MASTER' track is restricted | [source page](https://www.openstreetmap.org/relation/391736) | ODbL-1.0 | track |
| lost-coast | Bureau of Land Management and California State Parks (publish the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/6125620) | ODbL-1.0 | track |
| lowest-to-highest-route | simBLISSity Ultralight Designs (Brett Tucker and partner; publish the route) | [source page](http://simblissity.net/L2H.shtml) | none-stated | record only |
| loyalsock | Alpine Club of Williamsport (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/3134579) | ODbL-1.0 | track |
| maah-daah-hey | USDA Forest Service, Dakota Prairie Grasslands (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/11562289) | ODbL-1.0 | track |
| maricopa-trail | Maricopa County Parks and Recreation (publishes the trail) | [source page](https://www.openstreetmap.org/relation/4020964) | ODbL-1.0 | track |
| mason-dixon | Mason-Dixon Trail System (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/1820324) | ODbL-1.0 | track |
| massanutten | USDA Forest Service, George Washington and Jefferson National Forests (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/11520193) | ODbL-1.0 | track |
| mattabesett | Connecticut Forest and Park Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/2971739) | ODbL-1.0 | track |
| metacomet-monadnock | Appalachian Mountain Club (publishes the New Hampshire part); the National Park Service carries the Metacomet section in the New England NST track | [source page](https://www.openstreetmap.org/relation/2317544) | ODbL-1.0 | track |
| mid-state | Mid State Trail Association (an ArcGIS item under an ArcGIS account, 2019; provenance not confirmed) | [source page](https://www.openstreetmap.org/relation/1022044) | ODbL-1.0 | track |
| middle-fork-trail | USDA Forest Service (National Forest System Trails, Enterprise Data Warehouse) | [source page](https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0) | us-gov-public-domain | track |
| midland-to-mackinac-trail | USDA Forest Service, Huron-Manistee National Forests (publishes the National Forest segment) | [source page](https://www.fs.usda.gov/r09/huron-manistee/recreation/trails/midland-mackinaw-trail) | none-stated | record only |
| midstate-ma | Midstate Trail Committee (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/5503042) | ODbL-1.0 | track |
| mogollon-rim-trail | Brett Tucker ("Blisterfree"), who publishes the route | [source page](https://www.simblissity.net/mogollon-rim-trail-mapset.shtml) | none-stated | record only |
| mojave-sonoran-trail | Eric Poulin (publishes the route) | [source page](https://seekinglost.com/thru-hikes/mojave-sonoran-trail-thru-hiking-route/) | none-stated | record only |
| monadnock-sunapee | Monadnock-Sunapee Greenway Trail Club (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/3888871) | ODbL-1.0 | track |
| montana-trail | Montana Trail 406 Association (publishes the route) | [source page](https://montanatrail.org/montana-trail-hike-sections/) | none-stated | record only |
| mountains-to-sea | North Carolina Division of Parks and Recreation; Friends of the Mountains-to-Sea Trail (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/1395404) | ODbL-1.0 | track |
| nankoweap-bright-angel-loop | Wilderness Press (publishes the route in the guidebook) | [source page](https://shop.adventurewithkeen.com/product/backpacking-arizona/) | none-stated | record only |
| nepisiguit-migmaq-trail | Sentier Nepisiguit Mi'gmaq Trail Inc. (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/13656926) | ODbL-1.0 | track |
| new-england | National Park Service with the Connecticut Forest & Park Association and the Appalachian Mountain Club | [source page](https://services1.arcgis.com/fBc8EJBxQRMcHlei/ArcGIS/rest/services/NEEN_BND_NationalScenicTrailCenterline_ln/FeatureServer/0) | us-gov-public-domain | track |
| north-boundary | Parks Canada, Jasper National Park (publishes the trail; no open geometry found) | [source page](https://parks.canada.ca/pn-np/ab/jasper/activ/passez-stay/arrierepays-backcountry/sugg-sentiers_trip-ideas/north-boundary) | none-stated | record only |
| north-country | North Country Trail Association for the National Park Service | [source page](https://www.openstreetmap.org/relation/11140515) | ODbL-1.0 | track |
| north-south | Rhode Island Department of Environmental Management (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/11102215) | ODbL-1.0 | track |
| north-south-lbl | USDA Forest Service, Land Between the Lakes National Recreation Area (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/6055272) | ODbL-1.0 | track |
| north-umpqua | USDA Forest Service (National Forest System trails) and Bureau of Land Management (Ground Transportation Linear Features) | [source page](https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0) | us-gov-public-domain | track |
| northern-colorado-trail | Kevin Silvernale, Northern Colorado Trail (publishes the route) | [source page](https://www.northerncoloradotrail.org/noco-trail-guides) | restricted | record only |
| northern-new-mexico-loop | Brett Tucker ("Blisterfree"), who publishes the route | [source page](https://simblissity.net/northern-nm-loop-mapset.shtml) | none-stated | record only |
| northville-placid | Adirondack Mountain Club; NY DEC (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/4286650) | ODbL-1.0 | track |
| oak-ridges | Oak Ridges Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/4287243) | ODbL-1.0 | track |
| ocean-to-lake | Florida Trail Association, Loxahatchee Chapter (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/7037710) | ODbL-1.0 | track |
| oregon-coast | Oregon Parks and Recreation Department (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/8310290) | ODbL-1.0 | track |
| oregon-desert | Oregon Natural Desert Association (ONDA) (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/10702483) | ODbL-1.0 | record only |
| ottawa-temiskaming-highland-trail | Nastawgan Trails Inc. (publishes the trail) | [source page](https://nastawgantrails.org/our-trails) | none-stated | record only |
| ouachita | Friends of the Ouachita Trail (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/3838499) | ODbL-1.0 | track |
| ozark-highlands | Ozark Highlands Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/10868744) | ODbL-1.0 | track |
| ozark-trail | Ozark Trail Association (publishes the trail); the ArcGIS item 'Ozark Trails Association' now answers 'Token Required' | [source page](https://www.openstreetmap.org/relation/16710911) | ODbL-1.0 | track |
| pacific-crest | Pacific Crest Trail Association (PCTA) | [source page](https://services5.arcgis.com/ZldHa25efPFpMmfB/ArcGIS/rest/services/PCTA_Centerline/FeatureServer/0) | CC-BY-4.0 | track |
| pacific-northwest | USDA Forest Service, Pacific Northwest Region (Region 6) | [source page](https://services1.arcgis.com/gGHDlz6USftL5Pau/arcgis/rest/services/Pacific_Northwest_National_Scenic_Trail/FeatureServer/0) | us-gov-public-domain | track |
| paumanok-path | Southampton Trails Preservation Society and Long Island Greenbelt Trail Conference (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/12900097) | ODbL-1.0 | track |
| pfiffner-traverse | Andrew Skurka (publishes the route) | [source page](https://andrewskurka.com/product/pfiffner-traverse-guide-maps/) | none-stated | record only |
| pinhoti | Pinhoti Trail Alliance (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/1642836) | ODbL-1.0 | track |
| powell-plateau-loop | Wilderness Press (publishes the route in the guidebook) | [source page](https://shop.adventurewithkeen.com/product/backpacking-arizona/) | none-stated | record only |
| prescott-circle | City of Prescott and Prescott National Forest (manage the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/4717133) | ODbL-1.0 | track |
| pukaskwa-coastal | Parks Canada (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/15361195) | ODbL-1.0 | track |
| quehanna | Keystone Trails Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/7236114) | ODbL-1.0 | track |
| rae-lakes-loop | National Park Service (publishes the loop; no open geometry found) | [source page](https://www.openstreetmap.org/relation/1710944) | ODbL-1.0 | track |
| rideau-trail | Rideau Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/7675635) | ODbL-1.0 | track |
| ring-the-peak | Friends of the Peak (publishes the trail and offers GPX tracks) | [source page](https://friendsofthepeak.org/ring-the-peak-2/) | none-stated | record only |
| river-to-river | River to River Trail Society (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/4645742) | ODbL-1.0 | track |
| route-in-between | Kevin "LarryBoy" DeVries (publishes the route) | [source page](http://www.lbhikes.com/p/a-complete-guide-to-deseret-hiking-route.html) | none-stated | record only |
| san-diego-trans-county-trail | Sea to Sea Trail Foundation (folded); current guide by Liz Thomas, Treeline Review | [source page](https://www.treelinereview.com/where-to-go/san-diego-trans-county-trail) | none-stated | record only |
| santa-fe-to-taos | Pam Neely and the Santa Fe to Taos Trail non-profit (publish the route) | [source page](https://santafetotaos.org/route/) | none-stated | record only |
| sawtooth-wilderness-high-route | Eric Poulin, who publishes the route | [source page](https://seekinglost.com/sawtooth-wilderness-high-route-8-day-solo-hike-aug-2017/) | none-stated | record only |
| sea-to-sea-route | Ron Strickland, with the overview published by Andrew Skurka | [source page](https://andrewskurka.com/adventures/sea-to-sea-route/overview/) | none-stated | record only |
| sentier-international-appalaches | Sentier international des Appalaches (Québec); IAT New Brunswick (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/9318808) | ODbL-1.0 | track |
| shawangunk-ridge-trail | New York-New Jersey Trail Conference (publishes the trail) | [source page](https://www.openstreetmap.org/relation/3934864) | ODbL-1.0 | track |
| sheltowee-trace | USDA Forest Service, Daniel Boone National Forest; Sheltowee Trace Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/12041542) | ODbL-1.0 | track |
| shenipsit-trail | Connecticut Forest and Park Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/11242812) | ODbL-1.0 | track |
| sierra-grand-traverse | John and Monica Chapman (publish the route) | [source page](https://www.mountaineers.org/books/books/sierra-grand-traverse-an-epic-route-across-the-range-of-light) | none-stated | record only |
| sierra-high-route | Steve Roper; Mountaineers Books publishes the route in its guidebook | [source page](https://www.mountaineers.org/books/books/sierra-high-route-2nd-edition-traversing-timberline-country) | none-stated | record only |
| sky-islands-traverse | Brett Tucker ("Blisterfree"), who publishes the route | [source page](http://simblissity.net/skit.shtml) | none-stated | record only |
| solitude-loop | USDA Forest Service (National Forest System Trails, Enterprise Data Warehouse) | [source page](https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0) | us-gov-public-domain | track |
| south-boundary | Parks Canada, Jasper National Park (publishes the trail; no open geometry found) | [source page](https://parks.canada.ca/pn-np/ab/jasper/activ/passez-stay/arrierepays-backcountry/sugg-sentiers_trip-ideas/south-boundary) | none-stated | record only |
| southeastern-serpentine-trail | Cam Honan, The Hiking Life (publishes the route) | [source page](https://thehikinglife.com/2016/07/southeastern-serpentine-trail/) | none-stated | record only |
| southern-sierra-high-route | Alan Dixon and Don Wilson (publish the route) | [source page](http://www.adventurealan.com/southern-sierra-high-route-soshr-guide/) | none-stated | record only |
| southwestern-horseshoe | Cam Honan, The Hiking Life (publishes the route) | [source page](https://thehikinglife.com/2019/03/southwestern-horseshoe/) | none-stated | record only |
| standing-stone | Standing Stone Trail Club (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/11360008) | ODbL-1.0 | track |
| stein-valley-traverse | BC Parks (Stein Valley Nlaka'pamux Heritage Park) (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/9983039) | ODbL-1.0 | track |
| sunapee-ragged-kearsarge | Sunapee-Ragged-Kearsarge Greenway Coalition (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/17943086) | ODbL-1.0 | track |
| sunshine-coast | Sunshine Coast Trail Society (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/7406716) | ODbL-1.0 | track |
| superior-hiking | North Country Trail Association (hosts the Superior Hiking Trail Association's track) | [source page](https://www.openstreetmap.org/relation/1612587) | ODbL-1.0 | track |
| susquehannock | Susquehannock Trail Club (publishes the loop; no open geometry found) | [source page](https://www.openstreetmap.org/relation/13079897) | ODbL-1.0 | track |
| sycamore-canyon-az | Wilderness Press (publishes the route in the guidebook) | [source page](https://shop.adventurewithkeen.com/product/backpacking-arizona/) | none-stated | record only |
| tahoe-rim | Tahoe Rim Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/3094865) | ODbL-1.0 | track |
| tahoe-yosemite-trail | Wilderness Press (publishes the route in the guidebook) | [source page](https://shop.adventurewithkeen.com/wilderness-press/) | none-stated | record only |
| teton-crest | National Park Service; USFS (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/3895101) | ODbL-1.0 | record only |
| teton-crest-route | Wilderness Mindset (publishes the route) | [source page](https://wildernessmindset.com/product/teton-crest-route-map-pack/) | none-stated | record only |
| teton-range-traverse | Cam Honan, The Hiking Life (publishes the route) | [source page](https://thehikinglife.com/2017/07/teton-range-traverse/) | none-stated | record only |
| teton-wilderness-loop | Wilderness Press (publishes the route in the guidebook) | [source page](https://shop.adventurewithkeen.com/product/backpacking-wyoming/) | none-stated | record only |
| thames-valley-trail | Thames Valley Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/3444520) | ODbL-1.0 | track |
| thorofare-and-south-boundary-trail | National Park Service (public Trails dataset) | [source page](https://mapservices.nps.gov/arcgis/rest/services/NationalDatasets/NPS_Public_Trails_Geographic/FeatureServer/0) | us-gov-public-domain | track |
| timberline | USDA Forest Service, Mount Hood National Forest | [source page](https://www.openstreetmap.org/relation/7641482) | ODbL-1.0 | track |
| toiyabe-crest | USDA Forest Service, National Forest System trails | [source page](https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0) | us-gov-public-domain | track |
| tonto-trail | National Park Service, Grand Canyon National Park (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/2836546) | ODbL-1.0 | track |
| trans-adirondack-route | Erik Schlimmer (publishes the route) | [source page](https://erikschlimmer.com/books-sale-/) | none-stated | record only |
| traversee-charlevoix | Traversée de Charlevoix (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/8082269) | ODbL-1.0 | track |
| tuscarora | Potomac Appalachian Trail Club (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/10449263) | ODbL-1.0 | track |
| uinta-highline | USDA Forest Service (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/13716825) | ODbL-1.0 | track |
| vagabond-loop | Ryan "Dirtmonger" Sylva, who publishes the route | [source page](https://www.freedirtmonger.com/p/vagabond-loop-four-corners-connection-1.html) | none-stated | record only |
| vancouver-island | Vancouver Island Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/12038457) | ODbL-1.0 | track |
| vancouver-island-backbone | Philip Stone, Alpine Pacific Images (publishes the route) | [source page](https://www.wildisle.ca/backbone/index.html) | none-stated | record only |
| warrior-trail | Warrior Trail Association (publishes the trail; no site of its own found, the Association is on Facebook) | [source page](https://visitgreene.org/?p=1265) | none-stated | record only |
| wasatch-traverse | Liz Thomas (publishes the route) | [source page](https://www.eathomas.com/other-long-trails/wasatchoverview) | none-stated | record only |
| waskahegan | Waskahegan Trail Association (publishes the trail) | [source page](https://waskahegantrail.ca/about-2) | none-stated | record only |
| washington-coast-trail | Lauren Lake, PacificCoastalTrail blog (publishes the route) | [source page](https://pacificcoastaltrail.wordpress.com/2022/03/23/itinerary-washington-coast/) | CC-BY-4.0 | track |
| west-coast-trail | Parks Canada (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/6955341) | ODbL-1.0 | track |
| western-uplands | Ontario Parks (Algonquin Provincial Park) (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/11851825) | ODbL-1.0 | track |
| wind-river-high-route-dixon-wilson | Alan Dixon and Don Wilson (publish the route) | [source page](https://www.adventurealan.com/wind-river-high-route/) | none-stated | record only |
| wind-river-high-route-skurka | Andrew Skurka (publishes the route) | [source page](https://andrewskurka.com/product/wind-river-high-route-guide/) | none-stated | record only |
| wonderland | National Park Service (Mount Rainier National Park) publishes the trail; the NPS Public Trails layer holds only part of the loop | [source page](https://www.openstreetmap.org/relation/4111743) | ODbL-1.0 | track |
| wyoming-range | U.S. Forest Service, Bridger-Teton National Forest (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/13395352) | ODbL-1.0 | track |
| yosemite-high-route | Andrew Skurka (publishes the route) | [source page](https://andrewskurka.com/product/yosemite-high-route-guide/) | none-stated | record only |
