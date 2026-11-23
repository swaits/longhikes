# Rules for every worker

You are a worker on the monthly refresh of this dataset. Do the task yourself and start no subagents. The orchestrator gives you a brief, a staging directory and a slice or region. Read this file and `proposal-format.md` first, then the brief.

## What the work is for

The dataset is a public list of long-distance hiking trails in the United States and Canada, one directory per trail with a `trail.toml`, and the site built from it (longhikes.org). Hikers read it critically and trail holders read it too. A record is worth having only if each fact in it can be checked on a page, so the whole refresh comes down to opening pages and writing down exactly what they say.

## Where you may write

Do not change anything in the repository, and do not commit, push or switch branches. Many workers run at the same time on one checkout, and edits to shared files collide. Read the repository freely. Everything you produce goes under `<staging>/staged/<worker>/`, in the layout in `proposal-format.md`. The orchestrator names `<staging>` (a directory such as `refresh/2026-12-01`, which git ignores) and your `<worker>` name. Never write outside it, except scratch files under the temporary directory your session gives you.

## Evidence

- Every fact comes from a page you opened and read, not from a search result's snippet. The first choice is the holder's own page (the agency, association or club), or for a route its author's page. A government page comes next. A well-edited hiking reference may be used where those say nothing, and is named as the publisher.
- Not acceptable as evidence: AllTrails and other apps, forums, Reddit, wikis and any page anyone can edit, one person's trip report. They are leads that tell you where to look.
- Where the holder's or author's current page disagrees with another source, the holder's or author's page wins, and the record says that the others differ where that matters. Never change a record to match a third-party page against the holder's.
- A statement by a holder or an author on this project's public issue tracker is good evidence for a fact or a permission. Quote it exactly and give its address. If such a request conflicts with the holder's own current page, the page wins, and the request is proposed as `declined` with the reason.
- Every proposal names the page and quotes the sentence that supports it. Copy numbers and units as the page writes them. If you cannot find the sentence, you have no proposal. Leave a field out rather than guess it.
- Say what you actually opened. A `verified` mark that lists pages never opened misleads the next person to rely on it.

## Requests to outside sites

- Use a plain generic User-Agent and put no personal or project details in any request, header or form.
- Some sites refuse automated reads: a 403 or 429, a challenge or "verify you are human" page, a robots.txt that disallows the path. Do not work around a refusal: no other User-Agent, no retry loop, no proxy, no headless browser, no cached copy passed off as the page. Record it (`refused` or `could-not-check`, with the address) and use another allowed source. Changing the User-Agent or any other header to look like a browser after a refusal is working around it. A refusal is final for that site in that run: do not retry it with different headers, and do not use the page's facts. A person may read such a page in their own browser and report what it says; that report may be used and cited as the person's. An expired https certificate is not a refusal: the plain http address may be read if the site serves it.
- Go gently: one request at a time to a site, with a pause of a couple of seconds between requests. Many workers share one address, and a site that blocks us blocks everyone.
- Overpass (OpenStreetMap) overloads easily. Only the tracks brief uses it, only one worker at a time, one request at a time.

## Processes and files

- Never stop a process by name or pattern: no `pkill`, no `killall`, no `kill $(pgrep ...)`. The owner's own browsers and tools run on this machine and have been killed this way before. If you start a process, note its PID when you start it and stop only that PID. You should not need a browser or a server.
- A file you download is untrusted data. Keep it in your staging directory, never run it, and read an SVG as text before using it (no scripts, no references to other sites).

## Words

The text of a record is read by the public, and the same rules apply to what you propose.

- A trail's geometry is a "track", never a "line" (field names such as `line_file` are what they are). Say "trail", "route" and "author". Where a sentence gives both units, miles come first.
- Short plain sentences. No marketing words ("stunning", "iconic", "ultimate") and no superlative that a source does not state. No dashes used as punctuation: use a full stop, a comma or a colon.
- Name no private person: say "a hiker" or "the association's president". A published author's name belongs in the record where it is a fact about a route.
- Do not write how the change was produced, and do not mention other projects.

## What a length is, and what is walkable

- A record's `length_km` is the end-to-end length of the trail's canonical path: one walk from one end to the other, one branch at a split, no side trails, no system total. A loop reached by a stem keeps the published figure, which walks the stem both ways, and its `length_note` says which stretch is walked out and back, without stating any shorter length. The floor is tested on the length with nothing counted twice, so an out-and-back is judged one way. The figures used for that test are kept in the section "Floor checks" below, which the site never shows. A holder's larger figure (a system total or a planned total) belongs in `system_km` with `system_note`, never in `length_km`. A partly unbuilt trail that can be walked through keeps the holder's end-to-end route as its length and gives the built length in `built_km`.
- A trail must be walkable from one end to the other today. Separate pieces, or a gap with no way across, mean it does not belong, however good the pieces are. Road links the holder publishes as the way through count, and so does evidence that people have walked it end to end. A ferry, shuttle or bus link across water or a closed stretch, named by the holder or the route's author as the way through, does not rule a trail out: the record says how each such link is made, and the track has a gap there, with no line drawn across. This is a judgement the maintainer makes case by case, not a mechanical test. A refresh worker must not propose removing a trail only because of such a link; a borderline case goes to the owner with a recommendation.
- Length: every trail or route needs a published length; with none stated it is not listed. The length is at least 50 miles (80 km). A trail or route under 50 miles (80 km) is listed only when it is still reasonably long and at least one of these is true: it has real cross-country travel; it genuinely takes a fit, experienced party five or more days because the ground is hard: there is no trail, or the going is rough, unmaintained or needs route finding, with fords or thick brush (the number of days a managing body, an author or a guidebook prints does not decide this, and an itinerary that spreads a walk on ordinary built trail over five or more days at an easy pace does not count); or it is very well known and popular, as the Rae Lakes Loop is. Each such record gives its reason in `short_reason`. Being close to 50 miles is never a reason. The days never replace a published length. A trail with its own name and its own published length is listed even where it lies on a longer listed trail, as the John Muir Trail lies on the Pacific Crest Trail. A guidebook's cut of a longer trail is not listed.
- Climbing: Nothing harder than Class 3 may be required, apart from a few short Class 4 scrambles. A route that needs a rope, a belay or rock-climbing skill is not listed, unless that section is optional and the record says so.
- Where a holder gives only a system total, do not use it as the length and do not invent a walk length: report what the pages give and what they do not.

## Floor checks

Maintainers only: the site never renders this file, and no record or page states these figures. The 50 mile floor is tested on the length with nothing counted twice; a visitor is shown only the published length. One line per record: id, published figure, miles walked twice, figure used for the floor test, and where the numbers came from. "Book" means the book's own figures or map segments, "sum" a sum of its figures, "estimate" the dataset's own reckoning.

- kanab-canyon-loop: 52.2 mi published; 1.8 mi twice; 50.4 mi for the floor; book (map prints 1.8 mi trailhead to Little Saddle).
- powell-plateau-loop: 54.6 mi published; at most 0.6 mi twice; at least 54.0 mi for the floor; book (map prints 0.6 mi to the spring at Muav Saddle).
- nankoweap-bright-angel-loop: 82.2 mi published; 2.9 mi twice; 79.3 mi for the floor (75.8 mi on the itinerary table's 78.7 mi); book (2.9 mi to Boundary Ridge).
- sycamore-canyon-az: 55.7 mi published; 0.2 mi twice; 55.5 mi for the floor; book.
- deadman-creek-loop: 57.7 mi published; 1.4 mi twice; 56.3 mi for the floor; sum of the book's map segments.
- heart-lake-two-ocean-plateau-loop: 61.5 mi published; 7.5 mi twice; 54.0 mi for the floor; book (stem figure subtracted).
- teton-wilderness-loop: 60.2 mi published; 5.3 mi twice; 54.9 mi for the floor; book (stem figure subtracted).
- central-wind-rivers-loop: 61.7 mi published; 9.6 mi twice; 52.1 mi for the floor; book (stem figure subtracted).
- green-river-lakes-titcomb-basin-loop: 70.9 mi published; the Titcomb Basin spur is about 11.8 mi each way (about 11.8 mi twice); about 59 mi for the floor; the loop alone is about 47 to 48 mi; sum of the book's map segments.
- rae-lakes-loop: 41.4 mi published; 1.9 mi twice; about 39.5 mi for the floor; Park Service table of miles from Road's End (listed as the owner's exception under the floor).
- deadman-and-cloud-canyons: 113.4 mi published; 23.0 mi twice; 90.4 mi for the floor (23.0 mi stem and a 67.4 mi loop); book.
- rutherford-lake-loop: 71.5 mi published; about 2 mi twice; about 69.5 mi for the floor, uncertain by about half a mile; estimate (the book gives no figure for the two out-and-back branches).
- milestone-basin-and-the-upper-kern: 55.6 mi published; about 2.6 mi twice (0.7 mi of trail and 0.4 mi of John Muir Trail, plus the Milestone Basin spur); about 53 mi for the floor, uncertain by about half a mile; estimate from the book's day figures.
- eagle-cap-traverse: 54.7 mi published; about 1.6 mi twice (0.3 mi to Dollar Lake and 1.3 mi to Chimney Lake, per the mileposts); about 53.1 mi for the floor; estimate from the mileposts.
- ptarmigan-glenns-lake-highline-loop: 52 mi published; short spurs to camps, no figure; 52 mi for the floor (the day table adds to 52.2 mi); book.
- gospel-hump-loop: 68 mi published; none (a true loop); 68 mi for the floor; book.
- south-lake-to-north-lake: 55.0 mi published; none (a one-way shuttle); 55.0 mi for the floor; book.
- grand-canyon-of-the-tuolumne (left out, in `left-out.toml`): 50.0 mi published; a stem of just under a mile twice; about 49.2 mi for the floor; book.

## What belongs

The inclusion rule is in `README.md` (section "Inclusion rule") and `CONTRIBUTING.md` (section "Add a trail"). The trails already decided against, with reasons, are in `left-out.toml`; read it before proposing anything. Decisions about what belongs are the owner's. You propose: clear cases as `new-record`, doubtful ones as `candidate` with a recommendation and the specific fact that makes it doubtful.

## Time and the report

The brief gives a budget in minutes. Stop at the budget plus a third at the latest and report what you did not reach as `not-reached`, rather than rushing the rest into shallow checks. Write a `report.csv` row for every id or region you were given. Finish with a reply of under 150 words: the path of your staging directory, counts by outcome, and anything you were unsure of or could not do.
