# The monthly audit of everything

A written checklist for the owner. It does not repeat the refresh runbook; it points at it. Work
down the list in order and stop at the first step that fails.

1. **Refresh the records.** Run `/refresh-trails` (the full run once a quarter, `light` in the
   months between). It verifies every record against the pages it cites, re-checks the left-out
   list, looks for missing trails and updates tracks and emblems. The runbook is
   `.claude/skills/refresh-trails/SKILL.md`; this checklist adds to it and does not replace it.
2. **Check the links.** `python3 tools/refresh.py links` lists every address a record cites that
   no longer answers. Fix each one in a record with a history entry.
3. **Validate the data.** `python3 tools/validate.py` must end `OK <n> trails`. It fails a record
   with no `places_checked`, and one whose track has changed since its places were measured.
4. **Check the history.** `python3 tools/check_history.py --base origin/main` must end
   `OK history`. A changed fact needs a new history entry.
5. **Run both test suites.** `python3 -m unittest discover tools/tests` and
   `python3 -m unittest discover -s web/tests` must both pass.
6. **Check the places.** `python3 tools/place_trails.py --check` downloads the current outlines,
   measures every track again and prints each difference from the records, one per line:
   - a place gained or lost by a trail: re-run `place_trails.py propose`, read the line, and
     apply it only when the new outline is right;
   - a boundary that moved (a new source version): the owner rules whether the new outline
     replaces the old one;
   - a place that crossed the 3-trail line: its page appears or goes, so check its links and the
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
