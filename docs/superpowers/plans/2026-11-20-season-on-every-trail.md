# A Season on Every Trail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every one of the 223 trail records carries `hike.season`, `hike.months` and where the season came from, and the site says which seasons are estimates.

**Architecture:** One new provenance field pair on `[hike]` (`season_basis`, `season_method`) checked by a new `tools/season.py` that `tools/validate.py` calls. The 109 existing seasons are classified by a proposed table a person reviews. The 114 missing ones are researched in batches, then the remainder are estimated by `tools/estimate_season.py`, whose rule is a pure function over monthly climate normals; the download (`tools/season_climate.py`) is separate and cached outside the repository. Seasons are written through the existing `tools/refresh.py` proposal and apply pipeline, so no record is re-serialised and every change carries a `[[history]]` entry. Site code changes only in the last ship.

**Tech Stack:** Python 3.12 standard library only (as CI has no packages), `unittest`, TOML records, the static site in `web/olt/` with `web/assets/app.js`, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-20-season-on-every-trail-design.md`. The owner has also ruled that a route author's stated season counts as `primary`.

## Commands (all from the repository root)

- Validator: `python3 tools/validate.py` (prints errors; ends with a non-zero exit on any).
- History check: `python3 tools/check_history.py --base main`.
- Tool tests: `python3 -m unittest discover tools/tests` (about 10 s). One file: `python3 -m unittest discover tools/tests -p "test_season_basis.py" -v`.
- Web tests: `python3 -m unittest discover -s web/tests` (builds the site; takes over two minutes, so run it in the background and read the tail). One file: `python3 -m unittest discover -s web/tests -p "test_facets.py" -v`.
- Site build: `python3 web/build.py --out _site`.
- A ship is done only when all five of the above pass on the branch and the ship's `CHANGELOG.md` entry is in the same commit.

## Global Constraints

- Every change to a record fact gets a `[[history]]` entry in the same change (`docs/schema.md`, section `[[history]]`; `python3 tools/check_history.py --base main` must pass). `season_basis` and `season_method` are facts for history purposes.
- Every ship adds a `CHANGELOG.md` entry, newest first, headed `## <date> - <title>`, in the same commit as the ship.
- Counts shown are exact: computed from the records at build time, never typed.
- An estimate must never read as a stated fact: it says "About", carries a note, is marked in rows, and is left out of structured data.
- The words record, tier, wave, held, listing, entry and the other dataset terms in `BANNED` (`web/tests/test_facets.py`) never appear on browsing pages. Site copy in this plan is already worded to avoid them; keep it so.
- Miles and feet come first on the site (`words.length`, `words.elevation` already do this; no new figure is written another way).
- Never kill a process by name or pattern (`pkill`, `killall`). Kill only a PID you started yourself, and only if it must stop.
- Tools use Python standard library only; the estimator runs in CI.
- House wording in new `.md` and workflow text: no em or en dashes, no " - " as punctuation, no all-capital emphasis words.
- A fact found on no acceptable page is never guessed, except season, which may be estimated and must then say so. Acceptable page: the trail's holder or a government page first; else an established hiking reference, guidebook publisher's page or association list. Not AllTrails, forums, social media or wikis.
- Work on a branch, never directly on `main`. Do not push; shipping is the owner's call.

## Decisions the design left open

| Question | Decision |
|---|---|
| Climate source | Settled by Task 11's trial on twelve trails, by licence, then coverage of the US, Canada and Alaska, then fit. |
| Sampling | One point per 50 km of track, at least 3, at most 12, evenly spaced along the track. No track: `hike.start_lonlat` and `hike.end_lonlat`; neither: the centre of the box of the record's first region (`web/place-bounds.toml`), flagged. Elevation per point from `<id>/elevation.json` `profile` (`[km, metres]` pairs); no profile: `high_point_m` for the highest point and the climate source's own cell elevation for the rest. |
| High and low ground | High ground is the sample points at or above the upper quartile of the profile (at least one point); low ground is the points at or below the median. |
| Measures | Per month: mean daily high temperature (`tmax_c`) and mean snow depth (`snow_cm`) at the point's elevation, normals period 1991 to 2020, fixed so a re-run changes only when records, tracks or the rule change. A month is in season when, over the high-ground points (median), `tmax_c >= cold_c_min` and `snow_cm <= snow_cm_max`, and over the low-ground points (median) `tmax_c <= heat_c_max`. If the source has no snow measure, the `snow_cm` test is dropped and `cold_c_min` alone stands in. |
| Fit | `fit_params` grid-searches the three numbers on the sourced trails whose id hashes even; the figure reported and tested is on those that hash odd; the numbers then shipped are refit on all. The figure on the site is the all-trails one, labelled as fitted on the same trails. |
| Bar (owner to confirm) | At least 75 percent of the held-out sourced trails have the estimated season within one month at each end, and at least 90 percent of sourced trails have enough data to be estimated at all. If either fails, estimates are not written (Task 17 stops). |
| Month arcs | A season's span is the smallest circular arc covering all its months (December to February is one arc). Grades: exact (same first and last month), within one (each end within one month), worse. |
| Phrase for an estimate | Built from the months, `"June to September"`; runs separated by "and"; twelve months `"All year"`. The site adds "About". |
| `season_method` | One fixed sentence from `season.method_sentence(...)`, naming the dataset, the period, the number and kind of points and the rule version. |
| Estimate source entry | One `[[hike.source]]` for the climate dataset, `facts = ["season", "months"]`. |
| Replacing an estimate | By hand-edit (a worker deletes the climate source block and `season_method`, sets the basis), because `refresh.py apply` cannot delete a source block. Validator, history check and the audit step guard it. |
| Batch size for research | 10 trails, grouped by region group, so 114 trails make 12 batches. A group of more than 10 is split, one of fewer than 5 is joined to its neighbour. |
| Where research and classification are staged | In the refresh pipeline's staging directory (`refresh/<date>/`, git-ignored), as `proposal.toml` files that `tools/refresh.py collect` and `apply` already handle. |
| Month rows | Every row writes a `Season` fact; CSS hides it unless the list is a month list or a month is chosen. The first screen is unchanged. |
| Leave-out control | A checkbox "Leave out estimated seasons", parameter `stated=1`, disabled until a month is chosen. |
| Home of the researchers' brief | `docs/season-research.md`, linked from `docs/audit.md`, so the audit's fresh search for sources uses the same brief. |

## Shared files (a sibling plan changes some of these at the same time, in another worktree)

Keep every edit to these small and local, and rebase onto the other branch before each ship.

| File | Our edit | Merge risk |
|---|---|---|
| `tools/validate.py` | `HIKE_KEYS` line, one `check_season(...)` call in `check_hike`, ship 4: one more call in `main` | High: edit in `check_hike` body |
| `docs/schema.md` | `[hike]` rows and one sentence in the `[hike]` intro, `[[history]]` fact lists | High |
| `tools/trail_history.py` | `_TABLES["hike"]` tuple, `FACTS_TEXT` | Medium |
| `<id>/trail.toml` (223 files) | `[hike]` lines, `[[hike.source]]` blocks, appended `[[history]]` entries | High where both add history to one file: the later merge keeps both entries in date order |
| `CHANGELOG.md` | One entry at the top per ship | Medium: keep both entries, newest first |
| `docs/audit.md` | `## Seasons` section (create the file if absent; add only the section if present) | Low |
| `.github/workflows/validate.yml` | One added step in the `validate` job | Low |
| `web/olt/browse.py`, `home.py`, `reference.py`, `facets.py`, `trail.py`, `words.py`, `glossary.toml`, `web/assets/app.js`, `web/assets/style.css`, `web/tests/test_facets.py`, `test_views.py`, `test_filter_bar.py` | Ship 4 only | Medium: sibling may add place pages that touch the same lists |

Files only we touch: `tools/season.py`, `tools/estimate_season.py`, `tools/season_climate.py`, `tools/season_batches.py`, `tools/season_classify.py`, `tools/season_fit.json`, `docs/season-research.md`, `.github/workflows/season-check.yml`, the `tools/tests/test_season*.py` files and `tools/tests/fixtures/season/`.

## Review Focus

Inputs and conditions the spec implies but does not name, most likely first. Each has a test in the named task.

1. A season that wraps the year end (a desert trail walked November to March): `months = [11, 12, 1, 2, 3]`, phrase "November to March", arcs and grades must be circular. Tasks 10 and 12.
2. A trail where no month qualifies (arctic, or hot all year), or where all twelve do: never write empty months; an empty result is flagged for hand review, twelve months reads "All year". Task 12.
3. Missing or partial climate data for a point (a download gap): the estimator refuses and lists the trail as "no data"; it never fills in zeros. Tasks 11 and 12.
4. A multi-part track (gaps, `MultiLineString`) or a track with a short profile: sample points still come out spaced along the parts, and a record with no `elevation.json` falls back as decided. Task 13.
5. An estimate leaking as a stated fact: structured data, the in-brief sentence, the summary line, collection tables and search must each show it as an estimate or leave it out. Tasks 21 and 22.

---

# Ship 1: Schema, validator, history tool, classify the 109

Leaves the site building and every test passing. The site changes by one line in "About this data" (Task 6).

### Task 1: Register the fields and write the schema rule

**Files:**
- Modify: `tools/trail_history.py` (`_TABLES["hike"]`, `FACTS_TEXT`)
- Modify: `docs/schema.md` (the `[hike]` intro paragraph, the `season` and `months` rows, two new rows, the `[[history]]` fact list)
- Test: `tools/tests/test_season_fields.py` (create)

**Interfaces:**
- Produces: `trail_history.SCHEMA_FIELDS` contains `hike.season_basis` and `hike.season_method`; both are facts (`trail_history.is_fact(...)` true).

- [ ] **Step 1: Write the failing tests** in `test_season_fields.py` (header as in `tools/tests/test_length_facts.py`):

```python
def test_the_new_fields_are_known_to_the_history_tool(self):
    for f in ("hike.season_basis", "hike.season_method"):
        self.assertIn(f, H.SCHEMA_FIELDS)
        self.assertTrue(H.is_fact(f))
def test_the_facts_text_names_them(self):
    self.assertIn("season_basis", H.FACTS_TEXT)
def test_the_schema_documents_them_and_the_estimate_exception(self):
    text = open(os.path.join(V.ROOT, "docs", "schema.md"), encoding="utf-8").read()
    for needle in ("`season_basis`", "`season_method`", "except season, which may be estimated"):
        self.assertIn(needle, text)
```

- [ ] **Step 2: Run** `python3 -m unittest discover tools/tests -p "test_season_fields.py" -v`. Expected: 3 failures.
- [ ] **Step 3: Implement.** Add `"season_basis", "season_method"` after `"months"` in `_TABLES["hike"]`; add them to `FACTS_TEXT`'s hike list. In `docs/schema.md` add rows after `months`: `season_basis` (string, required when `season` is present; one of `primary`, `sources`, `source`, `estimate` with the design's table of meanings, including that a route author's stated season is `primary`) and `season_method` (string, required with `estimate`, refused otherwise: one sentence naming method and inputs). Replace "A fact found on no acceptable page is left out, never guessed." with the same sentence plus "except season, which may be estimated and must then say so". Say in the `season` row that `months` and `season` come together, and that for `estimate` the phrase is built from the months. Say typical time is estimated at page-build time and never stored, while an estimated season is stored.
- [ ] **Step 4: Run** the same command. Expected: PASS. Also `python3 -m unittest discover tools/tests` stays green (schema text is read by `web/olt/reference.py`; Task 24 rewrites that sentence).
- [ ] **Step 5: Commit** `git add tools/trail_history.py docs/schema.md tools/tests/test_season_fields.py && git commit -m "Register season_basis and season_method; schema allows estimated seasons"`

### Task 2: The season checks, not yet wired

**Files:**
- Create: `tools/season.py`
- Test: `tools/tests/test_season_basis.py` (create)

**Interfaces:**
- Produces (all in `tools/season.py`):
  - `BASES = ("primary", "sources", "source", "estimate")`
  - `PROVENANCE_KEYS = frozenset({"season_basis", "season_method"})`
  - `check_season(tid: str, hike: dict, errors: list[str]) -> None`
  - `SEASON_REQUIRED = False` (Task 19 sets it true)

Rules `check_season` enforces (error text starts `f"{tid}: hike."`): `season` and `months` appear together; `season_basis` present exactly when `season` is, and one of `BASES`; `season_method` present exactly with `estimate`, non-empty string under 400 characters; for `primary` and `source`, at least one `[[hike.source]]` names `season`; for `sources`, at least two sources with different publishers (case-insensitive) name `season`; for `estimate`, exactly one source names `season` or `months`. If `SEASON_REQUIRED`, a hike without `season` is an error.

- [ ] **Step 1: Write failing tests** in `test_season_basis.py` with a helper `check(**hike_fields)` that builds a hike with sources and returns the errors list. Tests: `test_primary_with_one_naming_source_passes`; `test_season_without_basis_is_an_error` (expects "season_basis"); `test_basis_without_season_is_an_error`; `test_unknown_basis_is_an_error`; `test_months_without_season_is_an_error` and the reverse; `test_sources_needs_two_publishers` (two sources, same publisher, differing case: one error; different publishers: none); `test_source_basis_needs_a_naming_source`; `test_estimate_needs_a_method_and_refuses_one_otherwise`; `test_estimate_with_two_naming_sources_is_an_error`; `test_a_hike_without_season_passes_until_required` and `test_required_flag_makes_it_an_error` (patch `season.SEASON_REQUIRED`).
- [ ] **Step 2: Run** `python3 -m unittest discover tools/tests -p "test_season_basis.py" -v`. Expected: import error.
- [ ] **Step 3: Implement** the module as specified. Stdlib only; no imports from `validate.py` (it will import this module).
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `git add tools/season.py tools/tests/test_season_basis.py && git commit -m "Add the season provenance checks (not yet wired)"`

### Task 3: The classification table

**Files:**
- Create: `tools/season_classify.py`
- Test: `tools/tests/test_season_classify.py` (create)

**Interfaces:**
- Consumes: `refresh.load_toml`, `refresh.trail_ids(root)`, `refresh.staging_dir(root, given, create)` from `tools/refresh.py`.
- Produces:
  - `suggest_basis(rec: dict) -> tuple[str, str]`: (basis, reason).
  - `table(root: str) -> list[dict]` with keys `id, season, months, publishers, urls, n_sources, n_publishers, suggested, reason`.
  - CLI `python3 tools/season_classify.py table [--dir DIR]` writes `<staging>/season/classification.csv`.

The suggestion rule (a person reviews every row): among sources naming `season`, `primary` if a source's host equals the host of `hike.official_url` or `source.publisher_url`, or the record is a route (`kind == "route"`) and the source host equals the host of a `[[guide]]` url whose `link_is` is `author` or `publisher`, or `route.creator_words_url`; otherwise `sources` if two or more different publishers name it; otherwise `source`. `reason` says which signal fired.

- [ ] **Step 1: Write failing tests** with small in-memory records: `test_official_site_host_is_primary`; `test_route_author_page_is_primary` (the owner's ruling); `test_two_unrelated_publishers_are_sources`; `test_one_unrelated_page_is_source`; `test_www_and_bare_host_are_the_same_host`; `test_table_covers_every_record_with_a_season` (real records: row count equals the number of records with `hike.season`, currently 109, and every row's `suggested` is in `season.BASES`); `test_table_has_a_reason_for_every_row`.
- [ ] **Step 2: Run** `python3 -m unittest discover tools/tests -p "test_season_classify.py" -v`. Expected: import error.
- [ ] **Step 3: Implement** `suggest_basis`, `table`, and the CSV writer (`csv` module, columns in the order above).
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `git add tools/season_classify.py tools/tests/test_season_classify.py && git commit -m "Add the season classification table"`

### Task 4: A person reviews the table

**Files:** none in the repository. Output `refresh/<date>/season/classification.reviewed.csv` (git-ignored).

- [ ] **Step 1:** Run `python3 tools/season_classify.py table` and `wc -l refresh/*/season/classification.csv` (expected: 110 lines, header plus 109).
- [ ] **Step 2:** A worker of a different model family from the one that wrote Task 3 opens, for every row, the page that names the season, and writes `classification.reviewed.csv` with the columns of the table plus `basis` (final) and `note`. It changes any row where the publisher is not the managing body, the association, or (for a route) the author, and says why. It never opens a page that refuses automated reads; it records the refusal.
- [ ] **Step 3:** Put the rows where `basis` differs from `suggested`, and any with a `note`, in front of the owner, with a recommendation on each. The owner's rulings are written into the reviewed file. Do not go on without them.
- [ ] **Step 4:** Check yourself: `python3 - <<'E'` counting rows per `basis` prints four numbers that add to 109 (no `estimate` among them).

### Task 5: Write the 109 bases

**Files:**
- Modify: `tools/season_classify.py` (add `proposals(root, reviewed_csv) -> int`)
- Modify: the 109 `<id>/trail.toml` files, through `tools/refresh.py apply`
- Test: `tools/tests/test_season_classify.py`

**Interfaces:**
- Produces: CLI `python3 tools/season_classify.py proposals --reviewed PATH` writes `<staging>/staged/season-classify/<id>/proposal.toml` and `report.csv`. Each proposal is `kind = "change"` with one `[[proposal.edit]]` (`field = "hike.season_basis"`, `new = <basis>`, `page`, `quote`) and a `[proposal.history]`: `change` "The season is recorded as coming from <plain basis words>.", `basis` naming the publisher and what the page says, `basis_url` the page, `asked_by = "the dataset's own check"`, `fields = ["hike.season_basis"]`.

- [ ] **Step 1: Write the failing test** `test_a_proposal_collects_cleanly_and_applies`: build a temporary copy of one record (use `tempfile`, the helpers in `tools/tests/test_refresh.py`), run `proposals`, `refresh.cmd_collect`, `refresh.cmd_apply` against it, and assert the record gains `season_basis`, gains a history entry whose `fields == ["hike.season_basis"]`, and still parses.
- [ ] **Step 2: Run** `python3 -m unittest discover tools/tests -p "test_season_classify.py" -v`. Expected: the new test fails.
- [ ] **Step 3: Implement** `proposals` (one proposal per row; `quote` is the season phrase the record already holds).
- [ ] **Step 4: Run** the test. Expected: PASS.
- [ ] **Step 5: Apply to the real records.** `python3 tools/season_classify.py proposals --reviewed refresh/<date>/season/classification.reviewed.csv`, then `python3 tools/refresh.py collect`, `python3 tools/refresh.py apply --dry-run`, then `python3 tools/refresh.py apply`. Expected: 109 applied; `git diff --stat` shows 109 `trail.toml` files and no other file; `git diff` of any three shows one added line in `[hike]` and one added `[[history]]` block.
- [ ] **Step 6: Commit** `git add tools/season_classify.py tools/tests/test_season_classify.py */trail.toml && git commit -m "Record where each of the 109 seasons came from"`

### Task 6: Show the basis in "About this data", turn the check on, ship

**Files:**
- Modify: `tools/validate.py` (`HIKE_KEYS`; one `season.check_season(tid, hike, errors)` call at the end of `check_hike`; the coverage loop near the end of `check_hike` skips `PROVENANCE_KEYS`)
- Modify: `web/olt/facets.py` (add `SEASON_BASIS_TEXT` and `season_basis_line(rec) -> str`)
- Modify: `web/olt/trail.py` (`hike_sources_block` appends the line under "Checked ...")
- Modify: `CHANGELOG.md`
- Modify: `.github/workflows/validate.yml` (in `validate` job: `- run: python3 -m unittest discover tools/tests -p "test_season*.py"`)
- Test: `tools/tests/test_season_basis.py`, `web/tests/test_hike.py`

**Interfaces:**
- Consumes: `season.check_season`, `season.PROVENANCE_KEYS`, `season.BASES`.
- Produces: `facets.season_basis(rec) -> str` (`""` when none) and `facets.season_basis_line(rec) -> str`, texts: `primary` "The season comes from the page of the body that manages the trail or, for a route, its author."; `sources` "Two or more pages from different publishers agree on the season."; `source` "One page states the season. It is not the trail's own page."; `estimate` (used from Task 21) the method sentence plus "No page states a season."

- [ ] **Step 1: Write failing tests.** In `test_season_basis.py`: `test_every_record_with_a_season_passes_the_validator` (run `V.check_hike` over every real record; zero errors) and `test_provenance_keys_need_no_source_fact` (a hike with `season_basis` not in any source's facts passes). In `web/tests/test_hike.py`: `test_about_this_data_says_where_the_season_came_from` (a fixture with `season_basis = "primary"` renders the primary sentence inside `hike_sources_block`; one with no season renders no basis sentence).
- [ ] **Step 2: Run** both files. Expected: failures (validator rejects `season_basis` as an unknown field; no sentence).
- [ ] **Step 3: Implement** the edits above. `HIKE_KEYS = HIKE_FACTS | {"checked"} | season.PROVENANCE_KEYS`; `import season` next to the existing sibling imports.
- [ ] **Step 4: Changelog.** Add, headed with the ship date and `Every season now says where it came from`: the 109 seasons on file are now recorded as from the body that manages the trail (N), from several agreeing pages (N), or from one page (N); each trail page's "About this data" says which. Take N from the reviewed table; they must add to 109.
- [ ] **Step 5: Run everything.** `python3 tools/validate.py` (no errors), `python3 tools/check_history.py --base main` (no failures), `python3 -m unittest discover tools/tests` (OK), the full web tests (OK), `python3 web/build.py --out _site` (exit 0). Read the built HTML of two trails' "About this data".
- [ ] **Step 6: Commit** `git add tools/validate.py web/olt/facets.py web/olt/trail.py CHANGELOG.md .github/workflows/validate.yml tools/tests web/tests && git commit -m "Show where a season came from; check it"`. **Ship 1 is complete.**

---

# Ship 2: Research the 114

Each cycle (Task 9) is a ship of its own. The site needs no change: the month lists already count exact numbers (`browse.month_note`), and they grow as seasons land.

### Task 7: The researchers' brief and the batches

**Files:**
- Create: `docs/season-research.md`
- Create: `tools/season_batches.py`
- Test: `tools/tests/test_season_batches.py` (create)

**Interfaces:**
- Produces: `season_batches.missing_ids(root: str) -> list[str]` (records with no `hike.season`, sorted); `season_batches.batches(root: str, size: int = 10) -> list[list[str]]`; `REGION_GROUPS: dict[str, tuple[str, ...]]` (region codes by group: west coast, interior west, southwest, Rockies, plains and midwest, northeast, southeast, Canada west, Canada east and north). CLI `python3 tools/season_batches.py --n 10` writes `<staging>/season/batches/season-NN.txt`, one id per line.

**What `docs/season-research.md` says** (it is the brief; write it for a worker with nothing else):
1. Goal and the rules in Global Constraints that matter to a researcher (acceptable pages, never guess, nothing copied: the wording is ours).
2. For each trail the researcher stages one `[[proposal]]` (kind `change`, format in `.claude/skills/refresh-trails/proposal-format.md`) holding: `hike.season` (a short phrase in our words), `hike.months` (a month counts when about half of it or more is in season; for a trail walked in more than one window list every month), `hike.season_basis` (see below), `hike.checked` (the date the page was read), an appended `hike.source` entry (page `url`, `publisher`, `facts = ["season", "months"]`), the page's own address and a quote of at most 25 words as `quote`, and a `[proposal.history]` with `fields = ["hike.season", "hike.months", "hike.season_basis"]`, `asked_by = "the dataset's own check"`.
3. Basis: `primary` if the page is the managing body's, the trail's own association's, or for a route its author's; `sources` if no such page but two or more pages from different publishers agree; `source` if one other acceptable page; trip reports count only when they speak of the usual season, never of one trip, and then only as `source`. Where pages disagree, the managing body wins, and the phrase may carry the nuance ("northbound starts late February to April").
4. A trail with no acceptable page gets a `report.csv` row `not-found` listing every page and search tried (at least three places). It stays for estimating; a quiet first pass gets a second worker of another model family.
5. What a reviewer checks, every trail, not a sample: the page opens and says the quoted thing; the phrase is in our words; months follow the phrase and the half-month rule; the basis fits the publisher (managing body or not) and the count of different publishers; the page is about this trail and not a section or a different year's event; a disagreement was resolved toward the managing body; no hut or park opening dates stand in for a walking season unless they set it; the `hike.source` entry names `season` and `months`. A different model family from the researcher's. Reviewers write `review/<name>.csv` as the refresh pipeline does.
6. Never kill a process by name; plain User-Agent; do not work round a site that refuses automated reads.
7. "Replacing an estimate" (used by the audit): by hand-edit, in order: set `season`, `months`, `season_basis`; delete `season_method`; delete the climate `[[hike.source]]` block; add the page's source block; append a history entry naming `hike.season`, `hike.months`, `hike.season_basis`, `hike.season_method`; run the validator and history check.

- [ ] **Step 1: Write failing tests.** `test_missing_ids_are_the_records_without_a_season` (tmp root with three records, one with a season); `test_batches_are_at_most_the_size_and_cover_every_id_once`; `test_a_batch_stays_in_one_region_group_unless_joined` (a group of 23 splits into 10, 10, 3, and the 3 joins a neighbouring group's batch only if that batch has room); `test_real_count` (`len(missing_ids(ROOT))` equals the count of records without `hike.season`, and `len(batches(ROOT)) == ceil(n / 10)` or one more); `test_the_brief_names_what_a_researcher_records` (reads `docs/season-research.md`; asserts it contains `hike.season_basis`, `hike.months`, `quote`, `not-found`, `publisher`).
- [ ] **Step 2: Run** `python3 -m unittest discover tools/tests -p "test_season_batches.py" -v`. Expected: import error.
- [ ] **Step 3: Implement** `season_batches.py` and write `docs/season-research.md` as above.
- [ ] **Step 4: Run** the same command. Expected: PASS. Then `python3 tools/season_batches.py --n 10` prints the batch count (about 12) and the total (114 at the time of writing).
- [ ] **Step 5: Commit** `git add tools/season_batches.py tools/tests/test_season_batches.py docs/season-research.md && git commit -m "Add the season research brief and the batches"`

### Task 8: Make `refresh.py apply` take the new fields

The staged proposal format checks field names with `tools/refresh.py` `schema_path` and `validate_proposal`. Task 1 made the names known; this task proves the whole route works for a researched season before the first batch.

**Files:**
- Test: `tools/tests/test_season_batches.py`

- [ ] **Step 1: Write the test** `test_a_researched_season_proposal_collects_and_applies`: in a temporary copy of a record that has `[hike]` but no season, stage a proposal exactly as Task 7's brief describes it (edits adding `hike.season`, `hike.months`, `hike.season_basis`, `hike.checked`; an append to `hike.source`; a history block), run `collect` and `apply`, and assert the resulting record passes `V.check_hike` and `trail_history.check_entries`, and `hike.season` and `hike.months` are in the right order and type.
- [ ] **Step 2: Run** the file. Expected: it fails or passes; if `validate_proposal` rejects the shape (for example `months` as an array in `new`), fix `tools/refresh.py` minimally so it accepts it and keep the test.
- [ ] **Step 3: Run** `python3 -m unittest discover tools/tests`. Expected: OK.
- [ ] **Step 4: Commit** `git add tools/refresh.py tools/tests && git commit -m "Prove a researched season applies through the refresh pipeline"`

### Task 9: Land a group of batches (repeat per ship)

**Files:** the `trail.toml` of the researched trails; `CHANGELOG.md`.

- [ ] **Step 1: Research.** For each batch file in the group (three batches at a time, about 30 trails), start one researcher on the most capable model available with `docs/season-research.md` and the batch file, one batch per researcher, all at once. Do not poll; wait for each.
- [ ] **Step 2: Collect.** `python3 tools/refresh.py collect`. Expected: no problems; every id has a report row; `not-found` rows each list pages. Send back any that do not.
- [ ] **Step 3: Review.** One reviewer of a different model family per batch, following the brief's section 5 for every trail. Read the rejections yourself. Revise and re-review until the `must fix` list is empty.
- [ ] **Step 4: Owner rules** on borderline items: a trail whose only page is a trip report, any disagreement between a managing body and an association, any basis that looks too high. Record rulings in `owner.csv`.
- [ ] **Step 5: Apply.** `python3 tools/refresh.py apply --dry-run`, then `apply`. Expected: one `change` applied per accepted trail; `git diff --stat` matches the accepted list and touches no other trail.
- [ ] **Step 6: Verify.** `python3 tools/validate.py`; `python3 tools/check_history.py --base main`; `python3 -m unittest discover tools/tests`; the full web tests; `python3 web/build.py --out _site`. Read the built "Hiking in July" list page: its note says how many trails have a season exactly as many as the records now carry.
- [ ] **Step 7: Changelog and commit.** Entry headed `Seasons for N more trails`: the exact count added, how many are from the managing body, how many from other pages, and the new "of 223" figure; no figure typed that you did not compute from the records. `git add */trail.toml CHANGELOG.md && git commit -m "Add sourced seasons for N trails"`.
- [ ] **Step 8:** Repeat Steps 1 to 7 until `python3 tools/season_batches.py --n 10` lists only trails whose reports say `not-found`. Those are the trails left to estimate. **Ship 2 is complete when no unresearched batch remains.**

---

# Ship 3: The estimator, its check, the review list

Tools, a workflow and a checklist only. The site is unchanged, so the ship's `CHANGELOG.md` entry is a short "For contributors" one.

### Task 10: Season helpers shared by the checker and the estimator

**Files:**
- Modify: `tools/season.py`
- Test: `tools/tests/test_season_basis.py` (add), `tools/tests/test_season_helpers.py` (create)

**Interfaces:**
- Produces in `tools/season.py`:
  - `span(months: list[int]) -> tuple[int, int]`: the smallest circular arc covering the months (first, last).
  - `grade(estimated: list[int], sourced: list[int]) -> str`: `"exact"`, `"within1"` or `"worse"`.
  - `phrase_for(months: list[int]) -> str`.
  - `method_sentence(dataset: str, period: str, n_points: int, kind: str, rule_version: int) -> str`, `kind` one of `"track"`, `"ends"`, `"place"`.

- [ ] **Step 1: Write failing tests** in `test_season_helpers.py`: `test_span_wraps_the_year` (`span([11, 12, 1, 2, 3]) == (11, 3)`); `test_span_of_two_windows_covers_both` (`span([4, 5, 9, 10]) == (4, 10)`); `test_grade_exact`, `test_grade_within_one_at_each_end` (`grade([5,6,7,8,9],[6,7,8]) == "within1"`), `test_grade_worse` (`grade([6,7],[9,10]) == "worse"`), `test_grade_across_the_year_end` (`grade([12,1,2],[1,2,3]) == "within1"`); `test_phrase_runs` (`[6,7,8,9] -> "June to September"`; `[11,12,1,2,3] -> "November to March"`; `[4,5,9,10] -> "April to May and September to October"`; `[7] -> "July"`; all twelve `-> "All year"`); `test_method_sentence_names_dataset_period_and_points`.
- [ ] **Step 2: Run** `python3 -m unittest discover tools/tests -p "test_season_helpers.py" -v`. Expected: failures.
- [ ] **Step 3: Implement** the four functions. `phrase_for` uses `facets.MONTHS` names duplicated as a local tuple (tools do not import the web package).
- [ ] **Step 4: Run** the file. Expected: PASS.
- [ ] **Step 5: Commit** `git add tools/season.py tools/tests/test_season_helpers.py && git commit -m "Add season arcs, grades, phrases and the method sentence"`

### Task 11: Choose the climate source by trial

**Files:**
- Create: `tools/season_climate.py`
- Create: `tools/tests/fixtures/season/` (a small canned response per candidate, three points each)
- Test: `tools/tests/test_season_climate.py` (create)
- Modify: `NOTICE.md` (attribution for the chosen source, one short section)

**Interfaces:**
- Produces: `CACHE_DIR` (default `~/.cache/longhikes-climate/`, overridable by environment variable `LONGHIKES_CLIMATE_CACHE`); `PointNormals` (frozen dataclass: `lat: float`, `lon: float`, `elev_m: float`, `tmax_c: tuple[float, ...]` of 12, `snow_cm: tuple[float, ...] | None`); `fetch_normals(lat: float, lon: float, elev_m: float | None, cache: str = CACHE_DIR, opener=urllib.request.urlopen) -> PointNormals | None` (None when the source has no data for the point; never zeros); `SOURCE: dict` with `name`, `publisher`, `url`, `licence`, `period = "1991-2020"`. An adapter per candidate, each normalising to `PointNormals`: Open-Meteo historical API (ERA5 and ERA5-Land, CC BY 4.0), NOAA 1991 to 2020 normals and SNODAS (public domain, US only), Environment Canada normals (Canada only).

The trial (a command, `python3 tools/estimate_season.py trial`, added in Task 15; this task builds the adapters and the table it prints): twelve sourced trails, chosen by rule: at least two in Canada, one in Alaska or the far north (Akshayuk Pass), three alpine, two desert, two coastal, one prairie, one southeast. For each candidate and each trail it records: did data come back; the estimated months under a coarse default rule; the grade against the sourced months.

Choose by this order: (1) licence: derived monthly figures may be stored and published with attribution, with no non-commercial or private-use clause that excludes a public dataset (read the terms page and quote the line in the docstring); (2) coverage: data for all twelve trails including Canada and the far north, from one source or one per country normalised to `PointNormals`; (3) fit on the twelve; ties go to the simpler. Record the decision, the three tables and the quoted licence lines in the module docstring, and add the attribution to `NOTICE.md`.

- [ ] **Step 1: Write failing tests** in `test_season_climate.py`, all offline using an injected `opener` that returns the fixtures: `test_a_fixture_response_becomes_point_normals` (12 values each, rounded to 0.1); `test_a_second_call_reads_the_cache_not_the_network` (opener called once, assert via a counter); `test_a_point_with_no_data_returns_none_not_zeros`; `test_the_cache_is_outside_the_repository` (`CACHE_DIR` does not start with `V.ROOT`); `test_the_source_says_its_licence_and_period`.
- [ ] **Step 2: Run** `python3 -m unittest discover tools/tests -p "test_season_climate.py" -v`. Expected: import error.
- [ ] **Step 3: Implement** `season_climate.py` (urllib, `json`, a plain User-Agent with no personal or project details, a pause between requests, one request at a time, a cache file per point keyed by rounded coordinates and elevation). Network use happens only when the cache lacks a point.
- [ ] **Step 4: Run** the file. Expected: PASS.
- [ ] **Step 5: Run the trial** once Task 15 exists (`python3 tools/estimate_season.py trial`). If it runs long, start it in the background and wait for it; stop it only by the PID you started. If no candidate passes (1) and (2), stop and tell the owner; do not choose a source that fails the licence test.
- [ ] **Step 6: Commit** `git add tools/season_climate.py tools/tests NOTICE.md && git commit -m "Add the climate download, cached outside the repository, and record the source chosen"`

### Task 12: The rule, as a pure function

**Files:**
- Create: `tools/estimate_season.py`
- Test: `tools/tests/test_estimate_season.py` (create)

**Interfaces:**
- Consumes: `season_climate.PointNormals`.
- Produces: `SamplePoint` (frozen dataclass: `lat`, `lon`, `elev_m`, `km: float | None`); `Params` (frozen: `snow_cm_max`, `cold_c_min`, `heat_c_max`); `RULE_VERSION = 1`; `months_in_season(points: list[PointNormals], params: Params) -> list[int] | None` (sorted month numbers; None when `points` is empty or any point lacks data; an empty list is never returned, it is None with the reason from `why_not(points, params) -> str`).

- [ ] **Step 1: Write failing tests** with hand-made normals (a helper `normals(elev, tmax, snow=None)` builds a `PointNormals`): `test_a_cold_high_point_closes_the_winter` (high ground at or below `cold_c_min` in Jan to Mar drops them); `test_snow_over_the_limit_closes_a_month`; `test_heat_at_the_low_ground_closes_a_summer_month` (a desert trail: low ground at 40 degrees C in Jun to Aug gives `[10,11,12,1,2,3,4]`... assert the wrapped set); `test_high_ground_is_the_upper_quartile_of_points` (four points, only the highest decides snow); `test_no_snow_measure_uses_temperature_alone`; `test_a_wrapped_season_is_returned_sorted` (`[1,2,3,11,12]`); `test_no_qualifying_month_is_none_with_a_reason` (an arctic point: `months_in_season(...) is None`, `why_not(...)` contains "no month"); `test_all_twelve_months_is_allowed` (a mild coast point returns 1 to 12); `test_a_point_with_missing_data_makes_the_trail_unestimable` (a list containing `None` returns None, `why_not` contains "no data").
- [ ] **Step 2: Run** `python3 -m unittest discover tools/tests -p "test_estimate_season.py" -v`. Expected: import error.
- [ ] **Step 3: Implement** `months_in_season` and `why_not` exactly per the decisions table (quantile selection and medians via `statistics`; thresholds compared with `>=` and `<=`; values rounded to 0.1 before comparing so a re-run on cached data is bit-identical). No network access in this module's imports beyond `season_climate` types.
- [ ] **Step 4: Run** the file. Expected: PASS.
- [ ] **Step 5: Commit** `git add tools/estimate_season.py tools/tests/test_estimate_season.py && git commit -m "Add the season rule as a pure function over monthly normals"`

### Task 13: Sample points from a record

**Files:**
- Modify: `tools/estimate_season.py`
- Test: `tools/tests/test_estimate_season.py`

**Interfaces:**
- Produces: `sample_points(root: str, rec: dict) -> tuple[list[SamplePoint], str]`: the points and a kind, one of `"track"`, `"ends"`, `"place"`. Reads `<id>/line.geojson` (LineString or MultiLineString; parts are concatenated in order, gaps ignored), spaces points one per 50 km of track length (min 3, max 12) by cumulative haversine distance, and gets each point's elevation from `<id>/elevation.json` `profile` by interpolating on `km`; with no profile, `hike.high_point_m` for the highest point and `None` elsewhere (the climate adapter then supplies the cell elevation). No track: `hike.start_lonlat` and `hike.end_lonlat` (`"ends"`); neither: the centre of the box in `web/place-bounds.toml` for `rec["regions"][0]` with the country prefix (`"place"`), read with `tomllib`.

- [ ] **Step 1: Write failing tests** with a temporary record directory: `test_a_track_gives_points_spaced_along_it` (a 200 km synthetic line gives 5 points, first at km 0, last within 50 km of the end); `test_a_short_track_still_gets_three_points`; `test_a_very_long_track_is_capped_at_twelve`; `test_a_multipart_track_is_sampled_along_all_parts`; `test_elevation_comes_from_the_profile_by_distance`; `test_a_track_without_a_profile_uses_the_high_point_for_the_top_only`; `test_no_track_uses_the_two_ends` (kind `"ends"`); `test_no_track_and_no_ends_uses_the_place_centre` (kind `"place"`, point inside the box).
- [ ] **Step 2: Run** the file. Expected: new tests fail.
- [ ] **Step 3: Implement** `sample_points`.
- [ ] **Step 4: Run** the file. Expected: PASS.
- [ ] **Step 5: Commit** `git add tools/estimate_season.py tools/tests/test_estimate_season.py && git commit -m "Sample points along a track, from the ends, or from the place"`

### Task 14: Fit the rule against the sourced seasons

**Files:**
- Modify: `tools/estimate_season.py`
- Create: `tools/season_fit.json` (written by the tool, committed)
- Test: `tools/tests/test_estimate_season.py`, `tools/tests/test_season_fit.py` (create)

**Interfaces:**
- Produces: `BAR = {"within1_min": 0.75, "coverage_min": 0.90}`, a figure for the owner to confirm, held in one place; `fit_params(sourced: list[tuple[str, list[PointNormals], list[int]]], grid: dict[str, list[float]]) -> Params`; `report(sourced, params) -> dict` with `n`, `exact`, `within1`, `worse`, `no_data` (counts) and `by_group` (the same, per region group from `tools/season_batches.REGION_GROUPS`); `held_out(tid: str) -> bool` (true when a stable hash of the id is odd; use `hashlib.sha256`, not `hash()`); CLI `python3 tools/estimate_season.py fit` loads every record with a sourced season (`season_basis` not `estimate`), fetches its normals through the cache, grid-searches on the even-hash trails, reports on the odd-hash trails, refits the shipped numbers on all, and writes `tools/season_fit.json`: `computed`, `rule_version`, `dataset`, `period`, `params`, the all-trails report, the held-out report, `bar`, `passes` (true when held-out `within1 / n >= within1_min` and `1 - no_data / n >= coverage_min`).

- [ ] **Step 1: Write failing tests**: `test_held_out_is_stable_and_splits_roughly_in_half` (1000 ids, between 40 and 60 percent); `test_fit_recovers_known_params_from_synthetic_trails` (generate normals and sourced months from a known `Params`; the fit returns values within one grid step); `test_report_counts_grades_and_no_data` (`exact + within1 + worse + no_data == n`; `within1` counts exact too, or state the convention and assert it); `test_passes_is_false_below_the_bar_and_true_at_it` (call the pass logic with 74 of 100 and 75 of 100); `test_the_same_input_gives_the_same_report_twice`. In `test_season_fit.py`: `test_the_committed_fit_has_the_fields_the_site_reads` (keys listed above) and `test_estimates_only_with_a_passing_fit`: if any real record has `season_basis == "estimate"` then `season_fit.json["passes"]` is true and `held_out.within1 / n >= BAR["within1_min"]`.
- [ ] **Step 2: Run** both files. Expected: failures.
- [ ] **Step 3: Implement.** The search is a plain grid over the three numbers with ranges that cover the trial's plausible values (snow 0 to 60 cm in 5 cm steps; cold 0 to 12 degrees C in 1; heat 24 to 40 in 1); the score is mean grade (exact 2, within one 1, worse 0). Run the CLI; read `tools/season_fit.json`.
- [ ] **Step 4: Run** both files. Expected: PASS. If `passes` is false, keep the file (it is the evidence), and say so in the Task 17 gate.
- [ ] **Step 5: Commit** `git add tools/estimate_season.py tools/season_fit.json tools/tests && git commit -m "Fit the season rule against the sourced seasons and record the figure"`

### Task 15: The review list, the proposals and the check

**Files:**
- Modify: `tools/estimate_season.py`
- Test: `tools/tests/test_estimate_season.py`

**Interfaces:**
- Produces: `estimate(root: str, rec: dict, params: Params, fetch=season_climate.fetch_normals) -> dict` with `months`, `phrase`, `method`, `kind`, `flags: list[str]`, `comparable: str`; flags are `no-track`, `place-centre`, `no-data`, `no-month`, `desert`, `coast`, `far-north` (latitude above 60), `few-points`; `comparable` is the id of the nearest sourced trail by distance between sample centres, with its phrase. CLI: `trial`; `propose` (writes `<staging>/season/estimates.csv`: `id, proposed_months, phrase, kind, flags, comparable, comparable_phrase`, and lists every unestimable trail with its reason); `proposals --reviewed PATH` (writes `<staging>/staged/season-estimate/<id>/proposal.toml` per accepted row, `kind = "change"`, edits adding `hike.season`, `hike.months`, `hike.season_basis = "estimate"`, `hike.season_method`, `hike.checked`; an append to `hike.source` (`url`, `publisher` from `season_climate.SOURCE`, `facts = ["season", "months"]`); a history block with `fields = ["hike.season", "hike.months", "hike.season_basis", "hike.season_method"]`, `basis` "No page states a season; it is estimated from climate (rule version N).", `basis_url` the dataset's address, `asked_by = "the dataset's own check"`); `check` (re-runs every record whose basis is `estimate` and the fit; exit 1 with a listed difference when an estimate would now come out different, or the held-out `within1` has fallen by more than 0.02 from `season_fit.json`, or `passes` is false).

- [ ] **Step 1: Write failing tests** with an injected `fetch` returning synthetic normals: `test_a_no_track_record_is_flagged`; `test_a_trail_with_no_data_is_listed_not_estimated`; `test_flags_include_far_north_above_sixty_degrees`; `test_comparable_is_the_nearest_sourced_trail`; `test_propose_writes_one_row_per_unsourced_trail` (csv header and count); `test_check_passes_when_nothing_changed` and `test_check_names_the_trail_whose_estimate_changed` (change one normal; the output lists the id with old and new months); `test_check_fails_when_the_fit_got_worse`; `test_proposals_collect_cleanly` (collect a staged proposal with `tools/refresh.py`, as in Task 5); `test_nothing_in_estimate_touches_the_network_without_a_fetch` (the default `fetch` is only used when none is passed; assert with a fetch that raises).
- [ ] **Step 2: Run** the file. Expected: failures.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the file and `python3 -m unittest discover tools/tests`. Expected: OK.
- [ ] **Step 5: Commit** `git add tools/estimate_season.py tools/tests && git commit -m "Add the estimate review list, the proposals and the check"`

### Task 16: The monthly workflow, the audit checklist, ship

**Files:**
- Create: `.github/workflows/season-check.yml`
- Create or modify: `docs/audit.md` (create if absent, with a one-paragraph introduction saying it is the checklist for the roughly monthly audit of everything, that `/refresh-trails` (`.claude/skills/refresh-trails/SKILL.md`) is the step for pages and records, and one `## <name>` section per topic; if the file exists, add only the `## Seasons` section and touch nothing else)
- Modify: `.github/workflows/validate.yml` (already has the season step from Task 6)
- Modify: `CHANGELOG.md`
- Test: `tools/tests/test_season_audit.py` (create)

**Interfaces:** `docs/audit.md` section `## Seasons` has two numbered steps: (1) run `python3 tools/estimate_season.py check` and act on what it lists; (2) for every record whose `season_basis` is `estimate` (list them with `python3 tools/estimate_season.py estimates`), search afresh for a page that states a season, using `docs/season-research.md`, and replace the estimate when one turns up. `estimate_season.py estimates` prints the ids of records with basis `estimate`, one per line.

The workflow: triggers `schedule` (monthly: `cron: "17 6 1 * *"`) and `workflow_dispatch`; one job on `ubuntu-latest`, Python 3.12; `actions/cache` on `~/.cache/longhikes-climate` keyed by month; runs `python3 tools/estimate_season.py check`; a failure fails the job so the owner is notified.

- [ ] **Step 1: Write failing tests** in `test_season_audit.py`: `test_the_audit_checklist_has_a_seasons_section_naming_both_steps` (`docs/audit.md` exists, contains `## Seasons`, `estimate_season.py check`, `docs/season-research.md`); `test_the_commands_it_names_exist` (the `estimate_season.py` parser has the subcommands `check` and `estimates`); `test_the_monthly_workflow_runs_the_check_on_a_schedule` (text of `season-check.yml` contains `schedule`, `workflow_dispatch`, `estimate_season.py check`); `test_house_wording_in_the_audit_doc` (no em or en dash, no " - " outside code).
- [ ] **Step 2: Run** `python3 -m unittest discover tools/tests -p "test_season_audit.py" -v`. Expected: failures.
- [ ] **Step 3: Implement** the files and the `estimates` subcommand.
- [ ] **Step 4: Changelog.** Entry headed `A written audit checklist, and a monthly check of estimated seasons`, "For contributors" style: what the checklist is, that the check runs monthly and fails with a list, no site change.
- [ ] **Step 5: Run everything** (the five commands). Also `python3 tools/estimate_season.py check` once by hand with a warm cache; expected: exits 0 when there are no estimates yet and says so.
- [ ] **Step 6: Commit** `git add .github docs/audit.md tools CHANGELOG.md && git commit -m "Check estimated seasons monthly, and write the season steps into the audit"`. **Ship 3 is complete.**

---

# Ship 4: Write the estimates, change the site

### Task 17: The gate, the run, the review

**Files:** none in the repository. Output `refresh/<date>/season/estimates.reviewed.csv`.

- [ ] **Step 1: Gate.** `python3 tools/estimate_season.py fit`, then read `tools/season_fit.json`. If `passes` is false, stop here: tell the owner the held-out figure, the bar, and the groups that fail, and do not run Step 2. The estimate is not shipped below the bar. (The bar is the figure in `BAR`: 75 percent within one month at each end, held out, and 90 percent of sourced trails estimable; the owner confirms it before this ship starts.)
- [ ] **Step 2:** `python3 tools/estimate_season.py propose`. Expected: one row per trail still with no season; every other row flagged or clean; trails with `no-data` or `no-month` listed with reasons.
- [ ] **Step 3: Review.** A person (the owner, with a worker preparing the comparison) reads every row. Rows flagged `no-track`, `place-centre`, `desert`, `coast`, `far-north` or `few-points` are hand checked against the `comparable` sourced trail and the high-ground and heat reasoning; a row that does not hold up is corrected (months edited in the reviewed file, with a `note`) or, for an unestimable trail, researched again by hand under `docs/season-research.md`. An edited row keeps `season_method` truthful: the method sentence then ends "and adjusted by hand against <comparable>". Write `estimates.reviewed.csv`.
- [ ] **Step 4:** Check yourself: the reviewed file has a row for every trail with no season, and none has empty months.

### Task 18: Write the estimates

**Files:** the remaining `trail.toml` files, through `tools/refresh.py apply`.

- [ ] **Step 1:** `python3 tools/estimate_season.py proposals --reviewed refresh/<date>/season/estimates.reviewed.csv`, then `python3 tools/refresh.py collect` (no problems), `apply --dry-run`, `apply`.
- [ ] **Step 2: Check.** `git diff --stat` lists exactly the reviewed trails; read three hunks: each adds `season`, `months`, `season_basis = "estimate"`, `season_method`, a climate `[[hike.source]]` block, and one `[[history]]` block naming four fields. `python3 tools/validate.py` still passes (the validator does not yet require a season for every record).
- [ ] **Step 3: Commit** `git add */trail.toml && git commit -m "Estimate a season for the trails no page gives one for"`

### Task 19: Every record has a season; the validator says so

**Files:**
- Modify: `tools/season.py` (`SEASON_REQUIRED = True`; `CLIMATE_HOSTS` from `season_climate.SOURCE`)
- Modify: `tools/validate.py` (nothing more than the existing call; confirm a record with no `[hike]` is also an error when seasons are required: in `main`, one line `season.check_present(tid, rec, errors)` next to the other `check_*` calls)
- Test: `tools/tests/test_season_basis.py`, `tools/tests/test_season_records.py` (create)

**Interfaces:**
- Produces: `season.check_present(tid: str, rec: dict, errors: list[str]) -> None` (error when `rec` has no `hike` or no `hike.season`); `season.CLIMATE_HOSTS: frozenset[str]` (host of the chosen climate source). `check_season` additionally requires, for `estimate`, that the one source naming `season` has a host in `CLIMATE_HOSTS`, and for every other basis that no source naming `season` or `months` has one.

- [ ] **Step 1: Write failing tests.** `test_season_records.py` over the real records: `test_every_record_has_season_months_and_a_basis`; `test_the_basis_fits_the_sources` (each record passes `season.check_season`); `test_every_estimate_has_a_method_and_a_climate_source`; `test_no_sourced_season_cites_climate_data`; `test_no_record_says_a_season_is_missing` (no record's `hike` summary or caution contains "no season"); `test_the_estimated_phrase_is_built_from_its_months` (`hike.season == season.phrase_for(hike.months)` for every estimate). In `test_season_basis.py`: `test_a_record_with_no_hike_is_an_error_when_required` and `test_estimate_from_a_non_climate_host_is_an_error`.
- [ ] **Step 2: Run** `python3 -m unittest discover tools/tests -p "test_season*.py" -v`. Expected: failures on the new tests.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the same command, then `python3 tools/validate.py`. Expected: PASS, no errors.
- [ ] **Step 5: Commit** `git add tools && git commit -m "The validator requires a season on every trail"`

### Task 20: The season as the site reads it

**Files:**
- Modify: `web/olt/facets.py`
- Test: `web/tests/test_facets.py` (add), `web/tests/test_hike.py`

**Interfaces:**
- Produces in `facets.py`: `season_estimated(rec) -> bool` (true when `hike.season_basis == "estimate"`); `season_text(rec)` returns `"About " + phrase` for an estimate (phrase left as it is after "About", so "About June to September"), unchanged for others; `season_note(rec) -> str` (`""` unless estimated; else "Estimated from climate at the trail's elevation. No source states a season. This is the usual window, not a closure."); `SEASON_STATED_NOTE` not needed.

- [ ] **Step 1: Write failing tests** (fixtures built like `fake(...)` in `web/tests/test_views.py`): `test_an_estimated_season_reads_about_and_has_a_note`; `test_a_stated_season_is_unchanged_and_has_no_note`; `test_an_estimated_all_year_season_reads_about_all_year`; `test_season_estimated_is_false_without_a_basis`.
- [ ] **Step 2: Run** `python3 -m unittest discover -s web/tests -p "test_facets.py" -v`. Expected: the new tests fail.
- [ ] **Step 3: Implement** in `facets.py` (`"About"` is not doubled when the phrase already starts with "about", as `time_text` does).
- [ ] **Step 4: Run** the file. Expected: PASS.
- [ ] **Step 5: Commit** `git add web/olt/facets.py web/tests && git commit -m "Say an estimated season is about, with a note"`

### Task 21: Trail page, summary, structured data

**Files:**
- Modify: `web/olt/trail.py` (`season_sentence`, `glance`)
- Modify: `web/olt/summary.py`
- Modify: `web/olt/seo.py` (the `Usual season` property, near line 287)
- Modify: `web/olt/facets.py` (`season_basis_line` for `estimate`)
- Test: `web/tests/test_hike.py`, `web/tests/test_trust.py`, `web/tests/test_structured_data.py`

**Behaviour:**
- Glance: the Season row passes `facets.season_note(rec)` as the row's note; `SEASON` is removed from the `missing` list that writes "... not on file for this trail yet."
- In brief (`season_sentence`): an estimate returns `("estimate", "No source gives a season; the climate suggests about June to September")` (months phrase from `hike.season`), and the caller adds the full stop; it is never joined to the GPX clause with "and".
- Summary line (`summary.py`, line 149 area): "Season: About June to September, estimated from climate."
- Structured data: `Usual season` is emitted only when `hike.season_basis != "estimate"`.
- About this data: `season_basis_line` for `estimate` is the record's `season_method` followed by "No page states a season."

- [ ] **Step 1: Write failing tests.** `test_hike.py`: `test_an_estimated_season_row_carries_the_note`; `test_a_sparse_trail_no_longer_says_season_is_missing` (the fixture at lines 135 and 166 now expects "Terrain, walking and permits are not on file for this trail yet." and no "Season ... not on file"); `test_about_this_data_gives_the_method_for_an_estimate`. `test_trust.py`: `test_an_estimated_season_sentence_says_no_source_gives_one` (and the in-brief paragraph of every estimated real record contains "No source gives a season"); rewrite the check at lines 222 to 236 so it asserts that every real record's in-brief paragraph has a season sentence, not that records without one lack it. `test_structured_data.py`: replace line 214 with `("Usual season", None) in props == bool(h.get("season") and h.get("season_basis") != "estimate")`; add `test_no_estimated_season_appears_in_structured_data`.
- [ ] **Step 2: Run** the three files. Expected: failures.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the three files. Expected: PASS.
- [ ] **Step 5: Commit** `git add web && git commit -m "Show an estimated season as an estimate on the trail page, and not in structured data"`

### Task 22: Month lists, rows, collection tables

**Files:**
- Modify: `web/olt/browse.py` (`BROWSE` blurb at the `month` group, `_month_list`, `month_note`)
- Modify: `web/olt/home.py` (`entry`: a `Season` fact and `data-estimate`)
- Modify: `web/olt/standing.py` (`season_cell`, `figures_note`)
- Modify: `web/assets/style.css` (hide `.entry__season` unless `[data-season-shown]`)
- Test: `web/tests/test_views.py`, `web/tests/test_facets.py`, `web/tests/test_filter_bar.py`

**Behaviour and copy:**
- Group blurb: "Trails normally hiked in the month. Estimated seasons are marked."
- `_month_list` description: "Trails normally hiked in {name}. Estimated seasons are marked."
- `month_note(name)` returns "A source states the season for X of these. For the other Y it is estimated from climate, and marked." (X, Y computed; with Y zero: "A source states the season for all X."; with X zero: "No source states the season for these, so each is estimated from climate.")
- Row: `<div class="entry__season"><dt>Season</dt><dd>{season_text}<small class="entry__est">estimate</small></dd></div>` (the small label only when estimated), `data-estimate="yes"` on the row when estimated, nothing when not. `listing()` sets `data-season-shown` on the results container for month lists; Task 23's script sets it when a month is chosen.
- `standing.season_cell(rec)` returns `facets.season_text(rec)` ("Not on file" removed); `figures_note` adds "Seasons that start with “About” are estimated from climate (N of these)."

- [ ] **Step 1: Write failing tests.** `test_views.py`: rewrite `MonthListTest.test_a_month_needs_eight_trails_and_says_how_many_have_a_season` as `test_a_month_note_counts_stated_and_estimated_exactly` (ten stated and five estimated in July: the note contains "A source states the season for 10 of these. For the other 5 it is estimated from climate, and marked."), plus `test_a_month_list_with_no_estimates_says_so` and `test_the_month_blurb_no_longer_says_only_some_trails`. `test_facets.py`: `test_a_row_marks_an_estimated_season` (the row HTML contains `data-estimate="yes"` and `entry__est">estimate`; a stated one contains neither); `test_the_season_fact_is_hidden_unless_a_month_is_shown` (CSS text contains the `[data-season-shown]` rule). `test_filter_bar.py`: `test_standing_tables_mark_an_estimated_season` (collection table cell reads "About June to September"). Run `BuiltVocabularyTest.test_no_banned_word_on_a_browsing_page` after.
- [ ] **Step 2: Run** the three files. Expected: failures.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the three files. Expected: PASS.
- [ ] **Step 5: Commit** `git add web && git commit -m "Month lists, rows and tables include every trail and mark estimates"`

### Task 23: The filter bar

**Files:**
- Modify: `web/olt/home.py` (`finder_form`: the checkbox inside the `data-facet="month"` field; `results()`: remove the `unseasoned` note)
- Modify: `web/assets/app.js` (state `stated`; `FacetCount.passes`; URL parameter; remove the `unseasoned` block near lines 2062 to 2071, 2464 to 2471 and 2502 to 2509; set `data-season-shown` when a month is chosen)
- Test: `web/tests/test_filter_bar.py`, `web/tests/test_facets.py`

**Behaviour:** a checkbox `<input type="checkbox" name="stated" value="1">` labelled "Leave out estimated seasons", inside the month field, `disabled` until a month is chosen; rows carry `data-estimate`; with a month and `stated` on, `FacetCount.passes(d, s, 'month')` is false for a row whose `d.estimate` is true; the address carries `?month=7&stated=1`; the count words and the per-month numbers ignore estimated rows exactly when `stated` is on (they come from `passes`). The "N trails with no season on file" note, the "Show them" button and their script are gone.

- [ ] **Step 1: Write failing tests.** Delete `UnseasonedNoteTest` and replace with `LeaveOutEstimatesTest`: `test_the_month_field_has_the_checkbox_and_it_starts_disabled`; `test_the_results_have_no_unseasoned_note` (`'data-unseasoned'` absent from `home.results(recs, finder=True)`); under node (skip when node is missing, as the file does): `test_with_stated_on_estimated_rows_leave_the_month` and `test_counts_follow_it` (rows `{months: [7], estimate: true}` and `{months: [7], estimate: false}`; month 7 count is 2 with it off and 1 with it on; the shown count matches `sum(...)`, as `test_the_number_is_the_trails_that_pass_everything_else...` does). In `test_facets.py`: drop `test_a_month_row_with_no_season_is_left_out...` assertions that pin "no season on file" only if they fail, keeping the generic mechanism test on `terrain`; assert `data-months=""` is no longer needed for real records (every real row has months).
- [ ] **Step 2: Run** the two files. Expected: failures.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the two files. Expected: PASS.
- [ ] **Step 5: Commit** `git add web && git commit -m "Let the month filter leave out estimated seasons; drop the no-season note"`

### Task 24: Reference page, glossary, schema wording

**Files:**
- Modify: `web/olt/reference.py` (the coverage rows around line 123; the "Season and high point" section around line 147)
- Modify: `glossary.toml` (the `season` term)
- Modify: `docs/schema.md` (only if Task 1's `season` meaning needs the phrase the reference page quotes)
- Test: `web/tests/test_trust.py` or `web/tests/test_pages.py` (whichever holds the reference page assertions; find with `grep -n "reference\\." web/tests/*.py`)

**Behaviour:**
- Coverage table: the single "A season" row becomes "A season a source states" and "A season estimated from climate", each counted from the records (their two counts add to 223).
- "Season and high point" section: drops "Not every record has them, so a page built from them says how many records it covers." for season; adds a paragraph: "Every trail has a season. Where a page states one, the season is that page's. Where none does, the season is estimated from climate at the trail's elevation, shown as 'About' with a note, and marked in lists. Checked against the seasons that pages do state, the estimates for N of M trails (P percent) come within a month at each end of the stated season." N, M, P come from `tools/season_fit.json` at build time, labelled as fitted on the same trails; the paragraph says it again as "This is a measure of fit, not a promise for a single trail."
- Glossary `season`: "The months in which the whole trail is usually walked. Where a page states them, that is shown. Otherwise they are estimated from climate at the trail's elevation, and the page says so." (Remove "Only some records state one.")

- [ ] **Step 1: Write failing tests:** `test_the_reference_page_counts_stated_and_estimated_seasons` (the two rows' counts equal the real counts and add to the number of trails); `test_the_reference_page_gives_the_fit_from_the_fit_file` (the page contains the figures in `season_fit.json`); `test_the_glossary_no_longer_says_only_some_records_state_a_season`; `test_no_page_says_only_some_trails_have_a_season` (build once and search the built HTML of every page for "Only some trails have a season" and "season on file"; none).
- [ ] **Step 2: Run** the file. Expected: failures.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the file. Expected: PASS.
- [ ] **Step 5: Commit** `git add web glossary.toml docs && git commit -m "Reference page and glossary describe seasons and the fit of the estimates"`

### Task 25: Verify and ship

**Files:** `CHANGELOG.md`.

- [ ] **Step 1: Changelog.** Entry headed `Every trail now has a season`: exact counts of stated and estimated seasons (computed, not typed), what "About" means, that estimated seasons are marked in lists and left out of structured data, that the month filter can leave estimates out, the fit figure from `tools/season_fit.json`, and that the month lists now include every trail.
- [ ] **Step 2: Run everything.** `python3 tools/validate.py`; `python3 tools/check_history.py --base main`; `python3 -m unittest discover tools/tests`; the full web tests (includes `BuiltVocabularyTest`, which fails on any banned word on a browsing page); `python3 web/build.py --out _site`.
- [ ] **Step 3: Read the built pages.** Three trails (one primary, one sourced from one page, one estimated with no track), the "Hiking in July" list, the home page with `?month=7` (use the built `_site/index.html` and read the form), the reference page. Check: miles and feet first; no estimate without "About" and a note; no "no season on file" anywhere; counts equal the records'.
- [ ] **Step 4: Commit** `git add CHANGELOG.md && git commit -m "Every trail has a season"`. **Ship 4 is complete.**

---

## Self-review

**Spec coverage.**
- Schema, `season_basis`, `season_method`, the estimate exception: Task 1. Validator rules (count fits basis, exempt from the facts rule, `season` with `months`, estimate's only source is climate): Tasks 2, 6, 19. History: Global Constraints, Tasks 5, 9, 15, 18.
- Step 1 classify the 109 (proposed table, person reviews): Tasks 3 to 5. Step 2 research the 114: Tasks 7 to 9 (batch size 10, what is recorded, what is acceptable, what a reviewer checks). Step 3 estimator: Tasks 10 to 16 (every push by the validator in Task 19, every month by Task 16's workflow, every audit by `docs/audit.md`); where, elevation, climate, rule, check, review list: Tasks 11 to 15; the bar and the "not shipped" gate: Tasks 14 and 17; climate source by trial: Task 11.
- Site: trail page, rows, month lists, blurb, note and button removal, filter, glossary, reference, structured data: Tasks 20 to 24. Tests rewritten, not patched: Tasks 21 to 23.
- Order, four ships with changelog entries: Tasks 6, 9, 16, 25.

**Step scan.** Every code step names a file and signature; tests name their assertions; commands and expected results are given.

**Type consistency.** `PointNormals` is defined in Task 11 and used in Tasks 12, 14, 15; `SamplePoint`, `Params` in Task 12; `season.BASES`, `PROVENANCE_KEYS`, `check_season`, `SEASON_REQUIRED` in Task 2 and used in 6 and 19; `phrase_for`, `span`, `grade`, `method_sentence` in Task 10 and used in 14, 15 and 19; `facets.season_basis_line` in Task 6 and extended in Task 21; `BAR` in Task 14 and used in 17.

**Proportion.** About three times the spec's length; the extra is the data tasks and test names, with no function bodies.

## Not verifiable from here

- The web test suite was not run to completion in planning (it takes over two minutes); the tool tests passed (322).
- Whether `refresh.py` `validate_proposal` accepts an array value for `hike.months` in an edit is proved or fixed by Task 8.
- The climate sources' current terms, rates and coverage, and whether any passes the bar, are unknown until Tasks 11 and 14. The 75 percent bar is a proposal for the owner to confirm.
- `grep -n "reference\\." web/tests/*.py` (Task 24) must find where the reference page is tested; none was located during planning.
