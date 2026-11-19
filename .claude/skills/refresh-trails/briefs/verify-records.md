# Verify records against the pages they cite

Read `../rules.md`, `../proposal-format.md` and `../records.md` first. You do this task yourself and start no subagents.

You receive a staging directory `<staging>`, a worker name (the slice name, for example `trails-03`) and a slice file `<staging>/slices/<worker>.txt` listing trail ids, one per line. Stage your work in `<staging>/staged/<worker>/`.

## What this is for

Trail pages change: a holder renames a trail, a section closes, a length is revised, a permit rule changes, a page moves. A record that was right when it was written drifts out of date, and a hiker who relies on it is the one who pays. Once a month every record is checked again against the pages it cites and against the holder's current site, so that what the dataset says is what the holder says today. Done means that for every id in your slice the record is either marked verified, with the pages you opened, or has proposals that say exactly what changed and where that is written.

## What to do for each id

1. Read `<id>/trail.toml` whole, including its `[[history]]`. Note every earlier `declined` entry and every entry asked for by someone other than the dataset's own check: those are decisions you must not quietly reverse.
2. Open every page the record cites: each `[[hike.source]]` url, `hike.official_url`, `source.publisher_url`, `source.url` and `source.permission_url` where present, the `[[guide]]` pages, and the pages named in `short_name_url` and `length_note`. Then open the holder's or author's current official site for the trail, even if the record does not cite its current address, and follow a moved page to where it went. `links.csv` in the staging directory says which of the record's addresses are dead, redirected or refused; use it to find where to start, and still read the page itself.
3. Check each of these against what the pages say now:
   - the name, and the holder or author
   - the length, and what it counts (built or planned, with or without side trails). The record's `length_km` must be one end-to-end walk of the canonical path: one branch at a split, no side trails, no system total. A loop reached by a stem keeps the published figure, and the record's length note says which stretch is walked out and back without stating a shorter length. If the page's figure is a system or planned total, find the end-to-end figure; the larger figure belongs in `system_km`. If the trail is partly unbuilt, check `built_km` and the `hike.unfinished` sentence against the page
   - whether the trail can be walked from one end to the other today: published in one piece, or with road links the holder publishes as the way through, or with end-to-end walks on record. Separate pieces or a gap with no way across is a finding
   - both ends (and for a loop the usual trailhead), by place name
   - allowed uses: hiking, bicycles, horses, dogs, motor vehicles
   - permits, reservations and fees for walking the whole trail
   - the season and the usual time to walk it
   - closures or reroutes that affect walking through (a loss of access the holder has reported in writing may be recorded; day to day conditions may not)
   - the official links: do the record's addresses still reach the right page
   - the track's source: is the source page still there, does it still state its terms, has the relation or layer been replaced? You do not fetch tracks here. Record only whether the source and its terms still say what the record says.
   - `short_name`, if present: is it still the holder's own or established use?
4. Decide:
   - Nothing changed: stage a `verified` proposal naming every page you opened.
   - Something changed: stage a `change` proposal with one `[[proposal.edit]]` per field, each with the `page` and the `quote` that support it, a `[proposal.history]`, and also a `verified` proposal for what you checked and found unchanged.
   - Pages disagree with each other, or with the record, and you cannot tell which is right: do not edit. Write a `could-not-check` proposal that says what disagrees and which pages say what.
   - A request recorded in the history is contradicted by the holder's page: a `declined` proposal, not a change.
   - The pages say the trail no longer exists, has been merged into another, or can no longer be walked through from one end to the other: never propose removing it. Stage a `could-not-check` proposal with the pages and sentences, because whether a trail still belongs is the owner's decision.

## The hard part

A cheap read finds nothing wrong. One page per trail, a glance at the length, and a verdict of "unchanged" is how drift survives. The checks above are meant to be done on pages you actually read to the end: the length is often in a paragraph, a table or a PDF, and the permit rule is often on a separate page from the trail page. When a page offers more than one figure, say which one you used and why in `quote`. Equally, never "fix" a record from a third-party page when the holder's own page disagrees. A hiking site, a map or an app that gives a different length is a lead. The holder's page decides. If the holder's page is missing or refuses automated reads, that is `could-not-check` for that fact, not a reason to take the third-party figure.

The second trap is changing wording that is merely different. The record's wording is ours. Propose an edit only where a fact is different, not where the page words the same fact differently.

## What to stage

For each id: `<staging>/staged/<worker>/<id>/proposal.toml` in the format of `../proposal-format.md`. For your slice: `<staging>/staged/<worker>/report.csv` with a row for every id: `verified`, `changed`, `declined`, `could-not-check`, `refused` or `not-reached`, and in `pages` every address you opened. Do not touch the record.

## Time

About 6 to 8 minutes per record on average, and no more than an hour and a half for a slice of about 35. Stop at the budget plus a third and mark what is left `not-reached`.

## Report

Reply with under 150 words: your staging path, the count of each outcome, the three most important changes you propose, and any site that refused.
