# Long Hikes

A public dataset of long-distance hiking trails in the United States and Canada: one directory per trail, with a written record, the trail's track where it may be shared, and the trail's logo where one exists. First compiled for the PHRP route planner. The site built from it is at https://longhikes.org.

## What this is, and what it is not

This is a dataset, not a guide. Each record says what the trail is, how long it is, where its track came from, and under what terms that track may be used. It is not a navigation product: tracks vary in quality, some trails are unfinished, and some records have no track at all. Check a trail's own record before using its track.

The counts at this release:

<!-- BEGIN COUNTS -->

225 trails, 124 with a track and 101 with no track included. Of these, 78 are routes: 2 with a track and 76 without.

<!-- END COUNTS -->

## Inclusion rule

A long trail here is a named, continuous walking route, or a named loop, of at least 50 miles (80 km), in the United States or Canada: either a trail that a land agency or a trail association designates, maintains and publishes as one trail, or a route, as described below. The floor is 50 miles because that is about what multi-day wilderness backpacking takes. A trail under 50 miles is listed only for a stated reason, given below.

A trail's length is the end-to-end length of its canonical path: one walk from one end to the other, with one branch taken at a split, no side trails and no system total. A loop reached by a stem is shown at the published figure, which walks the stem both ways, and its `length_note` says which stretch is walked out and back. The 50-mile floor is tested on the length with nothing counted twice, so an out-and-back is judged one way; that figure is never shown as a trail's length. A trail must also be walkable from one end to the other today. A trail published in separate pieces, or with gaps that have no way across, is not listed, and goes in `left-out.toml`. Road links that the holder publishes as the way through count as walkable, and so does evidence that people have walked it end to end. A ferry, shuttle or bus link across water or a closed stretch, named by the holder or the route's author as the way through, does not rule a trail out: the record says how each such link is made, and the track has a gap there, with no line drawn across. This is a judgement the maintainer makes case by case, not a mechanical test. A trail that can be walked through but is partly unbuilt is listed: its length is the holder's end-to-end route, and the built length is stated beside it. A larger figure that the holder publishes, such as a system total or a planned total, is kept as a separate, labelled fact.

Every trail or route needs a published length, and a route with no stated length is not listed. The length rule is at least 50 miles (80 km). A trail or route under 50 miles (80 km) is listed only when it is still reasonably long and at least one of these is true: it has real cross-country travel; it genuinely takes a fit, experienced party five or more days because the ground is hard: there is no trail, or the going is rough, unmaintained or needs route finding, with fords or thick brush (the number of days a managing body, an author or a guidebook prints does not decide this, and an itinerary that spreads a walk on ordinary built trail over five or more days at an easy pace does not count); or it is very well known and popular, as the Rae Lakes Loop is. Each such record gives its reason in `short_reason`. Being close to 50 miles is never a reason. The days never replace a published length. A trail with its own name and its own published length is listed even where it lies on a longer listed trail, as the John Muir Trail lies on the Pacific Crest Trail. A guidebook's cut of a longer trail is not listed. The climbing rule is that nothing harder than Class 3 may be required, apart from a few short Class 4 scrambles. A route that needs a rope, a belay or rock-climbing skill is not listed, unless that section is optional and the record says so.

Not listed: paths made mainly for cycling, such as gravel rail trails and canal towpaths, and historic trails that are mainly driving routes with short walkable pieces.

A United States National Scenic Trail is listed when it can be walked from one end to the other. The Natchez Trace and the Potomac Heritage National Scenic Trails cannot be, and are in `left-out.toml`. Other trails are listed when they meet the rule above.

Routes are listed too, at the same 50-mile floor. A route is a trail that a hiker worked out and published: a high route, a traverse, or a loop of linked trails. Its record names the author and says where the route is got from: the guidebook, map set or page, and whether it is free or sold. Whether a track is included follows the author's choice:

- The author sells the route, or chooses not to publish a track: the record has no track. No track is included from any source, OpenStreetMap included.
- The author publishes the track freely: a track is included only where the author's terms allow passing it on, or where OpenStreetMap carries the route as a route relation. Otherwise the record points to the author's own download.
- Not settled: the record has no track until it is.

An author who wants a record changed or removed can ask; see NOTICE.md.

A trail may be listed with no track included, when no track for it may be shared. The record says why.

## Trails

<!-- BEGIN TRAIL TABLE -->

| ID | Trail | Country | States / provinces | Length (km) | Track | Licence |
| --- | --- | --- | --- | ---: | --- | --- |
| akshayuk-pass | Akshayuk Pass | CA | NU | 97 | no | none-stated |
| alexander-mackenzie | Alexander MacKenzie Heritage Trail | CA | BC | 420 | yes | ODbL-1.0 |
| allegheny-trail | Allegheny Trail | US | WV | 509 | yes | ODbL-1.0 |
| alpine-trail-7 | Alpine Trail #7 | US | MT | 88 | yes | us-gov-public-domain |
| american-discovery-trail | American Discovery Trail | US | DE, MD, DC, WV, OH, KY, IN, IL, IA, MO, KS, NE, CO, UT, NV, CA | 8060 | yes | ODbL-1.0 |
| appalachian | Appalachian National Scenic Trail | US | GA, NC, TN, VA, WV, MD, PA, NJ, NY, CT, MA, VT, NH, ME | 3537 | yes | us-gov-public-domain |
| arizona | Arizona National Scenic Trail | US | AZ | 1287 | yes | ODbL-1.0 |
| avon | Avon Trail | CA | ON | 130 | yes | ODbL-1.0 |
| backbone | Backbone Trail | US | CA | 108 | yes | ODbL-1.0 |
| baker | Baker Trail | US | PA | 216 | yes | ODbL-1.0 |
| bartram | Bartram Trail | US | GA, NC | 180 | yes | us-gov-public-domain |
| batona | Batona Trail | US | NJ | 80 | yes | ODbL-1.0 |
| bay-circuit | Bay Circuit Trail | US | MA | 370 | yes | ODbL-1.0 |
| bayou-state-trail | Bayou State Trail | US | LA | 772 | no | none-stated |
| benton-mackaye | Benton MacKaye Trail | US | GA, TN, NC | 463 | yes | ODbL-1.0 |
| black-canyon | Black Canyon National Recreation Trail | US | AZ | 129 | yes | us-gov-public-domain |
| border-route | Border Route Trail | US | MN | 105 | yes | ODbL-1.0 |
| boreal-trail | Boreal Trail | CA | SK | 135 | no | none-stated |
| boundary-trail-mount-st-helens | Boundary Trail #1 (Mount St. Helens) | US | WA | 86 | yes | ODbL-1.0 |
| boundary-trail-pasayten | Boundary Trail (Pasayten Wilderness) | US | WA | 117 | yes | ODbL-1.0 |
| brazeau-loop | Brazeau Loop | CA | AB | 81 | no | none-stated |
| bristol-hills-trail | Bristol Hills Trail | US | NY | 89 | yes | ODbL-1.0 |
| bruce-trail | Bruce Trail | CA | ON | 890 | yes | ODbL-1.0 |
| buckeye | Buckeye Trail | US | OH | 2250 | yes | ODbL-1.0 |
| california-coastal | California Coastal Trail | US | CA | 1931 | yes | CC-BY-4.0 |
| canol | Canol Heritage Trail | CA | NT | 371 | yes | ODbL-1.0 |
| centennial-sd | Centennial Trail | US | SD | 179 | yes | ODbL-1.0 |
| cohos | Cohos Trail | US | NH | 270 | yes | ODbL-1.0 |
| colorado-trail | Colorado Trail | US | CO | 782 | yes | ODbL-1.0 |
| conestoga-trail | Conestoga Trail | US | PA | 103 | yes | ODbL-1.0 |
| conservation-trail | Conservation Trail | US | NY | 285 | no | none-stated |
| continental-divide | Continental Divide National Scenic Trail | US | NM, CO, WY, ID, MT | 4989 | yes | CC-BY |
| corvallis-to-the-sea | Corvallis-to-the-Sea Trail | US | OR | 97 | yes | ODbL-1.0 |
| cottonwood-trail | Cottonwood Trail | CA | YT | 85 | no | none-stated |
| cranberry-lake-50 | Cranberry Lake 50 | US | NY | 80 | yes | ODbL-1.0 |
| cross-vermont | Cross Vermont Trail | US | VT | 145 | yes | ODbL-1.0 |
| dan-zhur-donjek | Dän Zhùr (Donjek) Route | CA | YT | 110 | no | none-stated |
| donut-hole | Donut Hole Trail | US | PA | 152 | yes | ODbL-1.0 |
| east-beach-trail | East Beach Trail (Naikoon) | CA | BC | 90 | no | none-stated |
| east-coast-trail | East Coast Trail (Newfoundland) | CA | NL | 336 | yes | ODbL-1.0 |
| finger-lakes | Finger Lakes Trail | US | NY | 933 | yes | ODbL-1.0 |
| florida | Florida National Scenic Trail | US | FL | 1818 | yes | ODbL-1.0 |
| foothills | Foothills Trail | US | SC, NC | 122 | yes | ODbL-1.0 |
| fremont | Fremont National Recreation Trail | US | OR | 216 | yes | us-gov-public-domain |
| ganaraska | Ganaraska Hiking Trail | CA | ON | 500 | yes | ODbL-1.0 |
| general-george-crook | General George Crook National Recreation Trail | US | AZ | 222 | yes | us-gov-public-domain |
| gila-centennial-loop | Gila Wilderness Centennial Loop | US | NM | 161 | no | none-stated |
| grand-sawtooth-loop | Grand Sawtooth Loop | US | ID | 113 | no | none-stated |
| grand-valley-trail | Grand Valley Trail | CA | ON | 240 | yes | ODbL-1.0 |
| great-divide-trail | Great Divide Trail | CA | AB, BC | 1130 | yes | ODbL-1.0 |
| great-eastern | Great Eastern Trail | US | AL, GA, TN, KY, VA, WV, MD, PA, NY | 2897 | yes | ODbL-1.0 |
| guadalupe-ridge-trail | Guadalupe Ridge Trail | US | TX, NM | 161 | no | none-stated |
| high-country-pathway | High Country Pathway | US | MI | 132 | yes | ODbL-1.0 |
| high-sierra | High Sierra Trail | US | CA | 116 | yes | us-gov-public-domain |
| highlands | Highlands Trail | US | NJ, NY, PA, CT | 290 | yes | ODbL-1.0 |
| highline | Highline National Recreation Trail | US | AZ | 89 | yes | ODbL-1.0 |
| hoosier-heritage-trail | Hoosier Heritage Trail | US | IN | 259 | yes | stated-permission |
| horse-shoe | Horse-Shoe Trail | US | PA | 225 | yes | ODbL-1.0 |
| iat-newfoundland-labrador | International Appalachian Trail, Newfoundland and Labrador | CA | NL | 750 | yes | ODbL-1.0 |
| ice-age | Ice Age National Scenic Trail | US | WI | 1931 | yes | ODbL-1.0 |
| idaho-centennial | Idaho Centennial Trail | US | ID | 1448 | yes | ODbL-1.0 |
| international-appalachian-trail-maine | International Appalachian Trail, Maine section | US | ME | 222 | no | none-stated |
| island-walk | The Island Walk | CA | PE | 700 | yes | ODbL-1.0 |
| itijjagiaq-trail | Itijjagiaq Trail | CA | NU | 120 | no | none-stated |
| john-muir | John Muir Trail | US | CA | 340 | yes | ODbL-1.0 |
| knobstone | Knobstone Hiking Trail | US | IN | 257 | yes | ODbL-1.0 |
| koroc-palmer-loop | Koroc River and Palmer River Loop (Boucle des rivières Koroc et Palmer) | CA | QC, NL | 90 | no | none-stated |
| la-cloche | La Cloche Silhouette Trail | CA | ON | 80 | yes | ODbL-1.0 |
| laurel-highlands | Laurel Highlands Hiking Trail | US | PA | 113 | yes | ODbL-1.0 |
| lone-star | Lone Star Hiking Trail | US | TX | 155 | yes | ODbL-1.0 |
| long-path | Long Path | US | NJ, NY | 576 | yes | ODbL-1.0 |
| long-trail | Long Trail (Vermont) | US | VT | 438 | yes | ODbL-1.0 |
| lost-coast | Lost Coast Trail | US | CA | 80 | yes | ODbL-1.0 |
| loyalsock | Loyalsock Trail | US | PA | 95 | yes | ODbL-1.0 |
| maah-daah-hey | Maah Daah Hey Trail | US | ND | 232 | yes | ODbL-1.0 |
| maricopa-trail | Maricopa Trail | US | AZ | 507 | yes | ODbL-1.0 |
| mason-dixon | Mason-Dixon Trail | US | PA, MD, DE | 311 | yes | ODbL-1.0 |
| massanutten | Massanutten Trail | US | VA | 114 | yes | ODbL-1.0 |
| mattabesett | Mattabesett Trail | US | CT | 105 | yes | ODbL-1.0 |
| metacomet-monadnock | Metacomet-Monadnock Trail | US | CT, MA, NH | 185 | yes | ODbL-1.0 |
| mid-state | Mid State Trail | US | PA | 515 | yes | ODbL-1.0 |
| middle-fork-trail | Middle Fork Trail | US | ID | 132 | yes | us-gov-public-domain |
| midland-to-mackinac-trail | Midland to Mackinac Trail | US | MI | 338 | no | none-stated |
| midstate-ma | Midstate Trail (Massachusetts) | US | MA | 148 | yes | ODbL-1.0 |
| monadnock-sunapee | Monadnock-Sunapee Greenway | US | NH | 80 | yes | ODbL-1.0 |
| mountains-to-sea | Mountains-to-Sea Trail | US | NC | 1890 | yes | ODbL-1.0 |
| nepisiguit-migmaq-trail | Sentier Nepisiguit Mi'gmaq Trail | CA | NB | 150 | yes | ODbL-1.0 |
| new-england | New England National Scenic Trail | US | CT, MA | 378 | yes | us-gov-public-domain |
| north-boundary | North Boundary Trail | CA | AB, BC | 159 | no | none-stated |
| north-country | North Country National Scenic Trail | US | ND, MN, WI, MI, OH, PA, NY, VT | 7403 | yes | ODbL-1.0 |
| north-south | North-South Trail | US | RI | 125 | yes | ODbL-1.0 |
| north-south-lbl | North/South Trail (Land Between the Lakes) | US | KY, TN | 95 | yes | ODbL-1.0 |
| north-umpqua | North Umpqua Trail | US | OR | 127 | yes | us-gov-public-domain |
| northville-placid | Northville-Placid Trail | US | NY | 220 | yes | ODbL-1.0 |
| oak-ridges | Oak Ridges Trail | CA | ON | 270 | yes | ODbL-1.0 |
| ocean-to-lake | Ocean to Lake Hiking Trail | US | FL | 99 | yes | ODbL-1.0 |
| oregon-coast | Oregon Coast Trail | US | OR | 650 | yes | ODbL-1.0 |
| oregon-desert | Oregon Desert Trail | US | OR | 1207 | no | ODbL-1.0 |
| ottawa-temiskaming-highland-trail | Ottawa-Temiskaming Highland Trail | CA | ON | 142 | no | none-stated |
| ouachita | Ouachita National Recreation Trail | US | AR, OK | 359 | yes | ODbL-1.0 |
| ozark-highlands | Ozark Highlands Trail | US | AR | 523 | yes | ODbL-1.0 |
| ozark-trail | Ozark Trail (Missouri) | US | MO | 370 | yes | ODbL-1.0 |
| pacific-crest | Pacific Crest National Scenic Trail | US | CA, OR, WA | 4265 | yes | CC-BY-4.0 |
| pacific-northwest | Pacific Northwest National Scenic Trail | US | MT, ID, WA | 1931 | yes | us-gov-public-domain |
| paumanok-path | Paumanok Path | US | NY | 201 | yes | ODbL-1.0 |
| pinhoti | Pinhoti Trail | US | AL, GA | 540 | yes | ODbL-1.0 |
| prescott-circle | Prescott Circle Trail | US | AZ | 90 | yes | ODbL-1.0 |
| ptarmigan-glenns-lake-highline-loop | North Circle | US | MT | 84 | yes | us-gov-public-domain |
| quehanna | Quehanna Trail | US | PA | 119 | yes | ODbL-1.0 |
| rae-lakes-loop | Rae Lakes Loop | US | CA | 67 | yes | us-gov-public-domain |
| rideau-trail | Rideau Trail | CA | ON | 387 | yes | ODbL-1.0 |
| ring-the-peak | Ring the Peak Trail | US | CO | 101 | no | none-stated |
| river-to-river | River to River Trail | US | IL | 257 | yes | ODbL-1.0 |
| sawback-trail | Sawback Trail | CA | AB | 74 | no | none-stated |
| selway-river-trail | Selway River Trail | US | ID | 80 | yes | us-gov-public-domain |
| sentier-international-appalaches | Sentier international des Appalaches (International Appalachian Trail, Quebec and New Brunswick) | CA | QC, NB | 1177 | yes | ODbL-1.0 |
| shawangunk-ridge-trail | Shawangunk Ridge Trail | US | NJ, NY | 114 | yes | ODbL-1.0 |
| sheltowee-trace | Sheltowee Trace National Recreation Trail | US | KY, TN | 552 | yes | ODbL-1.0 |
| shenipsit-trail | Shenipsit Trail | US | CT | 80 | yes | ODbL-1.0 |
| silver-moccasin-trail | Silver Moccasin Trail | US | CA | 82 | yes | ODbL-1.0 |
| solitude-loop | Solitude Loop Trail | US | WY | 89 | yes | us-gov-public-domain |
| south-boundary | South Boundary Trail | CA | AB | 121 | no | none-stated |
| standing-stone | Standing Stone Trail | US | PA | 137 | yes | ODbL-1.0 |
| stein-valley-traverse | Stein Valley Traverse | CA | BC | 80 | yes | ODbL-1.0 |
| sunapee-ragged-kearsarge | Sunapee-Ragged-Kearsarge Greenway | US | NH | 121 | yes | ODbL-1.0 |
| sunshine-coast | Sunshine Coast Trail | CA | BC | 180 | yes | ODbL-1.0 |
| superior-hiking | Superior Hiking Trail | US | MN | 499 | yes | ODbL-1.0 |
| susquehannock | Susquehannock Trail System | US | PA | 135 | yes | ODbL-1.0 |
| tahoe-rim | Tahoe Rim Trail | US | CA, NV | 266 | yes | ODbL-1.0 |
| teton-crest | Teton Crest Trail | US | WY | 63 | yes | us-gov-public-domain |
| thames-valley-trail | Thames Valley Trail | CA | ON | 110 | yes | ODbL-1.0 |
| thorofare-and-south-boundary-trail | Thorofare and South Boundary Trail | US | WY | 109 | yes | us-gov-public-domain |
| timberline | Timberline Trail (Mount Hood) | US | OR | 64 | yes | ODbL-1.0 |
| toiyabe-crest | Toiyabe Crest National Recreation Trail | US | NV | 101 | yes | us-gov-public-domain |
| tonto-trail | Tonto Trail | US | AZ | 153 | yes | ODbL-1.0 |
| traversee-charlevoix | Traversée de Charlevoix | CA | QC | 105 | yes | ODbL-1.0 |
| tuscarora | Tuscarora Trail | US | PA, MD, VA, WV | 406 | yes | ODbL-1.0 |
| uinta-highline | Uinta Highline Trail | US | UT | 167 | yes | ODbL-1.0 |
| vancouver-island | Vancouver Island Trail | CA | BC | 800 | yes | ODbL-1.0 |
| warrior-trail | Warrior Trail | US | PA, WV | 108 | no | none-stated |
| waskahegan | Waskahegan Trail | CA | AB | 309 | no | none-stated |
| west-coast-trail | West Coast Trail | CA | BC | 75 | yes | ODbL-1.0 |
| western-uplands | Western Uplands Backpacking Trail | CA | ON | 88 | yes | ODbL-1.0 |
| wind-river-highline-trail | Wind River Highline Trail | US | WY | 103 | no | none-stated |
| wonderland | Wonderland Trail | US | WA | 150 | yes | ODbL-1.0 |
| wyoming-range | Wyoming Range National Recreation Trail | US | WY | 113 | yes | ODbL-1.0 |
| yosemite-high-sierra-camp-loop | High Sierra Camp Loop | US | CA | 78 | no | none-stated |

<!-- END TRAIL TABLE -->

## Routes

A route is a trail that a hiker worked out and published. The record names the author, says where the route is got from, and whether the author shares the track. See the inclusion rule above.

<!-- BEGIN ROUTE TABLE -->

| ID | Route | Country | States / provinces | Length (km) | Author | Track policy | Track | First guide |
| --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| across-utah-route | Across Utah Route | US | UT | 1127 | Jamal Green | unclear | no | [The Route](http://www.acrossutah.com/wordpress/the_route/) (free) |
| appalachian-high-route | Appalachian High Route | US | NC, TN | 531 | Jake Blood and Jennifer Pharr Davis | unclear | no | [Appalachian High Route: basic maps and directions](https://jenniferpharrdavis.com/blog/hiking-appalachian-high-route) (free) |
| basin-and-range-trail | Basin and Range Trail | US | NV | 1754 | Eric Poulin | sold | no | [Complete Basin and Range Trail Planning Kit: Guidebook, GPX, Maps, Waypoints, Water Chart](https://basinandrangetrail.com/product/complete-basin-and-range-trail-planning-kit/) (purchase) |
| beartooth-high-route | Beartooth High Route | US | MT, WY | 145 | Wilderness Mindset | sold | no | [Beartooth High Route Map Pack](https://wildernessmindset.com/product/beartooth-high-route-map-pack/) (purchase) |
| big-bend-100 | Big Bend 100 | US | TX | 161 | Ky Harkey and Anna Claire Eddington | unclear | no | [The Big Bend 100: A Hike Across Two West Texas Parks](https://tpwmagazine.com/adventure-recreation/the-big-bend-100-a-hike-across-two-west-texas-parks/) (free) |
| big-seki-loop | Big SEKI Loop | US | CA | 249 | Amy and James (Doing Miles) | open | yes | [Big SEKI Loop Route Guide](https://doingmiles.com/route-big-seki-loop/) (free) |
| bigfoot-trail | Bigfoot Trail | US | CA, OR | 579 | Michael Kauffmann | sold | no | [Bigfoot Trail Mapset: Printed](https://www.bigfoottrail.org/product/bigfoot-trail-mapset-printed/) (purchase) |
| bitterroots-80-mile-route | Bitterroots 80-mile Route | US | MT | 126 | Wilderness Mindset | sold | no | [Bitterroots 80-mile Route Map Pack](https://wildernessmindset.com/product/bitterroots-80-mile-route-map-pack/) (purchase) |
| blue-mountains-trail | Blue Mountains Trail | US | OR | 853 | Greater Hells Canyon Council | open | no | [Blue Mountains Trail Caltopo maps and Databook](https://www.hellscanyon.org/blue-mountains-trail/maps) (free) |
| brooks-range-traverse | Brooks Range Traverse | US | AK | 1609 | Luc Mehl and Sarah Histand | unclear | no | [Brooks Range Traverse trip reports](https://thingstolucat.com/brooks-range-traverse/) (free) |
| central-wilderness-grand-tour | Central Wilderness Grand Tour | US | CA | 127 | Suzanne Swedo | sold | no | [Hiking California's Golden Trout Wilderness: A Guide to Backpacking and Day Hiking in the Golden Trout and South Sierra Wildernesses](https://openlibrary.org/books/OL8034582M) (purchase) |
| central-wind-rivers-loop | Central Wind Rivers Loop | US | WY | 99 | Douglas Lorain | sold | no | [Backpacking Wyoming: From Towering Granite Peaks to Steaming Geyser Basins](https://shop.adventurewithkeen.com/product/backpacking-wyoming/) (purchase) |
| chinese-wall-circuit | The Chinese Wall Circuit | US | MT | 127 | Wilderness Mindset | unclear | no | [The Chinese Wall Circuit route page](https://wildernessmindset.com/bob-marshall-wilderness-chinese-wall-circuit/) (free) |
| circle-of-solitude | Circle of Solitude | US | CA | 109 | Mike White | unclear | no | [Sequoia and Kings Canyon National Parks: Your Complete Hiking Guide](https://shop.adventurewithkeen.com/product/sequoia-and-kings-canyon-national-parks/) (purchase) |
| condor-trail | Condor Trail | US | CA | 644 | Condor Trail Association | open | no | [Maps & Trail Descriptions (county KML files and mileage sheet)](http://www.condortrail.com/maps-trail-descriptions/) (free) |
| deadman-and-cloud-canyons | Deadman and Cloud Canyons | US | CA | 182 | Elizabeth Wenk and Mike White | sold | no | [Sierra South: Backcountry Trips in California's Sierra Nevada](https://shop.adventurewithkeen.com/product/sierra-south-2/) (purchase) |
| deadman-creek-loop | Deadman Creek Loop | US | AZ | 93 | Bruce Grubbs | sold | no | [Backpacking Arizona: From Deep Canyons to Sky Islands](https://shop.adventurewithkeen.com/product/backpacking-arizona/) (purchase) |
| deseret-hiking-route | Deseret Hiking Route | US | UT, ID | 1609 | Kevin "LarryBoy" DeVries | withheld | no | [A Complete Guide to the Deseret Hiking Route](http://www.lbhikes.com/p/a-complete-guide-to-deseret-hiking-route.html) (free) |
| desert-trail | Desert Trail | US | CA, NV, OR | 2552 | Desert Trail Association, with the route scouted by Russel Pengely, D. W. "Old Creosote" Tomer and Steve Tabor | unclear | no | [Desert Trail site](https://deserttrail.net) (free) |
| desert-winter-thru-hike | Desert Winter Thru-Hike | US | AZ, CA | 1287 | Brett Tucker ("Blisterfree") and partner, simBLISSity Ultralight Designs | withheld | no | [Desert WTH! topo mapset](https://www.simblissity.net/desert-wth-mapset.shtml) (free) |
| eagle-cap-traverse | Eagle Cap Traverse | US | OR | 88 | Eli Boschetto | sold | no | [Backpacking Oregon: Overnight and Multiday Routes](https://www.mountaineers.org/books/books/backpacking-oregon-overnight-and-multiday-routes) (purchase) |
| eastern-continental-trail | Eastern Continental Trail | US | FL, AL, GA, TN, NC, VA, WV, MD, PA, NJ, NY, CT, MA, VT, NH, ME, QC, NB | 7081 | M. J. Eberhart (trail name Nimblewill Nomad) | unclear | no | [Ten Million Steps: Nimblewill Nomad's Epic 10-Month Trek from the Florida Keys to Quebec](https://openlibrary.org/books/OL8257206M) (purchase) |
| eastern-sierra-high-route | Eastern Sierra High Route | US | CA | 113 | Dan Stenziano | sold | no | [Eastern Sierra High Route Guide](https://danstenziano.com/products/eastern-sierra-high-route-guide) (purchase) |
| georgia-loop | Georgia Loop | US | GA | 89 | Benton MacKaye Trail Association | unclear | no | [Georgia Loop](https://bmta.org/backpacking-hikes/) (free) |
| gospel-hump-loop | Gospel Hump Loop | US | ID | 109 | Douglas Lorain | sold | no | [Backpacking Idaho: From Alpine Peaks to Desert Canyons](https://openlibrary.org/books/OL8277207M) (purchase) |
| grand-enchantment | Grand Enchantment Trail | US | AZ, NM | 1239 | Brett Tucker | sold | no | [Grand Enchantment Trail Official Mapset](http://www.simblissity.net/get/) (purchase) |
| grand-moab-route | Grand-Moab Route | US | CO, UT | 225 | Paul Mags (PMags.com) | withheld | no | [The Grand-Moab Route](https://pmags.com/the-grand-moab-route) (free) |
| grand-teton-loop | Grand Teton Loop | US | WY | 78 | Douglas Lorain | sold | no | [Backpacking Wyoming: From Towering Granite Peaks to Steaming Geyser Basins](https://shop.adventurewithkeen.com/product/backpacking-wyoming/) (purchase) |
| great-basin-trail | Great Basin Trail | US | NV | 1931 | Ryan "Dirtmonger" Sylva | unclear | no | [Great Basin Trail article](https://www.gossamergear.com/blogs/our-blog/great-basin-trail) (free) |
| great-colorado-route | Great Colorado Route | US | CO | 3219 | Donovan "Iceman" Rice | open | no | [Great Colorado Route route page and GPX](https://www.greatcoloradoroute.com/route) (free) |
| great-plains-trail | Great Plains Trail | US | SK, ND, SD, NE, TX | 3540 | Steve Myers (Great Plains Trail Alliance) | unclear | no | [Great Plains Trail map](https://www.greatplainstrail.org/gpt-map/) (free) |
| great-western-divide-loop | Sequoia Great Western Divide Loop | US | CA | 93 | Brian Lucido | open | no | [Sequoia Great Western Divide Loop route page](https://www.brianlucido.com/sequoia-great-western-divide-loop/) (free) |
| great-western-loop | Great Western Loop | US | AZ, NM, CO, WY, ID, MT, CA, OR, WA | 11064 | Andrew Skurka and Ryan Jordan | withheld | no | [Great Western Loop route description](https://andrewskurka.com/adventures/great-western-loop/route-description/) (free) |
| green-river-lakes-titcomb-basin-loop | Green River Lakes & Titcomb Basin Loop | US | WY | 114 | Douglas Lorain | sold | no | [Backpacking Wyoming: From Towering Granite Peaks to Steaming Geyser Basins](https://shop.adventurewithkeen.com/product/backpacking-wyoming/) (purchase) |
| hayduke-trail | Hayduke Trail | US | UT, AZ | 1287 | Joe Mitchell and Mike Coronella | sold | no | [The Hayduke Trail: A Guide to the Backcountry Hiking Trail on the Colorado Plateau](https://uofupress.com/books/the-hayduke-trail/) (purchase) |
| heart-lake-two-ocean-plateau-loop | Heart Lake & Two Ocean Plateau Loop | US | WY | 99 | Douglas Lorain | sold | no | [Backpacking Wyoming: From Towering Granite Peaks to Steaming Geyser Basins](https://shop.adventurewithkeen.com/product/backpacking-wyoming/) (purchase) |
| hot-springs-trail | Hot Springs Trail | US | CA, NV, OR, ID | 3896 | Aria Zoner | sold | no | [The Hot Springs Trail: Official Guidebook](https://www.amazon.com/Hot-Springs-Trail-Official-Guidebook/dp/1505613922) (purchase) |
| kanab-canyon-loop | Kanab Canyon Loop | US | AZ | 84 | Bruce Grubbs | sold | no | [Backpacking Arizona: From Deep Canyons to Sky Islands](https://shop.adventurewithkeen.com/product/backpacking-arizona/) (purchase) |
| kings-canyon-high-basin-route | Kings Canyon High Basin Route | US | CA | 200 | Andrew Skurka | sold | no | [Kings Canyon High Basin Route Guide](https://andrewskurka.com/product/kings-canyon-high-basin-route-guide/) (purchase) |
| lowest-to-highest-route | Lowest to Highest Route | US | CA | 209 | Brett Tucker ("Blisterfree") and partner, simBLISSity Ultralight Designs | open | no | [L2H Navigation Bundle](http://simblissity.net/L2H.shtml) (free) |
| middle-fork-kings-river | Middle Fork Kings River | US | CA | 133 | Mike White and Douglas Lorain | sold | no | [Best Backpacking Trips in California and Nevada](https://www.unpress.nevada.edu/9780874179712/best-backpacking-trips-in-california-and-nevada/) (purchase) |
| milestone-basin-and-the-upper-kern | Milestone Basin and the Upper Kern | US | CA | 89 | Elizabeth Wenk and Mike White | sold | no | [Sierra South: Backcountry Trips in California's Sierra Nevada](https://shop.adventurewithkeen.com/product/sierra-south-2/) (purchase) |
| mogollon-rim-trail | Mogollon Rim Trail | US | AZ, NM | 805 | Brett Tucker ("Blisterfree") | sold | no | [Mogollon Rim Trail Mapset & Resource Bundle](https://www.simblissity.net/mogollon-rim-trail-mapset.shtml) (purchase) |
| mojave-sonoran-trail | Mojave-Sonoran Trail | US | NV, CA, AZ | 1006 | Eric Poulin | open | no | [Mojave Sonoran Trail: A 625 Mile Thru-Hiking Route](https://seekinglost.com/thru-hikes/mojave-sonoran-trail-thru-hiking-route/) (free) |
| montana-trail | Montana Trail 406 | US | MT | 2934 | Montana Trail 406 Association | open | no | [Montana Trail hike sections and complete hike GPX](https://montanatrail.org/montana-trail-hike-sections/) (free) |
| nankoweap-bright-angel-loop | Nankoweap–Bright Angel Loop | US | AZ | 132 | Bruce Grubbs | sold | no | [Backpacking Arizona: From Deep Canyons to Sky Islands](https://shop.adventurewithkeen.com/product/backpacking-arizona/) (purchase) |
| northern-colorado-trail | Northern Colorado Trail | US | CO | 490 | Kevin Silvernale | open | no | [Northern Colorado Trail Guides](https://www.northerncoloradotrail.org/noco-trail-guides) (free) |
| northern-new-mexico-loop | Northern New Mexico Loop | US | NM | 805 | Brett Tucker ("Blisterfree") and collaborators | sold | no | [Northern New Mexico Loop Mapset & Resource Bundle](https://simblissity.net/northern-nm-loop-mapset.shtml) (purchase) |
| pfiffner-traverse | Pfiffner Traverse | US | CO | 124 | Andrew Skurka | sold | no | [Pfiffner Traverse Guide](https://andrewskurka.com/product/pfiffner-traverse-guide-maps/) (purchase) |
| powell-plateau-loop | Powell Plateau Loop | US | AZ | 88 | Bruce Grubbs | sold | no | [Backpacking Arizona: From Deep Canyons to Sky Islands](https://shop.adventurewithkeen.com/product/backpacking-arizona/) (purchase) |
| route-in-between | Route In Between | US | AZ, UT, ID | 4344 | Kevin "LarryBoy" DeVries | withheld | no | [A Complete Guide to the Deseret Hiking Route](http://www.lbhikes.com/p/a-complete-guide-to-deseret-hiking-route.html) (free) |
| rutherford-lake-loop | Rutherford Lake Loop | US | CA | 115 | Kathy Morey and Mike White, with Stacy Corless and Thomas Winnett | sold | no | [Sierra North: Backcountry Trips in California's Sierra Nevada](https://openlibrary.org/books/OL8277252M) (purchase) |
| san-diego-trans-county-trail | San Diego Trans County Trail | US | CA | 249 | Sea to Sea Trail Foundation (folded); guide by Liz Thomas | unclear | no | [San Diego Trans County Trail](https://www.treelinereview.com/where-to-go/san-diego-trans-county-trail) (free) |
| santa-fe-to-taos | Santa Fe to Taos Thru-Hike | US | NM | 212 | Pam Neely | sold | no | [The Santa Fe to Taos Thru-Hike Guidebook](https://santafetotaos.org/guidebook/) (purchase) |
| sawtooth-wilderness-high-route | Sawtooth Wilderness High Route | US | ID | 143 | Eric Poulin | open | no | [Sawtooth Wilderness High Route trip report and GPX](https://seekinglost.com/sawtooth-wilderness-high-route-8-day-solo-hike-aug-2017/) (free) |
| sea-to-sea-route | Sea-to-Sea Route | US | ND, MN, WI, MI, OH, PA, NY, VT, MT, ID, WA | 12513 | Ron Strickland | unclear | no | [Sea-to-Sea Route overview and route description](https://andrewskurka.com/adventures/sea-to-sea-route/overview/) (free) |
| sierra-grand-traverse | Sierra Grand Traverse | US | CA | 322 | John and Monica Chapman | sold | no | [Sierra Grand Traverse: An Epic Route Across the Range of Light](https://www.mountaineers.org/books/books/sierra-grand-traverse-an-epic-route-across-the-range-of-light) (purchase) |
| sierra-high-route | Sierra High Route | US | CA | 314 | Steve Roper | sold | no | [Sierra High Route, 2nd Edition: Traversing Timberline Country](https://www.mountaineers.org/books/books/sierra-high-route-2nd-edition-traversing-timberline-country) (purchase) |
| siskiyou-peaks-trail | Siskiyou Peaks Trail | US | OR, CA | 721 | Aria Zoner | sold | no | [The Siskiyou Peaks Trail: From Ashland, OR to Mt Shasta, CA - Thru the Klamath Knot](https://www.abebooks.com/9781983447525/Siskiyou-Peaks-Trail-Ashland-Shasta-1983447528/plp) (purchase) |
| sky-islands-traverse | Sky Islands Traverse | US | AZ | 837 | Brett Tucker ("Blisterfree") | withheld | no | [Sky Islands Traverse page](http://simblissity.net/skit.shtml) (free) |
| south-lake-to-north-lake | South Lake to North Lake | US | CA | 89 | Elizabeth Wenk and Mike White | sold | no | [Sierra South: Backcountry Trips in California's Sierra Nevada](https://shop.adventurewithkeen.com/product/sierra-south-2/) (purchase) |
| southeastern-serpentine-trail | Southeastern Serpentine Trail | US | SC, NC, GA, TN | 938 | Cam Honan | unclear | no | [Southeastern Serpentine Trail](https://thehikinglife.com/2016/07/southeastern-serpentine-trail/) (free) |
| southern-sierra-high-route | Southern Sierra High Route | US | CA | 161 | Alan Dixon and Don Wilson | open | no | [Southern Sierra High Route (SoSHR) guide](http://www.adventurealan.com/southern-sierra-high-route-soshr-guide/) (free) |
| southwestern-horseshoe | Southwestern Horseshoe | US | UT, AZ, NM | 2867 | Cam Honan | unclear | no | [Southwestern Horseshoe](https://thehikinglife.com/2019/03/southwestern-horseshoe/) (free) |
| sycamore-canyon-az | Sycamore Canyon | US | AZ | 90 | Bruce Grubbs | sold | no | [Backpacking Arizona: From Deep Canyons to Sky Islands](https://shop.adventurewithkeen.com/product/backpacking-arizona/) (purchase) |
| tahoe-yosemite-trail | Tahoe–Yosemite Trail | US | CA | 299 | Thomas Winnett | sold | no | [The Tahoe–Yosemite Trail](https://openlibrary.org/books/OL2377803M) (purchase) |
| teton-crest-route | Teton Crest Route | US | WY | 95 | Wilderness Mindset | sold | no | [Teton Crest Route Map Pack](https://wildernessmindset.com/product/teton-crest-route-map-pack/) (purchase) |
| teton-range-traverse | Teton Range Traverse | US | WY | 171 | Cam Honan | unclear | no | [Teton Range Traverse](https://thehikinglife.com/2017/07/teton-range-traverse/) (free) |
| teton-wilderness-loop | Teton Wilderness Loop | US | WY | 97 | Douglas Lorain | sold | no | [Backpacking Wyoming: From Towering Granite Peaks to Steaming Geyser Basins](https://shop.adventurewithkeen.com/product/backpacking-wyoming/) (purchase) |
| three-sisters-loop | Three Sisters Loop | US | OR | 74 | Eli Boschetto | sold | no | [Backpacking Oregon: Overnight and Multiday Routes](https://www.mountaineers.org/books/books/backpacking-oregon-overnight-and-multiday-routes) (purchase) |
| trans-adirondack-route | Trans Adirondack Route | US | NY | 391 | Erik Schlimmer | sold | no | [Blue Line to Blue Line, with a map set](https://erikschlimmer.com/books-sale-/) (purchase) |
| vagabond-loop | Vagabond Loop | US | AZ, UT, CO, NM | 5632 | Ryan "Dirtmonger" Sylva | unclear | no | [Vagabond Loop route description](https://www.freedirtmonger.com/p/vagabond-loop-four-corners-connection-1.html) (free) |
| vancouver-island-backbone | Vancouver Island Backbone | CA | BC | 300 | Philip Stone | unclear | no | [Hiking Guide to the Vancouver Island Backbone](https://www.wildisle.ca/backbone/index.html) (free) |
| wasatch-traverse | Wasatch Traverse | US | UT | 455 | Liz Thomas | unclear | no | [Wasatch Traverse overview](https://www.eathomas.com/other-long-trails/wasatchoverview) (free) |
| washington-coast-trail | Washington Coast Trail | US | WA | 290 | Lauren Lake (PacificCoastalTrail blog) | open | yes | [Itinerary: Washington Coast](https://pacificcoastaltrail.wordpress.com/2022/03/23/itinerary-washington-coast/) (free) |
| wind-river-high-route-dixon-wilson | Wind River High Route (Dixon and Wilson) | US | WY | 129 | Alan Dixon and Don Wilson | open | no | [Wind River High Route guide](https://www.adventurealan.com/wind-river-high-route/) (free) |
| wind-river-high-route-skurka | Wind River High Route (Skurka guide) | US | WY | 156 | Andrew Skurka | sold | no | [Wind River Range High Route Guide](https://andrewskurka.com/product/wind-river-high-route-guide/) (purchase) |
| yosemite-high-route | Yosemite High Route | US | CA | 261 | Andrew Skurka | sold | no | [Yosemite High Route Guide](https://andrewskurka.com/product/yosemite-high-route-guide/) (purchase) |

<!-- END ROUTE TABLE -->

## Layout

One directory per trail. The directory name is the trail's stable `id` and never changes.

```text
<id>/trail.toml            the record (see docs/schema.md)
<id>/line.geojson          the main track, where one may be shared
<id>/alternates.geojson    alternate and connector tracks, where the source serves them separately
<id>/line-<source>.geojson one source's own extract, where a track combines sources
<id>/release.txt           the source, licence and date the track files came from
<id>/shield.svg            the trail's logo, where one exists (SVG preferred)
<id>/shield.png            the trail's logo, where no SVG exists
```

In the published copy, GeoJSON coordinates are rounded to 6 decimal places (about 0.1 m) and written as compact JSON. Geometry is otherwise as the source served it. Raw download files that were only used to build a track (for example raw OpenStreetMap XML extracts) are not included; the record names the source and relation they came from.

Top-level generated files:

```text
trails.csv      one row per trail (built by tools/build_index.py)
index.geojson   every included track, simplified to about 100 m, with id and name
SOURCES.md      each distinct source, its terms, and the trails that use it
```

## How to use it

- Read a trail: open its `trail.toml`. The `[source]` section says where the track came from and under what terms it may be used.
- Read all trails at once: use `trails.csv`, or `index.geojson` for a map overview.
- Check the data: run `python3 tools/validate.py`. It prints `OK <n> trails` when all records pass.
- Rebuild the generated files after editing a record: run `python3 tools/build_index.py`.

Follow the licence in each record. Tracks from OpenStreetMap need the credit "© OpenStreetMap contributors" and stay under the ODbL. Tracks from United States federal agencies are public domain in the United States. Other tracks carry the credit named in their record.

## Other lists of long trails

Other people keep lists of long trails, and this dataset is checked against them to find trails it lacks. A trail found that way is then confirmed on its holder's own pages before it is added. Nothing is copied from the lists: they tell us a trail exists, and the record's facts come from the pages it names.

With thanks to the lists checked so far:

- LongTrailsWiki's List of Long Trails and List of Trails to Review (https://www.longtrailswiki.net), part of OpenLongTrails (https://www.openlongtrails.org)
- Wikipedia's lists of long-distance trails in the United States and of trails in Canada
- The OpenStreetMap wiki's list of long distance trails in the United States
- ALDHA-West's list of trails (https://aldhawest.org/trails)
- The Trek's list of long-distance trails in the US (https://thetrek.co)
- thru-hiking.com
- Backpacking Routes (https://backpackingroutes.com)
- HikeBikeTravel's list of long distance trails in Canada (https://hikebiketravel.com)
- Explore magazine's list of Canada's longest hiking trails
- Hike Ontario's member trail associations
- Nutty Hiker's list of thru-hiking trails

If you keep such a list and want it named here, or named differently, open an issue.

## Licences

The records, documents and compiled index in this repository are dedicated to the public domain under CC0-1.0 (see LICENSE).
The tools in `tools/` are under the MIT licence (see LICENSES/MIT.txt).
Each trail's track keeps the terms of its source, stated in that trail's record (see SOURCES.md).
Tracks from OpenStreetMap are © OpenStreetMap contributors, under the ODbL (see LICENSES/ODbL-1.0.txt).
Trail logos are not covered by any of these licences; see NOTICE.md.

## Logos

Logos are included only to identify each trail. They belong to their holders, are not covered by this repository's licences, and will be removed at the holder's request. See NOTICE.md for how to ask.

## Report an error

Open an issue or a pull request at https://github.com/swaits/longhikes, with: the trail's `id`, what is wrong, and where the correct information can be checked (a source page, a map, or a measured track). Corrections to a track should name the source the corrected track came from and its licence. See CONTRIBUTING.md for how to correct a record, add a trail, or refresh a trail from its source.

## Sources

See SOURCES.md for each distinct source, the sentence that states its terms, the page it was read on, and the date it was read.
