# Season research brief

For a worker with nothing else to go on. You do this task yourself and start no subagents. Read `.claude/skills/refresh-trails/rules.md` and `.claude/skills/refresh-trails/proposal-format.md` first; this brief adds to them and does not replace them. The audit will use the same brief when it looks for a source for a season that is still an estimate.

## Goal

Every trail needs a season: when it is normally hiked. You are given a batch file of trail ids, one per line. For each trail, find a page that states when the trail is normally hiked, and stage what you found. Where no acceptable page states one, say so and leave the trail alone: it will be estimated from climate later, and an estimate is the last resort.

## Rules that matter here

- Acceptable pages: the trail's holder or a government page first; otherwise an established hiking reference, a guidebook publisher's page, or an association list. Not AllTrails, forums, social media or wikis.
- Never guess. A season found on no acceptable page is not written.
- Nothing is copied. The season phrase is in our words; the `quote` is evidence and stays at 25 words or fewer.
- Never kill a process by name or pattern. Kill only a process id you started yourself.
- Use a plain User-Agent. A site that refuses automated reads is not worked around: record the refusal and use another page.
- You never edit the repository. You stage files in `<staging>/staged/<worker>/`, where `<staging>` is the directory you are given and `<worker>` is the batch name (`season-03`).

## What to stage for each trail

One `[[proposal]]` of kind `change` in `<staging>/staged/<worker>/<id>/proposal.toml`, with:

- `[[proposal.edit]]` for `hike.season`: a short phrase in our words ("June to September", "Mid-July to early September"). Leave `old` out, because the field is absent.
- `[[proposal.edit]]` for `hike.months`: an array of month numbers. A month counts when about half of it or more is in season. For a trail walked in more than one window, list every month of every window.
- `[[proposal.edit]]` for `hike.season_basis`: see below.
- `[[proposal.edit]]` for `hike.checked`: the date the page was read. Replace the current value, with `old` copied from the record.
- A `[[proposal.append]]` to `hike.source`: the page `url`, its `publisher`, and `facts = ["season", "months"]`.
- On every edit and append, the page's own address as `page` and a quote of at most 25 words as `quote`.
- A `[proposal.history]` with `change` (a plain sentence saying what was added), `basis`, `basis_url`, `asked_by = "the dataset's own check"` and `fields = ["hike.season", "hike.months", "hike.season_basis"]`.

Strings and arrays stay on one line. The report goes in `<staging>/staged/<worker>/report.csv` with one row for every id you were given.

## Basis

- `primary`: the page is the managing body's, the trail's own association's, or for a route its author's. A season in the author's guidebook, cited through the publisher's catalogue page, is the author's.
- `sources`: no such page, but two or more pages from different publishers agree.
- `source`: no such page, and one other acceptable page.

Trip reports count only when they speak of the usual season and never of one trip, and then only as `source`. Where pages disagree, the managing body wins, and the phrase may carry the nuance ("northbound starts late February to April"). Opening dates of a hut or a park are not a walking season unless they set it.

## When nothing is found

A trail with no acceptable page gets a `report.csv` row with outcome `not-found`, every page and search tried in `pages` (at least three places), and one plain sentence in `remark`. It stays for estimating. A quiet first pass gets a second worker of another model family before the trail is left to the estimate.

## What a reviewer checks

Every trail, not a sample. The reviewer is of a different model family from the researcher, and writes `review/<name>.csv` as the refresh pipeline does.

1. The page opens and says the quoted thing.
2. The phrase is in our words.
3. The months follow the phrase and the half-month rule.
4. The basis fits the publisher (managing body or not) and the number of different publishers.
5. The page is about this trail and not a section of it or one year's event.
6. Where pages disagree, the managing body was followed.
7. No hut or park opening dates stand in for a walking season unless they set it.
8. The `hike.source` entry names `season` and `months`.

## Replacing an estimate

Used by the audit when a source turns up for a season marked `estimate`. It is a hand edit, because `refresh.py apply` cannot delete a source block. In order:

1. Set `season`, `months` and `season_basis` to the page's.
2. Delete `season_method`.
3. Delete the climate `[[hike.source]]` block.
4. Add the page's source block, with `facts = ["season", "months"]`.
5. Append a `[[history]]` entry whose `fields` name `hike.season`, `hike.months`, `hike.season_basis` and `hike.season_method`.
6. Run `python3 tools/validate.py` and `python3 tools/check_history.py --base main`.
