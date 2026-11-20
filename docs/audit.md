# The monthly audit of everything

A written checklist for the owner. It does not repeat the refresh runbook; it points at it. Work
down the list in order and stop at the first step that fails.

## Records and places

1. **Refresh the records.** Run the `/refresh-trails` skill (the full run once a quarter, `light`
   in the months between). It verifies every record against the pages it cites, re-checks the
   left-out list, looks for missing trails and updates tracks and emblems. The runbook is
   `.claude/skills/refresh-trails/SKILL.md`; this checklist adds to it and does not replace it.
2. **Check the links.** `python3 tools/refresh.py links` lists every address a record cites that
   no longer answers (`--limit 20` is a quick trial). Fix each one in a record with a history
   entry.
3. **Validate the data.** `python3 tools/validate.py` must end `OK <n> trails`. It fails a record
   with no `places_checked`, and one whose track has changed since its places were measured.
4. **Check the history.** `python3 tools/check_history.py --base origin/main` must end
   `OK history`. A changed fact needs a new history entry.
5. **Run both test suites.** `python3 -m unittest discover tools/tests` and
   `python3 -m unittest discover -s web/tests` must both pass.
6. **Check the places.** `.venv-places/bin/python tools/place_trails.py --check --refresh`
   downloads every outline again (without `--refresh` it reuses the files already in the cache,
   which are the ones first downloaded), measures every track again and prints each difference
   from the records, one per line. The venv is made as `tools/place_trails.py --help` says. For
   each line:
   (a) a place gained or lost by a trail: run `.venv-places/bin/python tools/place_trails.py propose`,
   read the line, and apply it only when the new outline is right;
   (b) a boundary that moved (a new source version): the owner rules whether the new outline
   replaces the old one;
   (c) a place that crossed the 3-trail line: its page appears or goes, so check its links and the
   counts that name it.
   The monthly workflow `.github/workflows/places.yml` runs this step by itself and fails with
   the list; this step is the one you run when it has failed, and before a release.
7. **Review the `stated` placements by hand.** A trail with no track is placed from a page, and no
   tool can measure that again. For each record with a place whose `basis` is `stated`, open the
   cited page again and confirm that it still names the trail in that place. The date of the last
   look is the record's `places_checked`; set it again when you have looked, and add a history
   entry when a placement changes.
8. **Build the site** with `python3 web/build.py --out _site` and read the places page, one park
   page, one range page and one wilderness page.

## Seasons

Every trail has a season. Where a page states one, the season is that page's. Where none does, the season is an estimate: set by a reviewer from the trail's climate and the seasons of similar trails, with its confidence on the record (`docs/season-judging.md`). Where pages from at least two publishers state different seasons and none is the trail's own, the season is set by judgement from all of them. The aim of this audit is that estimates shrink over time, and that none goes stale unnoticed.

The blind test behind the estimates has two figures, always read together: 114 of 148 (77 percent) had their first and last months within a month of the page's, and 105 (71 percent) also had no wrong gap in the middle. The 75 percent bar was set on the first measure; the second is below it. The owner decided that the estimates ship with both stated.

1. Search afresh for a page that states the season of every trail still marked `estimate`. List them with `python3 tools/estimate_season.py estimates`. For each, follow `docs/season-research.md`: the trail's holder or a government page first, then an established hiking reference, a guidebook publisher's page or an association list. When a page states a season, replace the estimate through `tools/refresh.py` (stage a proposal, then `python3 tools/refresh.py collect` and `python3 tools/refresh.py apply`): give the page's season and months, the basis (`primary`, `sources` or `source`), the page as a `[[hike.source]]` naming `season` and `months`, and remove the climate source and `season_method`. A change to the season gets a `[[history]]` entry like any other fact. Then run `python3 tools/season_judge.py inputs --points` so that the record of estimate inputs drops the trail. A trail with no page found stays an estimate, and nothing else about it changes.
2. Check that no estimate has gone stale: `python3 tools/estimate_season.py check`. It works offline and downloads nothing. For every estimate it compares the digest of the trail's current track and location with the one recorded in `tools/season_inputs.json` when the season was set, and lists each trail where they differ or none is recorded. The listing is a flag, not a rewrite. For each trail listed, build its packet (`python3 tools/season_judge.py packets --out /tmp/season-packets`; it writes a packet for every trail and reads the climate, which is a large download the first time and cached after), look at what changed, and either keep the season or set it again by judgement. Then run `python3 tools/season_judge.py inputs --points <id>` to record the new digest. The climate normals are a fixed published dataset (CHELSA, 1981 to 2010), so they do not change from month to month and are not read again; `python3 tools/season_judge.py inputs <id>` (with the network) also records the machine estimate and the climate digest at the time, if a person wants them. The check also fails when the blind test of the method (`tools/season_blind_test.json`) is below its bar on the first-and-last-months measure (77 percent when set, against a bar of 75; the stricter figure, 71 percent, which also needs no wrong gap in the middle, is recorded beside it).

The same check runs on its own on the first of each month (`.github/workflows/season-check.yml`), so a changed estimate is noticed even when the audit is late. The audit is still the step that acts on it.
