"""Lists: ready-made selections of trails, each a rule over a trail's attributes (olt/facets.py).

A list is defined once, here, as a test on a trail. No list names a trail by
id: membership follows the records, so a new trail or a new [hike] table moves
trails in and out of lists with no change to this file.

A list is shown (on the home page, on /lists/, and with a page of its own)
only when it is useful with today's trails:

    MIN_SIZE   at least this many trails (fewer reads as a gap, not a list)
    MAX_SHARE  at most this share of all trails (more is nearly everything)

Every list has its page at /lists/<key>/, except Routes, which keeps /routes/.
A list with a `noun` also has a page for each state or province where at least
MIN_SIZE of its trails are, and fewer than MAX_SHARE of that place's (olt/placefacets.py).
A list belongs to a `group` (GROUPS), the heading it sits under on /lists/.
"""
import contextlib
import re
from dataclasses import dataclass
from typing import Callable, Optional

from . import common, facets, hike, words

MIN_SIZE = 5
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
    # The heading it sits under on /lists/ (a key of GROUPS).
    group: str = ""
    # The words for this kind of trail in a place page's title: "Loop Hiking Trails" gives
    # "Loop Hiking Trails in Colorado: 6 Trails". Empty: no page for each place.
    noun: str = ""
    # (list's trails, all trails) -> a plain sentence or two that says what the list covers
    # where that is not every trail: how many have the fact the list is built on.
    note: Optional[Callable] = None
    # A larger least size than MIN_SIZE, where the list is thin by nature (a month's list).
    min_size: int = 0
    # False for a list that is one of a fixed set, so none may go missing: a month's list, however
    # many of the trails are walked in it, is not "nearly everything" but one of twelve.
    capped: bool = True

    def search_title(self, n):
        return (self.page_title or f"{self.title}: {{n}} Trails").format(n=n)


def _km(mi):
    return words.fmt_int(mi * words.KM_PER_MI)


def _band(key):
    return lambda r: facets.time_band(r) == key


# The terrain as an adjective, for a list's page title ("Coastal Hiking Trails").
TERRAIN_ADJECTIVE = {"coast": "Coastal", "lakes": "Lake"}

# The headings on /lists/, in order: (key, heading, one sentence under it).
GROUPS = (
    ("standing", "By standing", "What kind of trail it is: named by Congress, certified, or a route a hiker published."),
    ("length", "By length", "Trails sorted into length bands. Lengths are the published figures."),
    ("time", "By time to walk", "How long the whole trail usually takes, as a source states it or as estimated from the length."),
    ("walking", "By kind of walking", "Loops, high routes, walking with no trail, and trails not yet finished."),
    ("terrain", "By terrain", "The main kinds of country a trail crosses."),
    ("holder", "By who looks after it", "Trails whose designation names the holder."),
    ("month", "By month", "Trails normally hiked in the month. Estimated seasons are marked."),
    ("where", "By country and GPX", "Where a trail is, and whether its page has a track to download."),
)

# A month's list is shown with at least this many trails.
MONTH_MIN = 8

# Days: a weekend or a long weekend is up to four days.
WEEKEND_DAYS = 4


def _mid_days(rec):
    lo, hi, _ = facets.time_days(rec)
    return (lo + hi) / 2


def _mi(n):
    return round(words.km_to_mi(n))


def time_note(recs, records):
    """How many of a time list's trails have a time a source states, and how the rest were estimated."""
    est = sum(1 for r in recs if facets.time_days(r)[2])
    stated = len(recs) - est
    (a, b), (c, d) = facets.PACE_KM, facets.PACE_KM_CROSS
    how = (f"estimated from the length, at {_mi(a)} to {_mi(b)} miles a day, or {_mi(c)} to {_mi(d)} "
           f"where much of it is cross-country")
    if not est:
        return f"A source states the time for all {stated}."
    if not stated:
        return f"No source states the time for these, so each is {how}."
    return f"A source states the time for {stated} of these. For the other {est} it is {how}."


def _month_list(m):
    name = facets.MONTHS[m - 1]
    return List(f"hike-in-{name.lower()}", f"Hiking in {name}",
                f"Trails normally hiked in {name}. Estimated seasons are marked.",
                lambda r, m=m: m in facets.months(r),
                page_title=f"Long Trails to Hike in {name}: {{n}} Trails", group="month", note=month_note(name),
                min_size=MONTH_MIN, capped=False)


def month_note(name):
    def note(recs, records):
        unstated = [r for r in recs if facets.season_estimated(r)]
        est = len(unstated)
        stated = len(recs) - est
        if not est:
            return f"A source states the season for all {stated}."
        kinds = {facets.season_kind(r) for r in unstated}
        one = ("estimated from the climate and similar trails" if kinds == {"estimated"}
               else "set by judgement from pages that differ" if kinds == {"judged"} else "")
        if not stated:
            return (f"No source states the season for these, so each is {one}." if one
                    else f"No source states the season for these: {facets.season_unstated_clause(unstated)}.")
        if one:
            return f"A source states the season for {stated} of these. For the other {est} it is {one}, and marked."
        return (f"A source states the season for {stated} of these. For the other {est}, "
                f"{facets.season_unstated_clause(unstated)}, and marked.")
    return note


def _high_route(rec):
    text = " ".join((rec.get("name", ""), rec.get("common_name", ""), rec.get("designation", "")))
    return bool(re.search(r"\bhigh route\b", text, re.I))


def _designation(rx, routes=True):
    """A test on the designation field: it names the holder or the standing, as the record words it."""
    pattern = re.compile(rx, re.I)
    return lambda r: bool(pattern.search(r.get("designation", ""))) and (routes or facets.kind(r) != "route")


def _length_band(lo_mi, hi_mi):
    lo, hi = lo_mi * words.KM_PER_MI, hi_mi * words.KM_PER_MI
    return lambda r: lo <= r["length_km"] < hi


MID_MI = 200
MID_KM = MID_MI * words.KM_PER_MI
HALF_MI = 500
LISTS = (
    List("national-scenic-trails", "National Scenic Trails",
         "The long trails the United States Congress has named National Scenic Trails.",
         facets.is_national, page_title="National Scenic Trails: {n} Long Hiking Trails", group="standing"),
    List("national-recreation-trails", "National Recreation Trails",
         "Trails whose designation says they are National Recreation Trails.",
         _designation(r"National Recreation Trail"),
         page_title="National Recreation Trails: {n} Long Hiking Trails", group="standing"),
    List("routes", "Routes", facets.ROUTE_DEFINITION,
         lambda r: facets.kind(r) == "route", page_title="Long Hiking Routes by Author: {n} Routes",
         group="standing", noun="Long Hiking Routes"),
    List("high-routes", "High routes",
         "Routes whose own name says High Route: through high country, often off the trail.",
         _high_route, page_title="High Routes: {n} Long Hiking Routes", group="walking"),
    List("longest", "The longest",
         f"Trails of {LONG_MI:,} miles ({_km(LONG_MI)} km) or more.",
         lambda r: r["length_km"] >= LONG_KM, sort="length-desc",
         page_title=f"Longest Hiking Trails: {{n}} Trails of {LONG_MI:,}+ Miles", group="length"),
    List("500-to-1000-miles", f"{HALF_MI} to {LONG_MI:,} miles",
         f"Trails of {HALF_MI} miles ({_km(HALF_MI)} km) or more and shorter than {LONG_MI:,} miles ({_km(LONG_MI)} km).",
         _length_band(HALF_MI, LONG_MI), sort="length-desc",
         page_title=f"Hiking Trails of {HALF_MI} to {LONG_MI:,} Miles: {{n}} Long Trails", group="length",
         noun=f"Hiking Trails of {HALF_MI} to {LONG_MI:,} Miles"),
    List("200-to-500-miles", f"{MID_MI} to {HALF_MI} miles",
         f"Trails of {MID_MI} miles ({_km(MID_MI)} km) or more and shorter than {HALF_MI} miles ({_km(HALF_MI)} km).",
         _length_band(MID_MI, HALF_MI), sort="length-desc",
         page_title=f"Hiking Trails of {MID_MI} to {HALF_MI} Miles: {{n}} Long Trails", group="length",
         noun=f"Hiking Trails of {MID_MI} to {HALF_MI} Miles"),
    List("100-to-200-miles", f"{SHORT_MI} to {MID_MI} miles",
         f"Trails of {SHORT_MI} miles ({_km(SHORT_MI)} km) or more and shorter than {MID_MI} miles ({_km(MID_MI)} km).",
         _length_band(SHORT_MI, MID_MI), sort="length-desc",
         page_title=f"Hiking Trails of {SHORT_MI} to {MID_MI} Miles: {{n}} Long Trails", group="length",
         noun=f"Hiking Trails of {SHORT_MI} to {MID_MI} Miles"),
    List("under-100-miles", f"Under {SHORT_MI} miles",
         f"Trails shorter than {SHORT_MI} miles ({_km(SHORT_MI)} km).",
         lambda r: r["length_km"] < SHORT_KM, sort="length-asc",
         page_title=f"Hiking Trails Under {SHORT_MI} Miles: {{n}} Long Trails", group="length",
         noun=f"Hiking Trails Under {SHORT_MI} Miles"),
    List("under-200-miles", f"Under {MID_MI} miles",
         f"Trails shorter than {MID_MI} miles ({_km(MID_MI)} km): the two shortest bands together.",
         lambda r: r["length_km"] < MID_KM, sort="length-asc",
         page_title=f"Thru-Hikes Under {MID_MI} Miles: {{n}} Long Trails", group="length"),
    List("weekend", "A weekend or long weekend",
         f"Trails that take {WEEKEND_DAYS} days or fewer to walk whole.",
         lambda r: _mid_days(r) <= WEEKEND_DAYS, sort="time-asc",
         page_title="Long Trails to Hike in a Weekend: {n} Trails", group="time", note=time_note),
    List("a-week-or-less", "A week or less",
         "Trails most people walk in a week or less, as a source states it or as estimated from the length.",
         _band("week"), sort="time-asc", page_title="Long Trails to Hike in a Week or Less: {n} Trails",
         group="time", note=time_note),
    List("one-to-two-weeks", "One to two weeks",
         "Trails that take one to two weeks, as a source states it or as estimated from the length.",
         _band("two-weeks"), sort="time-asc", page_title="Long Trails to Hike in One to Two Weeks: {n} Trails",
         group="time", note=time_note),
    List("two-to-four-weeks", "Two weeks to a month",
         "Trails that take two to four weeks to walk whole.",
         _band("month"), sort="time-asc", page_title="Long Trails to Hike in 2 to 4 Weeks: {n} Trails",
         group="time", note=time_note),
    List("a-month-or-more", "A month or more",
         "Trails that take more than four weeks to walk whole.",
         lambda r: facets.time_band(r) in ("months", "long"), sort="time-asc",
         page_title="Long Trails That Take a Month or More: {n} Trails", group="time", note=time_note),
    List("loops", "Loops", "Trails that finish where they start.",
         lambda r: facets.shape(r) == "loop", page_title="Loop Hiking Trails: {n} Long Trail Loops",
         group="walking", noun="Loop Hiking Trails"),
    List("off-trail", "Cross-country",
         "Trails with stretches of walking where there is no trail.",
         lambda r: facets.walking(r) in facets.CROSS_COUNTRY,
         page_title="Cross-Country Hiking: {n} Long Trails and Routes", group="walking",
         noun="Cross-Country Hiking"),
    List("mostly-cross-country", "Mostly cross-country",
         "Trails where there is no trail for most of the way.",
         lambda r: facets.walking(r) == "mostly-cross-country",
         page_title="Mostly Cross-Country Hiking Routes: {n} Long Trails", group="walking"),
    List("unfinished", "Not yet finished",
         "Trails that are not complete on the ground.",
         lambda r: bool(hike.table(r).get("unfinished")),
         page_title="Unfinished Long Trails: {n} Trails Not Yet Complete", group="walking"),
    List("parks-canada", "Parks Canada",
         "Trails whose designation names Parks Canada.",
         _designation(r"Parks Canada"), page_title="Parks Canada Hiking Trails: {n} Long Trails", group="holder"),
    List("forest-service", "Forest Service",
         "Trails whose designation names the Forest Service.",
         _designation(r"Forest Service|USFS"), page_title="Forest Service Hiking Trails: {n} Long Trails",
         group="holder"),
    List("state-and-provincial-parks", "State and provincial parks",
         "Trails whose designation names a state or provincial park.",
         _designation(r"\b(state|provincial) parks?\b"),
         page_title="State and Provincial Park Trails: {n} Long Trails", group="holder"),
    List("clubs-and-associations", "Clubs and associations",
         "Trails, not routes, whose designation names a club, association, conservancy or similar group.",
         _designation(r"Association|Club|Conservancy|Alliance|Foundation|Society|Conference|Council|Trust",
                      routes=False),
         page_title="Trails Kept by Clubs and Associations: {n} Trails", group="holder"),
    List("with-gpx", "With a GPX to download",
         "Trails with a GPX file of the track on their page.",
         facets.gpx_here, page_title="Long Trails with a GPX to Download: {n} Trails", group="where",
         noun="Hiking Trails with a GPX"),
    List("canada", "In Canada", "Trails in Canada, or crossing into it.",
         lambda r: "CA" in common.countries(r), page_title="Hiking Trails in Canada: {n} Long Trails",
         group="where"),
    List("united-states", "In the United States", "Trails in the United States, or crossing into it.",
         lambda r: "US" in common.countries(r), page_title="Hiking Trails in the United States: {n} Long Trails",
         group="where"),
) + tuple(
    List(f"terrain-{t}", label, f"Trails with {t} among their main terrain.",
         lambda r, t=t: t in facets.terrain(r),
         page_title=f"{TERRAIN_ADJECTIVE.get(t, label)} Hiking Trails: {{n}} Long Trails", group="terrain",
         noun=f"{TERRAIN_ADJECTIVE.get(t, label)} Hiking Trails")
    for t, label in words.TERRAIN.items()
) + tuple(_month_list(m) for m in range(1, 13))


def members(lst, records):
    return facets.sort_records([r for r in records if lst.test(r)], lst.sort)


def is_shown(n, total, least=0, capped=True):
    """The threshold rule: a list is shown when it holds at least MIN_SIZE
    trails (or `least`, where the list asks for more) and no more than MAX_SHARE of all of them,
    unless it is not capped (the twelve month lists)."""
    return n >= max(MIN_SIZE, least) and (not capped or n <= MAX_SHARE * total)


_SHOWN_MEMO = None  # while a site is being rendered: {id(records): (records, shown)}


@contextlib.contextmanager
def remembering_shown():
    """Within this block shown() works each list of records out once. A site render asks
    for it from every state, place and list page; the records do not change meanwhile."""
    global _SHOWN_MEMO
    outer, _SHOWN_MEMO = _SHOWN_MEMO, {}
    try:
        yield
    finally:
        _SHOWN_MEMO = outer


def shown(records):
    """[(list, its trails)] for every list that passes is_shown, in LISTS order."""
    if _SHOWN_MEMO is not None:
        held = _SHOWN_MEMO.get(id(records))
        if held is not None and held[0] is records:
            return list(held[1])
    out = []
    for lst in LISTS:
        recs = members(lst, records)
        if is_shown(len(recs), len(records), lst.min_size, lst.capped):
            out.append((lst, recs))
    if _SHOWN_MEMO is not None:
        _SHOWN_MEMO[id(records)] = (records, out)
        return list(out)
    return out


def by_key(key):
    return next(lst for lst in LISTS if lst.key == key)


def facet_lists():
    """The lists that also have a page for each place (those with a noun)."""
    return [lst for lst in LISTS if lst.noun]


def path(lst):
    return "/routes/" if lst.key == "routes" else f"/lists/{lst.key}/"
