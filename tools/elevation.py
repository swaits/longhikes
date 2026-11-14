#!/usr/bin/env python3
"""Compute each trail's elevation facts and profile from its track.

Writes <id>/elevation.json beside the record for every trail that has a
track (source.line_file). The elevation comes from the Terrain Tiles open
dataset on AWS (Mapzen "terrarium" PNG tiles; see docs/schema.md and
NOTICE.md for the sources and the credit they require).

Needs Python 3 and numpy and Pillow. Run from anywhere:
    python3 tools/elevation.py              every trail with a track; skips those
                                            whose output is newer than the track
                                            and this tool
    python3 tools/elevation.py long-trail   only the named trails
    python3 tools/elevation.py --force      recompute even if up to date
    python3 tools/elevation.py --dry ID...  print the figures, write nothing

Tiles are fetched a few at a time and kept in ~/.cache/longhikes-dem/
(outside the repository), so a second run needs no network.

The method, in short (docs/schema.md has the long form):
  1. Join the track's pieces end to end (ends within 100 m), as the records do.
  2. Sample each part every 30 m along its length. Parts are never joined to
     each other; no ascent is counted across a gap.
  3. Read the elevation at each sample by bilinear interpolation of the tile grid
     (values below sea level are taken as 0).
  4. Smooth the profile with a moving average, then count a climb or a descent
     only after it exceeds a threshold (reversal threshold). This removes the
     noise that makes raw elevation models report far too much ascent.
"""
import sys

sys.dont_write_bytecode = True

import datetime
import io
import json
import math
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.abspath(__file__)

EARTH_R = 6371008.8  # metres; the same radius the records' measured lengths use
TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
USER_AGENT = "longhikes-dem/1.0 (open dataset tooling)"
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "longhikes-dem")
WORKERS = 4

# Method settings. Tuned once against published figures (see the report in
# docs/schema.md), then fixed for every trail. Change them and the method
# version, and every file is recomputed.
METHOD_VERSION = 1
ZOOM = 12                 # about 29 m per pixel at 40 degrees north
SPACING_M = 30.0          # distance between samples along the track
SMOOTH_M = 90.0           # moving-average window, in metres along the track
THRESHOLD_M = 5.0         # a climb or descent counts only once it exceeds this
DESPIKE_M = 100.0        # a tile pixel this far from the median of its neighbours is an
                          # artifact of the tile making and is replaced
JOIN_GAP_M = 100.0        # track pieces whose ends lie this close are joined
PROFILE_POINTS = 700      # most points kept in the profile
LOOP_FRACTION = 0.1       # a part whose ends are this close (as a share of its
                          # length) is a loop and keeps the direction it has

SOURCE_NAME = "Terrain Tiles (Mapzen terrarium), open data on AWS"
SOURCE_URL = "https://registry.opendata.aws/terrain-tiles/"
ATTRIBUTION = (
    "Terrain Tiles, accessed from https://registry.opendata.aws/terrain-tiles. "
    "United States 3DEP (formerly NED) and global GMTED2010 and SRTM terrain data "
    "courtesy of the U.S. Geological Survey. Canada terrain data contains "
    "information licensed under the Open Government Licence - Canada. ArcticDEM "
    "terrain data DEM(s) were created from DigitalGlobe, Inc., imagery and funded "
    "under National Science Foundation awards 1043681, 1559691, and 1542736. "
    "Global ETOPO1 terrain data U.S. National Oceanic and Atmospheric "
    "Administration."
)
SMOOTHING_TEXT = (
    f"Moving average over {SMOOTH_M:g} m of track; ascent and descent counted with "
    f"a {THRESHOLD_M:g} m reversal threshold"
)
LIMITS_TEXT = (
    "Computed from a public elevation model, not measured on the ground. Highest "
    "and lowest are the model's values at the sample points, with anything below "
    "sea level shown as 0. Ascent and descent "
    "depend on the smoothing and the threshold, and published figures for the same "
    "trail can differ from them by 15 percent or more. Parts of the track are "
    "never joined, so a gap is not counted."
)


# ---------------------------------------------------------------- tile maths

def lonlat_to_pixel(lon, lat, zoom):
    """Global pixel position (x, y) of longitude and latitude at a zoom level.

    Web Mercator, 256-pixel tiles: the world is 256 * 2**zoom pixels wide.
    Accepts numbers or numpy arrays; latitude is clipped to the Mercator limit.
    """
    n = 256.0 * (2 ** zoom)
    lon = np.asarray(lon, dtype=np.float64)
    lat = np.clip(np.asarray(lat, dtype=np.float64), -85.0511287798, 85.0511287798)
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - np.arcsinh(np.tan(np.radians(lat))) / math.pi) / 2.0 * n
    return x, y


def pixel_to_lonlat(x, y, zoom):
    """Inverse of lonlat_to_pixel."""
    n = 256.0 * (2 ** zoom)
    lon = np.asarray(x, dtype=np.float64) / n * 360.0 - 180.0
    lat = np.degrees(np.arctan(np.sinh(math.pi * (1.0 - 2.0 * np.asarray(y, dtype=np.float64) / n))))
    return lon, lat


def ground_m_per_pixel(lat, zoom):
    """Ground size of one pixel in metres at a latitude."""
    return 2.0 * math.pi * EARTH_R * math.cos(math.radians(lat)) / (256.0 * 2 ** zoom)


def decode_terrarium(rgb):
    """Elevation in metres from a terrarium tile: (red * 256 + green + blue / 256) - 32768.

    rgb is an array of shape (h, w, 3) of 0..255 values.
    """
    a = np.asarray(rgb, dtype=np.float64)
    return (a[..., 0] * 256.0 + a[..., 1] + a[..., 2] / 256.0 - 32768.0).astype(np.float32)


def despike(tile, threshold_m=DESPIKE_M):
    """Replace pixels that are far from their surroundings.

    The tiles hold a few artifacts: lines and small patches of pixels, mostly
    where a river or the coast meets sea level, with values thousands of
    metres off. A pixel more than threshold_m from the median of its 3 x 3
    neighbourhood is replaced by the median of the unflagged pixels in its
    5 x 5 neighbourhood (or the 3 x 3 median where none is left). The pass is
    repeated, up to four times, for patches that need more than one. Real
    terrain at this pixel size does not change that much in one pixel.
    """
    from numpy.lib.stride_tricks import sliding_window_view as windows
    h, w = tile.shape
    out = tile
    for _ in range(4):
        med3 = np.median(windows(np.pad(out, 1, mode="edge"), (3, 3)).reshape(h, w, 9), axis=2)
        bad = np.abs(out - med3) > threshold_m
        if not bad.any():
            break
        ys, xs = np.nonzero(bad)
        vals = windows(np.pad(out, 2, mode="edge"), (5, 5))[ys, xs].reshape(len(ys), 25).astype(np.float64)
        flags = windows(np.pad(bad, 2, mode="edge"), (5, 5))[ys, xs].reshape(len(ys), 25)
        vals[flags] = np.nan
        with np.errstate(all="ignore"):
            fill = np.nanmedian(vals, axis=1)
        fill = np.where(np.isnan(fill), med3[ys, xs], fill)
        out = out.copy()
        out[ys, xs] = fill
    return out


def below_sea_level_to_zero(tile):
    """Raise every value below sea level to 0.

    Beside a coast the tiles carry the depth of the sea, and a read near the
    shore would mix it into the land. None of the trails in this dataset goes
    below sea level, so a value below 0 is the sea and not the trail.
    """
    return np.maximum(tile, 0.0).astype(np.float32)


def corner_pixels(px, py):
    """The four pixels a bilinear read at (px, py) uses, with their weights.

    Pixel i covers [i, i + 1) and its value belongs at its centre, i + 0.5.
    Returns (ix0, iy0, fx, fy): the integer pixel up and left of the point and
    the fractions toward the next pixel in x and y.
    """
    fx = np.asarray(px, dtype=np.float64) - 0.5
    fy = np.asarray(py, dtype=np.float64) - 0.5
    ix0 = np.floor(fx).astype(np.int64)
    iy0 = np.floor(fy).astype(np.int64)
    return ix0, iy0, fx - ix0, fy - iy0


def tiles_needed(px, py):
    """Set of (x, y) tiles that a bilinear read at every (px, py) touches."""
    ix0, iy0, _, _ = corner_pixels(px, py)
    pairs = np.concatenate([
        np.stack([(ix0 + dx) // 256, (iy0 + dy) // 256], axis=1)
        for dx in (0, 1) for dy in (0, 1)])
    return {(int(a), int(b)) for a, b in np.unique(pairs, axis=0)}


def bilinear(px, py, tile_of):
    """Interpolated elevation at global pixel positions.

    tile_of(tx, ty) returns the 256 x 256 float32 elevation array of a tile.
    """
    ix0, iy0, fx, fy = corner_pixels(px, py)
    out = np.zeros(len(ix0), dtype=np.float64)
    corners = ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)),
               (0, 1, (1 - fx) * fy), (1, 1, fx * fy))
    for dx, dy, weight in corners:
        cx, cy = ix0 + dx, iy0 + dy
        tx, ty = cx // 256, cy // 256
        key = tx * 4194304 + ty  # unique per tile at any zoom up to 21
        for k in np.unique(key):
            sel = key == k
            tile = tile_of(int(tx[sel][0]), int(ty[sel][0]))
            out[sel] += weight[sel] * tile[cy[sel] % 256, cx[sel] % 256]
    return out


# ---------------------------------------------------------------- the track

def haversine_m(lon, lat):
    """Lengths in metres of the segments between consecutive points."""
    lo, la = np.radians(lon), np.radians(lat)
    dlat, dlon = np.diff(la), np.diff(lo)
    a = np.sin(dlat / 2) ** 2 + np.cos(la[:-1]) * np.cos(la[1:]) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_R * np.arcsin(np.minimum(1.0, np.sqrt(a)))


def track_parts(data):
    """LineString and MultiLineString parts of a GeoJSON track; two points or more."""
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
    return [[(c[0], c[1]) for c in p] for p in parts if len(p) >= 2]


def _gap_m(a, b):
    dx = (a[0] - b[0]) * math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot(dx, a[1] - b[1]) * math.pi / 180.0 * EARTH_R


def join_parts(parts, gap_m=JOIN_GAP_M):
    """Chain parts whose end points lie within gap_m of each other.

    Greedy: a chain grows at its tail, then at its head, taking the nearest
    unused part end each time (a part is reversed when its far end is the
    near one). Parts that touch nothing stay as they are. This is the same
    rule the records use for their `parts` count (verification.parts).
    """
    if not parts:
        return []
    cell = max(gap_m, 1.0)
    k = math.pi / 180.0 * EARTH_R
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


def orient_and_order(chains):
    """Give the parts a fixed direction and order, so the output is repeatable.

    The whole track runs south to north if it is taller than it is wide, and
    west to east otherwise. Each part is turned to run that way. A part that
    ends close to where it starts (a loop) keeps the direction it has. Parts
    are put in order along the same axis, by their centres. Returns
    (chains, orientation) with orientation "south-to-north" or "west-to-east".
    """
    if not chains:
        return [], "west-to-east"
    lons = [c[0] for ch in chains for c in ch]
    lats = [c[1] for ch in chains for c in ch]
    mid_lat = (min(lats) + max(lats)) / 2.0
    width = (max(lons) - min(lons)) * math.cos(math.radians(mid_lat))
    north = (max(lats) - min(lats)) > width
    axis = 1 if north else 0
    out = []
    for ch in chains:
        length = float(haversine_m(np.array([c[0] for c in ch]), np.array([c[1] for c in ch])).sum())
        if _gap_m(ch[0], ch[-1]) > LOOP_FRACTION * length and ch[-1][axis] < ch[0][axis]:
            ch = ch[::-1]
        out.append(ch)
    out.sort(key=lambda ch: sum(c[axis] for c in ch) / len(ch))
    return out, ("south-to-north" if north else "west-to-east")


def resample(chain, spacing_m=SPACING_M):
    """Points every spacing_m along a part, from its start and ending at its end.

    Returns (lon, lat, dist_m) as arrays, dist_m measured from the start of the
    part. The last step is shorter than spacing_m unless the length divides it.
    """
    lon = np.array([c[0] for c in chain], dtype=np.float64)
    lat = np.array([c[1] for c in chain], dtype=np.float64)
    cum = np.concatenate([[0.0], np.cumsum(haversine_m(lon, lat))])
    total = float(cum[-1])
    d = np.arange(0.0, total, spacing_m)
    if total - (d[-1] if len(d) else 0.0) > 1e-6 or len(d) < 2:
        d = np.append(d, total)
    # np.interp needs increasing x; drop zero-length steps (repeated points)
    keep = np.concatenate([[True], np.diff(cum) > 0])
    cum_k, lon_k, lat_k = cum[keep], lon[keep], lat[keep]
    if len(cum_k) < 2:
        return lon[:1], lat[:1], np.zeros(1)
    return np.interp(d, cum_k, lon_k), np.interp(d, cum_k, lat_k), d


# ---------------------------------------------------------------- the profile

def smooth(elev, window_samples):
    """Centred moving average; the window shrinks at the ends of the part."""
    n = len(elev)
    w = max(1, int(window_samples))
    if w % 2 == 0:
        w += 1
    half = w // 2
    if n < 2 or half == 0:
        return np.asarray(elev, dtype=np.float64).copy()
    c = np.concatenate([[0.0], np.cumsum(np.asarray(elev, dtype=np.float64))])
    idx = np.arange(n)
    lo = np.maximum(idx - half, 0)
    hi = np.minimum(idx + half + 1, n)
    return (c[hi] - c[lo]) / (hi - lo)


def climb(elev, threshold_m):
    """Total ascent and descent with a reversal threshold.

    Find the turning points of the profile: a high point counts as a turn only
    once the profile has fallen more than threshold_m below it, and a low point
    only once it has risen more than threshold_m above it. Ascent and descent
    are the rises and falls between successive turning points, so smaller
    wiggles count for nothing. Ascent minus descent is the net change from the
    first point to the last, to within threshold_m. Returns (ascent_m, descent_m).
    """
    e = np.asarray(elev, dtype=np.float64)
    if len(e) < 2:
        return 0.0, 0.0
    turns = [float(e[0])]
    hi = lo = float(e[0])
    mode = 0  # 0 not yet decided, 1 climbing, -1 descending
    for v in e[1:]:
        v = float(v)
        if mode == 0:
            hi, lo = max(hi, v), min(lo, v)
            if v - lo > threshold_m:
                turns.append(lo)
                mode, hi = 1, v
            elif hi - v > threshold_m:
                turns.append(hi)
                mode, lo = -1, v
        elif mode == 1:
            if v > hi:
                hi = v
            elif hi - v > threshold_m:
                turns.append(hi)
                mode, lo = -1, v
        else:
            if v < lo:
                lo = v
            elif v - lo > threshold_m:
                turns.append(lo)
                mode, hi = 1, v
    turns.append(hi if mode == 1 else lo if mode == -1 else float(e[-1]))
    d = np.diff(np.array(turns))
    return float(d[d > 0].sum()), float(-d[d < 0].sum())


def thin_profile(dist, elev, max_points=PROFILE_POINTS, keep=()):
    """Indices of at most max_points points that draw the profile faithfully.

    Ramer-Douglas-Peucker on elevation against distance, with the vertical
    tolerance found by bisection. The first and last points and the indices in
    keep (the extremes) are always kept. Deterministic.
    """
    n = len(dist)
    forced = sorted({0, n - 1} | {int(i) for i in keep})
    if n <= max_points:
        return list(range(n))
    d = np.asarray(dist, dtype=np.float64)
    e = np.asarray(elev, dtype=np.float64)

    def rdp(tol):
        marked = np.zeros(n, dtype=bool)
        marked[forced] = True
        stack = list(zip(forced[:-1], forced[1:]))
        while stack:
            a, b = stack.pop()
            if b - a < 2:
                continue
            seg = slice(a + 1, b)
            t = (d[seg] - d[a]) / (d[b] - d[a]) if d[b] > d[a] else np.zeros(b - a - 1)
            dev = np.abs(e[seg] - (e[a] + t * (e[b] - e[a])))
            j = int(np.argmax(dev))
            if dev[j] > tol:
                m = a + 1 + j
                marked[m] = True
                stack.append((a, m))
                stack.append((m, b))
        return np.flatnonzero(marked)

    lo, hi = 0.0, float(np.ptp(e)) + 1.0
    best = rdp(hi)
    for _ in range(40):
        mid = (lo + hi) / 2.0
        got = rdp(mid)
        if len(got) <= max_points:
            best, hi = got, mid
        else:
            lo = mid
    return [int(i) for i in best]


# ---------------------------------------------------------------- the tiles

def tile_path(cache, zoom, x, y):
    return os.path.join(cache, "terrarium", str(zoom), str(x), f"{y}.png")


def fetch_tile(cache, zoom, x, y, opener=urllib.request.urlopen):
    """Path of a tile in the cache, fetching it first if it is not there."""
    path = tile_path(cache, zoom, x, y)
    if os.path.isfile(path):
        return path
    url = TILE_URL.format(z=zoom, x=x, y=y)
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with opener(req, timeout=60) as r:
                body = r.read()
            Image.open(io.BytesIO(body)).verify()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = f"{path}.{os.getpid()}.part"
            with open(tmp, "wb") as f:
                f.write(body)
            os.replace(tmp, path)
            return path
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 404:
                break
        except Exception as e:  # noqa: BLE001 - retry any network or decode trouble
            last = e
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"could not fetch tile {zoom}/{x}/{y}: {last}")


def load_tile(path):
    with Image.open(path) as im:
        return below_sea_level_to_zero(despike(decode_terrarium(np.asarray(im.convert("RGB")))))


class TileStore:
    """Decoded tiles on demand; fetches the missing ones a few at a time."""

    def __init__(self, zoom, cache=CACHE_DIR):
        self.zoom, self.cache, self.tiles = zoom, cache, {}
        self.fetched = 0

    def prefetch(self, needed):
        missing = [t for t in sorted(needed) if not os.path.isfile(tile_path(self.cache, self.zoom, *t))]
        if missing:
            with ThreadPoolExecutor(max_workers=WORKERS) as pool:
                list(pool.map(lambda t: fetch_tile(self.cache, self.zoom, *t), missing))
            self.fetched += len(missing)
        for t in needed:
            self.get(*t)

    def get(self, x, y):
        if (x, y) not in self.tiles:
            n = 2 ** self.zoom
            if not 0 <= y < n:
                raise RuntimeError(f"tile row {y} is outside the map at zoom {self.zoom}")
            self.tiles[(x, y)] = load_tile(fetch_tile(self.cache, self.zoom, x % n, y))
        return self.tiles[(x, y)]

    def clear(self):
        self.tiles = {}


# ---------------------------------------------------------------- one trail

def sample_trail(data, store, zoom=ZOOM, spacing_m=SPACING_M):
    """Resample a track and read its elevations. Returns a list of parts.

    Each part is a dict of numpy arrays: lon, lat, dist_m (from the part's own
    start) and elev (raw interpolated metres). Also returns the orientation.
    """
    chains, orientation = orient_and_order(join_parts(track_parts(data)))
    sampled = [r for r in (resample(ch, spacing_m) for ch in chains) if len(r[2]) >= 2]
    pxs = [lonlat_to_pixel(lo, la, zoom) for lo, la, _ in sampled]
    needed = set()
    for px, py in pxs:
        needed |= tiles_needed(px, py)
    store.prefetch(needed)
    parts = []
    for (lon, lat, d), (px, py) in zip(sampled, pxs):
        parts.append({"lon": lon, "lat": lat, "dist_m": d, "elev": bilinear(px, py, store.get)})
    return parts, orientation


def summarise(parts, orientation, published_km, window_m=SMOOTH_M, threshold_m=THRESHOLD_M,
              spacing_m=SPACING_M, max_points=PROFILE_POINTS):
    """Turn sampled parts into the facts and the profile (a dict, not yet dated)."""
    window = max(1, round(window_m / spacing_m))
    ascent = descent = 0.0
    start = 0.0
    smoothed, offsets = [], []
    for p in parts:
        s = smooth(p["elev"], window)
        a, dn = climb(s, threshold_m)
        ascent += a
        descent += dn
        smoothed.append(s)
        offsets.append(start)
        start += float(p["dist_m"][-1])
    track_km = start / 1000.0

    lon = np.concatenate([p["lon"] for p in parts])
    lat = np.concatenate([p["lat"] for p in parts])
    raw = np.concatenate([p["elev"] for p in parts])
    dist = np.concatenate([p["dist_m"] + o for p, o in zip(parts, offsets)]) / 1000.0
    prof = np.concatenate(smoothed)
    hi, lo = int(np.argmax(raw)), int(np.argmin(raw))
    # The profile follows the smoothed values but passes through the true
    # extremes, so the chart agrees with the highest and lowest figures.
    prof[hi], prof[lo] = raw[hi], raw[lo]
    first_of_part = []
    k = 0
    for p in parts:
        first_of_part.append(k)
        k += len(p["lon"])
    keep = [hi, lo] + [i for i in first_of_part] + [i - 1 for i in first_of_part if i > 0]
    idx = thin_profile(dist, prof, max_points, keep)
    # Round the distances; where two points round to the same value drop the
    # later one, except the first point of a part, which sits at the same
    # distance as the end of the part before it (the gap between parts).
    starts = set(first_of_part)
    kept, last = [], None
    for i in idx:
        r = round(float(dist[i]), 2)
        if last is not None and r <= last and i not in starts:
            if i in (hi, lo) and kept[-1] not in starts and kept[-1] not in (hi, lo):
                kept[-1] = i           # an extreme takes the place of its neighbour
            continue
        kept.append(i)
        last = r
    idx = kept
    out = {
        "highest": {"m": int(round(raw[hi])), "lon": round(float(lon[hi]), 5),
                    "lat": round(float(lat[hi]), 5)},
        "lowest": {"m": int(round(raw[lo])), "lon": round(float(lon[lo]), 5),
                   "lat": round(float(lat[lo]), 5)},
        "ascent_m": int(round(ascent)),
        "descent_m": int(round(descent)),
        "track_km": round(track_km, 1),
        "published_km": published_km,
        "coverage": round(track_km / published_km, 3) if published_km else None,
        "parts": len(parts),
        "orientation": orientation,
        "profile": [[round(float(dist[i]), 2), int(round(prof[i]))] for i in idx],
    }
    if len(parts) > 1:
        out["part_starts_km"] = [round(o / 1000.0, 2) for o in offsets[1:]]
    return out


def build(trail_id, rec, data, store, today, zoom=ZOOM):
    parts, orientation = sample_trail(data, store, zoom)
    doc = summarise(parts, orientation, rec.get("length_km"))
    doc["source"] = {
        "model": SOURCE_NAME,
        "url": SOURCE_URL,
        "attribution": ATTRIBUTION,
        "zoom": zoom,
        "ground_m_per_pixel_at_40n": round(ground_m_per_pixel(40.0, zoom), 1),
        "sample_spacing_m": SPACING_M,
        "smoothing": SMOOTHING_TEXT,
        "limits": LIMITS_TEXT,
        "method_version": METHOD_VERSION,
        "computed": today,
    }
    return doc


def dumps(doc):
    """Compact, sorted, repeatable JSON text."""
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def write_if_changed(path, doc):
    """Write doc; keep the old date when nothing else changed. True if written."""
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                old = json.load(f)
            probe = json.loads(json.dumps(doc))
            probe["source"]["computed"] = old.get("source", {}).get("computed")
            if dumps(probe) == dumps(old):
                doc["source"]["computed"] = old["source"]["computed"]
        except (ValueError, KeyError, TypeError):
            pass
    text = dumps(doc)
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            if f.read() == text:
                os.utime(path)
                return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return True


# ---------------------------------------------------------------- the command

def load_record(trail_id):
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import build_index  # noqa: E402
    return build_index.load_toml(os.path.join(ROOT, trail_id, "trail.toml"))


def trails_with_track():
    import build_index  # noqa: E402
    out = []
    for tid in build_index.trail_dirs(ROOT):
        if os.path.isfile(os.path.join(ROOT, tid, "line.geojson")):
            out.append(tid)
    return out


def up_to_date(trail_id):
    out = os.path.join(ROOT, trail_id, "elevation.json")
    if not os.path.isfile(out):
        return False
    t = os.path.getmtime(out)
    return t > os.path.getmtime(os.path.join(ROOT, trail_id, "line.geojson")) and t > os.path.getmtime(TOOL)


def main(argv):
    force = dry = False
    zoom, cache, ids = ZOOM, CACHE_DIR, []
    args = list(argv)
    while args:
        a = args.pop(0)
        if a == "--force":
            force = True
        elif a == "--dry":
            dry = True
        elif a == "--zoom":
            zoom = int(args.pop(0))
        elif a == "--cache":
            cache = os.path.expanduser(args.pop(0))
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            ids.append(a)
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    every = trails_with_track()
    for tid in ids:
        if tid not in every:
            print(f"ERROR {tid}: no trail with a track by that id")
            return 1
    todo = ids or every
    today = datetime.date.today().isoformat()
    store = TileStore(zoom, cache)
    began = time.time()
    done = skipped = 0
    for tid in todo:
        if not ids and not force and not dry and up_to_date(tid):
            skipped += 1
            continue
        rec = load_record(tid)
        with open(os.path.join(ROOT, tid, "line.geojson"), encoding="utf-8") as f:
            data = json.load(f)
        t0 = time.time()
        doc = build(tid, rec, data, store, today, zoom)
        store.clear()
        h, lo = doc["highest"], doc["lowest"]
        print(f"{tid}: high {h['m']} m, low {lo['m']} m, ascent {doc['ascent_m']} m, "
              f"descent {doc['descent_m']} m, {doc['track_km']} km of {doc['published_km']} "
              f"({doc['parts']} parts, {len(doc['profile'])} points) in {time.time() - t0:.1f} s",
              flush=True)
        if not dry:
            write_if_changed(os.path.join(ROOT, tid, "elevation.json"), doc)
        done += 1
    print(f"{done} computed, {skipped} up to date, {store.fetched} tiles fetched, "
          f"{time.time() - began:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
