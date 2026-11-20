"""Season provenance checks for a trail record's [hike] table.

Python 3 standard library only. tools/validate.py imports this module; it
must not import validate.py. The fields are documented in docs/schema.md.
"""

import re
import urllib.parse

BASES = ("primary", "sources", "source", "estimate")
PROVENANCE_KEYS = frozenset({"season_basis", "season_method"})
SEASON_REQUIRED = True
# The host of the climate data an estimate cites (tools/season_climate.SOURCE).
CLIMATE_HOSTS = frozenset({"www.chelsa-climate.org"})
CONFIDENCES = ("high", "medium", "low")
_CONFIDENCE_END = re.compile(r"Confidence: (high|medium|low)\.\s*$")


def _is_climate(source):
    host = urllib.parse.urlparse(str(source.get("url", ""))).hostname
    return host in CLIMATE_HOSTS


def confidence_of(method):
    """"high", "medium" or "low" from the end of a season_method, else ""."""
    found = _CONFIDENCE_END.search(str(method or ""))
    return found.group(1) if found else ""


def read_from_a_page(hike):
    """True when a page states the season: one is present, its basis is not
    "estimate", and no method records that it was worked out by judgement
    (the seasons set from pages that disagree carry one)."""
    return bool(hike.get("season")) and hike.get("season_basis") in (
        "primary", "sources", "source") and not hike.get("season_method")


def check_present(tid, rec, errors):
    """Every record has a hike table (check_season then requires its season)."""
    if not isinstance(rec.get("hike"), dict):
        errors.append(f"{tid}: hike.season is required")


def _naming(sources, fact):
    return [s for s in sources if isinstance(s, dict) and fact in (s.get("facts") or [])]


def check_season(tid, hike, errors):
    """Check season, months, season_basis and season_method agree."""
    has_season = "season" in hike
    has_months = "months" in hike
    has_basis = "season_basis" in hike
    has_method = "season_method" in hike
    basis = hike.get("season_basis")
    sources = hike.get("source") or []
    if not isinstance(sources, list):
        sources = []

    if has_season != has_months:
        errors.append(f"{tid}: hike.season and hike.months must appear together")
    if not has_season:
        if SEASON_REQUIRED:
            errors.append(f"{tid}: hike.season is required")
        if has_basis:
            errors.append(f"{tid}: hike.season_basis must not be given without hike.season")
        if has_method:
            errors.append(f"{tid}: hike.season_method must not be given without hike.season")
        return

    if not has_basis:
        errors.append(f"{tid}: hike.season_basis is required when hike.season is present")
    elif basis not in BASES:
        errors.append(
            f"{tid}: hike.season_basis must be one of {', '.join(BASES)}, not {basis!r}")

    if has_method:
        method = hike.get("season_method")
        if basis not in ("estimate", "sources"):
            errors.append(
                f"{tid}: hike.season_method is only given with season_basis \"estimate\" "
                "or \"sources\"")
        elif not isinstance(method, str) or not method.strip():
            errors.append(f"{tid}: hike.season_method must not be empty")
        elif len(method) >= 400:
            errors.append(f"{tid}: hike.season_method must be under 400 characters")
        elif basis == "estimate" and not _CONFIDENCE_END.search(method):
            errors.append(
                f"{tid}: hike.season_method of an estimate must end with "
                "\"Confidence: high.\", \"Confidence: medium.\" or \"Confidence: low.\"")
    elif basis == "estimate":
        errors.append(f"{tid}: hike.season_method is required with season_basis \"estimate\"")

    if basis == "estimate" and has_months and isinstance(hike.get("months"), list):
        try:
            if hike.get("season") != phrase_for(hike["months"]):
                errors.append(f"{tid}: the season phrase of an estimate must be built from its "
                              f"months: {phrase_for(hike['months'])!r}")
        except (ValueError, TypeError):
            errors.append(f"{tid}: hike.months must be month numbers 1 to 12")

    naming_season = _naming(sources, "season")
    if basis != "estimate" and any(_is_climate(x) for x in naming_season):
        errors.append(
            f"{tid}: a source naming season may not cite climate data unless "
            "hike.season_basis is \"estimate\"")
    if basis in ("primary", "source"):
        if not naming_season:
            errors.append(
                f"{tid}: hike.season_basis \"{basis}\" needs a [[hike.source]] naming season")
        elif basis == "source":
            publishers = {str(s.get("publisher", "")).strip().casefold()
                          for s in naming_season}
            if len(publishers) != 1:
                errors.append(
                    f"{tid}: hike.season_basis \"source\" needs exactly one publisher "
                    "naming season (two or more is \"sources\")")
    elif basis == "sources":
        publishers = {str(s.get("publisher", "")).strip().casefold()
                      for s in naming_season if str(s.get("publisher", "")).strip()}
        if not naming_season:
            errors.append(
                f"{tid}: hike.season_basis \"sources\" needs a [[hike.source]] naming season")
        elif has_method:
            pass  # set by judgement from pages that differ; they may share a publisher
        elif len(publishers) < 2:
            errors.append(
                f"{tid}: hike.season_basis \"sources\" needs two sources from different "
                "publishers naming season")
    elif basis == "estimate":
        naming = {id(x): x for x in _naming(sources, "season") + _naming(sources, "months")}
        if len(naming) != 1:
            errors.append(
                f"{tid}: hike.season_basis \"estimate\" needs exactly one source naming "
                "season or months, and it must cite the climate data (no page states a season)")
        else:
            only = next(iter(naming.values()))
            facts = only.get("facts") or []
            if not _is_climate(only):
                errors.append(
                    f"{tid}: hike.season_basis \"estimate\" needs its source to cite the "
                    "climate data (CHELSA, with ETOPO); an ordinary page naming the season "
                    "makes the basis wrong")
            if "season" not in facts or "months" not in facts:
                errors.append(
                    f"{tid}: the climate source of an estimate must name both season and months")


# ---------------------------------------------------------------------------
# Shared helpers for the checker and the estimator. Months are a set on a
# circle: a season may wrap the year end (November to March), so spans,
# grades and phrases are all circular.

MONTH_NAMES = ("January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December")


def _months(months):
    got = sorted({int(m) for m in months})
    if not got or got[0] < 1 or got[-1] > 12:
        raise ValueError(f"not a set of months: {months!r}")
    return got


def span(months):
    """The smallest circular arc covering the months, as (first, last).

    December to February is one arc, (12, 2). Two separate windows give the
    arc covering both. All twelve months give (1, 12).
    """
    got = _months(months)
    if len(got) == 1:
        return (got[0], got[0])
    best_gap, first = -1, got[0]
    for i, month in enumerate(got):
        nxt = got[(i + 1) % len(got)]
        gap = (nxt - month) % 12
        if gap == 0:
            gap = 12
        # The arc starts after the largest gap. Ties go to the gap whose
        # following month is smallest, so all twelve months give (1, 12).
        if gap > best_gap or (gap == best_gap and nxt < first):
            best_gap, first = gap, nxt
    i = got.index(first)
    return (first, got[i - 1])


def _circ_distance(a, b):
    d = abs(a - b)
    return min(d, 12 - d)


def grade(estimated, sourced):
    """How well an estimated season matches a sourced one.

    "exact" when the arcs have the same first and last month, "within1"
    when each end is within one month (counted on the circle), else "worse".
    """
    if not estimated or not sourced:
        return "worse"
    est_first, est_last = span(estimated)
    src_first, src_last = span(sourced)
    if (est_first, est_last) == (src_first, src_last):
        return "exact"
    if (_circ_distance(est_first, src_first) <= 1
            and _circ_distance(est_last, src_last) <= 1):
        return "within1"
    return "worse"


def phrase_for(months):
    """The plain season phrase built from months, for an estimate.

    One run reads "June to September", a run over the year end reads
    "November to March", separate runs are joined with "and", one month
    reads "July" and twelve read "All year". Separate runs come in calendar
    order, so spring and fall read "March to May and October to November".
    """
    got = _months(months)
    if len(got) == 12:
        return "All year"
    runs = []
    start = prev = got[0]
    for month in got[1:]:
        if month == prev + 1:
            prev = month
        else:
            runs.append((start, prev))
            start = prev = month
    runs.append((start, prev))
    if len(runs) > 1 and runs[0][0] == 1 and runs[-1][1] == 12:
        runs = [(runs[-1][0], runs[0][1])] + runs[1:-1]
    # calendar order, except that a run over the year end comes first
    runs.sort(key=lambda run: (run[0] <= run[1], run[0]))

    def words(run):
        a, b = run
        if a == b:
            return MONTH_NAMES[a - 1]
        return f"{MONTH_NAMES[a - 1]} to {MONTH_NAMES[b - 1]}"

    return " and ".join(words(run) for run in runs)


def method_sentence(dataset, period, n_points, kind, rule_version):
    """The one fixed sentence an estimated season carries as its method."""
    where = {
        "track": "along the track",
        "ends": "at the trail ends",
        "place": "at the place centre",
    }.get(kind, kind)
    noun = "point" if n_points == 1 else "points"
    return (f"Estimated from {dataset} monthly climate ({period}) at "
            f"{n_points} {noun} {where}; rule version {rule_version}.")
