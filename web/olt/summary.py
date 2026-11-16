"""A paragraph built from the records that a page lists: what the set holds.

    facts(recs, records)   count, longest and shortest, loops and routes, times, terrain,
                           holders, highest point, and how many have a GPX

Every figure is counted from the records, and a sentence is left out when the records
give it nothing to say. No trail is named here: the longest and the shortest are found
by length. Used by the place pages and the list pages, so none is a bare list.
"""
from . import browse, common, facets, hike, related, words
from .markup import Markup, esc


def _plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def _name_link(rec):
    return f'<a href="{esc(common.trail_path(rec))}">{esc(common.plain_name(rec))}</a>'


def _miles(rec):
    return f'{words.fmt_int(rec["derived"]["length_mi"])} miles ({words.fmt_int(rec["length_km"])} km)'


def _join(parts):
    return words.join_names(parts)


def _list_link(records, key, label, n):
    link = related.list_link(records, key)
    text = f"{esc(label)} ({n})"
    return f'<a href="{esc(link[0])}">{text}</a>' if link else text


def terrain_counts(recs):
    """[(terrain value, how many of recs)], most first, for the terrain the records name."""
    counts = {}
    for r in recs:
        for t in facets.terrain(r):
            counts[t] = counts.get(t, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def holder_counts(recs, records):
    """[(list, how many of recs)] for the lists about standing and holder (olt/browse.py): the
    ones a trail is in by what its designation says."""
    out = []
    for lst, members in browse.shown(records):
        if lst.group not in ("standing", "holder") or lst.key == "routes":
            continue
        ids = {m["id"] for m in members}
        k = sum(1 for r in recs if r["id"] in ids)
        if k:
            out.append((lst, k))
    return out


def facts(recs, records):
    """The summary paragraphs (Markup) for a set of trails. Empty for no trails."""
    if not recs:
        return Markup("")
    by_length = sorted(recs, key=lambda r: (r["length_km"], r["id"]))
    shortest, longest = by_length[0], by_length[-1]
    sentences = []
    if len(recs) > 1:
        sentences.append(f"The longest is {_name_link(longest)}, {_miles(longest)}. "
                         f"The shortest is {_name_link(shortest)}, {_miles(shortest)}.")
    else:
        sentences.append(f"{_name_link(longest)} is {_miles(longest)} long.")
    loops = sum(1 for r in recs if facets.shape(r) == "loop")
    routes = [r for r in recs if facets.kind(r) == "route"]
    parts = []
    if loops:
        parts.append(_plural(loops, "loop"))
    if routes:
        authors = {facets.author(r) for r in routes if facets.author(r)}
        parts.append(f"{_plural(len(routes), 'route')}" + (f" by {_plural(len(authors), 'author')}" if authors else ""))
    if parts and len(recs) > 1:
        sentences.append(f"{_join(parts)[:1].upper()}{_join(parts)[1:]}.")
    paragraphs = [" ".join(sentences)]

    more = []
    timed = sorted(recs, key=lambda r: facets.time_days(r)[:2])
    if len(recs) > 1:
        quick, slow = timed[0], timed[-1]
        more.append(f"The quickest to walk whole is {_name_link(quick)}, {facets.time_text(quick).lower()}, "
                    f"and the slowest is {_name_link(slow)}, {facets.time_text(slow).lower()}.")
    terrain = terrain_counts(recs)
    if terrain:
        shown = _join(
            f'{_list_link(records, "terrain-" + t, words.TERRAIN[t].lower(), n)}' for t, n in terrain[:4])
        have = sum(1 for r in recs if facets.terrain(r))
        more.append(f"Terrain is on file for {have} of them; the most common is {shown}.")
    holders = holder_counts(recs, records)
    if holders:
        more.append("By designation: " + _join(_list_link(records, lst.key, lst.title, k) for lst, k in holders) + ".")
    high = [(hike.table(r).get("high_point_m"), r) for r in recs if isinstance(hike.table(r).get("high_point_m"), (int, float))]
    if high:
        m, top = max(high, key=lambda t: (t[0], t[1]["id"]))
        more.append(f"The highest point stated is {words.elevation(m)}, on {_name_link(top)}.")
    if more:
        paragraphs.append(" ".join(more))
    return Markup("".join(f"<p>{p}</p>" for p in paragraphs))


DETAIL_MAX = 3      # a page with this many trails or fewer gets a paragraph on each, so it is not a bare list


def _rest_of_summary(rec):
    text = hike.summary(rec)
    first = hike.first_sentence(text)
    return text[len(first):].strip() if text.startswith(first) else ""


def detail(rec):
    """One paragraph (HTML) on a trail from its own record: what it is, its ends, its places, its time,
    high point and season, then the rest of its summary and its permit sentence. Only what the record has."""
    h = hike.table(rec)
    kind = "route" if facets.kind(rec) == "route" else "trail"
    places = ", ".join(words.region_name(c) for c in rec.get("regions", []))
    ends = hike.ends(rec)
    where = ""
    if ends:
        label, value = ends
        if isinstance(value, tuple):
            where = f", from {esc(value[0])} to {esc(value[1])}"
        elif label == "Loop":
            where = f", a loop that {esc(value[:1].lower() + value[1:])}"
    author = facets.author(rec)
    what = f"a route by {esc(author)}" if author else f"a {kind}"
    out = [f"<strong>{esc(common.plain_name(rec))}</strong> is {what} of {_miles(rec)}{where}, in {esc(places)}."]
    out.append(f"The usual time to walk it whole is {esc(facets.time_text(rec).lower())}"
               f"{', as a source states it' if not facets.time_days(rec)[2] else ', estimated from its length'}.")
    name, m = h.get("high_point", ""), h.get("high_point_m")
    if isinstance(m, (int, float)) and not isinstance(m, bool):
        out.append(f"Its high point is {esc(name + ', ') if name else ''}{words.elevation(m)}.")
    season = facets.season_text(rec)
    if season:
        out.append(f"Season: {esc(season)}.")
    rest = _rest_of_summary(rec)
    if rest:
        out.append(f'<span class="record-text">{esc(rest)}</span>')
    if h.get("permit"):
        out.append(f'Permit: <span class="record-text">{esc(common.sentence(h["permit"]))}</span>')
    return " ".join(out)


def details(recs):
    """The paragraphs on each trail, under a heading, for a page with few trails; "" for none."""
    if not recs or len(recs) > DETAIL_MAX:
        return Markup("")
    return Markup("<h2>In more detail</h2>" + "".join(f"<p>{detail(r)}</p>" for r in recs))
