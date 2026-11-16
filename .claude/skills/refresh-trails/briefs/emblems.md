# Find the trail's own emblem

Read `../rules.md`, `../proposal-format.md` and `../records.md` first. You do this task yourself and start no subagents.

You receive a staging directory `<staging>`, a worker name (for example `emblems-1`) and a slice file `<staging>/slices/<worker>.txt` of trail ids, one per line, normally records whose `shield.status` is `logo-not-found`. Stage your work in `<staging>/staged/<worker>/`.

## What this is for

The site shows each trail's own emblem beside its name, and most long trails have a single crest-style marker. A record that says "emblem not found" is a gap the site shows to the reader. Earlier "not found" and "no emblem" verdicts were often reached without a real search, so do not trust them: search again. Done means that for every id there is either a clean emblem file that came from an allowed source, or a note that says exactly which pages were looked at and what marks were seen.

## What counts as the emblem

The trail's own crest, shield, badge, roundel, blaze-shaped marker or trail-sign symbol, alone. For a US National Scenic Trail, the official rounded-triangle trail marker; for a club trail, its blaze badge or roundel; for an author's route, the emblem the author uses for it, if there is one.

Not wanted: the holding organisation's lockup (an emblem with the organisation's name set beside it as type), a wordmark alone, a banner, a photo, a map, or an agency's logo standing in for the trail (the Forest Service shield, the National Park Service arrowhead, the Parks Canada beaver, a state parks logo). If the emblem inside an organisation's lockup is the trail's crest, crop it out. If the only mark is the organisation's and it does not stand for the trail, the trail has no emblem of its own. Text that is part of the emblem (the trail's name around a roundel) is fine; a tagline or organisation name outside it is cropped off.

## Where it may come from, in order

1. The holder's or author's own site: page header, footer, about page, media or press kit, brand page, map PDFs. Look at the page source for the largest version: an SVG first, then the biggest PNG (check `srcset`, the media library path, linked "logo" or "brand" files). Photos of a trail marker on a tree are not acceptable; artwork files are. A favicon or touch icon is a last resort, and only if it is the emblem at 180 px or more.
2. The managing agency's official page for the trail.
3. Wikimedia Commons, only when the file's page identifies it as the trail's official emblem and gives its origin, and it matches what the holder's own site shows. Record the Commons page as the source.

Never: social media, shops, apps (AllTrails, FarOut), fan redraws, stock sites, image-search thumbnails, or anything you cannot trace to the holder.

## Making the file

One file per trail, `shield.svg` (an SVG of the emblem alone, or one that can be reduced to it by deleting extra elements) or `shield.png`. Crop tight to the emblem with a small even margin. Trimming a uniform border is allowed; nothing else: no redrawing, recolouring, upscaling, sharpening, AI editing or background removal. Keep transparency if the source has it. Never enlarge; take the largest original and leave it at its size (reduce only if it is over 1024 px on the long side). ImageMagick (`magick`) is installed. After making the file, open it and look at it: one emblem, whole, legible, and not blank on a white page or on a dark page. If it is white-on-transparent or black-on-transparent, say so in the note. Aim for at least 256 px on the long side; smaller only when nothing larger exists at an allowed source, and the note says so.

## For each id

Read the record (name, holder or author, official site, the `[shield]` table and its note) and look at any existing file. Then decide:

- `kept`: the existing file is already the emblem alone at 256 px or more. Stage nothing but a report row.
- `replaced`: you found the emblem alone, or a larger or cleaner version.
- `cropped`: the best art is a composite and you cropped the emblem out.
- `new`: the trail had no file and you found its emblem.
- `none-exists`: you looked at the holder's or author's site and the agency page, and the trail has no emblem of its own. Say what marks you did see and why they do not count.
- `logo-not-found`, reported as `not-found`: an emblem seems to exist (seen on a sign in a photo, mentioned in text) but no usable artwork is at an allowed source. Say where it was seen.
- `refused`: every allowed source refused automated reads.

Staged, for every outcome except `kept`: the untouched download as `original.<ext>` in `<staging>/staged/<worker>/<id>/`, the logo file for `replaced`, `cropped` and `new`, and a `change` proposal with edits for `shield.status` (`use-real-logo`, `no-logo-exists` or `logo-not-found`), `shield.logo_source` (the exact address the artwork was downloaded from), `shield.contact`, `shield.logo_file`, `shield.logo_owner` and `shield.note`, a `[[proposal.file]]` for the logo (with `old_sha256` when replacing an existing one), and `[proposal.history]`. The note says, in short plain sentences, what the emblem is, which page shows it in use, what was done to the file ("Cropped from the association's header logo; the wordmark beside the crest was cut off."), any terms the holder states about its logo, and for a trail with no file, every address you looked at.

## The hard part

Deciding what counts as the trail's own emblem when the holder shows only its organisation's mark, and finding the largest original rather than the page's thumbnail. When you are torn, say so in the report and describe both candidates; the owner decides. Do not take the quick answer from the first page: look at the page source and the media library for a larger file, and at the holder's map and brochure PDFs for the emblem in artwork form.

## Time

About 10 minutes per id; at most 90 minutes for a slice. Stop at the budget plus a third and mark the rest `not-reached`.

## Report

`report.csv` with a row per id: outcome, the file, its width and height in `remark`, the source address. Reply with under 120 words: staging path, counts by outcome, and any trail where you were torn.
