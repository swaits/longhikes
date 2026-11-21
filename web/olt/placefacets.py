"""A page for one kind of trail in one state or province: /regions/<place>/<list key>/.

For every place and every list that has a `noun` (olt/browse.py), the page exists when the place has at
least MIN_SIZE trails in the list, no more than MAX_SHARE of the place's trails are in it (else it
would repeat the place page), and its trails are not nearly the same set as another such page of
the same place. For a park, range or wilderness area, a trail of 1,000 miles or more is shown but does
not count toward the 3 needed, and pages of different places for one list that hold exactly the same
trails are one page (the park's, else the range's, else the wilderness area's). A new trail or a
corrected record moves pages in and out with no change here.
"""
from . import bounds, browse, common, facets, home, places as places_mod, regions, summary
from .markup import Markup, esc

SAME_SET = 0.8   # two pages of one place whose trails overlap by this share (of the smaller union) are one page


def _jaccard(a, b):
    return len(a & b) / len(a | b)


PLACE_MIN = 3    # a park, range or wilderness area's list page needs this many trails

# Lists crossed with a park, range or wilderness area: those that cross a state, less any named here.
# A list that is itself a place or a holder has no noun, so none is crossed.
PLACE_LISTS_OUT = frozenset()

# A trail this long crosses a place and is not "in" it: it is shown on a place's list page but does
# not count toward the PLACE_MIN needed to build one.
VERY_LONG_KM = browse.LONG_KM
# Length bands of 500 miles or more are not crossed with a park or a wilderness area: no trail that
# long lies inside one. A range may keep them.
OUT_BY_KIND = {"park": frozenset({"500-to-1000-miles"}), "wilderness": frozenset({"500-to-1000-miles"})}


def _plan(units, records, min_size, path_of, lists, max_share, count_long=True):
    """[{slug, info, lst, recs, path, kind}]: for each unit (slug, info) and each list, a page when the
    place has min_size trails in the list, no more than max_share of the place's trails are in it,
    and its trails are not nearly the same set as another page of the same place. With count_long False
    a trail of VERY_LONG_KM or more is shown but not counted toward min_size."""
    shown = {lst.key for lst, _ in browse.shown(records)}
    out = []
    for slug, info in units:
        here = info["records"]
        kept = []
        for lst in lists:
            if lst.key not in shown or lst.key in OUT_BY_KIND.get(info["kind"], ()):
                continue
            recs = browse.members(lst, here)
            counted = len(recs) if count_long else sum(1 for r in recs if r["length_km"] < VERY_LONG_KM)
            if counted < min_size or len(recs) > max_share * len(here) or len(recs) >= len(here):
                continue
            ids = {r["id"] for r in recs}
            if any(_jaccard(ids, other) >= SAME_SET for other in kept):
                continue
            kept.append(ids)
            out.append({"slug": slug, "info": info, "lst": lst, "recs": recs,
                        "path": path_of(slug, info, lst), "kind": info["kind"]})
    return out


def plan(records):
    """[{slug, info, lst, recs, path, kind}] for every state page, in place then list order."""
    by_slug, _ = regions.collect_regions(records)
    return _plan([(slug, by_slug[slug]) for slug in sorted(by_slug)], records, browse.MIN_SIZE,
                 lambda slug, info, lst: f"/regions/{slug}/{lst.key}/", browse.facet_lists(), browse.MAX_SHARE)


def plan_places(infos, records, max_share=browse.MAX_SHARE):
    """The same for parks, ranges and wilderness areas: infos as olt/places.py collect gives them.
    The path is the place's own with the list's key after it."""
    units = [(i["slug"], i) for i in sorted(infos.values() if isinstance(infos, dict) else infos,
                                            key=lambda i: (places_mod.KIND_ORDER[i["kind"]], i["name"].lower()))]
    lists = [lst for lst in browse.facet_lists() if lst.key not in PLACE_LISTS_OUT]
    return _one_page_per_set(_plan(units, records, PLACE_MIN, lambda slug, info, lst: f"{info['path']}{lst.key}/",
                                   lists, max_share, count_long=False))


def _one_page_per_set(pages):
    """Of the place pages of one list that hold exactly the same trails, keep one: the park's, else
    the range's, else the wilderness area's; of two of a kind, the place with fewer trails (the more
    specific), then the name. The others are dropped, and nothing links to them."""
    rank = {"park": 0, "range": 1, "wilderness": 2}
    best = {}
    for p in pages:
        k = (p["lst"].key, frozenset(r["id"] for r in p["recs"]))
        mine = (rank[p["kind"]], len(p["info"]["records"]), p["info"]["name"].lower())
        if k not in best or mine < best[k][0]:
            best[k] = (mine, p)
    keep = {id(v[1]) for v in best.values()}
    return [p for p in pages if id(p) in keep]


def key_of(p):
    """What pages_by_place keys a page by: (kind, slug) for a place, the slug for a state."""
    return p["slug"] if p["kind"] == "state" else (p["kind"], p["slug"])


def place_noun(lst):
    """The short noun a place page's title and heading use for the list, the same whatever the name."""
    return lst.short or lst.noun


def label(lst):
    """A short name for the page in a list of links."""
    return lst.title


def pages_by_place(pages):
    """slug (a state) or (kind, slug) (a park, range or wilderness area) -> [page], in plan order."""
    out = {}
    for p in pages:
        out.setdefault(key_of(p), []).append(p)
    return out


def pages_by_list(pages):
    out = {}
    for p in pages:
        out.setdefault(p["lst"].key, []).append(p)
    return out


def places_nav(lst, pages):
    """HTML for a list's page: the places that have a page of their own for it."""
    here = [p for p in pages_by_list(pages).get(lst.key, []) if p["kind"] == "state"]
    if not here:
        return ""
    links = " · ".join(f'<a href="{esc(p["path"])}">{esc(p["info"]["name"])}</a> ({len(p["recs"])})'
                       for p in sorted(here, key=lambda p: p["info"]["name"]))
    return (f'<nav class="region-nav" aria-label="{esc(lst.title)} by place">'
            f'{esc(lst.title)} in a state or province, and how many there: {links}</nav>')


def _kind(info):
    """The PageKind of the place's own page: its where-filter, its map box and how it is named."""
    from . import placepages
    return regions.STATE if info["kind"] == "state" else placepages.PAGE_KINDS[info["kind"]]


def _own_path(info):
    return facets.place_path(info["key"]) if info["kind"] == "state" else info["path"]


def page(p, records, site, all_pages):
    """(title, description, body, needs_map) for one place-and-list page, of a state or of a park,
    range or wilderness area. Every string that depends on the kind of place comes from the place."""
    lst, info, recs = p["lst"], p["info"], p["recs"]
    kind = _kind(info)
    here = info["records"]
    name = info["name"]
    state = info["kind"] == "state"
    in_name = kind.in_name(info) if kind.in_name else name
    phrase = kind.phrase(info) if kind.phrase else f"in {in_name}"
    title_name = name if state else info["title_name"]
    prep = "in" if state else places_mod.prep_of(info)
    if state:
        only_routes = all(facets.kind(r) == "route" for r in recs)
        count = f"{len(recs)} {'Routes' if only_routes else 'Trails'}"
        short = lst.short or lst.noun
        # The state goes first, then the long noun; the count is never dropped (a title that still
        # does not fit, where the place's own name is long, keeps its count and goes over).
        ladder = [f"{lst.noun} {prep} {title_name}: {count}", f"{lst.noun} {prep} {name}: {count}",
                  f"{short} {prep} {title_name}: {count}", f"{short} {prep} {name}: {count}"]
        h1 = f"{lst.noun} {phrase}"
    else:
        # One fixed pattern: <short noun> <the place's preposition and name>: <N> Trails (Routes for
        # the routes list). The state follows a place in one state when the title still fits; a long
        # place name runs long and keeps its count. The heading is the title.
        count = f"{len(recs)} {'Routes' if lst.key == 'routes' else 'Trails'}"
        noun = place_noun(lst)
        ladder = [f"{noun} {prep} {title_name}: {count}", f"{noun} {prep} {name}: {count}"]
    title = common.fit_title(ladder, site)
    if not state:
        h1 = title
    n_gpx = sum(1 for r in recs if facets.gpx_here(r))
    gpx = f", {n_gpx} with a GPX here" if n_gpx else ""
    lede = (f"{esc(lst.blurb)} {len(recs)} of the {len(here)} trails {esc(phrase)}{gpx}. "
            f'<a href="{esc(_own_path(info))}">All the trails {esc(phrase)}</a>.')
    siblings = [q for q in pages_by_place(all_pages)[key_of(p)] if q is not p]
    others = [q for q in pages_by_list(all_pages)[lst.key] if q is not p and q["kind"] == p["kind"]]
    nav = ""
    if siblings:
        nav += (f'<nav class="region-nav" aria-label="More {esc(phrase)}">More {esc(phrase)}: '
                + " · ".join(f'<a href="{esc(q["path"])}">{esc(q["lst"].title)}</a> ({len(q["recs"])})' for q in siblings)
                + "</nav>")
    if others:
        nav += (f'<nav class="region-nav" aria-label="{esc(lst.title)} elsewhere">{esc(lst.title)} elsewhere: '
                + " · ".join(f'<a href="{esc(q["path"])}">{esc(q["info"]["name"])}</a> ({len(q["recs"])})'
                             for q in sorted(others, key=lambda q: q["info"]["name"])) + "</nav>")
    crumbs = ('<li><a href="/">Trails</a></li><li><a href="/regions/">Places</a></li>'
              f'<li><a href="{esc(_own_path(info))}">{esc(name)}</a></li>')
    place = kind.facts_place(info)
    body = f"""<div class="page-head"><div class="container">
  <nav class="breadcrumb" aria-label="Breadcrumb"><ol>{crumbs}<li aria-current="page">{esc(lst.title)}</li></ol></nav>
  <header class="titleblock"><div class="titleblock__text">
  <p class="kicker">{esc(name)}</p>
  <h1>{esc(h1)}</h1>
  <p class="page-head__lede">{lede}</p>
  </div></header>
</div></div>
<div class="container section place">
  {home.browse_view(home.listing(recs, default_sort=lst.sort, top=2, where="" if state else kind.where, season=lst.group == "month"), home.overview_map(recs, f"Map of the trails {phrase}: {lst.title}", place=kind.box(info)),
               about=summary.facts(recs, records, place=place), about_title=f"About these trails {phrase}")}
  <nav class="region-nav" aria-label="Lists"><a href="{esc(browse.path(lst))}">{esc(lst.title)} everywhere</a> · <a href="/lists/">All lists</a></nav>
  {nav}
</div>"""
    by_length = sorted(recs, key=lambda r: (r["length_km"], r["id"]))
    keys = place[1]
    first = (f"{count} {phrase}, from {common.plain_name(by_length[0])}, {regions.trail_miles(by_length[0], keys)}, "
             f"to {common.plain_name(by_length[-1])}, {regions.trail_miles(by_length[-1], keys)}.")
    desc = regions._fit([f"{lst.blurb} {first}", f"{lst.noun} {phrase}: {first}"] if state
                        else [f"{lst.blurb} {first}", first])
    return title, desc, Markup(body), home.has_overview_map(recs)
