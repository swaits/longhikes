# Contributing

Thank you for helping correct or extend this dataset. Please keep changes small: one trail per change where you can.

## How to send a change

Issues and pull requests are taken at https://github.com/swaits/longhikes. That repository mirrors the maintainer's own, https://git.swaits.com/swaits/longhikes; a change accepted on GitHub is passed on to it automatically.

- You do not need git to report something. Every trail's page on https://longhikes.org has a "Report a problem" link that opens a short form, and the repository's issue forms cover a wrong record, a missing trail, and a request from a steward or author to remove or re-credit a track or a logo.
- To fix a record yourself, use "Edit this record" on the trail's page, or edit `<id>/trail.toml` in a fork, and open a pull request. Say where each changed fact can be checked.
- Every pull request is checked automatically by `tools/validate.py`, `tools/check_history.py` and the site's tests. A person still reviews it, most of all where a track is added or changed.

## Correct a trail

1. Edit only that trail's directory.
2. Keep every field name in `trail.toml` (see docs/schema.md). Say in the commit message which fields changed and why.
3. If you change a track, name its source and licence. A track may only be included when its source's terms allow redistribution. United States federal data is public domain. OpenStreetMap data is ODbL and needs the credit "© OpenStreetMap contributors". A track whose holder, author or recorder has stated in writing that it may be shared, without naming a licence, uses `licence = "stated-permission"`: quote the statement exactly in `source.licence_text`, say who made it (by role), where (a page or issue address) and when. It is not public domain or Creative Commons, and nothing may present it as either. If a publisher's own track may not be passed on, do not include it: keep the record, use an OpenStreetMap track if one is already recorded for the trail, or include no track and say why in `source.line_absent_reason`.
4. Update `release.txt` when track files change: source, licence, and the date read.
5. Add an entry at the end of the record's `[[history]]`: the date, what changed, the fields, the page it was read on, who asked (by role, never a private person's name) and the outcome. See "History and conflicts" below.
6. Rebuild the generated files and check everything:

```bash
python3 tools/build_index.py
python3 tools/validate.py
python3 tools/check_history.py
```

The second command must print `OK <n> trails`. The third must print `OK history`: it fails when a fact changed and no new history entry names the field. Run it before you send a change, whether you are a person or an agent. It compares your work with `origin/main` (or `main`), so fetch first if you have not lately. Do not remove or reword an entry that is already there.

## History and conflicts

Every record has a `[[history]]` list, oldest first, which says who asked for each change, on what evidence, and which requests were turned down. Git has the diffs; the history has the reasons, so that someone who later asks for the opposite change can see what was decided.

- Add one entry for each change to a fact (the list of facts is in docs/schema.md and `python3 tools/check_history.py --facts`), at the end of the file.
- `python3 tools/check_history.py` prints the earlier entries about each field you changed. If one was `declined`, or was asked for by someone other than the dataset's own check, read it before you go on.
- The holder's or the author's own current page wins. Where two requests conflict, the earlier decision stands unless the later one brings new evidence from such a page. The request that loses is recorded as an entry with the outcome `declined` and its reason, and nothing else in the record changes.
- Say who asked by role: "a hiker", "the trail association's president", "the route's author".

## Add a trail

A trail belongs here when it meets the inclusion rule in README.md: a named, continuous walking route, or a named loop, of at least 50 miles (80 km) (a few well-known routes of 60-80 km are also listed), in the United States or Canada. It is either a trail that a land agency or a trail association designates, maintains and publishes as one trail, or a route: a high route, a traverse or a loop of linked trails that a hiker or a small group worked out and published.

A route whose author chooses not to publish a track is still added, with no track included, pointing to where the route is got from. No track for it is included from any source, OpenStreetMap included. The rule is in README.md, section "Inclusion rule"; the fields are in docs/schema.md.

Before suggesting or adding a trail, look at https://longhikes.org/left-out/ first. It lists the trails that were considered and left out, with the reason and the date for each one; the same list is `left-out.toml` at the top of this repository. If the trail is there and the facts have changed since the decision, open an issue with a page that shows the change. If a trail on that list is added, its entry is removed from `left-out.toml` in the same change; `tools/validate.py` refuses an entry that matches a listed trail.

To add one:

1. Create a directory named with a new stable `id`: lower-case words joined by hyphens. It never changes afterwards.
2. Write `trail.toml` with every required field in docs/schema.md. Give `short_name` only if the trail's holder or author uses an abbreviation, or hikers commonly do, and put the page where you saw it in `short_name_url`; never make one up.
3. Add `line.geojson` only if the track may be shared (see above), plus `release.txt`.
   For a track from an OpenStreetMap route relation, create the trail directory and `trail.toml` first, then run `python3 tools/osm_track.py RELATION_ID --id TRAIL_ID` (Python standard library only; add `--dry` to print the figures and write nothing). It fetches the relation and its sub-relations through Overpass, writes `line.geojson`, `alternates.geojson` (only when there are side ways) and `release.txt`, and prints the way counts, the measured length in km and the number of parts for `[verification]` and `[osm]`. It will not replace an existing `line.geojson` without `--force`.
   To point to other good pages about the trail (a wiki or encyclopedia article), add a `[[link]]` table for each; the trail's own page goes in `hike.official_url` instead.
4. Add a logo only as `shield.svg` or `shield.png`, and name its holder in `shield.logo_owner` and where the art came from in `shield.logo_source`.
5. Write the first `[[history]]` entry, with `fields = ["record"]`, the date, who asked for the trail (by role) and the page that shows it.
6. Run the three commands above.

## Refresh a trail from its source

1. Read the trail's `[source]` section. `source.url` is where to ask for the track; `source.discovery` says how to tell whether the source has changed.
2. Fetch the new track from that source. Do not pin a dated file name where the source offers a current layer or relation.
   For an OpenStreetMap relation, `python3 tools/osm_track.py RELATION_ID --id TRAIL_ID --force` does steps 2 and 3 and prints the figures for step 4 (see "Add a trail").
3. Replace `line.geojson` (and `alternates.geojson` or `line-<source>.geojson` where present), keeping coordinates in longitude, latitude order. The published copy rounds coordinates to 6 decimal places and uses compact JSON.
4. Update `source.source_checked`, `release.txt`, and the `[verification]` section (measured length of the new track, and the difference from `length_km`).
5. If the measured length differs from `length_km` by more than 15%, explain why in `source.length_gap_note` (for example: the trail is partly unbuilt, or the published length counts side trails).
6. Add a `[[history]]` entry saying the track was refreshed and from what. Run `python3 tools/build_index.py`, then `python3 tools/validate.py` and `python3 tools/check_history.py`.

## The monthly refresh

About once a month the maintainer runs a refresh of the whole dataset. Every record is checked again against the pages it cites and against its holder's or author's current site, the trails in `left-out.toml` are checked against the reason they were left out, and the web is searched for trails and routes that are missing. Tracks whose source has changed and emblems that were not found are looked at again. Nothing it proposes reaches a record until a second reader has opened the cited pages and the maintainer has ruled on what belongs.

It is run by an agent, started with `/refresh-trails` in Claude Code (`/refresh-trails light` for the short version that only verifies records and left-out entries). The runbook, the briefs given to each worker, the rules they follow and the format they stage proposals in are in `.claude/skills/refresh-trails/`. The mechanical steps are in `tools/refresh.py`: `preflight`, `slices`, `links`, `collect` and `apply`. Staged work lives in `refresh/<date>/`, which git ignores, so that none of it can reach a commit.

You do not need any of this to report something. A trail's page has a "Report a problem" link, and a request from a holder or author on the issue tracker is read in the next refresh and sooner if it is simple.

## Style

- Plain, short English. No sales talk.
- Records state facts and sources. If a term comes from a source page, quote the sentence and give the page in `source.licence_text` or SOURCES.md.
- Do not add personal names or email addresses, local file paths, or notes about how a change was produced. This is about contributors and about how a change was made. The published name of a route's author, or of a guide's author, is a fact about the route and belongs in the record (`route.creator`, `guide.author`).
