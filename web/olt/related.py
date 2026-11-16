"""Links from one trail to others, worked out from the records alone.

Nothing here names a trail. Every link follows from a fact on the records:

    similar    close in length, with terrain or shape in common (similar_to)
    related    a trail whose own description names another, or two trails that
               share a name (related_to)
    lists      which ready-made list a trail is in, and so which ones its page links to

Every trail is listed by at least MIN_INBOUND other trails' pages (similar_to), so
none is left without a way in. The results are worked out once for a set of
records and kept (a build asks for every trail in turn).
"""
import math
import re

from . import browse, facets, home

SIMILAR_EACH = 4        # each trail picks this many neighbours
SIMILAR_MAX = 6         # most shown on one page
MIN_INBOUND = 3         # every trail is listed on at least this many pages
RELATED_MAX = 6
LENGTH_SPAN = math.log(2.5)   # trails more than 2.5 times apart in length are not alike

_CACHE = {}


def _once(key_records, name, build):
    """Keep build() for this very list of records (by identity)."""
    slot = _CACHE.get(name)
    if slot is None or slot[0] is not key_records:
        slot = (key_records, build())
        _CACHE[name] = slot
    return slot[1]


# Similar trails -------------------------------------------------------------

def similarity(a, b):
    """How alike two trails are for a hiker choosing between them; below zero when they
    are not alike. Length counts most (within a factor of 2.5), then the terrain they
    share, then shape, kind and place."""
    gap = abs(math.log(a["length_km"] / b["length_km"]))
    if gap >= LENGTH_SPAN:
        return -gap     # not alike; the nearest in length still ranks first
    ta, tb = set(facets.terrain(a)), set(facets.terrain(b))
    shared = len(ta & tb)
    score = 3.0 * (1 - gap / LENGTH_SPAN)
    score += 3.0 * shared / max(1, len(ta | tb))
    if shared == 0 and (ta or tb):
        score -= 1.0
    sa, sb = facets.shape(a), facets.shape(b)
    if sa and sa == sb:
        score += 1.0
    if facets.kind(a) == facets.kind(b):
        score += 0.75
    ca, cb = set(facets.place_keys(a)), set(facets.place_keys(b))
    if a["country"] == b["country"]:
        score += 0.75
    if ca & cb:
        score += 0.5
    return score


def _similar_graph(records):
    """id -> the trails its page lists as similar, best first.

    Each trail picks SIMILAR_EACH of the trails most like it, leaning a little toward
    trails that few others have picked yet, so that no trail is left unlinked. Then any
    trail that fewer than MIN_INBOUND pages list is added to the pages of the trails
    most like it that still have room (SIMILAR_MAX). A page lists only its own picks."""
    by_id = {r["id"]: r for r in records}
    score = {}
    for r in records:
        for o in records:
            if r["id"] != o["id"]:
                score[(r["id"], o["id"])] = similarity(r, o)
    picks = {r["id"]: [] for r in records}
    inbound = {r["id"]: 0 for r in records}
    for r in sorted(records, key=lambda r: r["id"]):
        rid = r["id"]
        rows = []
        for o in records:
            oid = o["id"]
            if oid == rid:
                continue
            lean = 0.6 if inbound[oid] < MIN_INBOUND else -0.2 * max(0, inbound[oid] - SIMILAR_EACH)
            rows.append((score[(rid, oid)] + lean, oid))
        rows.sort(key=lambda t: (-t[0], t[1]))
        for _, oid in rows[:SIMILAR_EACH]:
            picks[rid].append(oid)
            inbound[oid] += 1
    for oid in sorted(inbound, key=lambda i: (inbound[i], i)):
        rows = sorted((-score[(rid, oid)], rid) for rid in picks
                      if rid != oid and oid not in picks[rid] and len(picks[rid]) < SIMILAR_MAX)
        for _, rid in rows:
            if inbound[oid] >= MIN_INBOUND:
                break
            picks[rid].append(oid)
            inbound[oid] += 1
    return {rid: sorted(others, key=lambda o: (-score[(rid, o)], o)) for rid, others in picks.items()}


def similar_to(rec, records):
    """Trails like this one, best match first: close in length, alike in terrain,
    shape and place."""
    graph = _once(records, "similar", lambda: _similar_graph(records))
    by_id = {r["id"]: r for r in records}
    return [by_id[i] for i in graph.get(rec["id"], [])]


def shared_terrain(a, b):
    """The terrain two trails have in common, in the first trail's order."""
    tb = set(facets.terrain(b))
    return [t for t in facets.terrain(a) if t in tb]


# Related trails -------------------------------------------------------------

_PAREN = re.compile(r"\s*\([^)]*\)")


def _plain(text):
    return re.sub(r"[^\w]+", " ", text or "").strip().lower()


def _stems(rec):
    """The names a trail is called in running text: its name without any part in
    brackets, and the common name. Two words or more, so a one-word name never matches."""
    plain_name = _PAREN.sub("", rec["name"]).strip()
    out = {plain_name, plain_name.split(",")[0].strip()}
    if rec.get("common_name"):
        out.add(rec["common_name"])
    return {s for s in out if len(s.split()) >= 2}


def _prose(rec):
    """The record's own words about itself that its page shows near the top."""
    h = rec.get("hike", {})
    parts = [h.get("summary", ""), rec.get("designation", ""), h.get("caution", ""),
             rec.get("route", {}).get("note", "")]
    return " ".join(p for p in parts if p)


def _related_graph(records):
    """id -> {other id: reason}. "named": this trail's description names the other.
    "names": the other's description names this trail. "name": they share a name."""
    stems = {r["id"]: _stems(r) for r in records}
    full = {r["id"]: _plain(r["name"] + " " + r.get("common_name", "")) for r in records}
    out = {r["id"]: {} for r in records}
    for r in records:
        text = _prose(r)
        for o in records:
            if o["id"] == r["id"]:
                continue
            if any(re.search(r"(?<!\w)" + re.escape(s) + r"(?!\w)", text) for s in stems[o["id"]]):
                out[r["id"]].setdefault(o["id"], "named")
                out[o["id"]].setdefault(r["id"], "names")
            # a shared name: one trail's name, as a whole phrase, is inside the other's full name
            if any(f" {_plain(s)} " in f" {full[r['id']]} " for s in stems[o["id"]]) or \
                    any(f" {_plain(s)} " in f" {full[o['id']]} " for s in stems[r["id"]]):
                out[r["id"]][o["id"]] = "name"
                out[o["id"]][r["id"]] = "name"
    return out


RELATED_ORDER = {"name": 0, "named": 1, "names": 2}


def related_to(rec, records):
    """[(trail, reason)] for the trails this one is tied to by what the records say,
    shared names first, then the trails its description names, then trails whose
    descriptions name it; the longest first within each."""
    graph = _once(records, "related", lambda: _related_graph(records))
    by_id = {r["id"]: r for r in records}
    rows = [(by_id[i], why) for i, why in graph.get(rec["id"], {}).items()]
    rows.sort(key=lambda t: (RELATED_ORDER[t[1]], -t[0]["length_km"], t[0]["id"]))
    return rows[:RELATED_MAX]


# Lists ----------------------------------------------------------------------

def shown_lists(records):
    """{list key: List} for the lists that have a page of their own today."""
    return _once(records, "lists", lambda: {lst.key: lst for lst, _ in browse.shown(records)})


def list_link(records, key):
    """(path, title) of the list, or None when it is not shown."""
    if not records:
        return None
    lst = shown_lists(records).get(key)
    return (browse.path(lst), lst.title) if lst else None
