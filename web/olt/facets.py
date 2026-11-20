"""The attributes a hiker sees for a trail, each with one name used on every page.

    Where    the states and provinces, grouped into places (PLACE_GROUPS)
    Length   length_km
    Time     [hike].days as a source states it, else an estimate from the length
    Season   [hike].months (the phrase on the trail page is [hike].season)
    Terrain  [hike].terrain
    Kind     official trail, or route (the [route] table)
    Walking  [hike].travel
    Shape    [hike].shape
    GPX      one status per trail, from the track and, for a route, its author's terms
    Designation  National Scenic Trail (tier "national"), shown as a badge

Every value here is computed from the records by rule. Nothing names a trail.
The dataset's own terms (tier, wave, source status, track policy) are not
attributes a hiker filters by; they stay in "About this data" on each trail
page and on the pages under About.
"""
import math
import re
from functools import cmp_to_key

from . import common, elevation, hike, words
from .markup import Markup

# Facet names, exactly as every page shows them.
WHERE, LENGTH, TIME, SEASON, TERRAIN, KIND, WALKING, SHAPE, GPX = (
    "Where", "Length", "Time", "Season", "Terrain", "Kind", "Walking", "Shape", "GPX")

# A facet a trail may have no value for is offered as a filter only when at
# least this share of all trails has a value.
COVERAGE_MIN = 1 / 3

# Where ----------------------------------------------------------------------

# (key, name, [region keys]). Every state, province and territory code is in
# exactly one group (test_facets checks it against words.US_STATES and
# words.CA_PROVINCES, and against every code the records use).
PLACE_GROUPS = (
    ("west-coast", "West Coast", ["US-WA", "US-OR", "US-CA", "US-HI"]),
    ("mountain-west", "Mountain West", ["US-ID", "US-MT", "US-WY", "US-NV", "US-UT", "US-CO"]),
    ("southwest", "Southwest", ["US-AZ", "US-NM", "US-TX", "US-OK"]),
    ("midwest", "Midwest", ["US-ND", "US-SD", "US-NE", "US-KS", "US-MN", "US-IA", "US-MO",
                            "US-WI", "US-IL", "US-MI", "US-IN", "US-OH"]),
    ("south", "South", ["US-AR", "US-LA", "US-MS", "US-AL", "US-TN", "US-KY", "US-GA",
                        "US-FL", "US-SC", "US-NC"]),
    ("mid-atlantic", "Mid-Atlantic", ["US-NY", "US-NJ", "US-PA", "US-DE", "US-MD", "US-DC",
                                      "US-VA", "US-WV"]),
    ("new-england", "New England", ["US-CT", "US-RI", "US-MA", "US-VT", "US-NH", "US-ME"]),
    ("north", "Alaska and the North", ["US-AK", "CA-YT", "CA-NT", "CA-NU"]),
    ("western-canada", "Western Canada", ["CA-BC", "CA-AB", "CA-SK", "CA-MB"]),
    ("central-canada", "Central Canada", ["CA-ON", "CA-QC"]),
    ("atlantic-canada", "Atlantic Canada", ["CA-NB", "CA-NS", "CA-PE", "CA-NL"]),
)
GROUP_OF = {key: g for g, _, keys in PLACE_GROUPS for key in keys}
GROUP_NAME = {g: name for g, name, _ in PLACE_GROUPS}
# A trail that names "all provinces and territories" crosses Canada: it is in
# every Canadian group, but on no single province's page.
ACROSS_CANADA = "CA-*"
ACROSS_CANADA_NAME = "Across Canada"


def place_keys(rec):
    """The trail's states and provinces as keys ("US-AZ", "CA-ON", "CA-*"), in record order."""
    out = []
    for code in rec.get("regions", []):
        key = words.region_key(code, rec["country"])
        if key not in out:
            out.append(key)
    return out


def place_groups(rec):
    """The place groups a trail is in, in PLACE_GROUPS order."""
    keys = set(place_keys(rec))
    found = {GROUP_OF[k] for k in keys if k in GROUP_OF}
    if ACROSS_CANADA in keys:
        found |= {GROUP_OF[k] for k in GROUP_OF if k.startswith("CA-")}
    return [g for g, _, _ in PLACE_GROUPS if g in found]


def place_name(key):
    """"US-AZ" -> "Arizona"; "CA-*" -> "Across Canada"."""
    if key == ACROSS_CANADA:
        return ACROSS_CANADA_NAME
    return words.region_name(key.split("-", 1)[1])


def place_path(key):
    """The page of a state or province (the /regions/ URLs are kept)."""
    if key == ACROSS_CANADA:
        return "/regions/#across-canada"
    return f"/regions/{key.lower()}/"


def where_tokens(rec):
    """Every Where value a trail matches: its countries, states and provinces, and groups."""
    return common.countries(rec) + place_keys(rec) + ["g:" + g for g in place_groups(rec)]


# Time -----------------------------------------------------------------------

PACE_KM = (20, 30)              # km a day on trail
PACE_KM_CROSS = (12, 20)        # km a day where much of it is cross-country
CROSS_COUNTRY = ("some-cross-country", "mostly-cross-country")

# (key, label, most days). A trail falls in the band of the middle of its range.
TIME_BANDS = (
    ("week", "A week or less", 7),
    ("two-weeks", "One to two weeks", 14),
    ("month", "Two to four weeks", 28),
    ("months", "One to three months", 91),
    ("long", "More than three months", math.inf),
)
TIME_LABEL = {k: label for k, label, _ in TIME_BANDS}


def pace(rec):
    return PACE_KM_CROSS if hike.table(rec).get("travel") in CROSS_COUNTRY else PACE_KM


def time_days(rec):
    """(fewest, most, estimated): the days to walk it all. As a source states it in
    [hike].days; otherwise estimated from the length at pace(rec) km a day."""
    stated = hike.table(rec).get("days")
    if isinstance(stated, (int, float)):
        stated = [stated]
    stated = [d for d in (stated or []) if isinstance(d, (int, float)) and d > 0]
    if stated:
        return min(stated), max(stated), False
    slow, fast = pace(rec)
    km = rec["length_km"]
    return max(1, math.ceil(km / fast)), max(1, math.ceil(km / slow)), True


def time_band(rec):
    lo, hi, _ = time_days(rec)
    mid = (lo + hi) / 2
    for key, _, most in TIME_BANDS:
        if mid <= most:
            return key
    return TIME_BANDS[-1][0]


def time_text(rec):
    """"5 to 7 months"; "About 2 to 3 weeks" when estimated."""
    lo, hi, est = time_days(rec)
    text = words.fmt_days([lo, hi])
    if est and not text.startswith("about"):
        text = "about " + text
    return text[:1].upper() + text[1:]


def estimate_note(rec):
    """Says how an estimated time was worked out; "" when a source states it."""
    if not time_days(rec)[2]:
        return ""
    slow, fast = pace(rec)
    mi = f"{round(words.km_to_mi(slow))} to {round(words.km_to_mi(fast))} mi"
    return Markup(f'Estimated from the length, at <span class="len len--inline"><span class="len__mi">{mi}</span>'
                  f'<span class="len__km">{slow} to {fast} km</span></span> a day.')


# Season ---------------------------------------------------------------------

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December")


def months(rec):
    m = hike.table(rec).get("months")
    return sorted({x for x in (m or []) if isinstance(x, int) and 1 <= x <= 12})


def season_estimated(rec):
    """True when no page states the season: it was estimated (season_basis "estimate"), or set by
    judgement from pages that differ (it carries a season_method). Such a season reads "About"."""
    h = hike.table(rec)
    return bool(h.get("season")) and (h.get("season_basis") == "estimate" or bool((h.get("season_method") or "").strip()))


def season_phrase(rec):
    """The phrase on the trail page as the record gives it: [hike].season, else built from the months."""
    phrase = (hike.table(rec).get("season") or "").strip()
    if phrase:
        return phrase[:1].upper() + phrase[1:]
    ms = months(rec)
    if not ms:
        return ""
    if len(ms) == 12:
        return "All year"
    return words.join_names(MONTHS[m - 1] for m in ms)


def season_text(rec):
    """The season as a page shows it: the phrase, or "About ..." where it is estimated, so an
    estimate never reads as a stated fact ("About June to September", "About all year")."""
    phrase = season_phrase(rec)
    if not phrase or not season_estimated(rec):
        return phrase
    if phrase.lower().startswith("about"):
        return phrase
    if phrase.lower() == "all year":
        phrase = phrase.lower()
    return "About " + phrase


def season_kind(rec):
    """How the season is known: "stated" (a page states it), "judged" (set by judgement from pages
    that differ), "estimated" (no page states one), or "" when the trail has no season."""
    if not hike.table(rec).get("season"):
        return ""
    if not season_estimated(rec):
        return "stated"
    return "judged" if season_basis(rec) == "sources" else "estimated"


SEASON_CONFIDENCE = re.compile(r"\s*Confidence: (high|medium|low)\.\s*$")
JUDGED_LEAD = "Judged from the climate at the trail's elevation and from similar trails."


def season_confidence(rec):
    """"high", "medium" or "low" from the end of the season's method; "" when it names none."""
    found = SEASON_CONFIDENCE.search(hike.table(rec).get("season_method") or "")
    return found.group(1) if found else ""


def season_reason(rec):
    """What the season's method says sets the season, without its standard first sentence and its
    closing confidence."""
    text = SEASON_CONFIDENCE.sub("", (hike.table(rec).get("season_method") or "").strip()).strip()
    if text.startswith(JUDGED_LEAD):
        text = text[len(JUDGED_LEAD):].strip()
    return text


def season_pages_differ(rec):
    """True for a season set by judgement from pages that state different seasons."""
    return season_estimated(rec) and season_basis(rec) == "sources"


def season_note(rec):
    """Says an estimated season is not a page's statement, how it was worked out, what sets it
    there and how far to trust it; "" when a page states the season."""
    if not season_estimated(rec):
        return ""
    reason = season_reason(rec)
    if season_pages_differ(rec):
        lead = "No one page states this season."
    else:
        lead = ("No page states a season. This is estimated from the climate at the trail's "
                "elevation and from similar trails.")
    parts = [lead]
    if reason:
        parts.append(reason)
    conf = season_confidence(rec)
    if conf:
        parts.append(f"Confidence: {conf}.")
    parts.append("People do walk it outside these months.")
    return " ".join(parts)


SEASON_BASIS_TEXT = {
    "primary": "The season comes from the page of the body that manages the trail or the trail's own association or, for a route, its author.",
    "sources": "Two or more pages from different publishers agree on the season.",
    "source": "One page states the season. It is not the trail's own page.",
}


def season_basis(rec):
    """Where the season came from: primary, sources, source or estimate; "" when it has none."""
    h = hike.table(rec)
    if not h.get("season") and not h.get("months"):
        return ""
    return h.get("season_basis") or ""


def season_basis_line(rec):
    """One sentence for "About this data"; "" when the season has no recorded basis."""
    basis = season_basis(rec)
    if not season_estimated(rec):
        return SEASON_BASIS_TEXT.get(basis, "")
    method = (hike.table(rec).get("season_method") or "").strip()
    if season_pages_differ(rec):
        return (method + " It is a judgement, not any one page's statement.").strip()
    return (method + " No page states a season.").strip()


# Terrain, Walking, Shape ----------------------------------------------------

TERRAIN_VALUES = words.TERRAIN
WALKING_VALUES = {
    "trail": "On trail",
    "trail-and-road": "Trail and road",
    "some-cross-country": "Some cross-country",
    "mostly-cross-country": "Mostly cross-country",
}
WALKING_HINT = {
    "trail": "On built or maintained trail all or nearly all the way",
    "trail-and-road": "Trail, with long stretches on roads",
    "some-cross-country": "Mostly trail or road, with stretches that have no trail",
    "mostly-cross-country": "No trail for most of the way",
}
SHAPES = {"point-to-point": "End to end", "loop": "Loop", "network": "Network"}


def terrain(rec):
    return hike.terrain(rec)


def walking(rec):
    v = hike.table(rec).get("travel", "")
    return v if v in WALKING_VALUES else ""


def shape(rec):
    v = hike.shape(rec)
    return v if v in SHAPES else ""


# Kind -----------------------------------------------------------------------

KINDS = {"trail": "Official trail", "route": "Route"}
ROUTE_DEFINITION = ("A route is a trail that a hiker worked out and published. No agency or "
                    "association looks after it as one trail, and there may be no signs for it.")


def kind(rec):
    return "route" if common.is_route(rec) else "trail"


def route_by(rec):
    """"Route by Andrew Skurka, 2018"; "" for an official trail."""
    if not common.is_route(rec):
        return ""
    r = rec.get("route", {})
    who = r.get("creator", "")
    if not who:
        return "Route"
    return f"Route by {who}" + (f", {r['year']}" if r.get("year") else "")


def author(rec):
    return rec.get("route", {}).get("creator", "") if common.is_route(rec) else ""


def is_national(rec):
    return rec.get("tier") == "national"


# GPX ------------------------------------------------------------------------

# The same six, as short as a filter row needs: one line each beside its count.
GPX_FILTER = {
    "here": "GPX here",
    "partial": "Partial GPX here",
    "free": "Free from the author",
    "sold": "Sold by the author",
    "unpublished": "Not published",
    "elsewhere": "On the official site",
}
GPX_STATUS = {
    "here": "GPX to download here",
    "partial": "Partial GPX to download here",
    "free": "Free from its author",
    "sold": "Sold by its author",
    "unpublished": "Not published",
    "elsewhere": "Not here, see the official site",
}
# The short form in a list row.
GPX_SHORT = {
    "here": "GPX here",
    "partial": "Partial GPX here",
    "free": "Free from its author",
    "sold": "Sold by its author",
    "unpublished": "Not published",
    "elsewhere": "See the official site",
}


def gpx(rec):
    """The trail's one GPX status (a key of GPX_STATUS)."""
    if common.has_line(rec):
        return "partial" if common.line_short(rec) else "here"
    if common.is_route(rec):
        return {"open": "free", "sold": "sold", "withheld": "unpublished"}.get(common.policy(rec), "elsewhere")
    return "elsewhere"


def gpx_status_text(rec):
    """GPX_STATUS for the trail's page. A route sold only as a book or map set has no GPX to sell, so
    it is not "Sold by its author" as a GPX is."""
    status = gpx(rec)
    if status == "sold" and not common.sells_gpx(rec):
        return "Not here, sold as a guide"
    if status == "elsewhere":
        # What the page really offers is read from the same link the page's button uses.
        from . import trail
        return {"guide": "Not here, see the guide", "": "Not here"}.get(trail.see_kind(rec),
                                                                       GPX_STATUS[status])
    return GPX_STATUS[status]


def gpx_here(rec):
    return gpx(rec) in ("here", "partial")


# Coverage -------------------------------------------------------------------

# facet key -> (name, the trail's values: a list, empty when it has none)
OPTIONAL = {
    "season": (SEASON, months),
    "terrain": (TERRAIN, terrain),
    "walking": (WALKING, lambda r: [walking(r)] if walking(r) else []),
    "shape": (SHAPE, lambda r: [shape(r)] if shape(r) else []),
}
# The noun for "12 trails have no ... on file".
MISSING_NOUN = {"season": "season", "terrain": "terrain", "walking": "walking", "shape": "shape"}


def coverage(records, key):
    """(trails with a value, trails without) for an optional facet."""
    fn = OPTIONAL[key][1]
    have = sum(1 for r in records if fn(r))
    return have, len(records) - have


def offered(records, key):
    """True when the facet is offered as a filter: at least COVERAGE_MIN of trails have a value."""
    have, _ = coverage(records, key)
    return bool(records) and have >= COVERAGE_MIN * len(records)


def missing_text(n, key):
    """"12 trails have no season on file."; "" for none."""
    if not n:
        return ""
    return f"{n} trail{'s' if n != 1 else ''} {'has' if n == 1 else 'have'} no {MISSING_NOUN[key]} on file."


# Sorting ----------------------------------------------------------------------
# The one definition of each list order. app.js holds the same orders over the
# rows' data-* attributes; test_sorting checks the two agree.

SORTS = (
    ("name", "Name, A to Z"),
    ("name-desc", "Name, Z to A"),
    ("length-desc", "Length, longest first"),
    ("length-asc", "Length, shortest first"),
    ("time-asc", "Time, quickest first"),
    ("time-desc", "Time, slowest first"),
    ("climb-desc", "Climb, most first"),
    ("climb-asc", "Climb, least first"),
)
SORT_LABEL = dict(SORTS)
# Keys older addresses used, still honoured.
OLD_SORTS = {"long": "length-desc", "short": "length-asc",
             "quick": "time-asc", "climb": "climb-desc"}


def sort_name(rec):
    return re.sub(r"^The ", "", rec["name"]).lower()


def normalize_sort(key, default="name"):
    """A sort key from SORTS: key itself, its modern spelling, else default."""
    if key in SORT_LABEL:
        return key
    if key in OLD_SORTS:
        return OLD_SORTS[key]
    return default if default in SORT_LABEL else "name"


def row_climb_m(rec):
    """The climb a list row may show and sort by, in metres, or None.

    A climb from a track that covers only part of the trail, or more than
    the trail, would mislead in a list, so it counts as no climb here.
    """
    elev = elevation.get(rec)
    if elev and elevation.coverage_kind(elev):
        return None
    return elev["ascent_m"] if elev else None


def sort_values(rec):
    """(name, km, days, climb) exactly as the row's data-* attributes carry them."""
    return (sort_name(rec), rec["length_km"], time_days(rec)[1], row_climb_m(rec))


def _cmp(a, b):
    return (a > b) - (a < b)


def compare_values(va, vb, key):
    """Order two sort_values tuples under key. Ties fall back to name;
    a trail with no climb goes last in both climb orders."""
    key = normalize_sort(key)
    if key == "name":
        return _cmp(va[0], vb[0])
    if key == "name-desc":
        return _cmp(vb[0], va[0])
    if key.startswith("climb"):
        ca, cb = va[3], vb[3]
        if ca is None or cb is None:
            if ca is None and cb is None:
                return _cmp(va[0], vb[0])
            return 1 if ca is None else -1
        order = _cmp(cb, ca) if key == "climb-desc" else _cmp(ca, cb)
        return order or _cmp(va[0], vb[0])
    i = 1 if key.startswith("length") else 2
    order = _cmp(vb[i], va[i]) if key.endswith("-desc") else _cmp(va[i], vb[i])
    return order or _cmp(va[0], vb[0])


def sort_records(records, key="name"):
    """The records in the order key names, as a new list."""
    key = normalize_sort(key)
    values = {id(r): sort_values(r) for r in records}
    return sorted(records, key=cmp_to_key(lambda a, b: compare_values(values[id(a)], values[id(b)], key)))
