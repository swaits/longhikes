"""A page for one kind of trail in one state or province: /regions/<place>/<list key>/.

For every place and every list that has a `noun` (olt/browse.py), the page exists when the place has at
least MIN_SIZE trails in the list, no more than MAX_SHARE of the place's trails are in it (else it
would repeat the place page), and its trails are not nearly the same set as another such page of
the same place. A new trail or a corrected record moves pages in and out with no change here.
"""
from . import bounds, browse, common, facets, home, regions, summary
from .markup import Markup, esc

SAME_SET = 0.8   # two pages of one place whose trails overlap by this share (of the smaller union) are one page


def _jaccard(a, b):
    return len(a & b) / len(a | b)


def plan(records):
    """[{slug, info, lst, recs, path}] for every page, in place then list order."""
    shown = {lst.key for lst, _ in browse.shown(records)}
    by_slug, _ = regions.collect_regions(records)
    out = []
    for slug in sorted(by_slug):
        info = by_slug[slug]
        here = info["records"]
        kept = []
        for lst in browse.facet_lists():
            if lst.key not in shown:
                continue
            recs = browse.members(lst, here)
            if len(recs) < browse.MIN_SIZE or len(recs) > browse.MAX_SHARE * len(here):
                continue
            ids = {r["id"] for r in recs}
            if any(_jaccard(ids, other) >= SAME_SET for other in kept):
                continue
            kept.append(ids)
            out.append({"slug": slug, "info": info, "lst": lst, "recs": recs,
                        "path": f"/regions/{slug}/{lst.key}/"})
    return out


def label(lst):
    """A short name for the page in a list of links."""
    return lst.title


def pages_by_place(pages):
    """slug -> [page], in plan order."""
    out = {}
    for p in pages:
        out.setdefault(p["slug"], []).append(p)
    return out


def pages_by_list(pages):
    out = {}
    for p in pages:
        out.setdefault(p["lst"].key, []).append(p)
    return out


def places_nav(lst, pages):
    """HTML for a list's page: the places that have a page of their own for it."""
    here = pages_by_list(pages).get(lst.key, [])
    if not here:
        return ""
    links = " · ".join(f'<a href="{esc(p["path"])}">{esc(p["info"]["name"])}</a> ({len(p["recs"])})'
                       for p in sorted(here, key=lambda p: p["info"]["name"]))
    return (f'<nav class="region-nav" aria-label="{esc(lst.title)} by place">'
            f'{esc(lst.title)} in a state or province, and how many there: {links}</nav>')


def page(p, records, site, all_pages):
    """(title, description, body, needs_map) for one place-and-list page."""
    lst, info, recs = p["lst"], p["info"], p["recs"]
    here = info["records"]
    name = info["name"]
    only_routes = all(facets.kind(r) == "route" for r in recs)
    count = f"{len(recs)} {'Routes' if only_routes else 'Trails'}"
    title = common.fit_title([f"{lst.noun} in {name}: {count}", f"{lst.noun} in {name}"], site)
    h1 = f"{lst.noun} in {name}"
    n_gpx = sum(1 for r in recs if facets.gpx_here(r))
    gpx = f", {n_gpx} with a GPX here" if n_gpx else ""
    lede = (f"{esc(lst.blurb)} {len(recs)} of the {len(here)} trails in {esc(name)}{gpx}. "
            f'<a href="{esc(facets.place_path(info["key"]))}">All the trails in {esc(name)}</a>.')
    siblings = [q for q in pages_by_place(all_pages)[p["slug"]] if q is not p]
    others = [q for q in pages_by_list(all_pages)[lst.key] if q is not p]
    nav = ""
    if siblings:
        nav += (f'<nav class="region-nav" aria-label="More in {esc(name)}">More in {esc(name)}: '
                + " · ".join(f'<a href="{esc(q["path"])}">{esc(q["lst"].title)}</a> ({len(q["recs"])})' for q in siblings)
                + "</nav>")
    if others:
        nav += (f'<nav class="region-nav" aria-label="{esc(lst.title)} elsewhere">{esc(lst.title)} elsewhere: '
                + " · ".join(f'<a href="{esc(q["path"])}">{esc(q["info"]["name"])}</a> ({len(q["recs"])})'
                             for q in sorted(others, key=lambda q: q["info"]["name"])) + "</nav>")
    crumbs = (f'<li><a href="/">Trails</a></li><li><a href="/regions/">Places</a></li>'
              f'<li><a href="{esc(facets.place_path(info["key"]))}">{esc(name)}</a></li>')
    body = f"""<div class="page-head"><div class="container">
  <nav class="breadcrumb" aria-label="Breadcrumb"><ol>{crumbs}<li aria-current="page">{esc(lst.title)}</li></ol></nav>
  <header class="titleblock"><div class="titleblock__text">
  <p class="kicker">{esc(name)}</p>
  <h1>{esc(h1)}</h1>
  <p class="page-head__lede">{lede}</p>
  </div></header>
</div></div>
<div class="container section place">
  {home.browse_view(home.listing(recs, default_sort=lst.sort, top=2, where=""), home.overview_map(recs, f"Map of the trails in {name}: {lst.title}", place=bounds.place_box(info["key"])),
               about=summary.facts(recs, records), about_title=f"About these trails in {name}")}
  <nav class="region-nav" aria-label="Lists"><a href="{esc(browse.path(lst))}">{esc(lst.title)} everywhere</a> · <a href="/lists/">All lists</a></nav>
  {nav}
</div>"""
    by_length = sorted(recs, key=lambda r: (r["length_km"], r["id"]))
    first = (f"{count} in {name}, from {common.plain_name(by_length[0])}, {regions._miles(by_length[0])} miles, "
             f"to {common.plain_name(by_length[-1])}, {regions._miles(by_length[-1])} miles.")
    desc = regions._fit([f"{lst.blurb} {first}", f"{lst.noun} in {name}: {first}"])
    return title, desc, Markup(body), home.has_overview_map(recs)
