"""The static sketch: the tracks of a map, drawn into the page at build time.

A map frame is never empty. From the first paint it holds a light drawing of the track, on the
plain ground, in the colours the live map uses (the .fallback__* rules of style.css), and the live
map (app.js) takes over from it without a jump. For that the two must frame the same ground:

    frame      the extent of the tracks, widened on every side by PAD of its longer side, as
               [west, south, east, north] in degrees (data-frame on the figure). The drawing
               fits it exactly, and app.js opens the live map on the same box with no padding,
               so the track holds still when the base map arrives.

The drawing is an <svg> with a fixed viewBox (the frame, FIT units along its longer side) and
preserveAspectRatio="xMidYMid meet", so it fits any frame size the way the live map fits the
same bounds. Coordinates are Web Mercator, as the live map's. Each track is simplified to TOL
units and written as whole numbers in one relative path: a few kilobytes for a trail, and a
fixed, small size for the overview of every trail.

The tracks are read from the files the build has already written (trails/<id>/map.json,
data/overview.geojson): the same simplified geometry the page ships to the live map.
"""
import json
import math
import os

from . import geo
from .markup import Markup

FIT = 1200          # the longer side of the viewBox, in user units
PAD = 0.07          # each side of the frame, as a share of the extent's longer side
TOL = 1.1           # simplification, in viewBox units (about a pixel on a wide screen)
MANY = 12           # a map of more tracks than this is drawn lighter: coarser, and with no halo
TOL_MANY = 2.4
MIN_SPAN = (0.5, 0.36)  # degrees: a lone point or a tiny extent gets about a county of ground
RAD = math.pi / 180.0
EARTH_M = 6371008.8

DATA_DIR = ""       # the site being built (olt/pages.py sets it); no data, no sketch
_cache = {}


def use(out_dir):
    """Name the site directory the tracks are read from, and forget what was read before."""
    global DATA_DIR
    DATA_DIR = out_dir or ""
    _cache.clear()


def _read(*parts):
    if not DATA_DIR:
        return None
    path = os.path.join(DATA_DIR, *parts)
    if path not in _cache:
        try:
            with open(path, encoding="utf-8") as f:
                _cache[path] = json.load(f)
        except (OSError, ValueError):
            _cache[path] = None
    return _cache[path]


def trail_features(trail_id):
    """The features of one trail's map.json (main and alternates), or []."""
    fc = _read("trails", trail_id, "map.json") or _read("trails", trail_id, "sketch.json")
    return list(fc["features"]) if fc else []


def overview_features(ids=None):
    """The overview's features, limited to the trail ids given (all when None)."""
    fc = _read("data", "overview.geojson")
    if not fc:
        return []
    want = None if ids is None else set(ids)
    return [f for f in fc["features"] if want is None or (f.get("properties") or {}).get("id") in want]


def _merc(lat):
    return math.log(math.tan(math.pi / 4 + lat * RAD / 2))


def _unmerc(y):
    return math.degrees(2 * math.atan(math.exp(y)) - math.pi / 2)


def frame(box):
    """[west, south, east, north] of the ground a map frame shows for the extent `box`
    (the same box in degrees): widened by PAD, and given a minimum size."""
    w, s, e, n = box
    if e - w < 0.02:
        cx = (w + e) / 2
        w, e = cx - MIN_SPAN[0] / 2, cx + MIN_SPAN[0] / 2
    if n - s < 0.02:
        cy = (s + n) / 2
        s, n = cy - MIN_SPAN[1] / 2, cy + MIN_SPAN[1] / 2
    x0, x1 = w * RAD, e * RAD
    y0, y1 = _merc(s), _merc(n)
    pad = PAD * max(x1 - x0, y1 - y0)
    return [round((x0 - pad) / RAD, 5), round(_unmerc(y0 - pad), 5),
            round((x1 + pad) / RAD, 5), round(_unmerc(y1 + pad), 5)]


def frame_attr(box):
    return ",".join(f"{v:g}" for v in frame(box))


class Plane:
    """Projects [lon, lat] into the viewBox of a frame."""

    def __init__(self, fr):
        w, s, e, n = fr
        self.x0, self.x1 = w * RAD, e * RAD
        self.y0, self.y1 = _merc(s), _merc(n)
        span = max(self.x1 - self.x0, self.y1 - self.y0)
        self.k = FIT / span
        self.w = (self.x1 - self.x0) * self.k
        self.h = (self.y1 - self.y0) * self.k
        # metres on the ground per viewBox unit, at the middle of the frame
        mid = _unmerc((self.y0 + self.y1) / 2)
        self.m_per_unit = EARTH_M / self.k * math.cos(mid * RAD)

    def xy(self, point):
        return ((point[0] * RAD - self.x0) * self.k, (self.y1 - _merc(point[1])) * self.k)


def _path(plane, parts, tol=TOL):
    """One relative SVG path for the parts: whole-number steps, simplified to tol units."""
    out = []
    for part in geo.simplify(geo.join_parts(parts), tol * plane.m_per_unit):
        pts = []
        for p in part:
            x, y = plane.xy(p)
            q = (round(x), round(y))
            if not pts or q != pts[-1]:
                pts.append(q)
        if len(pts) < 2:
            continue
        steps = " ".join(f"{b[0] - a[0]} {b[1] - a[1]}" for a, b in zip(pts, pts[1:]))
        out.append(f"M{pts[0][0]} {pts[0][1]}l{steps}")
    return "".join(out)


def _parts(feature):
    g = feature.get("geometry") or {}
    if g.get("type") == "LineString":
        return [g["coordinates"]]
    return list(g.get("coordinates") or []) if g.get("type") == "MultiLineString" else []


def _points(feature):
    g = feature.get("geometry") or {}
    if g.get("type") == "Point":
        return [g["coordinates"]]
    return list(g.get("coordinates") or []) if g.get("type") == "MultiPoint" else []


def svg(features, fr, *, route_main=False, ident=False):
    """The sketch of these features on the frame `fr`, as Markup, or "" with nothing to draw.

    route_main: a route page draws its main track in the route colour and dashed, as the map does.
    ident: write each trail's id on its paths (data-id), for the filters of an overview to hide them.
    """
    if not features:
        return ""
    plane = Plane(fr)
    many = len(features) > MANY
    tol = TOL_MANY if many else TOL
    casings, lines, rings = [], [], []
    for f in features:
        props = f.get("properties") or {}
        rid = f' data-id="{props["id"]}"' if ident and props.get("id") else ""
        route = props.get("kind") == "route" or (route_main and (props.get("role") == "main" or props.get("sketch")))
        sketch = bool(props.get("sketch"))
        d = _path(plane, _parts(f), tol=tol if not sketch else 0.0)
        if d:
            if not sketch and not many:
                casings.append(f'<path class="fallback__casing" d="{d}"{rid}/>')
            mod = (" fallback__line--sketch" + (" fallback__line--sketch-route" if route else "")) if sketch \
                else " fallback__line--alternate" if props.get("role") == "alternate" \
                else " fallback__line--route" if route else ""
            lines.append(f'<path class="fallback__line{mod}" d="{d}"{rid}/>')
        for pt in _points(f):
            x, y = plane.xy(pt)
            cls = "fallback__ring" + (" fallback__ring--route" if props.get("kind") == "route" or route_main else "")
            rings.append(f'<circle class="{cls}" cx="{x:.0f}" cy="{y:.0f}" r="4"{rid}/>')
    if not lines and not rings:
        return ""
    return Markup(f'<svg class="map__sketch" viewBox="0 0 {plane.w:.2f} {plane.h:.2f}" '
                  f'preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false">'
                  f'{"".join(casings)}{"".join(lines)}{"".join(rings)}</svg>')
