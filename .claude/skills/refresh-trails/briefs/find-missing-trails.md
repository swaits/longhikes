# Search for trails the dataset is missing, by region

Read `../rules.md`, `../proposal-format.md` and `../records.md` first. You do this task yourself and start no subagents.

You receive a staging directory `<staging>`, a worker name (for example `region-us-west`) and a region: a group of states or provinces. Stage your work in `<staging>/staged/<worker>/`. Your task may also say it is a second pass and give you the list of places the first pass searched.

## What this is for

The dataset should hold every trail that meets its inclusion rule. It was built from other sites' lists, and every earlier search by list missed trails that a plain look at a state agency's pages found. One such search for a whole country once reported nothing missing, and a second worker with a different approach found seven. Done means that for your region you have searched widely and deeply, every candidate is confirmed on its holder's page, and every place you looked is listed, including the places that gave nothing.

## The inclusion rule, short

A named long-distance walking trail or route in the US or Canada, 50 miles (80 km) or longer as one continuous walk. Loops count. A trail that is partly built counts if its holder publishes it as one trail and it can be walked through from one end to the other today, with road links allowed; its length is the end-to-end length of the canonical path, not a system total. A trail published in separate pieces, or with a gap that has no way across, does not count. A trail has a holder (agency, association or club) that names it and states its length. A route was worked out by an author, and counts only if the author has a page or book of their own that describes it as a route with a stated length; one person's trip report is not a route. The full rule is in `README.md`. Left out on purpose: gravel rail trails and canal towpaths, paved greenways, trails mainly for horses, bikes, motor vehicles or paddling, mainly driving historic trails, networks that are not one continuous trail, trails closed for good, proposed trails with nothing on the ground. Everything already decided against is in `left-out.toml` with the reason: do not propose it again unless the page now shows that the deciding fact has changed. Trails between 40 and 50 miles are not candidates.

## How to search

- Go wide first. Use many varied words: "long trail", "long-distance trail", "thru-hike", "backpacking trail", "backpacking route", "multi-day", "100-mile", "end to end", "traverse", "high route", "loop", "wilderness trail", "footpath", "state trail", and in French "sentier de longue randonnée" where it applies. Combine each with every state or province, mountain range, national forest, national park, large state park or forest, river, lake shore, coast and desert in your region.
- Then go deep on the places that list trails officially: each state or provincial agency's trail pages and trail lists, the National Recreation Trails database, trail associations and hiking clubs, guidebook publishers' catalogues, regional hiking magazines, and articles on the best long trails of a place.
- Whole-country lists were already swept and are leads only for a single trail: Wikipedia's long-distance trail lists, ALDHA-West, The Trek, thru-hiking.com, Backpacking Routes, HikeBikeTravel and LongTrailsWiki.
- For every name, check the dataset before spending time: search `trails.csv`, the `name` and any other-name fields of `*/trail.toml`, and `left-out.toml`. Many trails are in under another spelling or inside a longer trail.
- A candidate counts only after you read its holder's or author's own page and saw the length stated there (or, failing that, a government page). Apps, forums, Reddit and wikis are leads, never evidence.

## The hard part

Searching is where cheap, quick attempts fail: a few queries, a page or two per state, and "nothing found". Do the dull part: walk each state's agency trail list to the end, not just the first search page. When a state seems empty, check it from a second direction (the national forests in it, its long-distance hiking club, its National Recreation Trails) before you say so. If this is a second pass, the places listed as already searched are not a reason to skip a state; use different questions and different sources, and treat a quiet first pass as a reason to look harder, not as evidence.

## What to stage

- Before you propose anything, confirm on the holder's page two things: the end-to-end length of one walk (one branch at a split, no side trails, no system total), and that the trail can be walked through today.
- For a candidate that clearly meets the rule: a `new-record` proposal, with the complete record staged as `staged/<worker>/<id>/trail.toml` written as `../records.md` says. A new official trail gets no track now: write the honest absent reason ("No track has been added yet" in substance). Do not fetch any track and do not call Overpass: a later serial pass does that. If you can find the trail's OpenStreetMap route relation number through the openstreetmap.org search page or Nominatim (one light request per trail), put it in the record's `[osm]` note and in your report.
- For a candidate that is doubtful (length near the floor, partly built, a network or a loop of linked trails, a route with a thin author page, an owner who might dispute it): a `candidate` proposal with `borderline = true`, the length as stated, the page, and a recommendation (`add`, `owner` or `decline`) with the specific doubt in `summary`.
- Trails of 40 to 50 miles that are well known: a `candidate` proposal with `recommendation = "decline"` and `reason = "below-floor"`, so the owner can see them.
- `report.csv` with one row per state or province in your region: `found` (with the ids), or `not-found`, with `pages` listing every place you looked for that state: the agency pages, the lists, the queries by kind. "Not found" without where you looked is not accepted.

## Time

About 60 minutes for a region of 5 to 8 states or provinces. Stop at 80.

## Report

Reply with under 150 words: staging path, number of new records and candidates, the two or three strongest, and the states or provinces where you found nothing and how sure you are.
