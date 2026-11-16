# The staged proposal format

Workers never edit the repository. They stage what they found as files in the staging directory, `tools/refresh.py collect` gathers and checks them, a reviewer and the owner decide, and `tools/refresh.py apply` makes the accepted changes. This file is the one place the format is defined; the briefs point here, and `collect` and `apply` enforce it.

## Layout

```
refresh/<YYYY-MM-DD>/              the staging directory, ignored by git
  slices/<slice>.txt               ids for each slice, one per line (written by `slices`)
  links.csv                        written by `links`
  staged/<worker>/                 one directory per worker; <worker> is the slice or region name
    report.csv                     one row for every id (or region) the worker was given
    <id>/proposal.toml             every proposal about that id
    <id>/<files>                   staged files: a new record's trail.toml, tracks, an emblem
  review/<reviewer>.csv            a reviewer's decisions
  owner.csv                        the owner's rulings
  collected.toml, summary.md       written by `collect`
  apply-log.csv                    written by `apply`
```

`<worker>` is the slice name (`trails-03`, `left-out-01`) or, for work that is not sliced, a short name the orchestrator gives (`region-us-west`, `tracks-1`, `emblems-2`). Two workers never share a directory, so two workers can propose the same new trail without overwriting each other. `collect` reports the duplicate.

## report.csv

Header: `id,outcome,pages,remark`. One row for every id or region the worker was given, so that nothing is silently skipped.

| Column | Content |
| --- | --- |
| `id` | The trail id, the left-out id, or the region searched. |
| `outcome` | One word from the list below. |
| `pages` | The addresses opened, or for a search the places looked, separated by semicolons. Required for `verified`, `not-found`, `none-exists`, `refused` and `could-not-check`. |
| `remark` | One plain sentence. Required for `could-not-check`, `refused` and `not-found`. |

Outcomes: `verified` (every check passed; nothing to change), `changed` (at least one proposal; the pages are those opened), `declined` (a request was recorded as declined), `could-not-check` (say what and why), `refused` (every allowed source refused automated reads), `not-reached` (out of time), `found` and `not-found` (searches), `none-exists`, `kept`, `replaced`, `cropped`, `new` (emblems and tracks), `accepted` and `rejected` (review).

A `verified` row needs a `verified` proposal as well, and the pages listed should include every page the record cites. `collect` warns for each cited page that was not listed.

## proposal.toml

A file holds one or more `[[proposal]]` tables. Strings and arrays stay on one line, because `apply` replaces whole lines. Every proposal has these fields:

| Field | Meaning |
| --- | --- |
| `kind` | One of the kinds below. |
| `id` | The trail id (the directory name), or the left-out id. For a candidate, the id it would have. It must equal the directory `<id>` the file sits in. |
| `target` | `"left-out"` to change an entry of `left-out.toml`. Omitted for a record. |
| `date` | `YYYY-MM-DD`, the day the pages were read. |
| `summary` | One plain sentence saying what is proposed. |

### `verified`

The record was checked against its pages and still says what they say. Fields: `pages` (array of addresses opened). `apply` sets `hike.checked` to `date` (for a record with no `[hike]`, `source.source_checked`). These are not facts, so no history entry is added. A trail with `change` proposals also gets a `verified` proposal: it says that everything not named in a change was checked and stands.

```toml
[[proposal]]
kind = "verified"
id = "long-trail"
date = "2026-12-03"
summary = "Name, length, ends, uses, permit and season checked against the club's pages."
pages = ["https://www.greenmountainclub.org/the-long-trail/", "https://www.greenmountainclub.org/hike/"]
```

### `change`

Changes fields of a record, or of a left-out entry (`target = "left-out"`). It holds any of `[[proposal.edit]]`, `[[proposal.append]]` and `[[proposal.file]]`, and a `[proposal.history]`.

```toml
[[proposal]]
kind = "change"
id = "long-trail"
date = "2026-12-03"
summary = "The permit sentence changed."

[[proposal.edit]]
field = "hike.permit"
old = "No permit is needed."
new = "A free permit is needed for groups of ten or more."
page = "https://www.greenmountainclub.org/hike/"
quote = "Groups of ten or more need a free permit."

[proposal.history]
change = "The permit sentence now says groups of ten or more need a free permit."
basis = "The club's page says groups of ten or more need a free permit."
basis_url = "https://www.greenmountainclub.org/hike/"
asked_by = "the dataset's own check"
```

**`[[proposal.edit]]`** changes one field. `field` is named as `docs/schema.md` names it: `length_km`, `source.licence`, `hike.permit`. For an entry of an array of tables, add its position, counting from 0: `guide[0].price`, `hike.source[1].facts`. `old` is the current value, copied from the record as it stands when you read it; `apply` refuses if the record no longer has exactly that value. Leave `old` out to add a field that is absent. Leave `new` out to remove a field. `page` and `quote` are the page and the sentence on it that support the change. They are required for every edit. A number is copied as the page writes it, and `quote` is copied exactly.

**`[[proposal.append]]`** adds an entry to `hike.source`, `guide` or `link`: `table`, `page`, `quote`, and a `[proposal.append.entry]` table holding the new entry's fields. It is added after the last entry of that table. An entry whose `url` is already there is refused.

**`[[proposal.file]]`** puts a file into the record's directory: `to` (one of `line.geojson`, `alternates.geojson`, `line-<source>.geojson`, `release.txt`, `elevation.json`, `shield.svg`, `shield.png`), `from` (a path inside the proposal's own directory), `source_url` (where the file came from), and `old_sha256` (required when `to` already exists; it must match, so a file that changed meanwhile is never overwritten). `remove = true` in place of `from` deletes `to`. Track files carry no `old` and `new`; the fields that describe them (`source.status`, `source.licence`, `source.line_file`, `verification.*`) are ordinary edits in the same proposal.

**`[proposal.history]`** is the `[[history]]` entry `apply` appends: `change`, `basis`, `basis_url`, `asked_by`, and optionally `fields`. `date` is the day `apply` runs, and `outcome` is `applied`. Without `fields`, they are worked out from the edits (`hike.source[1].facts` becomes `hike.source.facts`; a track file becomes `source.line_file`; an emblem file `shield.logo_file`). The entry is required whenever a fact changes; `python3 tools/check_history.py --facts` lists what counts as a fact. `asked_by` is a role, never a person's name: `the dataset's own check`, `a hiker`, `the trail association's president`, `the route's author`.

### `declined`

A request, usually from the issue tracker, that the holder's or author's own current page contradicts. Nothing in the record changes except that a history entry with the outcome `declined` is added. It has no edits. `[proposal.history]` must name `fields`, and `basis` says which page wins and why.

### `new-record`

A new trail. The complete record is staged as `staged/<worker>/<id>/trail.toml`, with its track files and emblem beside it. Its own first `[[history]]` entry has `fields = ["record"]`. Fields: `basis_url` (the page that shows the trail meets the inclusion rule). A new record is one the worker recommends adding; a doubtful one is a `candidate` instead. `sources_md` is one line for the `SOURCES.md` row that must change: publisher, source page, licence, and `track` or `record only`. `apply` copies the directory (without `proposal.toml`) into the repository and refuses if the id exists. If the trail is in `left-out.toml`, a `left-out-remove` proposal must accompany it.

### `left-out-add`, `left-out-remove`

Adds an entry to `left-out.toml` (a `[proposal.entry]` table with the fields in `docs/schema.md`; `apply` puts it in name order), or removes the entry for `id` (`why` says why; `basis_url` is the page). A change to an existing entry is a `change` with `target = "left-out"`; its edits name plain fields (`note`, `decided`, `reason`) without a table.

### `candidate`

A trail that might belong, for the owner to decide. It is never applied. Fields: `name`, `country`, `regions`, `length_mi`, `source_url` (the holder's or author's page where the length was read), `recommendation` (`add`, `owner` or `decline`), `reason` (the left-out reason when the recommendation is `decline`), `borderline` (true when it needs the owner), and `summary` (which says what is doubtful).

### `could-not-check`

Something that could not be checked: `what` and `why`, and `tried` (the pages opened). It is never applied and is listed in the summary, so the owner sees what was not verified.

### `sources_md`

Any proposal may carry `sources_md`, a one-line note about `SOURCES.md` (that file is written by hand): the id, the publisher, the page, the licence, and `track` or `record only`. `collect` lists them.

## Decisions

A reviewer writes `review/<reviewer>.csv`, and the owner `owner.csv`, with the header `pid,digest,decision,note`. `pid` and `digest` are the ones in `summary.md` for that proposal. `decision` is `accept`, `reject` or `hold`. An `accept` counts only if its `digest` matches the proposal as it is now, so a proposal that changed after review has to be reviewed again. The owner's row wins; otherwise a `reject` or `hold` from any reviewer blocks, and an `accept` from at least one reviewer accepts. `note` gives the reason: for a `reject`, the page and the sentence that do not support the proposal.

## collected.toml and apply

`collect` writes every proposal, with its `pid` (`<worker>:<id>:<n>`), `digest`, `status` (`proposed`, `accepted`, `rejected`, `held`, `invalid`, or `info` for candidates and unchecked items) and the problems it found. Never edit it; record decisions in the CSV files and collect again. `apply` applies the `accepted` proposals only, by changing the named line, adding a line at the end of the field's table, or adding a block. It never re-serialises a record, so hand formatting and comments stay. It refuses a proposal whose `old` value no longer matches, whose staged file changed after `collect`, or whose target file changed (`sha256`), and it says so; `apply --dry-run` shows what would happen. Running it twice is safe: a proposal already applied is reported as such.
