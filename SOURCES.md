# Sources

Each trail's record (`<id>/trail.toml`) names its source, the page to ask for the line, and the terms that apply. This file collects the distinct terms, the sentence that states them, the page they were read on, and the date read. Dates read: records were first read on 2026-11-08; the licence pages below were read again on 2026-11-09; 40 records were added and read on 2026-11-10.

A line is included in this repository only when its source's terms allow redistribution. Where they do not, the trail is a record only and `source.line_absent_reason` in its record says why.

## OpenStreetMap (ODbL-1.0)

Used by: 76 trails with an included line, and part of the Colorado Trail line (about 38 km; the rest is United States Forest Service data). Also named as the recorded source for 8 record-only trails, where no line was downloaded or none was usable. Five more records added on 2026-11-10 have no OpenStreetMap relation at all and name no source licence.

Quoted terms: "You are free to copy, distribute, transmit and adapt our data, as long as you credit OpenStreetMap and its contributors."

Page: https://www.openstreetmap.org/copyright (read 2026-11-09). Full text: LICENSES/ODbL-1.0.txt. Credit required: "© OpenStreetMap contributors". Adapted lines stay under the ODbL.

## United States federal agencies (public domain)

Publishers: National Park Service, USDA Forest Service and Bureau of Land Management services named in each record. Used by: 6 trails with an included line (Appalachian, Colorado Trail in part, Natchez Trace, New England, Pacific Northwest, Potomac Heritage), and named in 4 record-only records (Iditarod, Nez Perce, Overmountain Victory, Timberline).

Quoted terms: "Data and content created by government employees within the scope of their employment are not subject to domestic copyright protection under 17 U.S.C. 105."

Page: https://irma.nps.gov/DataStore/Reference/Profile/2311077 (read 2026-11-09). United States federal government work is public domain in the United States under 17 U.S.C. 105. Two included lines were produced with partner associations (Appalachian and New England); the partners' share is not separately licensed in those services, and is noted in the records.

## Pacific Crest Trail Association (CC-BY-4.0)

Used by: 1 trail (Pacific Crest).

Quoted terms: "All of the data accessed through this page are licensed under the Creative Commons Attribution 4.0 International License."

Page: https://www.pcta.org/discover-the-trail/maps/pct-data/ (read 2026-11-09). Full text: LICENSES/CC-BY-4.0.txt. Credit required: Pacific Crest Trail Association.

## Continental Divide Trail Coalition (CC-BY, version not stated)

Used by: 1 trail (Continental Divide).

Quoted terms: the source item's licence field reads "CC BY" (no version stated).

Page: https://services8.arcgis.com/WyuHwdftppQLa5KO/arcgis/rest/services/Continental_Divide_Trail_2/FeatureServer/0 (read 2026-11-09). Treated here as Creative Commons Attribution, with credit to the Continental Divide Trail Coalition. The version should be confirmed with the Coalition before a use that needs a named version.

## Publishers with no stated licence (no line included)

Used by: 2 records, none with an included line: California Coastal Commission with the Coastal Trails Alliance; Arizona State Parks (Great Western, Arizona part only).

Terms found: no licence stated on the items, and no licence found on the publishers' pages when read on 2026-11-09. The items carry disclaimers only. A disclaimer is not a licence, so these publishers' lines are not redistributed here. Each record's `source.url` is the page to ask for the line, and `source.line_absent_reason` states this reason. Nine more records that were listed here had a line added from OpenStreetMap on 2026-11-09; their publishers' own lines are still not used, and each record keeps the publisher and its page in `source.publisher` and `source.publisher_url`.

## Trans Canada Trail (CC-BY-NC-ND-4.0)

Used by: 1 record (The Great Trail), record only.

Terms: Creative Commons Attribution-NonCommercial-NoDerivatives 4.0, as stated on the source item (read 2026-11-09; source page in the record). Those terms do not allow commercial use or derivatives, so no line from this source is included.

## Person-defined routes (creator's own pages, no line included)

Used by: the person-defined routes (`kind = "route"`). Each record names its creator and the guide the route is got from, in its `[[guide]]` tables, and `route.line_policy` says whether the creator shares the line.

Terms found: none. No route creator's page read on 2026-11-10 states a licence for the route's line. The record says where the line may be got from the creator, and `source.line_absent_reason` says why no line is included here: the route is sold as a guide, the creator withholds the line, the question is not settled, or the creator offers a download with no licence that allows passing it on. Where OpenStreetMap carries the route as a route relation and the creator publishes the line freely, the line comes from OpenStreetMap under the terms above.

Page: the creator's or publisher's own page for the guide, given in each record's first `[[guide]]` and quoted in `route.creator_words_url` where the creator's words are quoted.

## Every record's source


| Trail | Publisher | Page | Licence | Included |
| --- | --- | --- | --- | --- |
| alexander-mackenzie | Province of British Columbia (BC Geographical Names record; no open geometry found) | [source page](https://www.openstreetmap.org/relation/2654551) | ODbL-1.0 | line |
| allegheny-trail | West Virginia Scenic Trails Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/1772789) | ODbL-1.0 | line |
| appalachian | National Park Service Appalachian NST and Appalachian Trail Conservancy | [source page](https://services1.arcgis.com/fBc8EJBxQRMcHlei/ArcGIS/rest/services/ANST_Centerline/FeatureServer/0) | us-gov-public-domain | line |
| arizona | Arizona Trail Association (AZTA) | [source page](https://www.openstreetmap.org/relation/2804113) | ODbL-1.0 | line |
| avon | Avon Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/3442182) | ODbL-1.0 | line |
| backbone | National Park Service, Santa Monica Mountains NRA | [source page](https://mapservices.nps.gov/arcgis/rest/services/NationalDatasets/NPS_Public_Trails_Geographic/FeatureServer/0) | ODbL-1.0 | line |
| baker | Rachel Carson Trails Conservancy (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/9078832) | ODbL-1.0 | line |
| bartram | Blue Ridge Bartram Trail Conservancy (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/9955138) | ODbL-1.0 | line |
| batona | Batona Hiking Club (publishes the trail with the New Jersey State Park Service; no open geometry found) | [source page](https://www.openstreetmap.org/relation/4129027) | ODbL-1.0 | line |
| bay-circuit | Appalachian Mountain Club (leads the trail's partners; no open geometry found) | [source page](https://www.openstreetmap.org/relation/12779888) | ODbL-1.0 | line |
| benton-mackaye | Benton MacKaye Trail Association (publishes the trail); the only other line, a Blue Ridge Forever ArcGIS item (2017), is restricted | [source page](https://www.openstreetmap.org/relation/1675439) | ODbL-1.0 | line |
| border-route | Border Route Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/5996078) | ODbL-1.0 | line |
| brazeau-loop | Parks Canada, Jasper National Park (publishes the trail) | [source page](https://parks.canada.ca/pn-np/ab/jasper/activ/passez-stay/arrierepays-backcountry/sugg-sentiers_trip-ideas) | none-stated | record only |
| bruce-trail | Bruce Trail Conservancy (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/3375262) | ODbL-1.0 | line |
| buckeye | Buckeye Trail Association (publishes the loop); the Ohio DNR MapServer requires a token | [source page](https://www.openstreetmap.org/relation/1738661) | ODbL-1.0 | line |
| california-coastal | California Coastal Commission; Coastal Trails Alliance | [source page](https://services9.arcgis.com/wwVnNW92ZHUIr0V0/arcgis/rest/services/California_Coastal_Trail_April_2021/FeatureServer) | none-stated | record only |
| canol | Northwest Territories Parks (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/13591414) | ODbL-1.0 | line |
| centennial-sd | USDA Forest Service, Black Hills National Forest (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/7330792) | ODbL-1.0 | line |
| chesapeake-ohio-canal | National Park Service, Chesapeake and Ohio Canal National Historical Park (publishes the trail; no open geometry found) | [source page](https://www.nps.gov/choh/planyourvisit/hiking.htm) | none-stated | record only |
| cohos | Cohos Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/14765821) | ODbL-1.0 | line |
| colorado-trail | USDA Forest Service (EDW National Forest System trails), with OpenStreetMap where the Forest Service publishes no segment | [source page](https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0) | us-gov-public-domain | line |
| continental-divide | Continental Divide Trail Coalition (CDTC) | [source page](https://services8.arcgis.com/WyuHwdftppQLa5KO/arcgis/rest/services/Continental_Divide_Trail_2/FeatureServer/0) | CC-BY | line |
| corvallis-to-the-sea | Corvallis-to-the-Sea Trail (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/14706511) | ODbL-1.0 | line |
| cranberry-lake-50 | Cranberry Lake 50 volunteer trail crew (publishes the loop; no open geometry found) | [source page](https://www.openstreetmap.org/relation/7580730) | ODbL-1.0 | line |
| cross-vermont | Cross Vermont Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/2750828) | ODbL-1.0 | line |
| cumberland-trail | Tennessee State Parks (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/13968933) | ODbL-1.0 | line |
| donut-hole | Keystone Trails Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/13780803) | ODbL-1.0 | line |
| east-coast-trail | East Coast Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/2199386) | ODbL-1.0 | line |
| finger-lakes | Finger Lakes Trail Conference (publishes the trail; the North Country Trail Association hosts its line as 'agol_flt') | [source page](https://www.openstreetmap.org/relation/12725656) | ODbL-1.0 | line |
| florida | Florida Trail Association with the USDA Forest Service Southern Region | [source page](https://www.openstreetmap.org/relation/14480287) | ODbL-1.0 | line |
| foothills | Foothills Trail Conservancy (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/4572989) | ODbL-1.0 | line |
| fundy-footpath | Fundy Footpath Inc. (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/4077806) | ODbL-1.0 | record only |
| ganaraska | Ganaraska Hiking Trail Association (publishes the trail; no open line found) | [source page](https://www.openstreetmap.org/relation/3696751) | ODbL-1.0 | line |
| grand-enchantment | simBLISSity Ultralight Designs (publishes the route, mapset and guidebook; no open geometry) | [source page](https://www.openstreetmap.org/relation/4485206) | ODbL-1.0 | record only |
| great-divide-trail | Great Divide Trail Association (account 'GreatDivideTrail', public map) | [source page](https://www.openstreetmap.org/relation/8139599) | ODbL-1.0 | line |
| great-eastern | Great Eastern Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/11364314) | ODbL-1.0 | record only |
| great-trail | Trans Canada Trail (account 'mappingtct') | [source page](https://services2.arcgis.com/rDdKyyk7uludsLpI/arcgis/rest/services/ExploreTheMap_EN_2022/FeatureServer/15) | CC-BY-NC-ND-4.0 | record only |
| great-western | Arizona State Parks for the Arizona part; no whole-trail publisher found | [source page](https://services2.arcgis.com/gdcQ6sUWKP8qwBmV/arcgis/rest/services/GWT_Alignment_Public_View/FeatureServer/0) | none-stated | record only |
| high-sierra | National Park Service, Sequoia and Kings Canyon National Parks (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/1714300) | ODbL-1.0 | line |
| highlands | New York-New Jersey Trail Conference (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/6335422) | ODbL-1.0 | line |
| horse-shoe | Horse-Shoe Trail Conservancy (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/1596895) | ODbL-1.0 | line |
| ice-age | Ice Age Trail Alliance for the National Park Service | [source page](https://www.openstreetmap.org/relation/2381423) | ODbL-1.0 | line |
| idaho-centennial | Idaho Department of Parks and Recreation | [source page](https://www.openstreetmap.org/relation/10758083) | ODbL-1.0 | line |
| iditarod | Bureau of Land Management | [source page](https://services1.arcgis.com/fBc8EJBxQRMcHlei/arcgis/rest/services/Iditarod_National_Historic_Trail_BLM_Official_Temp/FeatureServer/0) | us-gov-public-domain | record only |
| island-walk | Island Walk PEI Inc. (publishes the route; no open geometry found) | [source page](https://www.openstreetmap.org/relation/12307947) | ODbL-1.0 | line |
| john-muir | No single publisher: NPS Yosemite and Sequoia-Kings Canyon, USFS Inyo and Sierra National Forests | [source page](https://mapservices.nps.gov/arcgis/rest/services/NationalDatasets/NPS_Public_Trails_Geographic/FeatureServer/0) | ODbL-1.0 | line |
| kekekabic | Kekekabic Trail Club; USFS (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/10831114) | ODbL-1.0 | record only |
| la-cloche | Ontario Parks (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/14141941) | ODbL-1.0 | line |
| laurel-highlands | Keystone Trails Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/7192246) | ODbL-1.0 | line |
| lone-star | Lone Star Hiking Trail Club (publishes the trail; no open line found) | [source page](https://www.openstreetmap.org/relation/7014936) | ODbL-1.0 | line |
| long-path | New York-New Jersey Trail Conference (an ArcGIS item 'Long Path' under an ArcGIS account, 2025; provenance not confirmed) | [source page](https://www.openstreetmap.org/relation/919642) | ODbL-1.0 | line |
| long-trail | Green Mountain Club (publishes the trail); its ArcGIS 'TRAIL_MASTER' line is restricted | [source page](https://www.openstreetmap.org/relation/391736) | ODbL-1.0 | line |
| loyalsock | Alpine Club of Williamsport (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/3134579) | ODbL-1.0 | line |
| maah-daah-hey | USDA Forest Service, Dakota Prairie Grasslands (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/11562289) | ODbL-1.0 | line |
| mason-dixon | Mason-Dixon Trail System (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/1820324) | ODbL-1.0 | line |
| mattabesett | Connecticut Forest and Park Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/2971739) | ODbL-1.0 | line |
| metacomet-monadnock | Appalachian Mountain Club (publishes the New Hampshire part); the National Park Service carries the Metacomet section in the New England NST line | [source page](https://www.openstreetmap.org/relation/2317544) | ODbL-1.0 | line |
| mid-state | Mid State Trail Association (an ArcGIS item under an ArcGIS account, 2019; provenance not confirmed) | [source page](https://www.openstreetmap.org/relation/1022044) | ODbL-1.0 | line |
| midstate-ma | Midstate Trail Committee (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/5503042) | ODbL-1.0 | line |
| monadnock-sunapee | Monadnock-Sunapee Greenway Trail Club (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/3888871) | ODbL-1.0 | line |
| mountains-to-sea | North Carolina Division of Parks and Recreation; Friends of the Mountains-to-Sea Trail (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/1395404) | ODbL-1.0 | line |
| natchez-trace | National Park Service, Natchez Trace Parkway | [source page](https://services1.arcgis.com/fBc8EJBxQRMcHlei/arcgis/rest/services/NATT_TRANS_NSTTrail/FeatureServer/0) | us-gov-public-domain | line |
| new-england | National Park Service with the Connecticut Forest & Park Association and the Appalachian Mountain Club | [source page](https://services1.arcgis.com/fBc8EJBxQRMcHlei/ArcGIS/rest/services/NEEN_BND_NationalScenicTrailCenterline_ln/FeatureServer/0) | us-gov-public-domain | line |
| nez-perce | USDA Forest Service Region 1 | [source page](https://services1.arcgis.com/gGHDlz6USftL5Pau/arcgis/rest/services/R01_NezPerceNeeMePoo_NationalHistoricTrail_Centerline/FeatureServer/0) | us-gov-public-domain | record only |
| north-boundary | Parks Canada, Jasper National Park (publishes the trail; no open geometry found) | [source page](https://parks.canada.ca/pn-np/ab/jasper/activ/passez-stay/arrierepays-backcountry/sugg-sentiers_trip-ideas/north-boundary) | none-stated | record only |
| north-country | North Country Trail Association for the National Park Service | [source page](https://www.openstreetmap.org/relation/11140515) | ODbL-1.0 | line |
| north-south | Rhode Island Department of Environmental Management (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/11102215) | ODbL-1.0 | line |
| northville-placid | Adirondack Mountain Club; NY DEC (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/4286650) | ODbL-1.0 | line |
| oak-ridges | Oak Ridges Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/4287243) | ODbL-1.0 | line |
| oregon-coast | Oregon Parks and Recreation Department (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/8310290) | ODbL-1.0 | line |
| oregon-desert | Oregon Natural Desert Association (ONDA) (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/10702483) | ODbL-1.0 | record only |
| ouachita | Friends of the Ouachita Trail (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/3838499) | ODbL-1.0 | line |
| overmountain-victory | National Park Service | [source page](https://services1.arcgis.com/fBc8EJBxQRMcHlei/arcgis/rest/services/Overmountain_Victory_National_Historic_Trail_Official_Temp/FeatureServer/0) | us-gov-public-domain | record only |
| ozark-highlands | Ozark Highlands Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/10868744) | ODbL-1.0 | line |
| ozark-trail | Ozark Trail Association (publishes the trail); the ArcGIS item 'Ozark Trails Association' now answers 'Token Required' | [source page](https://www.openstreetmap.org/relation/16710911) | ODbL-1.0 | line |
| pacific-crest | Pacific Crest Trail Association (PCTA) | [source page](https://services5.arcgis.com/ZldHa25efPFpMmfB/ArcGIS/rest/services/PCTA_Centerline/FeatureServer/0) | CC-BY-4.0 | line |
| pacific-northwest | USDA Forest Service, Pacific Northwest Region (Region 6) | [source page](https://services1.arcgis.com/gGHDlz6USftL5Pau/arcgis/rest/services/Pacific_Northwest_National_Scenic_Trail/FeatureServer/0) | us-gov-public-domain | line |
| palmetto | Palmetto Conservation Foundation (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/5385288) | ODbL-1.0 | line |
| pinhoti | Pinhoti Trail Alliance (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/1642836) | ODbL-1.0 | line |
| potomac-heritage | National Park Service, Potomac Heritage NST | [source page](https://services1.arcgis.com/fBc8EJBxQRMcHlei/arcgis/rest/services/POHE_Trail_Centerline_(Public_NPMap_Builder)_/FeatureServer/0) | us-gov-public-domain | line |
| pukaskwa-coastal | Parks Canada (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/15361195) | ODbL-1.0 | record only |
| quehanna | Keystone Trails Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/7236114) | ODbL-1.0 | line |
| rideau-trail | Rideau Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/7675635) | ODbL-1.0 | line |
| river-to-river | River to River Trail Society (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/4645742) | ODbL-1.0 | line |
| sentier-international-appalaches | Sentier international des Appalaches (Québec); IAT New Brunswick (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/9318808) | ODbL-1.0 | line |
| sentier-national | Fédération québécoise de la marche (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/7300742) | ODbL-1.0 | line |
| sheltowee-trace | USDA Forest Service, Daniel Boone National Forest; Sheltowee Trace Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/12041542) | ODbL-1.0 | line |
| south-boundary | Parks Canada, Jasper National Park (publishes the trail; no open geometry found) | [source page](https://parks.canada.ca/pn-np/ab/jasper/activ/passez-stay/arrierepays-backcountry/sugg-sentiers_trip-ideas/south-boundary) | none-stated | record only |
| standing-stone | Standing Stone Trail Club (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/11360008) | ODbL-1.0 | line |
| sunapee-ragged-kearsarge | Sunapee-Ragged-Kearsarge Greenway Coalition (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/17943086) | ODbL-1.0 | line |
| sunshine-coast | Sunshine Coast Trail Society (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/7406716) | ODbL-1.0 | line |
| superior-hiking | North Country Trail Association (hosts the Superior Hiking Trail Association's line) | [source page](https://www.openstreetmap.org/relation/1612587) | ODbL-1.0 | line |
| susquehannock | Susquehannock Trail Club (publishes the loop; no open geometry found) | [source page](https://www.openstreetmap.org/relation/13079897) | ODbL-1.0 | line |
| tahoe-rim | Tahoe Rim Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/3094865) | ODbL-1.0 | line |
| teton-crest | National Park Service; USFS (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/3895101) | ODbL-1.0 | record only |
| timberline | USDA Forest Service, Mount Hood National Forest | [source page](https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0) | us-gov-public-domain | record only |
| traversee-charlevoix | Traversée de Charlevoix (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/8082269) | ODbL-1.0 | line |
| tuscarora | Potomac Appalachian Trail Club (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/10449263) | ODbL-1.0 | line |
| uinta-highline | USDA Forest Service (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/13716825) | ODbL-1.0 | line |
| vancouver-island | Vancouver Island Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/12038457) | ODbL-1.0 | line |
| voyageur | Voyageur Trail Association (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/18529238) | ODbL-1.0 | line |
| waskahegan | Waskahegan Trail Association (publishes the trail) | [source page](https://waskahegantrail.ca/about-2) | none-stated | record only |
| west-coast-trail | Parks Canada (publishes the trail; no open geometry found) | [source page](https://www.openstreetmap.org/relation/6955341) | ODbL-1.0 | record only |
| wonderland | National Park Service (Mount Rainier National Park) publishes the trail; the NPS Public Trails layer holds only part of the loop | [source page](https://www.openstreetmap.org/relation/4111743) | ODbL-1.0 | line |
