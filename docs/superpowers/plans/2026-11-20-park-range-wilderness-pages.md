# Park, Range and Wilderness Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add pages for national and provincial parks, mountain ranges and wilderness areas with 3 or more trails, crossed with the existing lists, from a place field on every record.

**Architecture:** A top-level `places.toml` registry and a `[[place]]` table on each record hold membership. `tools/place_trails.py` (third-party geometry libraries, never part of the build) measures tracks against published outlines and writes both. The build (standard library only) reads the registry and records, and the state-page code is generalised so a place is a kind plus a slug, with states as one kind.

**Tech Stack:** Python 3.12 standard library for `tools/validate.py` and `web/`; `shapely`, `pyproj`, `pyogrio` for `tools/place_trails.py` only; `unittest`; GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-20-park-range-wilderness-pages-design.md`

## Global Constraints

- Membership: at least 1 mile (1.6 km) of the trail's main track inside the outline; alternates do not count. A nested range also gives membership of every `within` parent.
- A place page and a place-plus-list page need 3 or more trails; the 3 counts both bases (`track` and `stated`). A place below 3 gets no page and no link. A place-plus-list page is not built when the list holds every trail on the place page.
- URLs: `/parks/<slug>/`, `/ranges/<slug>/`, `/wilderness/<slug>/`, and `/<kind>/<slug>/<list key>/`. No existing URL changes. Navigation stays as built (`layout.NAV`: Trails, Places, Lists, About).
- The site build and `tools/validate.py` use only the Python standard library. Only `tools/place_trails.py` may use other libraries.
- Every change to a record fact has a `[[history]]` entry (`docs/schema.md`, "The check"). Adding or removing a place on a record is a fact change; a re-run that only changes `km` is not.
- Every ship has a `CHANGELOG.md` entry in the same commit as the ship (standing rule). Land each ship as one squash commit so the entry travels with the code. Commit messages end with the attribution line the session gives.
- Counts shown are exact. A browsing page's first screen holds the filter bar, rows and map; search-oriented text goes below.
- The words `record`, `tier`, `wave`, `held`, `listing`, `entry`, `regions` and the rest of `BANNED` in `web/tests/test_facets.py` never appear on a browsing page.
- The measured `km` inside a place is never shown anywhere, including `[[history]]` text and the page's structured data.
- Never kill a process by name (`pkill`, `killall`). Kill only a PID you started.
- Boundary sources, licences and credits are those of the spec's "Boundary sources" table. Outlines are cached outside the repo and never committed.
- Slugs are unique within a kind, not across kinds.

## Existing refresh machinery and docs/audit.md

Found, not invented here:

- `.claude/skills/refresh-trails/SKILL.md` is the monthly refresh runbook (phases 0 to 9, `light` mode). It verifies every record against its cited pages, re-checks the left-out list, searches for missing trails, updates tracks and emblems, reviews, and applies. `tools/refresh.py` does its mechanical parts (`preflight`, `slices`, `links`, `collect`, `apply`); staging is `refresh/<date>/`, which `.gitignore` lists. `tools/tests/test_refresh_skill.py` guards the skill's wording and files.
- Its phase 8 worker (`briefs/apply.md`) applies new records. After this plan a new record fails `validate.py` without `places_checked`, so the brief and the skill gain a step that runs `place_trails.py` for new or changed-track ids.
- The "monthly audit of everything" has no written checklist. `docs/audit.md` becomes it: a plain checklist the owner runs, whose first items are the existing machinery (`/refresh-trails` full or light, `python3 tools/refresh.py links`, `validate.py`, `check_history.py`, both test suites) and whose new items are `place_trails.py --check` and the hand review of `stated` placements. `docs/audit.md` does not duplicate the skill's phases; it points at them. The monthly GitHub workflow in this plan runs only the automatic part.

## Decisions the design left to the builder

1. A record's `[[place]]` carries `kind` and `slug` (the design's example omits `kind`, but slugs repeat across kinds).
2. A record carries two top-level fields: `places_checked` (a date) and `places_track` (first 16 hex digits of the SHA-256 of `line.geojson`'s bytes; absent when the record has no track). The validator fails a record whose `places_track` differs from its track's hash. Neither field is a fact in `trail_history`. `place.km` is not a fact; `place.kind`, `place.slug`, `place.basis` and `place.source` are.
3. Parents are never stored on records. The build closes membership over `within` (`places.membership`); a `within` cycle or unknown parent is a validator error.
4. `basis = "stated"` is allowed only on a record with no track; `track` only on one with a track. A trail later given a track must be re-measured, which the `places_track` check forces.
5. Ship 1 validates shape only. The rule "every record has `places_checked`" is switched on by one constant, `check_places.REQUIRE_PLACES_CHECKED`, in ship 2 after the records are written.
6. Registry fields: `slug`, `kind`, `name`, `where`, `within`, `source`, `source_id` (a string, or an array when one page joins units), `source_version`, `box`. `where` is proposed by the tool from the `regions` codes shared by at least half of the place's measured trails and is confirmed by a reviewer.
7. The range allow-list and the extra park units live in `tools/place_allowlist.toml`; wilderness and national parks are taken whole from their sources. Slugs come from the name; a collision within a kind is resolved by appending the state code.
8. On a place page: rows in plain A to Z (the state pages' "wholly in" lead does not apply), `where="all"` filter, map opened on the registry `box`, `summary.facts(place=(name, ()))` so no whole-trail figure is given as the place's.
9. Titles: parks "Long Hikes in {name}"; ranges and wilderness "Long Hikes in {name}, {State}" when `where` has one state, else no suffix; each adds ": N Trails" when it fits (`common.fit_title`). Place plus list: "{lst.noun} in {title name}".
10. Place-plus-list uses `PLACE_MIN = 3` and `browse.shown` (the list must be shown at all), and keeps `SAME_SET` de-duplication. State-plus-list keeps `browse.MIN_SIZE = 5`.
11. Site search: place names join the place text of each row's `data-search` (`searchtext.place_names`). The box filters rows; it does not return pages.
12. The Places hub title stays; its lede gains a sentence and three sections.
13. Ship 4 changes titles of state-plus-list pages where a list's `noun` changes. This is the design's intent ("existing list pages retitled"); the state pages themselves (`/regions/<state>/`) stay unchanged.
14. Tool output, proposals and worksheets go to `refresh/<date>/places/` (gitignored). Cache: `$PLACES_CACHE`, default `$XDG_CACHE_HOME/longhikes-places`.

## Review Focus

- A track in several features or parts whose short pieces inside an outline add up to over 1.6 km (counts); one that skims with 1.5 km in total (does not). Tested in Task 4.
- A place that has exactly 3 trails loses one: its page, its place-plus-list pages, its links and its hub row all go, and counts elsewhere stay exact. Tested in Tasks 7 and 11.
- Two places in different kinds share a slug (`glacier` park, `glacier` wilderness): both pages build, both resolve. Tested in Tasks 2 and 7.
- A `within` chain: a Teton Range trail is on the Rocky Mountains page; a cycle in `within` is refused. Tested in Tasks 3 and 7.
- A trackless trail given a track later: its `stated` entries become invalid and its `places_track` is required. Tested in Task 3.

---

## Ship 1: registry, record field, validator, tool, proposal

### Task 1: Guard for the existing state pages

The existing tests (`test_place_order`, `test_place_view`, `test_filter_bar`, `test_search_text`, `test_views`, `test_first_screen`, `test_empty_places`) check pieces of state pages. None compares their built output. Add one, before any code changes.

**Files:**
- Create: `web/tests/test_state_pages_unchanged.py`, `web/tests/golden/state-pages.json`, `web/tests/make_golden.py`
- Test: the same

**Interfaces:**
- Produces: `normalise(html: str) -> str` in the test module: removes `data-search="..."` attributes, and removes any `<nav class="region-nav" aria-label="Parks, ranges and wilderness in ...">` block (added in ship 2); later tasks reuse it.

- [ ] **Step 1: Write the golden maker.** `make_golden.py` builds a fixed set of fake records (use `fake()` from `test_hike.py`; 12 records over `US-CO`, `US-UT`, `CA-ON`, one `CA-*`, mixed trails and routes, loops, tracks with `derived["bbox"]` as `test_place_view` sets) and writes `{path: sha256(normalise(html))}` for `regions.region_page` (every state), `regions.group_page` (every group), `regions.regions_index_page`, `regions.empty_place_page("US-HI", ...)` and every `placefacets.page` of `placefacets.plan`.
- [ ] **Step 2: Write the test** `StatePagesUnchangedTest.test_every_state_group_and_state_list_page_is_byte_identical_after_normalising`: rebuilds the same map and `assertEqual`s it to `golden/state-pages.json`, naming each path that differs.
- [ ] **Step 3: Run the maker on current `main`**, before any other change: `python3 web/tests/make_golden.py`. Commit the golden.
- [ ] **Step 4: Take a whole-site baseline** for the ship gates: `python3 web/build.py --out web/.cache/baseline-site` (`web/.cache/` is ignored). Do not delete it until ship 4 lands.
- [ ] **Step 5: Run** `python3 -m unittest discover -s web/tests -p "test_state_pages_unchanged.py"`. Expected: OK.
- [ ] **Step 6: Commit** `test: pin the built state, group and state-list pages`.

### Task 2: Schema, registry file and the record's history fields

**Files:**
- Create: `places.toml` (header comment only, no entries), `tools/tests/test_places_schema.py`
- Modify: `docs/schema.md` (new sections `places.toml` and `[[place]]` on the record, plus `places_checked`, `places_track` under "Top level"; update the fact lists), `tools/trail_history.py` (`_TABLES`, `NOT_FACTS`, `FACTS_TEXT`, `NOT_FACTS_TEXT`), `web/olt/datafiles.py`
- Test: `tools/tests/test_places_schema.py`

**Interfaces:**
- Produces: `trail_history._TABLES[""]` gains `"places_checked", "places_track"`; new `_TABLES["place"] = ("kind", "slug", "basis", "km", "source")`; `NOT_FACTS` gains `"places_checked", "places_track", "place.km"`; `datafiles.places(repo_root) -> list[dict]` (the `[[place]]` tables of `places.toml`).

- [ ] **Step 1: Write failing tests.**
  - `test_place_fields_are_schema_fields`: `"place" in H.SCHEMA_FIELDS`, `"place.km" in H.SCHEMA_FIELDS`, `"places_checked" in H.SCHEMA_FIELDS`.
  - `test_km_and_stamps_are_not_facts`: `H.is_fact("place.km") is False`, same for `places_checked`, `places_track`; `H.is_fact("place.slug") is True`, `H.is_fact("place.basis") is True`.
  - `test_a_km_only_change_needs_no_history`: `H.changed_paths(old, new)` where only `place.km` differs returns `["place.km"]`, and a filter by `is_fact` is empty.
  - `test_schema_documents_every_place_field`: every name in `_TABLES["place"]` and `places_checked`, `places_track` appears in `docs/schema.md`.
  - `test_facts_text_names_place`: `"place" in H.FACTS_TEXT`.
- [ ] **Step 2: Run** `python3 -m unittest discover tools/tests -p "test_places_schema.py"`; expect FAIL.
- [ ] **Step 3: Implement** the edits above. In `docs/schema.md` document: registry fields (decision 6; `box` is `[west, south, east, north]` rounded to 2 decimals; `km` and `box` are measurements); the record `[[place]]` (`basis` `track` needs `km`, `stated` needs `source` and forbids `km`); `places_checked`, `places_track`; and say `km` is never shown. Add `datafiles.places`.
- [ ] **Step 4: Run** the new test and `python3 -m unittest discover tools/tests`; expect OK.
- [ ] **Step 5: Commit** `feat: schema for place registry and record place fields`.

### Task 3: Validator checks (`tools/check_places.py`)

**Files:**
- Create: `tools/check_places.py`, `tools/tests/test_places.py`
- Modify: `tools/validate.py` (call after `check_datafiles.check_datafiles(...)`), `.github/workflows/validate.yml` (add `python3 -m unittest discover tools/tests -p "test_places*.py"` to the `validate` job)
- Test: `tools/tests/test_places.py` (standard library only; no shapely)

**Interfaces:**
- Produces: `check_places.REQUIRE_PLACES_CHECKED = False`; `check_places.track_hash(path: str) -> str` (16 hex digits); `check_places.check_registry(entries: list[dict], errors: list[str]) -> None`; `check_places.check_record(tid: str, rec: dict, tdir: str, registry: dict[tuple[str, str], dict], errors: list[str]) -> None`; `check_places.check(root: str, trails: list[dict], errors: list[str]) -> None` (loads `places.toml`, builds `registry` keyed `(kind, slug)`, runs both, then the cross-checks).

- [ ] **Step 1: Write failing tests** (each builds small dicts or a temp directory; assert the error text contains the quoted phrase):
  - `test_registry_entry_needs_every_field`: missing `box` → "box".
  - `test_kind_must_be_park_range_or_wilderness`.
  - `test_same_slug_in_two_kinds_is_allowed_and_twice_in_one_kind_is_not`.
  - `test_within_names_existing_ranges_and_has_no_cycle`: unknown parent and a two-entry cycle each → "within".
  - `test_source_id_is_a_string_or_a_list_of_strings`.
  - `test_box_is_west_south_east_north_inside_the_world`.
  - `test_record_place_must_be_in_the_registry`: `(kind, slug)` absent → "not in places.toml".
  - `test_track_basis_needs_km_and_forbids_source_and_stated_the_reverse`.
  - `test_stated_needs_a_source_url_and_a_trackless_record`: a record with `source.line_file` and a `stated` place → "stated".
  - `test_a_place_is_listed_once_per_record`.
  - `test_every_registry_entry_is_named_by_a_record`: unnamed entry → "named by no record".
  - `test_places_track_must_match_the_track_file`: write `line.geojson`, set a wrong `places_track` → "track has changed since".
  - `test_a_record_with_a_track_needs_places_track_and_one_without_must_not_have_it`.
  - `test_places_checked_required_only_when_switched_on`: with `REQUIRE_PLACES_CHECKED` patched true, a record without it → "places_checked"; false → no error; a bad date → error either way.
  - `test_a_trackless_trail_given_a_track_later_is_refused`: stated place plus a track file → error (Review Focus).
  - `test_the_real_repository_passes`: `check_places.check(ROOT, trails, errors)` leaves `errors == []`.
- [ ] **Step 2: Run** `python3 -m unittest discover tools/tests -p "test_places.py"`; expect FAIL (module missing).
- [ ] **Step 3: Implement** the signatures above. Follow `check_datafiles.py`: one message per problem, standard library only. `track_hash` hashes the file's bytes with `hashlib.sha256`.
- [ ] **Step 4: Run** the test, then `python3 tools/validate.py`; expect `OK 223 trails`.
- [ ] **Step 5: Commit** `feat: validate places.toml and the record's place fields`.

### Task 4: `tools/place_trails.py` geometry and measuring

**Files:**
- Create: `tools/place_trails.py`, `tools/place_trails.requirements.txt` (`shapely>=2.0`, `pyproj>=3.6`, `pyogrio>=0.7`), `tools/tests/test_place_trails.py`
- Modify: `.gitignore` (add `.venv-places/`)
- Test: `tools/tests/test_place_trails.py` (`unittest.skipUnless(shapely importable)`; no network, tiny synthetic outlines and tracks)

**Interfaces:**
- Produces: `MIN_KM = 1.609344`; `main_track(rec_dir: str) -> shapely.MultiLineString | None` (every feature of the record's `source.line_file` only; `alternates.geojson` and `line-<source>.geojson` are never read); `km_inside(track, outline) -> float` (geodesic length of `track ∩ outline` with `pyproj.Geod(ellps="WGS84")`, summed over all pieces, holes respected); `box_of(outline) -> list[float]` (rounded to 2 decimals); `track_hash(rec_dir) -> str` (same value as `check_places.track_hash`; import it).
- Third-party use: only this file, and only after a guarded import so `python3 tools/place_trails.py --help` explains the install on failure.

- [ ] **Step 1: Write failing tests.**
  - `test_pieces_inside_are_summed`: a track of three features, each 0.7 km inside one outline → `km_inside` ≈ 2.1, over `MIN_KM`.
  - `test_a_skimming_track_is_under_the_threshold`: 1.5 km inside → below `MIN_KM`.
  - `test_a_hole_is_not_inside`: a track wholly in an enclave hole → 0.
  - `test_alternates_are_ignored`: a record directory with a long `alternates.geojson` inside and a short main track outside → `km_inside == 0`.
  - `test_a_record_with_no_line_file_has_no_track`: `main_track` returns `None`.
  - `test_box_of_is_west_south_east_north_rounded`.
  - `test_track_hash_matches_the_validators`.
- [ ] **Step 2: Run** `python3 -m unittest discover tools/tests -p "test_place_trails.py"` inside the venv (see Step 3); expect FAIL.
- [ ] **Step 3: Implement.** Install: `python3 -m venv .venv-places && .venv-places/bin/pip install -r tools/place_trails.requirements.txt`. The venv is for this tool only; the site build, `validate.py` and the `site` and `validate` workflow jobs never install it. Intersect in lon/lat; measure on the ellipsoid.
- [ ] **Step 4: Run** with `.venv-places/bin/python -m unittest discover tools/tests -p "test_place_trails.py"`; expect OK. Run `python3 -m unittest discover tools/tests` with the system Python; expect the file skipped, not failed.
- [ ] **Step 5: Commit** `feat: place_trails geometry`.

### Task 5: Outline sources, catalogue and the proposal

**Files:**
- Modify: `tools/place_trails.py`, `tools/tests/test_place_trails.py`
- Create: `tools/place_allowlist.toml` (empty tables, comments only)

**Interfaces:**
- Consumes: Task 4's functions.
- Produces: `SOURCES: dict[str, Source]` for `nps`, `wilderness-connect`, `cpcad`, `gmba-v2`; each `Source` holds `url` (confirmed in Step 3), `licence`, `credit`, and a reader `read(path) -> Iterator[Outline]`; `Outline = (kind, source, source_id, name, state_codes_hint, geometry)`; `fetch(source, cache_dir) -> tuple[str, str]` returns `(path, source_version)` (the publisher's version, else the download date) and never re-downloads a cached file; `catalogue(cache_dir) -> list[Outline]` (parks: NPS unit type National Park plus the allow-list's `[[park]]` extras, which carry two `source_id`s for Sequoia and Kings Canyon; all Wilderness Connect polygons; CPCAD national parks and BC and Alberta provincial parks; ranges only the allow-list's `[[range]]` ids: `gmba_id`, `slug`, `name`, `within`); `propose(records, outlines) -> Proposal`; `render_proposal(p, path) -> None`; subcommands `candidates` and `propose`.

- [ ] **Step 1: Write failing tests** (synthetic outlines through a stub `Source`):
  - `test_propose_lists_per_trail_places_and_per_place_trails`.
  - `test_a_trail_under_the_threshold_is_not_in_the_place`.
  - `test_places_with_fewer_than_three_trails_are_marked_no_page`.
  - `test_near_threshold_items_are_listed_first_and_flagged`: any `km` within 0.5 km of `MIN_KM`.
  - `test_where_is_the_regions_most_trails_share`.
  - `test_a_slug_collision_inside_a_kind_gets_the_state_code`.
  - `test_the_proposal_names_every_trail_with_no_track_as_needing_a_person`.
  - `test_one_gmba_id_outside_the_allow_list_is_not_proposed_but_is_listed_by_candidates` (`candidates` prints GMBA ranges that 3 or more tracks cross and that are not allow-listed).
- [ ] **Step 2: Run** the new tests; expect FAIL.
- [ ] **Step 3: Implement.** Before coding the readers, open each publisher's download page and confirm the endpoint, file format and field names (NPS boundary service unit-type field; Wilderness Connect; CPCAD's park-type and jurisdiction fields; GMBA v2's id field). The design's findings were not verified by the designer. Write each confirmed fact in the `SOURCES` comments. Proposal output: `refresh/<date>/places/proposal.md` (per trail, then per place) and `proposal.json` (the machine form Task 6 reads). `km` appears in the proposal for reviewers only.
- [ ] **Step 4: Run** the test file in the venv; expect OK.
- [ ] **Step 5: Commit** `feat: place_trails outline catalogue and proposal`.

### Task 6: Writing records and the registry; `stated`, `stamp` and `--check`

**Files:**
- Modify: `tools/place_trails.py`, `tools/tests/test_place_trails.py`

**Interfaces:**
- Consumes: `refresh.Doc` from `tools/refresh.py` (targeted line edits; `set_value`, `append_block`, `append_history`), Task 5's `Proposal`.
- Produces: `apply(proposal_path: str, root: str, today: str) -> list[str]` (ids written); `write_registry(root, entries) -> None` (rewrites `places.toml` sorted by kind then slug, only places some record names; keeps comments above the first entry); `add_stated(root, rid, kind, slug, source_url, quote, today) -> None`; `stamp_none(root, rid, today) -> None`; `check(root, cache_dir) -> list[str]` (differences; empty when none); subcommands `apply`, `stated`, `stamp`, `--check`.

- [ ] **Step 1: Write failing tests** (a temporary repository with two small records):
  - `test_apply_adds_place_tables_stamp_and_hash_by_line_edits`: the rest of `trail.toml` is byte-identical.
  - `test_apply_adds_one_history_entry_naming_place_with_no_distance_in_it`: `fields == ["place"]`, `asked_by` is `H.OWN_CHECK`, `basis_url` is the source's page, and `change` and `basis` match no `\d\s*(km|mi)`.
  - `test_a_rerun_that_only_changes_km_adds_no_history_and_keeps_the_stamp_date_rule`: updates `places_checked` and `km`, adds no entry.
  - `test_a_rerun_that_adds_or_removes_a_place_adds_history`.
  - `test_registry_lists_only_named_places_and_is_sorted`.
  - `test_stated_requires_an_http_source_a_quote_and_a_trackless_record`.
  - `test_stamp_none_sets_places_checked_with_no_place_tables_and_no_history`.
  - `test_check_reports_a_place_gained_lost_a_moved_boundary_and_a_place_crossing_three_trails`, each as its own line.
  - `test_check_exits_nonzero_with_differences_and_zero_without`.
  - `test_the_written_records_pass_check_places`: runs `check_places.check` on the temp repository.
- [ ] **Step 2: Run**; expect FAIL.
- [ ] **Step 3: Implement.** `apply` writes top-level `places_checked` and `places_track` with `Doc.set_value`, each `[[place]]` with `Doc.append_block("place", ...)`, and the history with `Doc.append_history`. History date is today; `basis` names the outline source and its `source_version`; `basis_url` is the source's page. `--check` reuses `propose` against the current outlines (cache refreshed), compares to the committed records and registry (including `source_version`), and prints one difference per line.
- [ ] **Step 4: Run** the tool tests in the venv; expect OK.
- [ ] **Step 5: Commit** `feat: place_trails writes records, stated placements and --check`.

### Task 7: First run, proposal review and the ship

This is data work with a gate: nothing is written to records in this ship.

**Files:**
- Modify: `tools/place_allowlist.toml`, `CHANGELOG.md`
- No record changes.

- [ ] **Step 1: Run** `.venv-places/bin/python tools/place_trails.py propose`, then `candidates`. Both write to `refresh/<date>/places/`.
- [ ] **Step 2: Review.** A worker on a different model family from the one that built the tool reads `proposal.md` and reports, for each of: (a) every trail whose proposed places do not fit its own summary, `designation` or ends; (b) every near-threshold item (open the clipped piece in `near-threshold.geojson` and say whether the track really enters); (c) places that would fall under 3 trails; (d) the range candidates (3 or more tracks cross): keep, drop, rename; (e) any source whose field or licence reading looks wrong. The owner reads the reviewer's list and the proposed range allow-list and rules on both. The owner's rulings are recorded in `tools/place_allowlist.toml`.
- [ ] **Step 3: Run** `python3 tools/validate.py` and `python3 -m unittest discover tools/tests`, then `python3 -m unittest discover -s web/tests` and `python3 web/build.py --out _site`; all pass and the site is unchanged.
- [ ] **Step 4: Compare** `diff -r web/.cache/baseline-site _site -q`; expect only files that embed a build date or hash (explain any other).
- [ ] **Step 5: Add the CHANGELOG entry** `## 2026-MM-DD - The place registry and the placing tool`, in the voice of the entries there: for contributors, `places.toml`, the `[[place]]` table, `places_checked`, `place_trails.py` (venv install line), the allow-list; no visitor change.
- [ ] **Step 6: Squash and ship** (one commit with the entry); push. Expected: `validate`, `history` and `site` jobs green.

---

## Ship 2: records written, place pages, hub and cross-links

### Task 8: The place loader (`web/olt/places.py`)

**Files:**
- Create: `web/olt/places.py`, `web/tests/test_places.py`
- Modify: `web/olt/datafiles.py` (already has `places`)
- Test: `web/tests/test_places.py`

**Interfaces:**
- Produces: `PAGE_MIN = 3`; `KINDS: dict[str, Kind]` with `Kind(key, segment, hub_title, noun)` for `park` (`parks`, "Parks"), `range` (`ranges`, "Mountain ranges"), `wilderness` (`wilderness`, "Wilderness areas"); `load(repo_root) -> dict[tuple[str, str], dict]` (registry keyed `(kind, slug)`); `membership(records, registry) -> dict[tuple[str, str], list[dict]]` (each place's records, deduplicated, A to Z by `home.sort_name`, closed over `within`); `collect(records, registry) -> dict[tuple[str, str], dict]` (only places with `PAGE_MIN` or more records; each info dict: `kind`, `slug`, `key` (`"<kind>/<slug>"`), `name`, `where`, `box`, `records`, `path`, `title_name`); `path(kind, slug) -> str` (`/parks/glacier/`); `title_name(info) -> str` (decision 9); `in_state(infos, state_key) -> list[dict]`; `of_record(rec, infos) -> list[dict]` (places of a trail that have a page, by kind then name).

- [ ] **Step 1: Write failing tests** (fixtures from `test_hike.fake`):
  - `test_a_range_gets_a_page_at_three_trails_and_not_at_two`.
  - `test_stated_and_track_trails_both_count`.
  - `test_a_trail_in_a_nested_range_is_on_every_parent` (Teton Range within Rocky Mountains).
  - `test_slugs_repeat_across_kinds`: `/parks/glacier/` and `/wilderness/glacier/` both collect, with different records.
  - `test_a_parent_is_counted_once_when_a_trail_is_in_two_children`.
  - `test_title_name_adds_the_state_for_a_range_with_one_state_only`: "Wind River Range, Wyoming"; a park gives its name alone.
  - `test_of_record_leaves_out_a_place_below_the_minimum`.
- [ ] **Step 2: Run** `python3 -m unittest discover -s web/tests -p "test_places.py"`; expect FAIL.
- [ ] **Step 3: Implement**, standard library only. `records.load_record` passes unknown tables through, so no change there; attach nothing to `rec["derived"]`.
- [ ] **Step 4: Run**; expect OK.
- [ ] **Step 5: Commit** `feat: place loader and membership`.

### Task 9: Generalise the state-page code

**Files:**
- Modify: `web/olt/regions.py` (`collect_regions`, `region_page`), `web/olt/home.py` only if a string is baked in
- Test: `web/tests/test_state_pages_unchanged.py` (Task 1) is the guard; add `web/tests/test_place_page.py` in Task 10

**Interfaces:**
- Produces: in `regions.py`, `PageKind` (frozen dataclass: `kicker(info) -> str`, `crumbs(info) -> str`, `lede(info, recs, n_gpx) -> str`, `where: str`, `wholly: bool`, `facts_place(info) -> tuple`, `title_options(info, recs, site) -> list[str]`, `description(info, recs) -> str`); `STATE = PageKind(...)` reproducing today's strings exactly; `regions.place_page(info, records, site, kind, *, facet_pages=(), place_links="") -> (title, description, body, needs_map)`. `region_page(slug, records, site, facet_pages=(), place_links="")` becomes a call to `place_page` with `STATE`. State info dicts gain `"kind": "state"`.

- [ ] **Step 1: Run** the Task 1 guard first; expect OK (baseline).
- [ ] **Step 2: Refactor** `region_page` into `place_page` plus `STATE`; no string changes. `place_links` is HTML put after the existing navs (empty for every state until Task 12).
- [ ] **Step 3: Run** `python3 -m unittest discover -s web/tests`; expect OK, including the guard.
- [ ] **Step 4: Commit** `refactor: state pages built through a page kind`.

### Task 10: Place pages and the page-kind plug-in point

**Files:**
- Create: `web/olt/placepages.py`, `web/tests/test_place_page.py`
- Modify: `web/olt/pages.py` (`render_site`), `web/olt/layout.py` (`NAV_PARENT`), `web/tests/test_facets.py` (`browsing_pages`)
- Test: `web/tests/test_place_page.py`

**Interfaces:**
- Consumes: `places.collect`, `regions.place_page`, `regions.PageKind`.
- Produces: `placepages.PARK`, `RANGE`, `WILDERNESS` (`PageKind`s); `placepages.Built = (path, title, description, body, needs_map, recs)`; `placepages.build(records, site, repo_root) -> list[Built]`. In `pages.py`: `EXTRA_PAGE_BUILDERS = (placepages.build,)`, run after the state and group pages; each `Built` is added with `add(...)` and its path appended to `region_paths` (so it reaches the sitemap). `layout.NAV_PARENT` gains `"/parks/": "/regions/"`, `"/ranges/": "/regions/"`, `"/wilderness/": "/regions/"`.

- [ ] **Step 1: Write failing tests** (fixtures with a three-trail park and a two-trail park):
  - `test_a_place_with_three_trails_gets_a_page_and_one_with_two_does_not`.
  - `test_the_page_has_the_filter_bar_rows_and_map_before_the_summary`: `body.index('class="finder__bar"') < body.index('class="browse__list"') < body.index('class="browse-about"')` (filter bar only with 10 or more trails, as `home.listing`; the fixture for this assertion has 10).
  - `test_the_count_in_the_lede_the_title_and_the_rows_agree`.
  - `test_the_map_opens_on_the_registry_box`: `data-bbox` equals the entry's `box`.
  - `test_trails_are_in_plain_a_to_z_order`.
  - `test_no_banned_word_and_no_internal_km`: with `km = 123.456` set, none of `123.4`, `123.5`, `76.7`, `76.8` (its miles) appears in the page, its structured data or its history-free text; none of the `BANNED` patterns matches `site_words(...)`.
  - `test_the_title_follows_the_search_phrasing`: "Long Hikes in the Wind River Range, Wyoming: 5 Trails" (or the shorter option when `common.fit_title` needs it).
  - `test_the_breadcrumb_is_trails_places_name` and `test_the_page_is_in_the_sitemap_with_the_newest_trail_date`.
  - `test_the_structured_data_is_a_collection_of_the_trails`.
  - `test_places_is_the_current_nav_item_on_a_place_page`.
- [ ] **Step 2: Run**; expect FAIL.
- [ ] **Step 3: Implement.** Kicker is the kind's label and the states from `where` (full names). The summary uses `summary.facts(recs, records, place=(name, ()))` and `summary.details(recs)`. Edit `test_facets.BuiltVocabularyTest.browsing_pages` to walk `parks`, `ranges` and `wilderness` as well as `regions` and `lists`.
- [ ] **Step 4: Run** `python3 -m unittest discover -s web/tests`; expect OK (golden still identical: no registry entries yet, no pages).
- [ ] **Step 5: Commit** `feat: park, range and wilderness pages`.

### Task 11: Hub sections, state-page and trail-page links, search, sources

**Files:**
- Modify: `web/olt/regions.py` (`regions_index_page`, `place_links` builder), `web/olt/pages.py` (pass infos), `web/olt/trail.py` (`record_block`'s `where`, and `onward`), `web/olt/searchtext.py` (`place_names`), `SOURCES.md`
- Test: `web/tests/test_place_links.py` (create), `web/tests/test_search_text.py` (extend), `web/tests/test_state_pages_unchanged.py` (extend)

**Interfaces:**
- Produces: `regions.regions_index_page(records, site, infos=())` (adds one `<section class="places__group">` per kind that has pages, each row `name` and exact count); `regions.place_links_for(state_key, infos) -> Markup` (a `<nav class="region-nav" aria-label="Parks, ranges and wilderness in {state}">` block, empty when none); `trail.place_links(rec, infos) -> Markup` (one link per place that has a page, in the glance beside the states); `searchtext.place_names(rec, infos=())` extended so a row's place tier also holds the names of the record's places.

- [ ] **Step 1: Write failing tests.**
  - `test_the_hub_lists_each_kind_with_exact_counts_and_hides_empty_kinds`.
  - `test_the_hub_still_lists_every_state_group_as_before` (strip the new sections, compare).
  - `test_a_state_page_links_to_the_places_in_the_state_with_exact_counts_and_nothing_else_changes`: `normalise(page)` equals the golden for the same page.
  - `test_a_state_with_no_place_has_no_block`.
  - `test_a_trail_page_links_to_each_of_its_places_that_has_a_page_and_not_to_a_place_below_three`.
  - `test_search_text_holds_the_place_names`: `searchtext.attribute` of a trail in the Wind River Range contains "wind river range".
  - `test_state_pages_differ_only_in_data_search_and_the_new_block` (this is the reason `normalise` strips `data-search`).
- [ ] **Step 2: Run**; expect FAIL.
- [ ] **Step 3: Implement.** The hub's lede gains: "Parks, mountain ranges and wilderness areas with three or more trails have pages too." Add rows to `SOURCES.md` (existing form: terms quoted, page, date read, credit) for the four sources, after reading each publisher's licence page; the site's sources page renders `SOURCES.md` (`docs.sources_page`), so no code change.
- [ ] **Step 4: Run** `python3 -m unittest discover -s web/tests`; expect OK.
- [ ] **Step 5: Commit** `feat: hub sections, links from state and trail pages, search by place`.

### Task 12: Data entry: place the 124 tracked trails

Data work, batched. Nothing here is code.

**Files:**
- Modify: `places.toml`, up to 124 `<id>/trail.toml` (targeted line edits by the tool)

- [ ] **Step 1: Run the tool for real.** `.venv-places/bin/python tools/place_trails.py propose` (allow-list from Task 7), writing `refresh/<date>/places/proposal.md`.
- [ ] **Step 2: Batch.** Split the proposal into batches of about 15 trails, grouped by the record's first `regions` code (so a reviewer knows the ground), about 8 batches. One reviewer per batch, a different model family from the one that built the tool. A reviewer checks, for every trail in the batch: (a) each proposed place fits the trail's `summary`, `designation`, `start` and `end`; (b) every item within 0.5 km of the threshold, opened in `near-threshold.geojson`; (c) no place whose only evidence is a skimming track; (d) the place names, kinds and `where` (read the outline's source page, not the proposal); (e) a trail the reviewer knows to run through a place the proposal omits is listed in `misses.md` for the owner and not edited. The reviewer's report lists accept, change and reject per trail; rejected ones are listed by `<id> <kind>/<slug>` in `refresh/<date>/places/exclude.txt`.
- [ ] **Step 3: Apply** `.venv-places/bin/python tools/place_trails.py apply refresh/<date>/places/proposal.json --exclude refresh/<date>/places/exclude.txt`. It writes the records and `places.toml`.
- [ ] **Step 4: Verify.** `python3 tools/validate.py` ends `OK 223 trails`; `python3 tools/check_history.py --base origin/main` ends `OK history`; `git diff --stat` touches only `places.toml` and `*/trail.toml`; in any three records the diff is only `places_checked`, `places_track`, `[[place]]` blocks and one new `[[history]]` entry, with no distance in its text.
- [ ] **Step 5: Commit** `data: place the trails with a track`.

### Task 13: Data entry: place the 99 trackless trails

The slow part. A trackless trail's places come from a cited source, never from guesswork.

**Files:**
- Modify: `places.toml`, up to 99 `<id>/trail.toml`

- [ ] **Step 1: Make the worklist.** Use `.venv-places/bin/python tools/place_trails.py worklist` (add as a small subcommand: records with no `source.line_file` and no `places_checked`), writing `refresh/<date>/places/worklist.md` with each id, name, `regions`, `designation`, `hike.start`, `hike.end`, `hike.start_lonlat` and `hike.end_lonlat`, and the registry or outline places within 25 km of either end (`place_trails.py candidates --near <id>`).
- [ ] **Step 2: Batch.** Group by first `regions` code into batches of 12 to 13, about 8 batches, one worker each. A worker fills `refresh/<date>/places/stated-NN.toml`: for each id either `places = [{kind, slug, source, quote}]` (a page naming the trail in or on the place, with the sentence that says so) or `none = true` with `why` (what the record's summary and ends show). Find places with `place_trails.py find "<name>"`, which searches the catalogue and gives `kind`, `slug` and the outline's name. A place not found in the catalogue is reported, not invented.
- [ ] **Step 3: Review.** A different model family opens every cited address, confirms the quote is on the page and that it puts this trail in this place (the trail, not a neighbour; the place, not a gateway town), and spot-checks one in five `none` decisions against the record's summary and the place's outline. It marks each item accept or reject with a reason; rejected items go back to the worker once, then to the owner.
- [ ] **Step 4: Apply** accepted items with `place_trails.py stated --file stated-NN.toml` (one history entry per record, `fields = ["place"]`, `basis` quoting the source's page) and `place_trails.py stamp --file` for the `none` items (sets `places_checked`, no history).
- [ ] **Step 5: Verify** as Task 12, Step 4. Then `python3 tools/validate.py` with `REQUIRE_PLACES_CHECKED` patched on by hand in a scratch run (`python3 -c "import sys; sys.path.insert(0,'tools'); import check_places as C; C.REQUIRE_PLACES_CHECKED=True; import validate; sys.exit(validate.main())"`) ends `OK 223 trails`: every record is stamped.
- [ ] **Step 6: Commit** `data: place the trails with no track from cited sources`.

### Task 14: Enforcement, the audit checklist, the monthly workflow

**Files:**
- Create: `docs/audit.md`, `.github/workflows/places.yml`, `tools/tests/test_audit_doc.py`
- Modify: `tools/check_places.py` (`REQUIRE_PLACES_CHECKED = True`), `.claude/skills/refresh-trails/SKILL.md` (phase 8: a clause pointing at `docs/audit.md` and at placing new records), `.claude/skills/refresh-trails/briefs/apply.md` (a step after step 4: run `place_trails.py` for each new or changed-track id, and `stated` for each new trackless one), `CONTRIBUTING.md` (one sentence: a new record needs its places; run the tool)
- Test: `tools/tests/test_audit_doc.py`, `tools/tests/test_places.py` (flag), `tools/tests/test_refresh_skill.py` (must still pass unchanged)

- [ ] **Step 1: Write failing tests.**
  - `test_every_record_must_have_places_checked_now`: `check_places.REQUIRE_PLACES_CHECKED is True` and a record without the date fails.
  - `test_the_audit_checklist_exists_and_names_each_step`: `docs/audit.md` contains `/refresh-trails`, `python3 tools/refresh.py links`, `place_trails.py --check`, `python3 tools/validate.py`, `python3 tools/check_history.py`, `python3 -m unittest discover tools/tests`, `python3 -m unittest discover -s web/tests`, and the words "stated" and "by hand".
  - `test_the_monthly_workflow_runs_the_check_and_installs_only_the_tool_requirements`: `places.yml` has a `schedule` cron, `tools/place_trails.requirements.txt`, `place_trails.py --check`, and the `validate.yml` file contains no `pip install`.
  - `test_the_apply_brief_places_new_records`: `briefs/apply.md` contains `place_trails.py`.
  - `test_docs_audit_keeps_the_house_wording`: no dash used as punctuation (`" - "`, `–`, `—`), as `test_refresh_skill.test_house_wording` demands.
- [ ] **Step 2: Run** `python3 -m unittest discover tools/tests -p "test_audit_doc.py"`; expect FAIL.
- [ ] **Step 3: Implement.** `docs/audit.md` is a short numbered checklist: `/refresh-trails` (full quarterly, `light` between), links, `validate.py`, `check_history.py`, both suites, `place_trails.py --check` (and what each kind of difference means and who rules), then "Review the `stated` placements by hand": open each cited page again (no tool can re-measure them), dated in the record's `places_checked`. `places.yml`: `schedule: cron "0 6 1 * *"` plus `workflow_dispatch`; steps: checkout, `setup-python` 3.12, `actions/cache` on the outline cache directory, `pip install -r tools/place_trails.requirements.txt`, `python tools/place_trails.py --check`. A failing run lists the differences in its log.
- [ ] **Step 4: Run** `python3 tools/validate.py`, `python3 -m unittest discover tools/tests`; expect OK (the validator is now strict).
- [ ] **Step 5: Commit** `feat: require places on every record; audit checklist; monthly place check`.

### Task 15: Ship 2 gate

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Run** all checks: `python3 tools/validate.py`, `python3 tools/check_history.py --base origin/main`, `python3 -m unittest discover tools/tests`, `python3 -m unittest discover -s web/tests`, `python3 web/build.py --out _site`.
- [ ] **Step 2: Compare with the baseline.** `diff -r -q web/.cache/baseline-site/regions _site/regions`: the only differing files are the hub, the state pages that gained the new block, and the state-list pages' `data-search` attributes; confirm by `normalise`. Every trail page differs by its place links and search text only; spot-read three.
- [ ] **Step 3: Read the built pages**: one park, one range, one wilderness page at 390, 768 and 1280 px widths and at real viewport heights in a browser (`web/serve.py`): the filter bar, rows and map are on the first screen at each; the summary is below. Check the counts against the number of rows. No `km` of a place, no banned word.
- [ ] **Step 4: Add the CHANGELOG entry**: a visitor-facing bullet (parks, ranges and wilderness areas, how many pages, the hub, links from states and trails, search by place name) and a contributor bullet (every record now carries its places; `place_trails.py`; the monthly check; `docs/audit.md`); exact counts of pages and of trails placed (124 by track, 99 by hand, how many in no place).
- [ ] **Step 5: Squash and ship** with the entry in the one commit.

---

## Ship 3: place-plus-list pages

### Task 16: Plan and build the pages

**Files:**
- Modify: `web/olt/placefacets.py`, `web/olt/pages.py`, `web/olt/placepages.py`, `web/olt/regions.py` (`place_page` nav)
- Test: `web/tests/test_place_facets.py` (create); `web/tests/test_state_pages_unchanged.py`, `web/tests/test_views.py` (must pass unchanged)

**Interfaces:**
- Produces: `placefacets.plan(records)` keeps its signature and result for states. New `placefacets.plan_places(infos, records) -> list[dict]` with the keys `slug`, `info`, `lst`, `recs`, `path` (path `"/<segment>/<slug>/<list key>/"`) and `kind`; a shared `_plan(units, records, min_size, path_of)` used by both, with `PLACE_MIN = 3` and `browse.MIN_SIZE` respectively. `placefacets.page(p, records, site, all_pages)` reads the kind's strings from `p["info"]["kind"]`. `placefacets.pages_by_place` keys by `(kind, slug)` for places, `slug` for states.

- [ ] **Step 1: Write failing tests.**
  - `test_a_place_list_page_exists_at_three_trails_not_two`.
  - `test_not_built_when_the_list_holds_every_trail_on_the_place_page`.
  - `test_not_built_when_the_list_is_not_shown_at_all`: below `browse.MIN_SIZE` or above `MAX_SHARE` of every trail.
  - `test_two_lists_with_nearly_the_same_trails_make_one_page` (`SAME_SET`).
  - `test_state_plan_is_unchanged_and_still_needs_five`.
  - `test_the_path_is_segment_slug_list_key`: `/ranges/wind-river-range/loops/`.
  - `test_title_h1_lede_use_the_list_noun_and_the_places_title_name`: "Loop Hiking Trails in Glacier National Park: 4 Trails".
  - `test_the_lede_count_and_the_row_count_agree` and `test_there_is_one_more_in_nav_and_a_link_back_to_the_place`.
  - `test_the_first_screen_order_and_no_km_and_no_banned_word`.
  - `test_the_place_page_links_to_its_list_pages_with_exact_counts`.
  - `test_losing_a_trail_removes_the_place_page_the_list_pages_and_every_link` (Review Focus; the place drops to 2, assert all four vanish).
- [ ] **Step 2: Run**; expect FAIL.
- [ ] **Step 3: Implement.** `region_page`/`place_page` gains the "More in {name}" nav through the existing `facet_pages` argument. In `render_site`, add the pages after the place pages and extend `region_paths`.
- [ ] **Step 4: Run** `python3 -m unittest discover -s web/tests`; expect OK, golden identical.
- [ ] **Step 5: Commit** `feat: place-plus-list pages`.

### Task 17: Ship 3 gate

- [ ] **Step 1: Run** the Task 15 Step 1 commands. Expect OK.
- [ ] **Step 2: Compare** `_site/regions` with the baseline as in Task 15 Step 2; nothing new differs. Count the built place-plus-list pages and confirm each has 3 or more rows and fewer rows than its place page.
- [ ] **Step 3: Check** the vocabulary test sees the new directories (`test_facets.browsing_pages`) and passes.
- [ ] **Step 4: Add the CHANGELOG entry** with the exact number of new pages and two or three examples by name.
- [ ] **Step 5: Squash and ship.**

---

## Ship 4: reworded lists

### Task 18: Titles, headings and ledes

URLs and rules do not change; only `title`, `blurb`, `page_title` and `noun` in `web/olt/browse.py`.

**Files:**
- Modify: `web/olt/browse.py` (the entries below), `web/tests/test_state_pages_unchanged.py` and `web/tests/golden/state-pages.json` (regenerate deliberately with `make_golden.py`, then review the diff)
- Create: `web/tests/test_list_wording.py`

**Interfaces:**
- Consumes: `browse.List`, `browse.by_key`, `search_title(n)`.

Wording decided here (each within the vocabulary rules and `common.TITLE_LIMIT` through `fit_title`):

| Key | `page_title` | `noun` (place-plus-list titles) |
|---|---|---|
| `longest` | "Longest Hiking Trails in the US: {n} Trails of 1,000+ Miles" | none |
| `under-100-miles` | "Short Thru-Hikes Under 100 Miles: {n} Long Trails" | "Short Thru-Hikes" |
| `under-200-miles` | "Thru-Hikes Under 200 Miles: {n} Long Trails" (unchanged) | none |
| `a-week-or-less` | "Week-Long Backpacking Trips: {n} Long Trails" | "Week-Long Backpacking Trips" (new) |
| `loops` | "Best Backpacking Loops: {n} Long Trail Loops" | "Backpacking Loops" |

The `title` and `blurb` of each list are reworded to match (for example `loops`: title "Loops", blurb "Backpacking loops: trails that finish where they start."), and `longest` keeps its lede's mile and kilometre figures.

- [ ] **Step 1: Write failing tests.**
  - `test_the_five_lists_have_the_new_page_titles`: `browse.by_key(k).search_title(7)` equals the table's text with `{n}` = 7.
  - `test_nouns_give_the_place_page_titles`: `placefacets.page` title for a loops list in a park starts "Backpacking Loops in".
  - `test_no_banned_word_in_any_list_title_blurb_or_noun`: each `BANNED` pattern against `title`, `blurb`, `search_title(9)` and `noun` of every list.
  - `test_list_urls_and_keys_are_unchanged`: `[lst.key for lst in browse.LISTS]` equals the pre-change list, written out in the test, and `browse.path(browse.by_key("loops")) == "/lists/loops/"`.
  - `test_every_search_title_is_unique_and_fits` (`test_views` already checks uniqueness; this also checks `common.TITLE_LIMIT` with `fit_title`).
- [ ] **Step 2: Run**; expect FAIL.
- [ ] **Step 3: Implement** the edits. `a-week-or-less` gets a `noun`, so it gains state-plus-list and place-plus-list pages wherever 5 (states) or 3 (places) trails match; the Task 17 count therefore changes only for it.
- [ ] **Step 4: Regenerate the golden** (`python3 web/tests/make_golden.py`) and read `git diff web/tests/golden`: only state-list pages for `loops`, `under-100-miles` and `a-week-or-less` change, and the state pages themselves (`/regions/<state>/`) do not.
- [ ] **Step 5: Run** `python3 -m unittest discover -s web/tests` and `python3 tools/validate.py`; expect OK.
- [ ] **Step 6: Commit** `feat: list titles in the words people search with`.

### Task 19: Ship 4 gate

- [ ] **Step 1: Run** all checks (Task 15 Step 1).
- [ ] **Step 2: Compare** with the baseline: the only differing pages besides earlier ships' are the five lists, their state-list and place-list pages, and the pages that link to them by title. Confirm no URL went missing: `test_facets.test_old_urls_still_built` passes, and `diff <(cd web/.cache/baseline-site && find . -name index.html | sort) <(cd _site && find . -name index.html | sort)` shows only added paths.
- [ ] **Step 3: Add the CHANGELOG entry** naming the five old and new titles.
- [ ] **Step 4: Squash and ship.** Then delete `web/.cache/baseline-site`.

---

## Self-review

- **Spec coverage:** place registry (T2, T3), record field and history (T2, T6), membership rule and parents (T4, T8), boundary sources and cache (T5), tool and its three guards: every push (T3, T14), every month (T6, T14), every audit (T14); pages (T10), hub and links (T11), place plus list (T16), rewording (T18), order (ships 1 to 4), "settled" items: reuse (T9), map box (T2, T10), filters (T10; decision 8), counting (T8), history (T2, T6), reproducing (`source_version`, T5), slugs (T3, T8), plug-in point (T10), builder's tests (T3, T8, T10). Data entry: T7, T12, T13.
- **Types:** `places.collect` info keys (`kind`, `slug`, `key`, `name`, `where`, `box`, `records`, `path`, `title_name`) are the ones `placepages`, `placefacets.plan_places` and `regions.place_page` read; `track_hash` is defined once (`check_places`) and imported by the tool; `normalise` is defined in Task 1 and reused in Task 11.
- **Proportion:** the plan is about three times the spec's length, mostly test names; no function bodies.
