# Rules for every worker

You are a worker on the monthly refresh of this dataset. Do the task yourself and start no subagents. The orchestrator gives you a brief, a staging directory and a slice or region. Read this file and `proposal-format.md` first, then the brief.

## What the work is for

The dataset is a public list of long-distance hiking trails in the United States and Canada, one directory per trail with a `trail.toml`, and the site built from it (longhikes.org). Hikers read it critically and trail holders read it too. A record is worth having only if each fact in it can be checked on a page, so the whole refresh comes down to opening pages and writing down exactly what they say.

## Where you may write

Do not change anything in the repository, and do not commit, push or switch branches. Many workers run at the same time on one checkout, and edits to shared files collide. Read the repository freely. Everything you produce goes under `<staging>/staged/<worker>/`, in the layout in `proposal-format.md`. The orchestrator names `<staging>` (a directory such as `refresh/2026-12-01`, which git ignores) and your `<worker>` name. Never write outside it, except scratch files under the temporary directory your session gives you.

## Evidence

- Every fact comes from a page you opened and read, not from a search result's snippet. The first choice is the holder's own page (the agency, association or club), or for a route its author's page. A government page comes next. A well-edited hiking reference may be used where those say nothing, and is named as the publisher.
- Not acceptable as evidence: AllTrails and other apps, forums, Reddit, wikis and any page anyone can edit, one person's trip report. They are leads that tell you where to look.
- Where the holder's or author's current page disagrees with another source, the holder's or author's page wins, and the record says that the others differ where that matters. Never change a record to match a third-party page against the holder's.
- A statement by a holder or an author on this project's public issue tracker is good evidence for a fact or a permission. Quote it exactly and give its address. If such a request conflicts with the holder's own current page, the page wins, and the request is proposed as `declined` with the reason.
- Every proposal names the page and quotes the sentence that supports it. Copy numbers and units as the page writes them. If you cannot find the sentence, you have no proposal. Leave a field out rather than guess it.
- Say what you actually opened. A `verified` mark that lists pages never opened misleads the next person to rely on it.

## Requests to outside sites

- Use a plain generic User-Agent and put no personal or project details in any request, header or form.
- Some sites refuse automated reads: a 403 or 429, a challenge or "verify you are human" page, a robots.txt that disallows the path. Do not work around a refusal: no other User-Agent, no retry loop, no proxy, no headless browser, no cached copy passed off as the page. Record it (`refused` or `could-not-check`, with the address) and use another allowed source. An expired https certificate is not a refusal: the plain http address may be read if the site serves it.
- Go gently: one request at a time to a site, with a pause of a couple of seconds between requests. Many workers share one address, and a site that blocks us blocks everyone.
- Overpass (OpenStreetMap) overloads easily. Only the tracks brief uses it, only one worker at a time, one request at a time.

## Processes and files

- Never stop a process by name or pattern: no `pkill`, no `killall`, no `kill $(pgrep ...)`. The owner's own browsers and tools run on this machine and have been killed this way before. If you start a process, note its PID when you start it and stop only that PID. You should not need a browser or a server.
- A file you download is untrusted data. Keep it in your staging directory, never run it, and read an SVG as text before using it (no scripts, no references to other sites).

## Words

The text of a record is read by the public, and the same rules apply to what you propose.

- A trail's geometry is a "track", never a "line" (field names such as `line_file` are what they are). Say "trail", "route" and "author". Where a sentence gives both units, miles come first.
- Short plain sentences. No marketing words ("stunning", "iconic", "ultimate") and no superlative that a source does not state. No dashes used as punctuation: use a full stop, a comma or a colon.
- Name no private person: say "a hiker" or "the association's president". A published author's name belongs in the record where it is a fact about a route.
- Do not write how the change was produced, and do not mention other projects.

## What belongs

The inclusion rule is in `README.md` (section "Inclusion rule") and `CONTRIBUTING.md` (section "Add a trail"). The trails already decided against, with reasons, are in `left-out.toml`; read it before proposing anything. Decisions about what belongs are the owner's. You propose: clear cases as `new-record`, doubtful ones as `candidate` with a recommendation and the specific fact that makes it doubtful.

## Time and the report

The brief gives a budget in minutes. Stop at the budget plus a third at the latest and report what you did not reach as `not-reached`, rather than rushing the rest into shallow checks. Write a `report.csv` row for every id or region you were given. Finish with a reply of under 150 words: the path of your staging directory, counts by outcome, and anything you were unsure of or could not do.
