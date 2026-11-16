# Writing and changing records

Read this when a brief has you propose a change to a record, or write a new one. `docs/schema.md` is the schema: read it whole before writing, because the validator is strict and unknown fields are errors. `CONTRIBUTING.md` explains the tracks and the history.

## Copy an existing record of the same kind

Open two or three records that match what you are writing, and copy their field names, wording patterns and the order of tables. At the time of writing, `tonto-trail` is an official trail with a track from OpenStreetMap, `black-canyon` an official trail with its holder's track, and `hayduke-trail` and `across-utah-route` are routes with no track. If any of them is gone, pick another of the same kind.

## Rules that decide what a record may say

- Every fact comes from a page you read, named in a source entry with the facts it supports (`[[hike.source]]` for the hiker facts). The holder's or author's page is first choice, then a government page, then an established hiking reference named as the publisher. Leave a field out rather than guess it.
- Where sources disagree on a length, the record gives the holder's or author's figure, and `length_note` says what the others give. `length_km` is the published length, not a measurement of the track.
- A route (`kind = "route"`) worked out by an author gets no track unless the author's own page states terms that allow passing it on. An official trail's track may come from its holder under a stated open licence, from a US federal government work, from the holder's written permission (`stated-permission`, see `CONTRIBUTING.md`), or from OpenStreetMap (ODbL) with `tools/osm_track.py`. Read a data source's terms before using it. If they forbid redistribution, do not use it, and say so in `source.line_absent_reason`.
- A track that differs from the published length by more than 15% needs `source.length_gap_note` that explains the difference with facts: which parts are missing or extra. Summing the length by way name usually shows where it sits.
- `short_name` only with prior art: the holder's or author's own use, or established use among hikers, with the page named in `short_name_url`. Never invent one.
- `start_lonlat` and `end_lonlat` for a trail with no track only from a source that gives or pins the place (a government place-name record, the land manager's trailhead page, the author's page), to three decimals. If you cannot source a point, leave it out.
- Allowed uses (hiking, bicycles, horses, dogs), permits, fees and seasons are facts hikers rely on. Where a page lists uses, the record must not leave one out.
- Words, as in `rules.md`: "track", never "line"; "author"; miles first; short plain sentences; no dashes as punctuation.

## History

Every changed fact needs a `[proposal.history]` (see `proposal-format.md`), and a new record has its own first `[[history]]` entry. Before you propose a change to a field, look at the record's `[[history]]`: an earlier `declined` entry about the same field, or one asked for by the holder, is a decision you must not quietly reverse. The holder's or author's current page wins; a request that loses is proposed as `declined`.

## Shared files

Do not edit `README.md`, `trails.csv`, `index.geojson`, `SOURCES.md`, anything under `web/`, `tools/` or `docs/`. The orchestrator rebuilds the shared files after the proposals are applied. Where `SOURCES.md` needs a row, put it in `sources_md` on the proposal.

## Tools

- `python3 tools/osm_track.py --id <id> <relation> --dry` prints the figures for an OpenStreetMap route relation and writes nothing. Without `--dry` it writes `line.geojson`, `alternates.geojson` and `release.txt` into `<out>/<id>/`. Use `--out <staging>/staged/<worker>` so they land beside your `proposal.toml`; the directory `<staging>/staged/<worker>/<id>/` must exist first. Read `--help` and the header of the file.
- `python3 tools/gpx_track.py` does the same for a GPX file that a holder or hiker has sent.
- `python3 tools/elevation.py` writes `elevation.json` from a record's track inside the repository, so it runs in the apply phase and not in a worker's staging directory.
- `python3 tools/validate.py` checks the repository as it is, so it cannot check your staged work. To test a new record, copy it into a scratch copy of the repository (a plain `cp -r` into the temporary directory) and run the validator there. Errors that name your id are yours. Stale counts in shared files are not.
