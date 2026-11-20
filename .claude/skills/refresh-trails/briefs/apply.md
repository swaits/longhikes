# Apply the accepted proposals and rebuild

Read `../rules.md` and `../proposal-format.md` first. You do this task yourself and start no subagents. This is the one brief that changes the repository: it is the only worker allowed to, and only one runs at a time.

You receive a staging directory `<staging>`, on a branch the orchestrator has checked out, and a clean tree. You do not commit, push or switch branches.

## What this is for

Everything staged so far was written without touching the repository, so that many workers could run at once. This step brings the accepted proposals in, in one place, one by one, and leaves the repository in a state the orchestrator can commit: records changed, shared files rebuilt, every check green. Done means all accepted proposals are applied or reported as refused with the reason, the validator, all test suites and the history check pass, and `CHANGELOG.md` has an entry for the work.

## Steps

1. `python3 tools/refresh.py collect`, then read `<staging>/summary.md`. The count of proposals with status `accepted` must match what the orchestrator told you. Anything with the status `proposed`, `held`, `rejected` or `invalid` is not applied.
2. `python3 tools/refresh.py apply --dry-run`. Read what would be refused. A refusal means the record no longer says what the proposal expects (someone changed it, or two proposals touch the same field), and it is reported, not worked around. Never edit a record by hand to make a proposal fit.
3. `python3 tools/refresh.py apply`. It changes the named lines and adds the history entries.
4. For each new track (a proposal with a track file), `python3 tools/elevation.py <id>`: it writes `elevation.json` from the track. For a replaced track, `--force`.
5. Add the rows named in `sources_md` fields to `SOURCES.md`, by hand, in the existing form and place. Where a record was removed or a track dropped, take the row's counts and lists with it.
6. Place each new record, and each record whose track was replaced: the validator fails a record with no `places_checked`, or whose track changed after its places were measured. For an id with a track, run `.venv-places/bin/python tools/place_trails.py propose`, read the proposal for those ids, and `apply` it (the tool's libraries are in that virtual environment, set up from `tools/place_trails.requirements.txt`). For a new trail with no track, find the places it is in on a page that names the trail there, and run `place_trails.py stated <id> <kind> <slug> <page address> "<the sentence that says so>"` for each; where it is in none, run `place_trails.py stamp <id>`. Report any place you could not find in the registry or the outlines instead of inventing it.
7. `python3 tools/build_index.py` rebuilds `trails.csv`, `index.geojson` and the counts in `README.md`. Do not edit those files by hand. It also appends any new record to the end of `trail-numbers.txt` (a trail's permanent number); commit that line with the record and never change, remove or reorder the lines already there.
8. `python3 tools/validate.py` must end `OK <n> trails`. `python3 tools/check_history.py` must end `OK history`. A failure that names a record you changed is yours: find the cause, and if it is a proposal that was wrong, say so in your report and revert that record from git (`git checkout -- <id>`, then apply the rest without it, by `--only`). A failure in a record you did not touch is reported.
9. Run all the test suites: `python3 -m unittest discover tools/tests` and `python3 -m unittest discover -s web/tests`. The web tests hold counts of trails, tracks and emblems; if one fails only because a count moved with the change, update that count. Any other failure is a real failure: stop and report it.
10. Write the entry at the top of `CHANGELOG.md`, in the voice of the entries already there (read the top two): a dated heading with a short title, then plain bullets saying what changed for contributors and, where a visitor can see it, what a visitor will see. State the counts that changed (trails, tracks, emblems). Say what was checked and left unchanged only where it matters. The orchestrator reads and edits it.

## The hard part

Order and exactness. A proposal applied against a record that changed in the meantime is the way a good record gets damaged, which is why `apply` refuses it; do not defeat that check. Rebuild the shared files after the last apply, not before. And the history check compares your work with the base branch, so run it with the base the orchestrator names (`--base REV`), not by guess.

## Report

Reply with under 200 words: the counts (applied, refused with reasons, already applied), the ids with a new or replaced track, the validator and test tails, and anything you did that the proposals did not say.
