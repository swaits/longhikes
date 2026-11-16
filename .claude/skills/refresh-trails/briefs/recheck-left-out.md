# Re-check the trails that were left out

Read `../rules.md`, `../proposal-format.md` and `../records.md` first. You do this task yourself and start no subagents.

You receive a staging directory `<staging>`, a worker name (for example `left-out-01`) and a slice file `<staging>/slices/<worker>.txt` listing ids of entries in `left-out.toml`, one per line. Stage your work in `<staging>/staged/<worker>/`.

## What this is for

`left-out.toml` lists trails that were looked at and left out, each with the specific fact that decided it. It is shown to the public as "Considered and left out", so that a trail is not suggested and argued over again from nothing. A decision can go stale: a trail that was too short gains miles, a proposed trail gets built, a National Scenic Trail is designated, a closed trail reopens, a page the decision rests on moves. Done means that for every entry in your slice you know whether the deciding fact still holds on the page, and every entry that has changed has a proposal.

## What to do for each entry

1. Read the entry (`left-out.toml`, found by `id`), and `docs/schema.md`, section "left-out.toml", for the reasons. Note `reason`, `note`, `source_url`, `decided`, and for `waiting` entries `waiting_for`.
2. Open `source_url`. Then open the holder's or author's current page for the trail, and one government page where there is one. Check that the deciding fact is still what the entry says it is: the length against the 50 mile floor, the surface, the owner or purpose, the state of construction, whether it can be walked through.
3. For an entry whose `reason` is `waiting`, `waiting_for` is the one condition that would change the decision. Look specifically for whether that has happened: a designation made, a length settled, a gap closed, a route published. Say what you found and where, even when nothing has changed.
4. A trail the dataset now lists (look in `trails.csv` by id and name) must not stay in this file. Report it.
5. Decide:
   - Still holds: stage a `verified` proposal for the entry (`target = "left-out"`) with the pages opened. Nothing is applied for it; it records that the check happened.
   - The page says something different but the decision stands: a `change` proposal with `target = "left-out"` and edits to `note`, `length_mi` and `length_km` (they must agree), `source_url`. `decided` is left alone because the decision has not changed.
   - The fact that decided it no longer holds, or the `waiting_for` has happened: a `candidate` proposal with your recommendation (`add` if it now clearly meets the inclusion rule, otherwise `owner`) and the sentence that changed. Do not write the record and do not remove the entry. That is the owner's decision.
   - The entry's page is gone and no other page shows the fact: `could-not-check`.

## The hard part

For `waiting` entries a quick look at the trail's home page is not enough. "Waiting for designation" is answered by the agency's page, not by the advocacy group's. "Waiting for a settled length" is answered by the holder's current length, which may be in a map, a PDF or a news release. Read the whole page and say where on it the fact sits. Treat a hopeful announcement (a bill introduced, a section planned, a ribbon cutting scheduled) as not yet meeting the condition, and quote it so the owner can judge.

## What to stage

Per entry, `<staging>/staged/<worker>/<id>/proposal.toml`. For the slice, `<staging>/staged/<worker>/report.csv` with a row for every id: `verified`, `changed`, `could-not-check`, `refused` or `not-reached`, with the pages opened. Entries you recommend to the owner have outcome `changed` and a `candidate` proposal.

## Time

About 5 minutes per entry; at most 90 minutes for a slice. Stop at the budget plus a third and mark the rest `not-reached`.

## Report

Reply with under 120 words: staging path, counts, and every entry where the deciding fact has changed.
