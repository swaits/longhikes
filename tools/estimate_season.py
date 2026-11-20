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

import bisect
import json
import math
import os
import statistics
import tomllib
from dataclasses import dataclass, replace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import season_climate  # noqa: E402  (types and distance only; no network)

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


# ---------------------------------------------------------------------------
# Sample points from a record. Track pieces are joined and oriented with
# the same rule tools/elevation.py uses to build elevation.json (ends
# within 100 m join, the whole track runs south to north or west to
# east, parts in order along that axis, gaps between parts not counted
# in the distance), reimplemented here with the standard library only,
# so a sample point's kilometre matches the profile's kilometre and its
# elevation can be read from the profile.

EARTH_R_M = 6371008.8
JOIN_GAP_M = 100.0
LOOP_FRACTION = 0.1
SAMPLE_KM = 50.0
MIN_POINTS = 3
MAX_POINTS = 12


def _track_parts(data):
    if data.get("type") == "FeatureCollection":
        geoms = [(f.get("geometry") or {}) for f in data.get("features", [])]
    elif data.get("type") == "Feature":
        geoms = [data.get("geometry") or {}]
    else:
        geoms = [data]
    parts = []
    for geom in geoms:
        if geom.get("type") == "LineString":
            parts.append(geom["coordinates"])
        elif geom.get("type") == "MultiLineString":
            parts.extend(geom["coordinates"])
    return [[(float(c[0]), float(c[1])) for c in p] for p in parts if len(p) >= 2]


def _gap_m(a, b):
    dx = (a[0] - b[0]) * math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot(dx, a[1] - b[1]) * math.pi / 180.0 * EARTH_R_M


def _seg_km(a, b):
    return season_climate.haversine_km(a[1], a[0], b[1], b[0])


def _join_parts(parts, gap_m=JOIN_GAP_M):
    if not parts:
        return []
    cell = max(gap_m, 1.0)
    k = math.pi / 180.0 * EARTH_R_M
    max_lat = max(abs(c[1]) for p in parts for c in (p[0], p[-1]))
    scale = max(math.cos(math.radians(max_lat)), 1e-9) * k

    def cell_of(c):
        return (math.floor(c[0] * scale / cell), math.floor(c[1] * k / cell))

    grid = {}
    for i, p in enumerate(parts):
        for end in (0, 1):
            grid.setdefault(cell_of(p[0] if end == 0 else p[-1]), []).append((i, end))
    used = [False] * len(parts)

    def nearest(point):
        gx, gy = cell_of(point)
        best = None
        for x in (gx - 1, gx, gx + 1):
            for y in (gy - 1, gy, gy + 1):
                for i, end in grid.get((x, y), ()):
                    if used[i]:
                        continue
                    d = _gap_m(point, parts[i][0] if end == 0 else parts[i][-1])
                    if d <= gap_m and (best is None or d < best[0]):
                        best = (d, i, end)
        return best

    out = []
    for i0, first in enumerate(parts):
        if used[i0]:
            continue
        used[i0] = True
        chain = list(first)
        while True:
            hit = nearest(chain[-1])
            if hit is None:
                break
            _, i, end = hit
            used[i] = True
            chain.extend(parts[i] if end == 0 else parts[i][::-1])
        while True:
            hit = nearest(chain[0])
            if hit is None:
                break
            _, i, end = hit
            used[i] = True
            chain[:0] = parts[i][::-1] if end == 0 else parts[i]
        out.append(chain)
    return out


def _orient(chains):
    """Chains turned to run south to north or west to east and put in
    order along that axis, as tools/elevation.py does."""
    if not chains:
        return []
    lons = [c[0] for ch in chains for c in ch]
    lats = [c[1] for ch in chains for c in ch]
    mid_lat = (min(lats) + max(lats)) / 2.0
    width = (max(lons) - min(lons)) * math.cos(math.radians(mid_lat))
    axis = 1 if (max(lats) - min(lats)) > width else 0
    out = []
    for ch in chains:
        length_km = sum(_seg_km(a, b) for a, b in zip(ch, ch[1:]))
        if (_gap_m(ch[0], ch[-1]) > LOOP_FRACTION * length_km * 1000.0
                and ch[-1][axis] < ch[0][axis]):
            ch = ch[::-1]
        out.append(ch)
    out.sort(key=lambda ch: sum(c[axis] for c in ch) / len(ch))
    return out


def _ordered_track(path):
    """(vertices, cumulative km) along the joined, oriented track.
    The first vertex of each part sits at the same distance as the last
    vertex of the part before it: gaps are not counted."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    chains = _orient(_join_parts(_track_parts(data)))
    verts, cum = [], []
    total = 0.0
    for chain in chains:
        for j, vertex in enumerate(chain):
            if j:
                total += _seg_km(chain[j - 1], vertex)
            verts.append(vertex)
            cum.append(total)
    return verts, cum


def _point_at(verts, cum, target_km):
    i = bisect.bisect_right(cum, target_km) - 1
    i = max(0, min(i, len(verts) - 2))
    span = cum[i + 1] - cum[i]
    frac = 0.0 if span <= 0 else (target_km - cum[i]) / span
    frac = max(0.0, min(1.0, frac))
    lon = verts[i][0] + frac * (verts[i + 1][0] - verts[i][0])
    lat = verts[i][1] + frac * (verts[i + 1][1] - verts[i][1])
    if target_km >= cum[-1]:
        lon, lat = verts[-1]
    return lat, lon


def _profile_elev(profile, km):
    """Elevation in metres from an elevation.json profile at km."""
    if not profile:
        return None
    kms = [float(p[0]) for p in profile]
    i = bisect.bisect_right(kms, km) - 1
    if i < 0:
        return float(profile[0][1])
    if i >= len(profile) - 1:
        return float(profile[-1][1])
    km0, el0 = float(profile[i][0]), float(profile[i][1])
    km1, el1 = float(profile[i + 1][0]), float(profile[i + 1][1])
    if km1 <= km0:
        return el1
    return el0 + (km - km0) / (km1 - km0) * (el1 - el0)


def _load_profile(root, tid):
    path = os.path.join(root, tid, "elevation.json")
    if not os.path.exists(path):
        return None, None
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    return doc.get("profile") or None, (doc.get("highest") or None)


def _give_high_point(points, hike, highest):
    """With no profile, one point carries high_point_m so the high
    ground is represented at all: the point nearest the profile's
    highest place when that is known, else the first point."""
    high_m = hike.get("high_point_m")
    if high_m is None or not points:
        return points
    idx = 0
    if highest and highest.get("lat") is not None:
        idx = min(range(len(points)),
                  key=lambda i: season_climate.haversine_km(
                      points[i].lat, points[i].lon,
                      float(highest["lat"]), float(highest["lon"])))
    return [replace(p, elev_m=float(high_m)) if i == idx else p
            for i, p in enumerate(points)]


def sample_points(root, rec):
    """Sample points for a record and how they were got: "track" (one
    per 50 km of track, at least 3, at most 12, evenly spaced, with
    elevations from the profile), "ends" (hike.start_lonlat and
    hike.end_lonlat), or "place" (the centre of the first region's box
    in web/place-bounds.toml). An elevation of None lets the climate
    source supply its own cell elevation. With no profile, one point
    carries hike.high_point_m when the record has one."""
    tid = rec.get("id") or ""
    hike = rec.get("hike") or {}
    line_file = (rec.get("source") or {}).get("line_file") or "line.geojson"
    line_path = os.path.join(root, tid, line_file)
    if tid and os.path.exists(line_path):
        try:
            verts, cum = _ordered_track(line_path)
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            verts, cum = [], []
        if len(verts) >= 2 and cum and cum[-1] > 0:
            total = cum[-1]
            n = min(MAX_POINTS, max(MIN_POINTS, int(round(total / SAMPLE_KM)) + 1))
            profile, highest = _load_profile(root, tid)
            points = []
            for i in range(n):
                target = total * i / (n - 1)
                lat, lon = _point_at(verts, cum, target)
                elev = _profile_elev(profile, target)
                points.append(SamplePoint(lat=lat, lon=lon, elev_m=elev,
                                          km=round(target, 2)))
            if not profile:
                points = _give_high_point(points, hike, highest)
            return points, "track"

    ends = []
    for key in ("start_lonlat", "end_lonlat"):
        value = hike.get(key)
        if value and len(value) == 2:
            ends.append(SamplePoint(lat=float(value[1]), lon=float(value[0]),
                                    elev_m=None, km=None))
    if ends:
        if hike.get("high_point_m") is not None:
            ends[0] = replace(ends[0], elev_m=float(hike["high_point_m"]))
        return ends, "ends"

    regions = rec.get("regions") or []
    country = rec.get("country") or ""
    bounds_path = os.path.join(root, "web", "place-bounds.toml")
    if regions and os.path.exists(bounds_path):
        with open(bounds_path, "rb") as f:
            boxes = (tomllib.load(f) or {}).get("box") or {}
        box = boxes.get(f"{country}-{regions[0]}")
        if box is None:
            for key, value in boxes.items():
                if key.endswith("-" + str(regions[0])):
                    box = value
                    break
        if box and len(box) == 4:
            elev = hike.get("high_point_m")
            return [SamplePoint(lat=(float(box[1]) + float(box[3])) / 2,
                                 lon=(float(box[0]) + float(box[2])) / 2,
                                 elev_m=None if elev is None else float(elev),
                                 km=None)], "place"
    return [], "place"
