#!/usr/bin/env python3
"""Estimate a hiking season from climate, for trails no page gives one.

Python 3 standard library only. The rule is a pure function over monthly
normals (tools/season_climate.py does the downloading, cached outside
the repository), so its tests run with no network. See
docs/superpowers/specs/2026-11-20-season-on-every-trail-design.md.

A month is in season when the trail's high ground is normally free of
deep snow and not bitterly cold, and its low ground is not dangerously
hot: over the high-ground points (at or above the upper quartile of
the sample elevations), the median mean daily high is at least
cold_c_min and the median mean snow depth is at most snow_cm_max, and
over the low-ground points (at or below the median elevation) the
median mean daily high is at most heat_c_max. When no high-ground
point has a snow measure the snow test is dropped and the cold test
stands in for it. That gives alpine trails a summer season, desert
trails a winter one that wraps the year end, and mild trails all
twelve months. It cannot know that some trails are walked in snow by
choice; the fit against sourced seasons says how often that matters.

Commands are added by the plan's later tasks (fit, propose, check).
"""
import sys

sys.dont_write_bytecode = True

import statistics
from dataclasses import dataclass

RULE_VERSION = 1


@dataclass(frozen=True)
class SamplePoint:
    lat: float
    lon: float
    elev_m: float = None
    km: float = None


@dataclass(frozen=True)
class Params:
    snow_cm_max: float
    cold_c_min: float
    heat_c_max: float


def _usable(points):
    """The points as a list, or None when any point lacks data. A trail
    with a gap in its climate data is unestimable, never filled in."""
    if not points:
        return None
    got = list(points)
    for point in got:
        if point is None or len(getattr(point, "tmax_c", ()) or ()) != 12:
            return None
        if point.snow_cm is not None and len(point.snow_cm) != 12:
            return None
    return got


def _high_low(points):
    """Split points into high ground (at or above the upper quartile of
    the elevations, at least one point) and low ground (at or below
    the median). A single point is both."""
    elevs = sorted(p.elev_m for p in points)
    if len(elevs) == 1:
        return points, points
    upper = statistics.quantiles(elevs, n=4, method="inclusive")[2]
    median = statistics.median(elevs)
    high = [p for p in points if p.elev_m >= upper]
    low = [p for p in points if p.elev_m <= median]
    if not high:
        high = [max(points, key=lambda p: p.elev_m)]
    if not low:
        low = [min(points, key=lambda p: p.elev_m)]
    return high, low


def _median_at(points, month, attr):
    values = [getattr(p, attr)[month] for p in points
              if getattr(p, attr) is not None]
    if not values:
        return None
    return round(statistics.median(values), 1)


def _month_passes(high, low, month, params):
    high_tmax = _median_at(high, month, "tmax_c")
    if high_tmax is None or high_tmax < params.cold_c_min:
        return False
    snow = _median_at(high, month, "snow_cm")
    if snow is not None and snow > params.snow_cm_max:
        return False
    low_tmax = _median_at(low, month, "tmax_c")
    if low_tmax is None or low_tmax > params.heat_c_max:
        return False
    return True


def months_in_season(points, params):
    """Sorted month numbers in season, or None. None means either some
    point has no data or no month qualifies; why_not says which. An
    empty list is never returned."""
    got = _usable(points)
    if got is None:
        return None
    high, low = _high_low(got)
    months = [m + 1 for m in range(12) if _month_passes(high, low, m, params)]
    return months or None


def why_not(points, params):
    """Why months_in_season returned None, or "" when it did not."""
    got = _usable(points)
    if got is None:
        return "no data for one of the sample points"
    if months_in_season(got, params) is not None:
        return ""
    high, low = _high_low(got)
    cold_ok = sum(1 for m in range(12)
                  if (_median_at(high, m, "tmax_c") or -999) >= params.cold_c_min)
    snow_ok = sum(1 for m in range(12)
                  if (_median_at(high, m, "snow_cm") is None
                      or _median_at(high, m, "snow_cm") <= params.snow_cm_max))
    heat_ok = sum(1 for m in range(12)
                  if (_median_at(low, m, "tmax_c") or 999) <= params.heat_c_max)
    return (f"no month passes the cold, snow and heat tests together "
            f"(cold passes in {cold_ok} months, snow in {snow_ok}, "
            f"heat in {heat_ok})")
