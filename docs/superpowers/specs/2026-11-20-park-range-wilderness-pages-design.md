# Park, range and wilderness pages

Design, 2026-11-20. Status: awaiting approval.

## Intent

People search for long hikes by named place: "wind river range wyoming",
"backpacking trips in glacier national park", "best backpacking loops in the
adirondacks". The site answers by state and province only. This adds pages for
national parks, mountain ranges and wilderness areas, so a search for a place
lands on the long trails in it. The aim is reach for free information, not
revenue.

## Goals

- A page for every national park, mountain range and wilderness area that has
  3 or more trails.
- Each of those pages crossed with the existing lists (loops, length bands,
  time bands and so on) wherever 3 or more trails match, as the state pages
  are today.
- Existing list pages retitled and re-led to match how people ask.
- Every trail placed, including the 99 with no track.

## Non-goals

- National forests, gateway towns, counties, beginner or no-permit lists.
- New rule-based lists (high routes, winter, desert, coastal).
- Showing boundary outlines on maps.
- Any planning feature. This is discovery.

## Anti-goals

- A page that lists one or two trails, or that repeats another page's set
  under a different name.
- A trail on a place page because its track skims the boundary.
- A place assignment nobody can check.
- Breaking any existing URL.

## Approaches considered

1. **A field on each record, filled from boundaries (chosen).** Each record
   lists the places it is in. A tool fills the list by crossing tracks with
   published outlines; trails without a track are filled by hand from a cited
   source. Covers every trail and each assignment can be reviewed.
2. **Computed at build only.** Nothing stored. No hand entry, but 99 trails
   could never appear on a place page.
3. **Hand-named sets in `collections.toml`.** Simple, but nothing checks an
   assignment against a boundary.

The owner picked 1.

## Decided by the owner

- Membership is a field on the record (approach 1).
- Kinds: national parks, mountain ranges, wilderness areas.
- A place page needs 3 or more trails.
- Place plus list pages, and rewording of existing lists, are in scope.

## Design

### Place registry

A new `places.toml` at the repo root, one entry per place that any record
names:

```toml
[[place]]
slug = "wind-river-range"
kind = "range"            # park | range | wilderness
name = "Wind River Range"
where = ["us-wy"]         # state or province codes
within = ["rocky-mountains"]   # optional, parent place slugs
source = "gmba-v2"
source_id = "..."         # the publisher's id for the outline
```

Only places that at least one record names are listed. The registry is the
one spot where a place's display name, kind and source live.

### On the record

```toml
[[place]]
slug = "wind-river-range"
basis = "track"           # track | stated
km = 142.3                # track length inside, basis "track" only
source = "..."            # citation, basis "stated" only
```

- `basis = "track"`: the tool measured it. `km` is recorded so the threshold
  can be audited. It is never shown on the site.
- `basis = "stated"`: no track. A person entered it, with a source that says
  the trail is in that place.
- Adding places to a record gets a `[[history]]` entry like any other fact.

### Membership rule

A trail is in a place when at least 1 mile (1.6 km) of its main track lies
inside the outline. Alternates do not count. A nested range also gives
membership of every `within` parent, so a Teton Range trail is on the Rocky
Mountains page too.

### Boundary sources

| Kind | Source | Licence |
|---|---|---|
| US national parks | National Park Service boundary service (unit type National Park, plus units the owner's search list names, such as Sequoia and Kings Canyon as one page) | Public domain |
| US wilderness | Wilderness Connect, all four agencies | Federal work, public domain; credited |
| Canadian national parks, BC and Alberta provincial parks | Environment and Climate Change Canada, CPCAD | Open Government Licence, Canada |
| Mountain ranges | GMBA Mountain Inventory v2 | CC BY 4.0 |

Outlines are downloaded by the tool into a cache outside the repo and are not
committed. Each source gets an entry on the site's sources page.

Ranges come from an allow-list in the tool (GMBA ids), not from one hierarchy
level, because the useful names sit at different depths. The list starts from
the ranges the owner named and every GMBA range that 3 or more tracks cross,
and is reviewed by a person before records are written.

### Tool

`tools/place_trails.py`. It is not part of the site build, because the build
uses only the standard library and the outlines are large. It is never left
to someone remembering to run it (the owner's ruling). Three things make sure
of that:

- **Every push.** Each record carries `places_checked`, the date its places
  were last measured or reviewed, and the fingerprint of the track that was
  measured. The validator fails a record that has no `places_checked`, or
  whose track has changed since. A new trail or a new track cannot ship
  unplaced. A record in no park, range or wilderness still carries the date.
- **Every month.** A scheduled workflow runs `place_trails.py --check`: it
  downloads the current outlines, re-measures every track, and fails with a
  list of every difference from the records (a place gained or lost, a
  boundary that moved, a place that crossed the 3-trail line).
- **Every audit.** `docs/audit.md`, a new written checklist for the monthly
  audit of everything, lists the place check as a step, with the hand review
  of the `stated` placements, which no tool can re-measure.

What the tool does:

1. Download and cache outlines; reproject to lon/lat.
2. For each record with `line.geojson`, measure the track length inside each
   candidate outline.
3. Print a proposal: per trail, the places and kilometres; per place, the
   trails. Nothing is written until the proposal is reviewed.
4. Write `[[place]]` entries and registry entries.

The tool may use libraries outside the standard library. The site build may
not, and does not need to: it reads only the records and the registry.

### Pages

- `/parks/<slug>/`, `/ranges/<slug>/`, `/wilderness/<slug>/`, each with the
  same layout as a state page: filter bar, rows, map and counts on the first
  screen, summary panel and cross-links below.
- `/parks/<slug>/<list>/` and so on for place plus list, 3 or more trails,
  and not when the list holds every trail on the place page.
- The Places hub (`/regions/`) gains three sections listing them. Navigation
  stays Trails, Places, About.
- State pages link to the parks, ranges and wilderness areas in the state.
  Trail pages link to each of their places.
- Titles follow the search phrasing: "Long Hikes in the Wind River Range,
  Wyoming", "Backpacking Loops in Yosemite National Park".
- Structured data, sitemap and filter behaviour are the same as for state
  pages. Counts are exact. A place below 3 trails gets no page and no link.

### Rewording existing lists (second ship)

Titles, headings and ledes only; URLs and rules unchanged. Targets: "longest
hiking trails in the US", "thru-hikes under 100 / 200 miles", "short
thru-hikes", "week-long backpacking trips", "best backpacking loops". Wording
must pass the banned-word test in `test_facets`.

### Order

1. Registry, record field, validator, tool, and the proposal for review.
2. Records written, place pages, hub and cross-links. Ship with a changelog
   entry.
3. Place plus list pages. Ship.
4. Reworded lists. Ship.

## Settled after a builder's read (designer's calls)

- **Reuse, not a copy.** The state-page code (`regions.region_page`,
  `placefacets.plan`, `home.listing`) is generalised so a place is a kind plus
  a slug, with states as one kind. The existing state-page tests are the
  guard: they must pass unchanged. Strings such as "in a state or province"
  become per-kind.
- **Map view.** The tool computes each place's bounding box from its outline
  and writes it to the registry entry as `box`. `web/place-bounds.toml` stays
  for states.
- **Filters.** On a place page the Where filter lists states and provinces as
  it does today. The home page's Where filter is unchanged in the first ship.
  Site search matches place names, so typing "wind river" finds the page.
- **Counting.** The 3-trail minimum counts both bases, track and stated.
- **History.** Adding or removing a place on a record needs a `[[history]]`
  entry. `km` is a measurement, not a fact: a re-run that only changes `km`
  needs none.
- **Reproducing.** Each registry entry records the source's version or
  download date as `source_version`, so a measurement can be re-derived from
  the same outline.
- **Slugs** are unique within a kind, not across kinds: `/parks/glacier/` and
  `/wilderness/glacier-peak/` can coexist. A page that joins two units
  (Sequoia and Kings Canyon) is one registry entry with two `source_id`s.
- `pages.py` has no plug-in point for new page kinds today; adding one is
  part of the work.

## Left to the builder

- Schema and validator details for `[[place]]` and `places.toml`.
- Point-in-polygon and length-inside code, and simplification of outlines.
- Exact page titles and ledes within the vocabulary rules.
- Tests: every `[[place]]` slug is in the registry, every registry entry is
  named by a record, no place page below 3 trails, page structure tests as
  for state pages.

## Open risks

- Boundary findings come from a research worker and were not opened by the
  designer. The first tool run is the check.
- Hand-placing 99 trackless trails is the slow part. Many are in no park or
  wilderness and can be settled from the record's summary.
