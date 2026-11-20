"""A paragraph built from the records that a page lists: what the set holds.

    facts(recs, records)   one short paragraph: the longest and shortest, loops and routes,
                           the most common terrain and the highest point

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


def wholly_in(rec, keys):
    """True when every state or province the record names is one of keys (olt/facets.py place keys).
    A trail that names a place outside them only passes through, so its length and high point are
    not the place's. The record names whole states, never where a trail enters one, so this is the
    cautious reading."""
    return set(facets.place_keys(rec)) <= set(keys)


def facts(recs, records, by_authors=True, place=None):
    """The summary of a set of trails: one short paragraph (Markup). Empty for no trails. With
    by_authors False (an author's own page) the routes-and-authors clause is left out.

    place: (name, keys) on a page for a place, so no figure of a whole trail is given as the place's.
    The length of a trail that also lies elsewhere is said to be its length "in all", and the highest
    point is taken only from the trails wholly in the place (a high point on file has no location)."""
    if not recs:
        return Markup("")
    by_length = sorted(recs, key=lambda r: (r["length_km"], r["id"]))
    shortest, longest = by_length[0], by_length[-1]
    name, keys = place if place else ("", ())
    inside = [r for r in recs if wholly_in(r, keys)] if place else recs
    crossing = len(inside) < len(recs)
    sentences = []
    if crossing and len(recs) > 1:
        sentences.append(f"The longest trail that passes through {esc(name)} is {_name_link(longest)}, {_miles(longest)} in all, "
                         f"and the shortest {_name_link(shortest)}, {_miles(shortest)} in all.")
    elif crossing:
        sentences.append(f"{_name_link(longest)} passes through {esc(name)} and is {_miles(longest)} long in all.")
    elif len(recs) > 1:
        sentences.append(f"The longest is {_name_link(longest)}, {_miles(longest)}, "
                         f"and the shortest {_name_link(shortest)}, {_miles(shortest)}.")
    else:
        sentences.append(f"{_name_link(longest)} is {_miles(longest)} long.")
    loops = sum(1 for r in recs if facets.shape(r) == "loop")
    routes = [r for r in recs if facets.kind(r) == "route"]
    parts = []
    if loops:
        parts.append(f"{loops} {'is a loop' if loops == 1 else 'are loops'}")
    if routes and by_authors:
        authors = {facets.author(r) for r in routes if facets.author(r)}
        n = len(routes)
        parts.append(f"{n} {'is a route' if n == 1 else 'are routes'}"
                     + (f" by {_plural(len(authors), 'author')}" if authors and n > 1 else ""))
    if parts and len(recs) > 1:
        text = _join(parts)
        sentences.append(f"{text[:1].upper()}{text[1:]}.")
    terrain = terrain_counts(recs)
    if terrain and len(recs) > 1:
        shown = _join(
            f'{_list_link(records, "terrain-" + t, words.TERRAIN[t].lower(), n)}' for t, n in terrain[:3])
        sentences.append(f"The most common terrain is {shown}.")
    high = [(hike.table(r).get("high_point_m"), r) for r in inside if isinstance(hike.table(r).get("high_point_m"), (int, float))]
    if high:
        m, top = max(high, key=lambda t: (t[0], t[1]["id"]))
        which = f"The highest point on file among the trails wholly in {esc(name)}" if crossing else "The highest point on file"
        sentences.append(f"{which} is {words.elevation(m)}, on {_name_link(top)}.")
    return Markup(f"<p>{' '.join(sentences)}</p>")


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
        how = (", judged from pages that differ" if facets.season_pages_differ(rec)
               else ", estimated from the climate and similar trails" if facets.season_estimated(rec) else "")
        out.append(f"Season: {esc(season)}{how}.")
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
