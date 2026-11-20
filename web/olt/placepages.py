"""Pages for national parks, mountain ranges and wilderness areas:
    /parks/<slug>/, /ranges/<slug>/, /wilderness/<slug>/

The page itself is regions.place_page, the same one a state page uses; this module
holds only what is different here, as a regions.PageKind each: plain A to Z rows,
the states-and-provinces Where filter, the map opened on the registry's box, and
no whole-trail figure given as the place's (the summary's place has no state keys).
olt/pages.py runs build() through its EXTRA_PAGE_BUILDERS. A place is here only
with three or more trails (olt/places.py collect)."""
from collections import namedtuple

from . import common, places, regions, words
from .markup import esc

Built = namedtuple("Built", ("path", "title", "description", "body", "needs_map", "recs"))


def _in_name(info):
    return places.in_name(info)


def _phrase(info):
    """"in the Wind River Range", "on the Colorado Plateau", "along the Mogollon Rim"."""
    return places.in_phrase(info)


def _kicker(info):
    label = info.get("label") or places.label_of(info)
    names = places.state_names(info)
    return f"{label} · {words.join_names(names)}" if names else label


def _crumbs(info):
    return '<li><a href="/">Trails</a></li><li><a href="/regions/">Places</a></li>'


def _lede(info, recs, n_gpx):
    return f"{regions._plural(len(recs))} {esc(_phrase(info))}, {n_gpx} with a GPX here."


def _title_options(info, recs, site):
    """Every title keeps the count of trails. The state goes first when the title is too long
    (and is never there when the name already holds it); a title that is still over the cap
    keeps its count rather than lose it. "Long Hikes" and the preposition are never cut."""
    count = regions._plural(len(recs), "Trail")
    prep = places.prep_of(info)
    return [f"Long Hikes {prep} {info['title_name']}: {count}",
            f"Long Hikes {prep} {info['name']}: {count}"]


def _description(info, recs):
    n_gpx = regions._gpx_count(recs)
    routes = sum(1 for r in recs if common.is_route(r))
    what = regions._plural(len(recs), "trail") + (" and routes" if 0 < routes < len(recs) else "")
    if routes == len(recs):
        what = regions._plural(len(recs), "route")
    what = what[:1].upper() + what[1:]
    gpx = (f" {regions._with_gpx(n_gpx, len(recs))[:1].upper()}{regions._with_gpx(n_gpx, len(recs))[1:]}."
           if n_gpx else "")
    by_length = sorted(recs, key=lambda r: (r["length_km"], r["id"]))
    # No state keys: a trail that runs on out of the place is never sized as the place's.
    first = (f"{what} {places.prep_of(info)} {info['title_name']}, from {common.plain_name(by_length[0])}, "
             f"{regions.trail_miles(by_length[0], ())}, to {common.plain_name(by_length[-1])}, "
             f"{regions.trail_miles(by_length[-1], ())}.")
    return regions._fit([first + gpx, first, f"{what} {places.prep_of(info)} {info['title_name']}.{gpx}"])


def _nav(info, records, recs, facet_pages):
    return (regions._lists_nav(_in_name(info), recs, records, _phrase(info))
            + regions._facet_nav(_in_name(info), facet_pages, _phrase(info)))


def _kind():
    return regions.PageKind(
        kicker=_kicker, crumbs=_crumbs, lede=_lede, where="all", wholly=False,
        facts_place=lambda info: (_in_name(info), ()), title_options=_title_options,
        description=_description, box=lambda info: info.get("box"), nav=_nav,
        in_name=_in_name, phrase=_phrase)


PARK = _kind()
RANGE = _kind()
WILDERNESS = _kind()
PAGE_KINDS = {"park": PARK, "range": RANGE, "wilderness": WILDERNESS}


def build(records, site, repo_root):
    """[Built] for every place with a page, parks then ranges then wilderness areas,
    each A to Z. The plug-in point's shape (olt/pages.py EXTRA_PAGE_BUILDERS)."""
    infos = places.collect(records, places.load(repo_root))
    out = []
    for info in sorted(infos.values(),
                       key=lambda i: (places.KIND_ORDER[i["kind"]], i["name"].lower())):
        title, description, body, needs_map = regions.place_page(
            info, records, site, PAGE_KINDS[info["kind"]])
        out.append(Built(info["path"], title, description, body, needs_map, info["records"]))
    return out
