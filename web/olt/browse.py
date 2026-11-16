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

# The two lists defined by length are set in miles; membership compares the
# record's kilometres with the mile figure converted once, here.
LONG_MI = 1000
SHORT_MI = 100
LONG_KM = LONG_MI * words.KM_PER_MI
SHORT_KM = SHORT_MI * words.KM_PER_MI


@dataclass(frozen=True)
class List:
    key: str
    title: str
    blurb: str
    test: Callable[[dict], bool]
    # The order the list opens in, a key of facets.SORTS. Name order unless
    # the list is defined by an order (the longest, the shortest, a week).
    sort: str = "name"
    # The page's <title> before the site name, in the words people search with; {n} is
    # the number of trails. Empty: the list's own title with the count.
    page_title: str = ""

    def search_title(self, n):
        return (self.page_title or f"{self.title}: {{n}} Trails").format(n=n)


def _km(mi):
    return words.fmt_int(mi * words.KM_PER_MI)


def _band(key):
    return lambda r: facets.time_band(r) == key


# The terrain as an adjective, for a list's page title ("Coastal Hiking Trails").
TERRAIN_ADJECTIVE = {"coast": "Coastal", "lakes": "Lake"}

LISTS = (
    List("national-scenic-trails", "National Scenic Trails",
         "The long trails the United States Congress has named National Scenic Trails.",
         facets.is_national, page_title="National Scenic Trails: {n} Long Hiking Trails"),
    List("routes", "Routes", facets.ROUTE_DEFINITION,
         lambda r: facets.kind(r) == "route", page_title="Long Hiking Routes by Author: {n} Routes"),
    List("longest", "The longest",
         f"Trails of {LONG_MI:,} miles ({_km(LONG_MI)} km) or more.",
         lambda r: r["length_km"] >= LONG_KM, sort="length-desc",
         page_title=f"Longest Hiking Trails: {{n}} Trails of {LONG_MI:,}+ Miles"),
    List("under-100-miles", f"Under {SHORT_MI} miles",
         f"Trails shorter than {SHORT_MI} miles ({_km(SHORT_MI)} km).",
         lambda r: r["length_km"] < SHORT_KM, sort="length-asc",
         page_title=f"Hiking Trails Under {SHORT_MI} Miles: {{n}} Long Trails"),
    List("a-week-or-less", "A week or less",
         "Trails most people walk in a week or less, as a source states it or as estimated from the length.",
         _band("week"), sort="time-asc", page_title="Long Trails to Hike in a Week or Less: {n} Trails"),
    List("one-to-two-weeks", "One to two weeks",
         "Trails that take one to two weeks, as a source states it or as estimated from the length.",
         _band("two-weeks"), sort="time-asc", page_title="Long Trails to Hike in One to Two Weeks: {n} Trails"),
    List("loops", "Loops", "Trails that finish where they start.",
         lambda r: facets.shape(r) == "loop", page_title="Loop Hiking Trails: {n} Long Trail Loops"),
    List("with-gpx", "With a GPX to download",
         "Trails with a GPX file of the track on their page.",
         facets.gpx_here, page_title="Long Trails with a GPX to Download: {n} Trails"),
    List("canada", "In Canada", "Trails in Canada, or crossing into it.",
         lambda r: "CA" in common.countries(r), page_title="Hiking Trails in Canada: {n} Long Trails"),
    List("united-states", "In the United States", "Trails in the United States, or crossing into it.",
         lambda r: "US" in common.countries(r), page_title="Hiking Trails in the United States: {n} Long Trails"),
    List("off-trail", "Cross-country",
         "Trails with stretches of walking where there is no trail.",
         lambda r: facets.walking(r) in facets.CROSS_COUNTRY,
         page_title="Cross-Country Hiking: {n} Long Trails and Routes"),
) + tuple(
    List(f"terrain-{t}", label, f"Trails with {t} among their main terrain.",
         lambda r, t=t: t in facets.terrain(r),
         page_title=f"{TERRAIN_ADJECTIVE.get(t, label)} Hiking Trails: {{n}} Long Trails")
    for t, label in words.TERRAIN.items()
)


def members(lst, records):
    return facets.sort_records([r for r in records if lst.test(r)], lst.sort)


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
