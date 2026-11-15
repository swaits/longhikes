# Contributing

Thank you for helping correct or extend this dataset. Please keep changes small: one trail per change where you can.

## How to send a change

Issues and pull requests are taken at https://github.com/swaits/longhikes. That repository mirrors the maintainer's own, https://git.swaits.com/swaits/longhikes; a change accepted on GitHub is passed on to it automatically.

- You do not need git to report something. Every trail's page on https://longhikes.org has a "Report a problem" link that opens a short form, and the repository's issue forms cover a wrong record, a missing trail, and a request from a steward or author to remove or re-credit a track or a logo.
- To fix a record yourself, use "Edit this record" on the trail's page, or edit `<id>/trail.toml` in a fork, and open a pull request. Say where each changed fact can be checked.
- Every pull request is checked automatically by `tools/validate.py` and the site's tests. A person still reviews it, most of all where a track is added or changed.

## Correct a trail

1. Edit only that trail's directory.
2. Keep every field name in `trail.toml` (see docs/schema.md). Say in the commit message which fields changed and why.
3. If you change a track, name its source and licence. A track may only be included when its source's terms allow redistribution. United States federal data is public domain. OpenStreetMap data is ODbL and needs the credit "© OpenStreetMap contributors". If a publisher's own track may not be passed on, do not include it: keep the record, use an OpenStreetMap track if one is already recorded for the trail, or include no track and say why in `source.line_absent_reason`.
4. Update `release.txt` when track files change: source, licence, and the date read.
5. Rebuild the generated files and check everything:

```bash
python3 tools/build_index.py
python3 tools/validate.py
```

The second command must print `OK <n> trails`.

## Add a trail

A trail belongs here when it meets the inclusion rule in README.md: a named, continuous walking route, or a named loop, of at least 50 miles (80 km) (a few well-known routes of 60-80 km are also listed), in the United States or Canada. It is either a trail that a land agency or a trail association designates, maintains and publishes as one trail, or a route: a high route, a traverse or a loop of linked trails that a hiker or a small group worked out and published.

A route whose author chooses not to publish a track is still added, with no track included, pointing to where the route is got from. No track for it is included from any source, OpenStreetMap included. The rule is in README.md, section "Inclusion rule"; the fields are in docs/schema.md.

To add one:

1. Create a directory named with a new stable `id`: lower-case words joined by hyphens. It never changes afterwards.
2. Write `trail.toml` with every required field in docs/schema.md. Give `short_name` only if the trail's holder or author uses an abbreviation, or hikers commonly do, and put the page where you saw it in `short_name_url`; never make one up.
3. Add `line.geojson` only if the track may be shared (see above), plus `release.txt`.
   For a track from an OpenStreetMap route relation, create the trail directory and `trail.toml` first, then run `python3 tools/osm_track.py RELATION_ID --id TRAIL_ID` (Python standard library only; add `--dry` to print the figures and write nothing). It fetches the relation and its sub-relations through Overpass, writes `line.geojson`, `alternates.geojson` (only when there are side ways) and `release.txt`, and prints the way counts, the measured length in km and the number of parts for `[verification]` and `[osm]`. It will not replace an existing `line.geojson` without `--force`.
   To point to other good pages about the trail (a wiki or encyclopedia article), add a `[[link]]` table for each; the trail's own page goes in `hike.official_url` instead.
4. Add a logo only as `shield.svg` or `shield.png`, and name its holder in `shield.logo_owner` and where the art came from in `shield.logo_source`.
5. Run the two commands above.

## Refresh a trail from its source

1. Read the trail's `[source]` section. `source.url` is where to ask for the track; `source.discovery` says how to tell whether the source has changed.
2. Fetch the new track from that source. Do not pin a dated file name where the source offers a current layer or relation.
   For an OpenStreetMap relation, `python3 tools/osm_track.py RELATION_ID --id TRAIL_ID --force` does steps 2 and 3 and prints the figures for step 4 (see "Add a trail").
3. Replace `line.geojson` (and `alternates.geojson` or `line-<source>.geojson` where present), keeping coordinates in longitude, latitude order. The published copy rounds coordinates to 6 decimal places and uses compact JSON.
4. Update `source.source_checked`, `release.txt`, and the `[verification]` section (measured length of the new track, and the difference from `length_km`).
5. If the measured length differs from `length_km` by more than 15%, explain why in `source.length_gap_note` (for example: the trail is partly unbuilt, or the published length counts side trails).
6. Run `python3 tools/build_index.py`, then `python3 tools/validate.py`.

## Style

- Plain, short English. No sales talk.
- Records state facts and sources. If a term comes from a source page, quote the sentence and give the page in `source.licence_text` or SOURCES.md.
- Do not add personal names or email addresses, local file paths, or notes about how a change was produced. This is about contributors and about how a change was made. The published name of a route's author, or of a guide's author, is a fact about the route and belongs in the record (`route.creator`, `guide.author`).
