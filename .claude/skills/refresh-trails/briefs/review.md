# Review proposals and new records against their pages

Read `../rules.md`, `../proposal-format.md` and `../records.md` first. You do this task yourself and start no subagents.

You receive a staging directory `<staging>`, a reviewer name (for example `review-1`) and a list of proposal ids (`pid`) from `<staging>/summary.md`, or the name of a worker whose proposals you review. Your work is read-only: change nothing in the repository or in anyone's staged files. You write two files, `<staging>/review/<reviewer>.md` and `<staging>/review/<reviewer>.csv`.

## What this is for

The workers who wrote the proposals meant well and are sometimes wrong. A review of freshly written records by a second reader, opening the cited pages, once found seven must-fix defects in twenty-three records: facts that the cited page did not support, a wrong start point, allowed uses left out. A record goes to the public only after someone who did not write it has opened its pages. You are that reader, and a different one from the writer, ideally from a different model family. Done means every proposal you were given has a decision and the reasons are written down.

## What to do

For each proposal, read it in `summary.md` and in its `proposal.toml`, and for a new record read the whole staged `trail.toml`. Do not read the writer's conclusions first and then look for support. Open the pages and read them. For each edit or fact:

1. Open the page named. Find the quote. Is it there, word for word, and does it say what the proposal says it does?
2. Is the page the right source? The holder's or author's own page beats everything else. If another page disagrees, which one is current?
3. Does the record, after the change, say anything the pages do not? Read every sentence of a new record's `summary`, `designation`, `length_note`, `caution` and `[route]` text for claims such as "the Forest Service describes it as" or "the association maintains it" that no cited page makes. The summary is our wording but not our invention.
4. The facts that hikers act on: the start and end (is the length the one that belongs to those ends?), allowed uses (every use the page lists is in the record), permits and fees, season, closures that affect walking through.
5. Is a cited address a page that opens and says what the record claims (not a redirect to a general page that never mentions the trail)?
6. Is the length source right: which figure belongs to which definition (built or planned, with or without side trails)?
7. Words: "track" and not "line", "author" and not "creator" in text, miles first, plain sentences, no dashes as punctuation, no private person's name, no marketing words.
8. History: is `[proposal.history]` present for every changed fact, with a role in `asked_by`, a basis and an address that does open? Was an earlier `declined` entry about the same field passed over?
9. Is the proposal narrower or wider than its summary says? Did the writer quietly drop a part of the task?
10. For a track: does the licence in `source.licence` match the terms on the page, is a route's track (`kind = "route"`) included without the author's stated terms?

## The hard part

Agreeing is easy and wrong. When a quote is there, check that the sentence is about this trail and this fact (a nearby trail, an older edition, a segment and not the whole). When the page cannot be opened, say it is unchecked; do not accept on trust and do not reject for it. Where you cannot tell which of two pages is right, say so and let the owner rule.

## What to write

`<staging>/review/<reviewer>.csv`, header `pid,digest,decision,note`, one row for every proposal you were given. `digest` is the one in `summary.md`. `decision` is `accept` (every fact supported, nothing to fix), `reject` (not supported, or wrong, with the fix described in the report), or `hold` (needs the owner: the holder might dispute it, the sources conflict, or it is a matter of what belongs). A proposal with a small fix is a `reject` and the fix is written out, so it comes back as a new proposal and is read again. `note` is the reason, with the page and the sentence.

`<staging>/review/<reviewer>.md`, compact, no preamble, in this order:

1. `## Must fix`: numbered; each names the trail id and the fields, what is wrong, the page and the sentence that shows it, and the exact replacement text.
2. `## Should fix`: the same for lesser defects.
3. `## Answers`: for each question you were asked, the evidence and the conclusion.
4. `## Checked and sound`: one line per proposal, saying what you confirmed (for example: "ends, 54.7 mi, uses, archive copy read").
5. `## Could not check`: what you could not open or read, and why.

## Report

Reply with under 120 words: the two file paths, the number of accepts, rejects and holds, and the most serious defect.
