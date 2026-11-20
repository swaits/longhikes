# A season on every trail

Design, 2026-11-20. Status: built; the method changed after the climate model was tried (see "What changed in the method").

## Intent

The "By month" lists say "Only some trails have a season", and they are right:
109 of 223 records have one. A hiker picking a month sees half the catalogue.
The owner wants every record to carry a season, with its provenance on the
record, so a reader and a maintainer can tell a season an association
publishes from one worked out from climate. Some will be less trustworthy than
others, and the site says which.

## Goals

- All 223 records have `hike.season` and `hike.months`.
- Each season records where it came from and how far to trust it.
- A sourced season is always preferred. An estimate is the last resort and is
  replaced when a source turns up.
- The site marks estimated seasons wherever a season is shown, and stops
  saying only some trails have one.

## Non-goals

- Conditions, snow reports, or anything that changes year to year.
- Per-section or per-direction seasons beyond what the season phrase already
  says.
- Re-researching the 109 seasons already on file, beyond classifying them.

## Anti-goals

- An estimate that reads like a stated fact.
- A season that tells someone a trail is closed. Trails in cold places are
  walked in snow; an estimated season means the usual snow-free, not
  dangerously hot months, and says so.
- A method nobody can re-run or check.

## Approaches considered

1. **Research first, estimate the rest, mark both (chosen).** Look for a
   stated season for each of the 114 missing records. Estimate only what is
   left, from climate normals, with a rule tested against the 109 seasons
   already sourced.
2. **Estimate all 114 from climate.** Fast and uniform, but throws away
   seasons that pages do state, and the Pacific Crest and Continental Divide
   trails are among the 114.
3. **Research only, leave the rest blank.** Keeps the "never guessed" rule but
   does not meet the goal.

## Decided by the owner

- Every record ends with a season.
- Provenance is on the record: a source, several sources, or an estimate, and
  how much it is trusted.
- Climate data may be used to estimate, with the known weakness that people do
  hike in snow and cold.
- When pages disagree and none is the managing body, association or route
  author, the season is set by judgement from all the pages and the climate
  estimate, and the record says how.

## Design (designer's calls, for the owner to correct)

### Schema

One new field, `hike.season_basis`, required whenever `season` is present:

| Value | Meaning | Trust |
|---|---|---|
| `primary` | The managing agency, the trail's own association, or for a route its author states it | Highest |
| `sources` | No primary page, but two or more pages from different publishers agree | High |
| `source` | One page that is not a primary one | Medium |
| `estimate` | No page states one; worked out from climate | Low |

- For the first three, `[[hike.source]]` entries name `season` in `facts`, as
  today. The validator checks the count fits the basis (`sources` needs two).
- For `estimate`, a second new field `hike.season_method` holds one sentence
  naming the method and its inputs, and the `[[hike.source]]` entry cites the
  climate data. `months` is still given; `season` is the plain phrase built
  from the months.
- `docs/schema.md` changes its rule: a hike fact found on no acceptable page
  is left out, never guessed, **except season, which may be estimated and
  must then say so**. Typical time is estimated too, but at page-build time
  and never stored; an estimated season is stored on the record. Only the
  display pattern is shared ("About …" plus a note, and the small estimate
  label on rows).
- `season_basis` and `season_method` are facts for history purposes. Each
  record changed gets a `[[history]]` entry.

### Step 1: classify the 109

Each existing season gets a basis from its sources: by publisher (managing
body or not) and by count. A worker proposes; a person reviews the table.

### Step 2: research the 114

For each record with no season, look for a page that states when the trail is
normally hiked: the managing agency, the association, a guidebook publisher,
the route author. Record the season phrase, the months, the sources and the
basis. Trip reports count as `source` only when they speak of the usual
season, not one trip. Disagreement between pages is resolved toward the
managing body, and the season phrase may carry the nuance ("northbound starts
late February to April").

### Step 3: estimate the remainder

`tools/estimate_season.py`. It is not part of the site build, and it is never
left to someone remembering to run it (the owner's ruling):

- **Every push.** The validator fails any record with no season, so a new
  trail cannot ship without one, sourced or estimated.
- **Every month.** A scheduled workflow runs `estimate_season.py --check`: it
  re-runs every estimate and the fit against sourced seasons, and fails with
  a list of estimates that would now come out different, or a fit that has
  got worse.
- **Every audit.** `docs/audit.md`, the written checklist for the monthly
  audit of everything, lists two season steps: the check above, and a fresh
  search for a source for every season still marked `estimate`, so estimates
  shrink over time.

What the tool does:

- **Where:** sample points along the track. With no track, the start and end
  points; with neither, the place centroid of the record's regions, flagged
  for hand review.
- **Elevation:** the track's high ground (upper quartile of the profile),
  since the high sections decide when a trail opens. With no track,
  `high_point_m` or the terrain at the sample points.
- **Climate:** monthly normals for temperature and snow cover at those points
  and elevations, from an openly licensed source. Candidates to settle in the
  plan: Open-Meteo's historical API (ERA5, CC BY 4.0), NOAA climate normals
  and SNODAS (public domain, US only), Environment Canada normals.
- **Rule:** a month is in season when the high ground is normally free of snow
  and the mean daily high at the low ground is under a heat limit. The
  thresholds are fitted, not chosen: the rule is run against the 109 sourced
  seasons and tuned until it reproduces them as well as it can.
- **Check:** the tool reports how often its months match the sourced months
  (exact, within one month at each end, worse). That figure goes on the
  site's reference page, so the trust in an estimate is a number. If the rule
  cannot get most sourced trails within one month, estimates are not shipped
  and the owner is told.
- **Review:** the proposed seasons are listed for a person to read before any
  record is written. Odd ones (desert, coastal, far north) get a hand check
  against a comparable sourced trail nearby.

### On the site

- Trail page: an estimated season reads "About June to September" with a
  note, as estimated time does today: "Estimated from climate at the trail's
  elevation. No source states a season. People do walk it outside these
  months." Sourced seasons show their basis in "About this data".
- Rows, summary lines and month lists include every trail. Estimated seasons
  are marked in the row.
- The "By month" blurb becomes "Trails normally hiked in the month. Estimated
  seasons are marked." The "N trails with no season on file" note, the "Show
  them" button and the "Not on file" cell go once coverage is complete.
- The filter bar's month filter gains a way to leave estimates out.
- The glossary entry and reference page coverage row are rewritten to match.
- Structured data states a season only for sourced ones.

### Order

1. Schema, validator, history tool, classify the 109. Ship.
2. Research the 114 in batches by region; write sourced seasons. Ship as
   batches land.
3. Estimator, its check against sourced seasons, the review list.
4. Write estimates, change the site wording and filters. Ship.

## Settled after a builder's read (designer's calls)

- **Who is primary is a judgement, not a lookup.** `publisher` is free text
  with 92 distinct values, so step 1 is a proposed table of all 109, read by
  a person. The rule follows the schema's existing idea of the acceptable
  page: the managing body, or for a route its author.
- **Most seasons will be `primary` or `source`.** Only 6 of the 109 have more
  than one source naming the season today. `sources` is for the few with no
  primary page and several agreeing ones.
- **Validator.** `season_basis` and `season_method` are provenance, not
  facts: they are exempt from the rule that every hike field is named in a
  source's `facts`, as `checked` is. `season` and `months` must appear
  together. An estimate's only source naming `season` and `months` is the
  climate data; any other source naming them makes the basis wrong.
- **Shipping step 1.** `season_basis` is required wherever `season` is
  present from the first ship, covering the 109.
- **Site code.** Rows, the filter bar, `standing.season_cell` and
  `reference.py` assume seasons are partial and tests pin that wording; those
  tests are rewritten, not patched. They change only in the last step, when
  coverage is complete.

## Left to the builder

- The climate source, after trying the candidates on a dozen trails.
- Sampling density, the exact snow and heat measures, and the fit.
- Wording of notes within the vocabulary rules and the banned-word test.
- Tests: every record has season, months and basis; basis fits the sources;
  estimates have a method; no page says a season is missing.

## What changed in the method

The plan above chose a rule over climate normals for Step 3. It was built and tested (`tools/estimate_season.py`, `tools/season_model.py`; CHELSA V2.1 1981 to 2010 normals, CC0, with NOAA ETOPO 2022 elevation), and it matched only 67.6 percent of the sourced seasons within one month at each end, under the owner's bar of 75 percent. Its output is therefore not written to a record. What was decided instead:

- **A reviewer judges each estimate.** For each of the 75 trails with no season, a reviewer set the months from a packet: the trail's location, elevation, monthly climate normals, the machine estimate, and the ten most similar sourced trails (`tools/season_judge.py packets`; the reviewer's instruction is `docs/season-judging.md`). The machine estimate stays in the repository as an input to the packets and as the monthly check.
- **The method is tested blind.** The same reviewers estimated the 148 trails whose season a page states, from identical packets with the season hidden, and a trail's comparable trails never came from its own part of the split. They matched 114 of 148 (77.0 percent), by the reviewer's confidence 48 of 52 (high), 55 of 76 (medium) and 11 of 20 (low). The figures are in `tools/season_blind_test.json`, written by `season_judge.py score`, and the site reads them.
- **An estimate is stricter.** `season_basis = "estimate"` means no page states a season. `season` is built from `months`; `season_method` is one or two plain sentences saying how it was set and what sets the season there, ending "Confidence: high.", "medium." or "low."; and its one `[[hike.source]]` names `season` and `months` and cites the climate data. The validator refuses an estimate with any ordinary page naming the season, or with no method, and requires a season on every trail.
- **Pages that disagree.** Six trails have pages that disagree where none is the managing body, association or route author. Their season is set by judgement from all the pages and the estimate: basis `sources`, the pages cited as sources naming the season, and a `season_method` saying the pages differ and how it was settled. A season with a method is shown as an estimate (it reads "About" with a note), left out of structured data, and not counted among the seasons a page states.
- **The monthly check** (`estimate_season.py check`) reruns the machine estimate for every estimate and flags any whose inputs have changed since `tools/season_inputs.json` recorded them. It does not rewrite anything. The audit (`docs/audit.md`) also searches afresh for a page for every estimate.
- **On the site**, a trail's page reads "About April to October" with a note (no page states a season; estimated from the climate at the trail's elevation and from similar trails; what sets it there; the confidence; that people walk it outside these months). Rows, tables and month lists mark estimates, the month filter can leave them out, and the reference page and glossary give the counts and the blind-test result.

## Open risks

- Climate normals are coarse in steep terrain. The fit against sourced
  seasons is the guard, and it may show the method is too weak for some
  regions.
- 42 of the 114 have no track and 95 have no high point, so some estimates
  rest on a start point or less. Those are the least trustworthy and are
  flagged for hand review.
- Research may find seasons for most of the 114, leaving few estimates. That
  is the good outcome.
