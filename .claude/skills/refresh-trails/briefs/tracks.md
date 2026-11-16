# Tracks: trails that have none, and tracks whose source has changed

Read `../rules.md`, `../proposal-format.md` and `../records.md` first. You do this task yourself and start no subagents.

You receive a staging directory `<staging>`, a worker name (for example `tracks-1`) and a list of trail ids in two groups: A, records that have no track, and B, records whose track source may have changed. Stage your work in `<staging>/staged/<worker>/`. If your task has you using Overpass, you are the only worker that does.

## What this is for

A track is what lets a hiker see where a trail goes. A record without one says why (`source.line_absent_reason`), and often the reason has passed: a relation has since been added to OpenStreetMap, or the holder has published open data. A track that came from a source goes stale when the source is edited. Done means that for each id you either have a staged track with the figures that go with it, or an honest statement of why none can be included.

## Group A: records with no track

1. Read the record: `source.line_absent_reason`, `[osm]`, `kind`. A route worked out by an author (`kind = "route"`) never gets a track unless the author's own page states terms that allow passing it on; quote them if they exist, and otherwise move on.
2. Look for a track that may lawfully be included, in this order: the holder's own open data under a stated open licence (or a US federal government work), the holder's written permission (the holder's statement in the public issue tracker counts, quoted with its address), then an OpenStreetMap route relation (ODbL). Read the data source's terms. If they forbid redistribution or commercial use, do not use it, and say so.
3. For an OpenStreetMap relation, first run `python3 tools/osm_track.py --id <id> <relation> --dry` and read the figures: the number of ways, the measured length, the parts. Compare with the published `length_km`. If it is within 15% and the ways are the trail (no other trail's name among them), run it again without `--dry`, with `--out <staging>/staged/<worker>`, so the files land beside your proposal. A way that carries another trail's name is excluded with `--exclude-name`, and the exclusion is said in the record.
4. Beyond 15%, find out why before staging anything: sum the length by way name, look at which parts are missing or extra, and write `source.length_gap_note` with facts. If the track is mostly another trail, or mostly unbuilt, do not stage it and say why.

## Group B: tracks whose source has changed

`source.discovery` says how to tell whether the source has a newer release. For an OpenStreetMap relation, read the relation's version and timestamp (`rel(ID); out meta;`) and compare with `release.txt` and `[osm]`. If it has not changed, stage a `verified` proposal. If it has, fetch it with `osm_track.py --force --out <staging>/staged/<worker>`, compare the new figures with the old (`verification.measured_km`, `parts`), and look at what moved: a track that has doubled or lost a third is more often an editing accident than a change in the trail. Stage a change only where the new track is the better description of the same trail. For a track from a holder, check that the holder's page and its terms still say what the record says.

## What to stage

For each track you propose, a `change` proposal for the record (or a `new-record` if it is staged with a new record) that has:

- `[[proposal.file]]` entries for `line.geojson`, `alternates.geojson` where the tool wrote it, and `release.txt`, with `source_url` and, for a file that already exists, `old_sha256` (`sha256sum <id>/line.geojson`). Do not stage `elevation.json`: it is computed from the track in the apply phase.
- edits for the fields the track changes: `source.status`, `source.licence`, `source.licence_text`, `source.attribution`, `source.osm_only`, `source.line_source`, `source.line_file`, `source.source_checked`, `source.redistributable`, `source.length_gap_note` where needed, `source.line_absent_reason` removed where a track now exists, `osm.relation` and `osm.note`, and the `[verification]` figures (`verified`, `date`, `measured_km`, `difference_percent`, `parts`, `note`) as the tool printed them. For a field the tool computes, `page` is the relation or data page and `quote` is the line of tool output.
- `[proposal.history]`, because a track change is a change to `source.line_file`.
- `sources_md`: the row `SOURCES.md` needs.

Records are copied for form from existing ones with the same kind of track (`../records.md`). Report with `report.csv`: for each id `new` (a track is staged), `replaced` (a changed track), `verified`, `none-exists` (no lawful track is available, with the pages looked at), `refused`, `could-not-check` or `not-reached`.

## The hard part

Overpass overloads easily. `osm_track.py` tries several endpoints by itself, one request at a time. Never run two fetches at once, and do not start another tool that calls Overpass while one runs. If all endpoints are down, say so and stop the track work. Do not build a track by hand and do not trace one from an app or a map. A track you cannot source is a record with an honest absent reason, which is a perfectly good record.

## Time

About 10 minutes per id. Stop at the budget plus a third.

## Report

Reply with under 150 words: staging path, counts by outcome, any track beyond 15% of the published length and what explains it, and whether Overpass was down.
