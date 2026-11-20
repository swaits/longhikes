"""Season provenance checks for a trail record's [hike] table.

Python 3 standard library only. tools/validate.py imports this module; it
must not import validate.py. The fields are documented in docs/schema.md.
"""

BASES = ("primary", "sources", "source", "estimate")
PROVENANCE_KEYS = frozenset({"season_basis", "season_method"})
SEASON_REQUIRED = False


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

    if basis == "estimate":
        method = hike.get("season_method")
        if not isinstance(method, str) or not method.strip():
            errors.append(f"{tid}: hike.season_method is required with season_basis \"estimate\"")
        elif len(method) >= 400:
            errors.append(f"{tid}: hike.season_method must be under 400 characters")
    elif has_method:
        errors.append(f"{tid}: hike.season_method is only given with season_basis \"estimate\"")

    naming_season = _naming(sources, "season")
    if basis in ("primary", "source"):
        if not naming_season:
            errors.append(
                f"{tid}: hike.season_basis \"{basis}\" needs a [[hike.source]] naming season")
    elif basis == "sources":
        publishers = {str(s.get("publisher", "")).strip().casefold()
                      for s in naming_season if str(s.get("publisher", "")).strip()}
        if len(publishers) < 2:
            errors.append(
                f"{tid}: hike.season_basis \"sources\" needs two sources from different "
                "publishers naming season")
    elif basis == "estimate":
        naming = {id(s) for s in _naming(sources, "season") + _naming(sources, "months")}
        if len(naming) != 1:
            errors.append(
                f"{tid}: hike.season_basis \"estimate\" needs exactly one source naming "
                "season or months")
