"""Lists: ready-made selections of trails, each a rule over a trail's attributes (olt/facets.py).

A list is defined once, here, as a test on a trail. No list names a trail by
id: membership follows the records, so a new trail or a new [hike] table moves
trails in and out of lists with no change to this file.

A list is shown (on the home page, on /lists/, and with a page of its own)
only when it is useful with today's trails:

    MIN_SIZE   at least this many trails (fewer reads as a gap, not a list)
    MAX_SHARE  at most this share of all trails (more is nearly everything)

Every list has its page at /lists/<key>/, except Routes, which keeps /routes/.
"""
from dataclasses import dataclass
from typing import Callable

from . import common, facets, words

MIN_SIZE = 4
MAX_SHARE = 0.75

LONG_KM = 2000
SHORT_KM = 100


@dataclass(frozen=True)
class List:
    key: str
    title: str
    blurb: str
    test: Callable[[dict], bool]
    # Order within the list: longest first unless a list says otherwise.
    order: Callable[[dict], object] = lambda r: -r["length_km"]


def _mi(km):
    return words.fmt_int(words.km_to_mi(km))


def _band(key):
    return lambda r: facets.time_band(r) == key


def _days(r):
    return facets.time_days(r)[1]


LISTS = (
    List("national-scenic-trails", "National Scenic Trails",
         "The long trails the United States Congress has named National Scenic Trails.",
         facets.is_national),
    List("routes", "Routes", facets.ROUTE_DEFINITION,
         lambda r: facets.kind(r) == "route"),
    List("longest", "The longest",
         f"Trails of {LONG_KM:,} km ({_mi(LONG_KM)} mi) or more.",
         lambda r: r["length_km"] >= LONG_KM),
    List("under-100-km", f"Under {SHORT_KM} km",
         f"Trails shorter than {SHORT_KM} km ({_mi(SHORT_KM)} mi).",
         lambda r: r["length_km"] < SHORT_KM, order=lambda r: r["length_km"]),
    List("a-week-or-less", "A week or less",
         "Trails most people walk in a week or less, as a source states it or as estimated from the length.",
         _band("week"), order=_days),
    List("one-to-two-weeks", "One to two weeks",
         "Trails that take one to two weeks, as a source states it or as estimated from the length.",
         _band("two-weeks"), order=_days),
    List("loops", "Loops", "Trails that finish where they start.",
         lambda r: facets.shape(r) == "loop"),
    List("with-gpx", "With a GPX to download",
         "Trails with a GPX file of the track on their page.",
         facets.gpx_here),
    List("canada", "In Canada", "Trails in Canada, or crossing into it.",
         lambda r: "CA" in common.countries(r)),
    List("united-states", "In the United States", "Trails in the United States, or crossing into it.",
         lambda r: "US" in common.countries(r)),
    List("off-trail", "Cross-country",
         "Trails with stretches of walking where there is no trail.",
         lambda r: facets.walking(r) in facets.CROSS_COUNTRY),
) + tuple(
    List(f"terrain-{t}", label, f"Trails with {t} among their main terrain.",
         lambda r, t=t: t in facets.terrain(r))
    for t, label in words.TERRAIN.items()
)


def members(lst, records):
    return sorted((r for r in records if lst.test(r)), key=lambda r: (lst.order(r), r["name"]))


def is_shown(n, total):
    """The threshold rule: a list is shown when it holds at least MIN_SIZE
    trails and no more than MAX_SHARE of all of them."""
    return n >= MIN_SIZE and n <= MAX_SHARE * total


def shown(records):
    """[(list, its trails)] for every list that passes is_shown, in LISTS order."""
    out = []
    for lst in LISTS:
        recs = members(lst, records)
        if is_shown(len(recs), len(records)):
            out.append((lst, recs))
    return out


def by_key(key):
    return next(lst for lst in LISTS if lst.key == key)


def path(lst):
    return "/routes/" if lst.key == "routes" else f"/lists/{lst.key}/"
