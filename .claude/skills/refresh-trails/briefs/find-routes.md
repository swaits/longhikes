# Search for routes published by their authors

Read `../rules.md`, `../proposal-format.md` and `../records.md` first. You do this task yourself and start no subagents.

You receive a staging directory `<staging>`, a worker name (for example `routes-1`) and optionally a part of the country. Stage your work in `<staging>/staged/<worker>/`.

## What this is for

Some of the best long walks are not designated trails. A hiker or a guidebook author worked a high route, a traverse or a loop of linked trails out and published it with a stated length. The dataset lists these as routes when the author has a page or book of their own that describes the route with a length. They are missed by agency searches, because no agency holds them, and they are easy to over-count, because a trip report looks like a route. Done means you have searched the places routes are published, and each route you found is confirmed on its author's page.

## The rule, short

A route counts when its author has their own page or a published book that describes it as a route and states its length, and the length is 50 miles (80 km) or more as one continuous walk (loops count). A route under 50 miles counts only when it is still reasonably long and has real cross-country travel, genuinely takes a fit, experienced party five or more days because the ground is hard (no trail, or rough, unmaintained going that needs route finding, with fords or thick brush; the days a managing body, an author or a guidebook prints do not decide this, and an easy-paced itinerary on ordinary built trail does not count), or is very well known and popular, as the Rae Lakes Loop is; being close to 50 miles is never a reason. It still needs a stated length. A guidebook's cut of a longer trail is not a route; a trail with its own name and its own published length is listed even where it lies on a longer listed trail, as the John Muir Trail lies on the Pacific Crest Trail. The floor is tested on the length with nothing counted twice, so a loop reached by a stem is judged without the stem's return walk. Nothing harder than Class 3 may be required, apart from a few short Class 4 scrambles. A route that needs a rope, a belay or rock-climbing skill is not listed, unless that section is optional and the record says so. A trip report of one person's walk is not a route. A route of 50 miles or more that meets the climbing rule is listed even when every documented end-to-end completion is a single-push speed record and no multi-day walk of the whole line is published, without speed records. The author's name is the author the page names. Check `trails.csv`, the `name` fields of the records (`kind = "route"` ones especially) and `left-out.toml` first: the dataset already holds many routes and has decided against others, and the same route often goes under two names or sits inside a longer one.

## How to search

Search for the kinds of things authors publish: "high route", "traverse", "alternate route", "thru-hiking route", "loop", "off-trail route", "link-up", "cross-country route", with each mountain range, wilderness area, national park, desert, island, coast and territory in the US and Canada (or in your part). Look at guidebook publishers (the regional mountaineering and outdoor presses), the authors' own sites, hiker association pages that link to routes, and regional hiking magazines. A guidebook's own publisher page counts as the author's page for a book route. Routes already in the dataset have their author, year and `[[guide]]` in the record: read two to see how they are described.

## The hard part

Telling a route from a trip report, and telling the author's page from someone's summary of it. Read the author's own page, find the stated length and the sentence that calls it a route, and note whether the track is free, sold, withheld or unsettled (the record needs `[route]` and `line_policy`). Never include a track for a route. If the author's page states terms that allow passing a track on, quote them; otherwise there is no track, and the record says so. A route whose length is only given in someone else's article is a lead, not a candidate.

As with other searches, a quiet result needs a second look from another direction before you call a region empty, and "not found" must say where you looked.

## What to stage

The same as `find-missing-trails.md`: a `new-record` proposal with a staged `trail.toml` for each route that clearly meets the rule, `candidate` proposals for doubtful ones and for routes under 50 miles that appear to meet one of those conditions, and a `report.csv`. Its rows are the mountain ranges, regions or sources you covered, each `found` (with ids) or `not-found` with the places looked. For a new route record, `kind = "route"`, `[route]` with the author and `line_policy`, at least one `[[guide]]`, and no track.

## Time

About 60 minutes. Stop at 80.

## Report

Reply with under 150 words: staging path, number of new records and candidates, the strongest, and where you found nothing.
