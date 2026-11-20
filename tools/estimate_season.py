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

Commands: fit (tune and record the thresholds), trial (compare the
climate candidates), propose (the review list), proposals (stage
accepted estimates for the refresh pipeline) and check (rerun
every estimate and the fit).
"""
import sys

sys.dont_write_bytecode = True

import argparse
import bisect
import csv
import datetime
import hashlib
import json
import math
import os
import statistics
import tomllib
from dataclasses import dataclass, replace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import refresh  # noqa: E402
import season  # noqa: E402
import season_batches  # noqa: E402
import season_climate  # noqa: E402

ROOT = os.path.dirname(HERE)

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


def _medians(points):
    """Per-month medians the rule compares: (high-ground mean daily
    high, high-ground snow depth, low-ground mean daily high), each a
    tuple of twelve rounded to a tenth, snow entries None where no
    high-ground point has a snow measure. None when a point lacks
    data. Precomputing these once per trail is what makes the grid
    search cheap."""
    got = _usable(points)
    if got is None:
        return None
    high, low = _high_low(got)
    return (
        tuple(_median_at(high, m, "tmax_c") for m in range(12)),
        tuple(_median_at(high, m, "snow_cm") for m in range(12)),
        tuple(_median_at(low, m, "tmax_c") for m in range(12)),
    )


def _months_from(medians, params):
    high_tmax, high_snow, low_tmax = medians
    out = []
    for m in range(12):
        if high_tmax[m] is None or high_tmax[m] < params.cold_c_min:
            continue
        if high_snow[m] is not None and high_snow[m] > params.snow_cm_max:
            continue
        if low_tmax[m] is None or low_tmax[m] > params.heat_c_max:
            continue
        out.append(m + 1)
    return out


def months_in_season(points, params):
    """Sorted month numbers in season, or None. None means either some
    point has no data or no month qualifies; why_not says which. An
    empty list is never returned."""
    medians = _medians(points)
    if medians is None:
        return None
    return _months_from(medians, params) or None


def why_not(points, params):
    """Why months_in_season returned None, or "" when it did not."""
    medians = _medians(points)
    if medians is None:
        return "no data for one of the sample points"
    if _months_from(medians, params):
        return ""
    high_tmax, high_snow, low_tmax = medians
    cold_ok = sum(1 for v in high_tmax if v is not None and v >= params.cold_c_min)
    snow_ok = sum(1 for v in high_snow if v is None or v <= params.snow_cm_max)
    heat_ok = sum(1 for v in low_tmax if v is not None and v <= params.heat_c_max)
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


# ---------------------------------------------------------------------------
# Fitting the three thresholds against the sourced seasons. The rule is
# tuned on the sourced trails whose id hashes even and reported on the
# ones that hash odd (held out), then the shipped numbers are refit on
# all of them. Estimates may ship only over the owner's bar, held here
# in one place.

BAR = {"within1_min": 0.75, "coverage_min": 0.90}

DEFAULT_GRID = {
    "snow_cm_max": [float(v) for v in range(0, 65, 5)],
    "cold_c_min": [float(v) for v in range(-5, 26)],
    "heat_c_max": [float(v) for v in range(20, 46)],
}

SCORES = {"exact": 2, "within1": 1, "worse": 0}


def held_out(tid):
    """True when a stable hash of the id is odd. The split never
    changes as records come and go, unlike a random one."""
    return hashlib.sha256(str(tid).encode("utf-8")).digest()[-1] % 2 == 1


def _grade_of(estimated, sourced_months):
    if not estimated:
        return "worse"
    return season.grade(estimated, sourced_months)


def season_kind(months):
    """The kind of trail a sourced season describes, from the season
    alone: "year-round" (eleven or twelve months), "cool-season" (hiked
    in the cool months, none of June to August), "alpine" (a summer
    season that leaves out December to February and covers July or
    August, at most six months) or "other" (the shoulder seasons and
    the rest)."""
    months = set(months)
    if len(months) >= 11:
        return "year-round"
    if not months & {6, 7, 8}:
        return "cool-season"
    if not months & {12, 1, 2} and months & {7, 8} and len(months) <= 6:
        return "alpine"
    return "other"


KINDS = ("alpine", "cool-season", "year-round", "other")


def fit_params(sourced, grid):
    """Grid search the three thresholds for the best mean grade over
    the estimable trails in sourced, a list of (id, normals, months)
    with an optional fourth item ignored here. Grades score exact 2,
    within one month 1, worse 0. Ties go to the first combination in
    grid order, so the same input always gives the same numbers."""
    prepared = []
    for item in sourced:
        medians = _medians(item[1])
        if medians is not None:
            prepared.append((medians, item[2]))
    if not prepared:
        raise ValueError("no estimable trails to fit on")
    best, best_score = None, None
    for snow in grid["snow_cm_max"]:
        for cold in grid["cold_c_min"]:
            for heat in grid["heat_c_max"]:
                params = Params(snow_cm_max=float(snow), cold_c_min=float(cold),
                                heat_c_max=float(heat))
                total = sum(SCORES[_grade_of(_months_from(med, params), months)]
                            for med, months in prepared)
                score = total / len(prepared)
                if best_score is None or score > best_score:
                    best, best_score = params, score
    return best


def report(sourced, params):
    """Counts of how the rule does on sourced trails: n, exact,
    within1 (which counts exact too, so within1 + worse + no_data is
    n), worse and no_data, plus the same per region group in by_group.
    A trail whose points lack data is no_data; a trail with data but
    no qualifying month grades worse."""
    counts = {"n": 0, "exact": 0, "within1": 0, "worse": 0, "no_data": 0}
    by_group = {}
    by_kind = {k: dict(counts) for k in KINDS}
    for item in sourced:
        group = item[3] if len(item) > 3 else season_batches.OTHER
        bucket = by_group.setdefault(
            group, {"n": 0, "exact": 0, "within1": 0, "worse": 0, "no_data": 0})
        kind_bucket = by_kind[season_kind(item[2])]
        medians = _medians(item[1])
        for target in (counts, bucket, kind_bucket):
            target["n"] += 1
        if medians is None:
            for target in (counts, bucket, kind_bucket):
                target["no_data"] += 1
            continue
        grade = _grade_of(_months_from(medians, params), item[2])
        for target in (counts, bucket, kind_bucket):
            if grade == "exact":
                target["exact"] += 1
                target["within1"] += 1
            elif grade == "within1":
                target["within1"] += 1
            else:
                target["worse"] += 1
    counts["by_group"] = by_group
    counts["by_kind"] = by_kind
    return counts


def passes_bar(rep, bar=BAR):
    """The owner's bar: at least 75 percent of held-out sourced trails
    within one month at each end, and at least 90 percent estimable."""
    n = rep.get("n") or 0
    if not n:
        return False
    return (rep["within1"] / n >= bar["within1_min"]
            and 1 - rep["no_data"] / n >= bar["coverage_min"])


def _records(root):
    for tid in refresh.trail_ids(root):
        yield tid, refresh.load_toml(os.path.join(root, tid, "trail.toml"))


def normals_at(points, fetch):
    return [fetch(p.lat, p.lon, p.elev_m) for p in points]


def sourced_trails(root, fetch, log=None):
    """(id, normals, sourced months, region group) for every record
    whose season comes from a page. Fetching goes through the climate
    cache; a network failure aborts the run and a rerun resumes from
    the cache, so no point is ever downloaded twice."""
    out = []
    for tid, rec in _records(root):
        hike = rec.get("hike") or {}
        if not hike.get("season") or hike.get("season_basis") == "estimate":
            continue
        points, kind = sample_points(root, rec)
        normals = normals_at(points, fetch)
        if log:
            log(f"{tid}: {kind}, {len(points)} points")
        out.append((tid, normals, list(hike.get("months") or []),
                    season_batches.group_of(rec)))
    return out


def _fetch_with_cache(cache_dir):
    if cache_dir is None:
        return season_climate.fetch_normals
    return lambda lat, lon, elev: season_climate.fetch_normals(
        lat, lon, elev, cache=cache_dir)


def _params_doc(params):
    return {"snow_cm_max": params.snow_cm_max, "cold_c_min": params.cold_c_min,
            "heat_c_max": params.heat_c_max}


def cmd_fit(args):
    fetch = _fetch_with_cache(args.cache)
    sourced = sourced_trails(ROOT, fetch, log=lambda line: print(line, flush=True))
    train = [s for s in sourced if not held_out(s[0])]
    test = [s for s in sourced if held_out(s[0])]
    train_params = fit_params(train, DEFAULT_GRID)
    held = report(test, train_params)
    shipped = fit_params(sourced, DEFAULT_GRID)
    whole = report(sourced, shipped)
    doc = {
        "computed": datetime.date.today().isoformat(),
        "rule_version": RULE_VERSION,
        "dataset": season_climate.SOURCE["name"],
        "period": season_climate.SOURCE["period"],
        "params": _params_doc(shipped),
        "held_out_params": _params_doc(train_params),
        "all": whole,
        "held_out": held,
        "bar": BAR,
        "passes": passes_bar(held),
    }
    path = os.path.join(ROOT, "tools", "season_fit.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"sourced {len(sourced)} (train {len(train)}, held out {len(test)})")
    print(f"held out: within1 {held['within1']}/{held['n']}, "
          f"exact {held['exact']}, worse {held['worse']}, "
          f"no data {held['no_data']}, passes {doc['passes']}")
    print(f"all: within1 {whole['within1']}/{whole['n']}, "
          f"exact {whole['exact']}, worse {whole['worse']}, "
          f"no data {whole['no_data']}")
    print(f"shipped params {_params_doc(shipped)} "
          f"(held-out fit {_params_doc(train_params)})")
    print(f"wrote {path}")
    return 0



# ---------------------------------------------------------------------------
# Estimates for trails with no sourced season, the review list a person
# reads, the staged proposals that write accepted estimates through the
# refresh pipeline, and the check that reruns both.

COARSE_PARAMS = Params(snow_cm_max=10.0, cold_c_min=5.0, heat_c_max=32.0)

# The trial's twelve, by rule: akshayuk-pass is the far north trail;
# great-divide-trail and west-coast-trail are in Canada; john-muir,
# colorado-trail and uinta-highline are alpine; desert-winter-thru-hike
# and arizona are desert; west-coast-trail and washington-coast-trail
# are coastal; maah-daah-hey is prairie; florida is the southeast;
# superior-hiking fills the dozen from the midwest.
TRIAL_TRAILS = ["akshayuk-pass", "great-divide-trail", "west-coast-trail",
                "john-muir", "colorado-trail", "uinta-highline",
                "desert-winter-thru-hike", "arizona", "florida",
                "washington-coast-trail", "maah-daah-hey", "superior-hiking"]

FLAG_ORDER = ("no-track", "place-centre", "no-data", "no-month",
              "desert", "coast", "far-north", "few-points")

_CENTRES = {}


def _centre(points):
    if not points:
        return None
    return (sum(p.lat for p in points) / len(points),
            sum(p.lon for p in points) / len(points))


def _sourced_centres(root):
    """(id, centre lat, centre lon, season phrase) for sourced trails,
    computed once per root per run: sampling every track again for
    each estimate would make the review list take minutes."""
    if root not in _CENTRES:
        out = []
        for tid, rec in _records(root):
            hike = rec.get("hike") or {}
            if not hike.get("season") or hike.get("season_basis") == "estimate":
                continue
            points, _kind = sample_points(root, rec)
            centre = _centre(points)
            if centre:
                out.append((tid, centre[0], centre[1], str(hike.get("season"))))
        _CENTRES[root] = out
    return _CENTRES[root]


def _flags(points, kind, normals, medians, params):
    found = set()
    if kind != "track":
        found.add("no-track")
    if kind == "place":
        found.add("place-centre")
    if len(points) < 3:
        found.add("few-points")
    if points and max(p.lat for p in points) > 60:
        found.add("far-north")
    if medians is None:
        found.add("no-data")
    else:
        elevs = [n.elev_m for n in normals if n is not None]
        if elevs and max(elevs) <= 200:
            found.add("coast")
        high_tmax, high_snow, low_tmax = medians
        for m in range(12):
            cold_ok = high_tmax[m] is not None and high_tmax[m] >= params.cold_c_min
            snow_ok = high_snow[m] is None or high_snow[m] <= params.snow_cm_max
            heat_ok = low_tmax[m] is not None and low_tmax[m] <= params.heat_c_max
            if cold_ok and snow_ok and not heat_ok:
                found.add("desert")
                break
        if not _months_from(medians, params):
            found.add("no-month")
    return [name for name in FLAG_ORDER if name in found]


def estimate(root, rec, params, fetch=season_climate.fetch_normals):
    """One trail's estimated season and how much to trust it: months
    (None when unestimable, with the reason), the phrase and method
    sentence an accepted estimate would carry, how its points were got,
    flags for hand review, and the nearest sourced trail to compare
    it with. Fetch errors propagate; nothing here touches the network
    except through fetch."""
    points, kind = sample_points(root, rec)
    normals = normals_at(points, fetch)
    medians = _medians(normals)
    months = _months_from(medians, params) if medians is not None else None
    months = months or None
    comparable, comparable_phrase = "", ""
    centre = _centre(points)
    if centre:
        best = None
        for tid, clat, clon, phrase in _sourced_centres(root):
            if tid == rec.get("id"):
                continue
            dist = season_climate.haversine_km(centre[0], centre[1], clat, clon)
            if best is None or dist < best[0]:
                best = (dist, tid, phrase)
        if best:
            comparable, comparable_phrase = best[1], best[2]
    return {
        "months": months,
        "phrase": season.phrase_for(months) if months else "",
        "method": season.method_sentence(
            season_climate.SOURCE["name"], season_climate.SOURCE["period"],
            len(points), kind, RULE_VERSION),
        "kind": kind,
        "flags": _flags(points, kind, normals, medians, params),
        "comparable": comparable,
        "comparable_phrase": comparable_phrase,
        "reason": "" if months else why_not(normals, params),
        "points": points,
        "normals": normals,
    }


def load_fit(root):
    with open(os.path.join(root, "tools", "season_fit.json"), encoding="utf-8") as f:
        return json.load(f)


def load_params(root):
    doc = load_fit(root)["params"]
    return Params(snow_cm_max=float(doc["snow_cm_max"]),
                  cold_c_min=float(doc["cold_c_min"]),
                  heat_c_max=float(doc["heat_c_max"]))


def _with_cache(fetch_fn, cache_dir):
    if cache_dir is None:
        return fetch_fn
    return lambda lat, lon, elev: fetch_fn(lat, lon, elev, cache=cache_dir)


def propose(root, params, fetch, given_dir=None):
    """Write the review list, one row per trail with no season, to
    <staging>/season/estimates.csv and list every unestimable trail
    with its reason. Returns the row count."""
    staging = refresh.staging_dir(root, given_dir, create=True)
    out_dir = os.path.join(staging, "season")
    os.makedirs(out_dir, exist_ok=True)
    rows, unestimable = [], []
    for tid, rec in _records(root):
        if (rec.get("hike") or {}).get("season"):
            continue
        est = estimate(root, rec, params, fetch)
        rows.append([tid, " ".join(str(m) for m in est["months"] or []),
                     est["phrase"], est["kind"], ";".join(est["flags"]),
                     est["comparable"], est["comparable_phrase"]])
        if not est["months"]:
            unestimable.append((tid, est["reason"]))
    path = os.path.join(out_dir, "estimates.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "proposed_months", "phrase", "kind", "flags",
                         "comparable", "comparable_phrase"])
        writer.writerows(rows)
    for tid, reason in unestimable:
        print(f"{tid}: not estimable: {reason}")
    print(f"{len(rows)} rows written to {path} "
          f"({len(unestimable)} not estimable)")
    return len(rows)


def _toml_str(text):
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _parse_months(text):
    months = []
    for piece in (text or "").replace(",", " ").replace(";", " ").split():
        months.append(int(piece))
    return sorted(set(months))


def proposals(root, reviewed_csv, given_dir=None):
    """Stage one change proposal per accepted reviewed row (a row with
    months). A row with a note was adjusted by hand, and its method
    sentence says so. Returns how many proposals were staged."""
    with open(reviewed_csv, newline="", encoding="utf-8") as f:
        reviewed = list(csv.DictReader(f))
    staging = refresh.staging_dir(root, given_dir, create=True)
    out = os.path.join(staging, "staged", "season-estimate")
    today = datetime.date.today().isoformat()
    source = season_climate.SOURCE
    report = []
    for row in reviewed:
        tid = (row.get("id") or "").strip()
        try:
            months = _parse_months(row.get("proposed_months"))
        except ValueError:
            raise ValueError(f"{tid}: proposed_months {row.get('proposed_months')!r} "
                             "is not a list of month numbers")
        if not tid or not months:
            continue
        rec = refresh.load_toml(os.path.join(root, tid, "trail.toml"))
        hike = rec.get("hike") or {}
        if hike.get("season"):
            raise ValueError(f"{tid}: already has a season")
        points, kind = sample_points(root, rec)
        phrase = season.phrase_for(months)
        method = season.method_sentence(source["name"], source["period"],
                                         len(points), kind, RULE_VERSION)
        note = (row.get("note") or "").strip()
        comparable = (row.get("comparable") or "").strip()
        if note and comparable:
            method = method[:-1] + f", and adjusted by hand against {comparable}."
        quote = (f"Monthly climate ({source['period']}) from {source['name']} "
                 f"gives {phrase} at the trail elevation.")
        page = source["url"]
        lines = ["[[proposal]]", 'kind = "change"', f"id = {_toml_str(tid)}",
                 f"date = {_toml_str(today)}",
                 f"summary = {_toml_str('Add an estimated season: ' + phrase + '.')}", ""]

        def edit(field, new_toml, old_toml=None):
            lines.append("[[proposal.edit]]")
            lines.append(f"field = {_toml_str(field)}")
            if old_toml is not None:
                lines.append(f"old = {old_toml}")
            lines.append(f"new = {new_toml}")
            lines.append(f"page = {_toml_str(page)}")
            lines.append(f"quote = {_toml_str(quote)}")
            lines.append("")

        edit("hike.season", _toml_str(phrase))
        edit("hike.months", "[" + ", ".join(str(m) for m in months) + "]")
        edit("hike.season_basis", _toml_str("estimate"))
        edit("hike.season_method", _toml_str(method))
        checked_old = hike.get("checked")
        edit("hike.checked", _toml_str(today),
             _toml_str(checked_old) if checked_old else None)
        lines += ["[[proposal.append]]", 'table = "hike.source"',
                  f"page = {_toml_str(page)}", f"quote = {_toml_str(quote)}", "",
                  "[proposal.append.entry]",
                  f"url = {_toml_str(page)}",
                  f"publisher = {_toml_str(source['publisher'])}",
                  'facts = ["season", "months"]', "",
                  "[proposal.history]",
                  f"change = {_toml_str('A season was estimated from climate: ' + phrase + '.')}",
                  f"basis = {_toml_str('No page states a season; it is estimated from climate (rule version ' + str(RULE_VERSION) + ').')}",
                  f"basis_url = {_toml_str(page)}",
                  'asked_by = "the dataset\'s own check"',
                  'fields = ["hike.season", "hike.months", "hike.season_basis", "hike.season_method"]',
                  ""]
        d = os.path.join(out, tid)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "proposal.toml"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        remark = f"estimated season {phrase}" + (f"; note: {note}" if note else "")
        report.append((tid, "changed", page, remark))
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "report.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "outcome", "pages", "remark"])
        writer.writerows(report)
    return len(report)


def check(root, fetch):
    """Rerun every estimated season and the held-out fit. Returns
    (ok, lines): not ok when an estimate would now come out different,
    when the held-out within-one-month share has fallen by more than
    0.02 from season_fit.json, or when that file does not pass."""
    try:
        fit = load_fit(root)
    except OSError:
        return False, ["tools/season_fit.json is missing: run "
                       "python3 tools/estimate_season.py fit"]
    params = load_params(root)
    ok, lines, checked = True, [], 0
    for tid, rec in _records(root):
        hike = rec.get("hike") or {}
        if hike.get("season_basis") != "estimate":
            continue
        checked += 1
        est = estimate(root, rec, params, fetch)
        old = sorted(int(m) for m in hike.get("months") or [])
        new = sorted(est["months"] or [])
        if new != old:
            ok = False
            detail = est["phrase"] or est["reason"]
            lines.append(f"{tid}: estimate was {old}, now {new} ({detail})")
    sourced = sourced_trails(root, fetch)
    train = [s for s in sourced if not held_out(s[0])]
    test = [s for s in sourced if held_out(s[0])]
    if train and test:
        try:
            now = report(test, fit_params(train, DEFAULT_GRID))
        except ValueError:
            now = None
        stored = fit.get("held_out") or {}
        if now and stored.get("n"):
            was_share = stored["within1"] / stored["n"]
            now_share = now["within1"] / now["n"] if now["n"] else 0.0
            if was_share - now_share > 0.02:
                ok = False
                lines.append(
                    f"fit got worse: held-out within one month "
                    f"{now['within1']}/{now['n']} ({now_share:.2f}), "
                    f"was {stored['within1']}/{stored['n']} ({was_share:.2f})")
    if not fit.get("passes"):
        ok = False
        lines.append("tools/season_fit.json does not pass the bar; "
                     "estimates must not ship")
    if ok:
        lines.append(f"check passed: {checked} estimated seasons unchanged")
    return ok, lines


def cmd_trial(args):
    for name, fetch_fn in season_climate.CANDIDATES.items():
        fetch = _with_cache(fetch_fn, args.cache)
        print(f"{name}: trail (sourced months) gives estimated months, grade")
        data = within = 0
        for tid in TRIAL_TRAILS:
            rec = refresh.load_toml(os.path.join(ROOT, tid, "trail.toml"))
            sourced = list((rec.get("hike") or {}).get("months") or [])
            points, _kind = sample_points(ROOT, rec)
            try:
                normals = normals_at(points, fetch)
            except Exception as exc:
                print(f"  {tid} ({sourced}): error {type(exc).__name__}: {exc}")
                continue
            months = months_in_season(normals, COARSE_PARAMS) if points else None
            if normals and all(n is not None for n in normals):
                data += 1
                grade = season.grade(months, sourced) if months else "no-month"
                within += grade in ("exact", "within1")
                print(f"  {tid} ({sourced}): {months}, {grade}")
            else:
                print(f"  {tid} ({sourced}): no data")
        print(f"  data for {data} of {len(TRIAL_TRAILS)}, "
              f"exact or within one month for {within}")
    return 0


def all_sample_points(root):
    """Every sample point for every record, as (id, kind, points)."""
    out = []
    for tid, rec in _records(root):
        points, kind = sample_points(root, rec)
        out.append((tid, kind, points))
    return out


def cmd_warm(args):
    """Read the climate for every sample point of every trail into the
    cache, several points at a time. Safe to stop and rerun."""
    from concurrent.futures import ThreadPoolExecutor
    fetch = _fetch_with_cache(args.cache)
    jobs = []
    seen = set()
    for _tid, _kind, points in all_sample_points(ROOT):
        for p in points:
            key = (round(p.lat, 3), round(p.lon, 3),
                   None if p.elev_m is None else int(round(p.elev_m)))
            if key not in seen:
                seen.add(key)
                jobs.append(p)
    print(f"{len(jobs)} distinct points", flush=True)
    done = [0]
    nodata = [0]

    def one(p):
        n = fetch(p.lat, p.lon, p.elev_m)
        done[0] += 1
        if n is None:
            nodata[0] += 1
        if done[0] % 25 == 0 or done[0] == len(jobs):
            print(f"{done[0]}/{len(jobs)} done, {nodata[0]} without data",
                  flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(one, jobs))
    print("warm finished", flush=True)
    return 0


def cmd_propose(args):
    fetch = _fetch_with_cache(args.cache)
    propose(ROOT, load_params(ROOT), fetch, args.dir)
    return 0


def cmd_proposals(args):
    count = proposals(ROOT, args.reviewed, args.dir)
    print(f"{count} proposals staged")
    return 0


def cmd_check(args):
    fetch = _fetch_with_cache(args.cache)
    ok, lines = check(ROOT, fetch)
    for line in lines:
        print(line)
    return 0 if ok else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    fit_parser = sub.add_parser(
        "fit", help="fit the rule against the sourced seasons")
    fit_parser.add_argument("--cache", default=None,
                            help="climate cache directory")
    fit_parser.set_defaults(func=cmd_fit)
    trial_parser = sub.add_parser(
        "trial", help="compare the climate candidates on twelve trails")
    trial_parser.add_argument("--cache", default=None,
                              help="climate cache directory")
    trial_parser.set_defaults(func=cmd_trial)
    warm_parser = sub.add_parser(
        "warm", help="read the climate for every sample point into the cache")
    warm_parser.add_argument("--cache", default=None,
                             help="climate cache directory")
    warm_parser.add_argument("--workers", type=int, default=6)
    warm_parser.set_defaults(func=cmd_warm)
    propose_parser = sub.add_parser(
        "propose", help="write the estimate review list")
    propose_parser.add_argument("--dir", default=None,
                                help="staging directory")
    propose_parser.add_argument("--cache", default=None,
                                help="climate cache directory")
    propose_parser.set_defaults(func=cmd_propose)
    proposals_parser = sub.add_parser(
        "proposals", help="stage proposals from a reviewed list")
    proposals_parser.add_argument("--reviewed", required=True,
                                  help="reviewed estimates CSV")
    proposals_parser.add_argument("--dir", default=None,
                                  help="staging directory")
    proposals_parser.set_defaults(func=cmd_proposals)
    check_parser = sub.add_parser(
        "check", help="rerun every estimate and the fit")
    check_parser.add_argument("--cache", default=None,
                              help="climate cache directory")
    check_parser.set_defaults(func=cmd_check)
    argv = ["check" if a == "--check" else a
            for a in (sys.argv[1:] if argv is None else argv)]
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
