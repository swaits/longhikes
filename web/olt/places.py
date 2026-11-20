"""National parks, mountain ranges and wilderness areas: the places.toml registry
and which trails are in each place (the [[place]] tables of the records).

Membership is closed over the registry's `within` here, at build time: a trail in a
nested range is in every parent range too, though its record never names a parent.
A place has a page only with PAGE_MIN or more trails, counting measured (`track`)
and hand-entered (`stated`) placements alike. Below that it has no page and no link.
"""
from dataclasses import dataclass

from . import datafiles, facets, words

PAGE_MIN = 3


@dataclass(frozen=True)
class Kind:
    key: str        # the registry kind: "park", "range", "wilderness"
    segment: str    # the first part of the page's address: /parks/<slug>/
    hub_title: str  # the Places hub section's heading
    noun: str       # one place of this kind, for a page's kicker


KINDS = {
    "park": Kind("park", "parks", "Parks", "Park"),
    "range": Kind("range", "ranges", "Mountain ranges", "Mountain range"),
    "wilderness": Kind("wilderness", "wilderness", "Wilderness areas", "Wilderness area"),
}
KIND_ORDER = {key: i for i, key in enumerate(KINDS)}


def load(repo_root):
    """The place registry of places.toml, keyed (kind, slug). Slugs repeat across kinds."""
    out = {}
    for e in datafiles.places(repo_root):
        if isinstance(e, dict) and e.get("kind") and e.get("slug"):
            out[(e["kind"], e["slug"])] = e
    return out


def path(kind, slug):
    """The page of a place: /parks/glacier/, /ranges/wind-river-range/, /wilderness/<slug>/."""
    return f"/{KINDS[kind].segment}/{slug}/"


def _parents(registry):
    """(kind, slug) -> its parent (kind, slug)s. A `within` parent is always a range."""
    return {key: [("range", s) for s in (e.get("within") or []) if ("range", s) in registry]
            for key, e in registry.items()}


def _closure(key, parents):
    """The place itself and every ancestor, each once (a `within` cycle cannot loop)."""
    seen, stack = [], [key]
    while stack:
        k = stack.pop(0)
        if k in seen:
            continue
        seen.append(k)
        stack += parents.get(k, [])
    return seen


def membership(records, registry):
    """(kind, slug) -> the records in the place, deduplicated and A to Z, closed over
    `within`. Every registry place is a key, with no records when none is in it. A place
    a record names that the registry does not hold is ignored (the validator refuses it)."""
    parents = _parents(registry)
    out = {key: [] for key in registry}
    seen = {key: set() for key in registry}
    for rec in records:
        for p in rec.get("place") or []:
            if not isinstance(p, dict):
                continue
            key = (p.get("kind"), p.get("slug"))
            if key not in registry:
                continue
            for k in _closure(key, parents):
                if rec["id"] not in seen[k]:
                    seen[k].add(rec["id"])
                    out[k].append(rec)
    for recs in out.values():
        recs.sort(key=facets.sort_name)
    return out


def _state_key(code):
    """"WY" -> "US-WY"; a code already carrying its country ("us-wy") is put in the same form."""
    code = str(code or "").strip()
    if "-" in code:
        country, _, rest = code.partition("-")
        return f"{country.upper()}-{rest.upper()}"
    country = words.region_country(code)
    return f"{country}-{code}" if country else code


def state_names(info):
    """The full names of the states and provinces a place is in ("Wyoming"), from its `where`."""
    return [words.region_name(_state_key(c).split("-", 1)[-1]) for c in info.get("where") or []]


def in_name(info):
    """The name as it reads after "in": a range or a wilderness area takes "the"
    ("in the Wind River Range"), a park does not ("in Yosemite National Park")."""
    name = info["name"]
    if info.get("kind") in ("range", "wilderness") and not name.lower().startswith("the "):
        return f"the {name}"
    return name


def title_name(info):
    """The place as a page title names it: a park by its name alone; a range or a
    wilderness area in one state or province with that state spelled out
    ("Wind River Range, Wyoming"), and with no state when it spans several."""
    name = info["name"]
    if info.get("kind") == "park":
        return name
    names = state_names(info)
    return f"{name}, {names[0]}" if len(names) == 1 else name


_NAME_ENDS = (" national park", " provincial park", " wilderness area", " park", " wilderness")


def _core(name):
    text = " ".join(str(name).lower().split())
    changed = True
    while changed:
        changed = False
        for end in _NAME_ENDS:
            if text.endswith(end) and len(text) > len(end):
                text = text[:-len(end)].strip()
                changed = True
    return text


def _doubled(park_name, wild_name):
    """True when a park and a wilderness area are the same ground under two names: one
    name holds the other, or the names differ only in the kind words at the end."""
    a, b = " ".join(str(park_name).lower().split()), " ".join(str(wild_name).lower().split())
    if a in b or b in a:
        return True
    return bool(_core(a)) and _core(a) == _core(b)


_STEM_FILLER = {"national", "provincial", "park", "parks", "preserve", "wilderness", "area",
                "and", "the", "of", "mountains", "mountain", "range", "ranges"}


def _stem(name):
    return {w for w in str(name).lower().replace("-", " ").split() if w not in _STEM_FILLER}


def _same_stem(park_name, range_name):
    """True when a park and a mountain range have the same name once the kind words are
    taken away: Olympic National Park and Olympic Mountains, Great Smoky Mountains National
    Park and Great Smoky Mountains. Grand Teton National Park and the Teton Range do not."""
    a, b = _stem(park_name), _stem(range_name)
    return bool(a) and a == b


def collect(records, registry):
    """(kind, slug) -> info for every place with a page: PAGE_MIN or more trails.

    An info holds kind, slug, key ("<kind>/<slug>"), name, where, box, records, path
    and title_name. A wilderness area or a mountain range that holds exactly the
    trails of a park of much the same name gets no page: one page for the one set, under
    the park. The registry normally already leaves such a place out; the builder stays safe."""
    mem = membership(records, registry)
    out = {}
    for (kind, slug), recs in mem.items():
        if len(recs) < PAGE_MIN:
            continue
        e = registry[(kind, slug)]
        info = {"kind": kind, "slug": slug, "key": f"{kind}/{slug}", "name": e.get("name", slug),
                "where": list(e.get("where") or []), "box": e.get("box"), "records": recs,
                "path": path(kind, slug)}
        info["title_name"] = title_name(info)
        out[(kind, slug)] = info
    parks = [i for i in out.values() if i["kind"] == "park"]
    for key, info in list(out.items()):
        if info["kind"] not in ("wilderness", "range"):
            continue
        ids = {r["id"] for r in info["records"]}
        same = _doubled if info["kind"] == "wilderness" else _same_stem
        if any({r["id"] for r in p["records"]} == ids and same(p["name"], info["name"])
               for p in parks):
            del out[key]
    return out


def _infos(infos):
    return list(infos.values()) if isinstance(infos, dict) else list(infos or ())


def _by_kind_then_name(infos):
    return sorted(infos, key=lambda i: (KIND_ORDER.get(i["kind"], 99), i["name"].lower()))


def in_state(infos, state_key):
    """The places with a page that lie in one state or province (state_key as in
    olt/facets.py, "US-WY"), by kind then name."""
    want = _state_key(state_key)
    return _by_kind_then_name([i for i in _infos(infos)
                                if want in {_state_key(c) for c in i.get("where") or []}])


def of_record(rec, infos):
    """The places of one trail that have a page, by kind then name. A parent range is
    among them: the infos' records are already closed over `within`."""
    return _by_kind_then_name([i for i in _infos(infos)
                                if any(r["id"] == rec["id"] for r in i["records"])])
