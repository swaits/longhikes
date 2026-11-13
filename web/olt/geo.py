"""Line geometry helpers: reading GeoJSON, length, bbox, simplification, GPX.

Python 3 standard library only. A "part" is a list of coordinates, each
[lon, lat] or [lon, lat, ele]; a line is a list of parts.
"""
import json
import math
from xml.sax.saxutils import escape, quoteattr

EARTH_R = 6371008.8  # metres
LICENCE_URLS = {
    "us-gov-public-domain": "https://www.usa.gov/government-works",
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC-BY": "https://creativecommons.org/licenses/by/4.0/",
    "ODbL-1.0": "https://opendatacommons.org/licenses/odbl/1-0/",
}


def read_parts(path):
    """Read a GeoJSON file; return its LineString and MultiLineString parts."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return parts_from_geojson(data)


def parts_from_geojson(data):
    if data.get("type") == "FeatureCollection":
        geoms = [(f.get("geometry") or {}) for f in data.get("features", [])]
    elif data.get("type") == "Feature":
        geoms = [data.get("geometry") or {}]
    else:
        geoms = [data]
    parts = []
    for geom in geoms:
        gtype = geom.get("type")
        if gtype == "LineString":
            parts.append(geom["coordinates"])
        elif gtype == "MultiLineString":
            parts.extend(geom["coordinates"])
    return [p for p in parts if len(p) >= 2]


def point_count(parts):
    return sum(len(p) for p in parts)


def length_km(parts):
    """Geodesic (haversine) length of all parts, in kilometres."""
    total = 0.0
    for coords in parts:
        lon1, lat1 = math.radians(coords[0][0]), math.radians(coords[0][1])
        for c in coords[1:]:
            lon2, lat2 = math.radians(c[0]), math.radians(c[1])
            a = (math.sin((lat2 - lat1) / 2) ** 2
                 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
            total += 2 * EARTH_R * math.asin(min(1.0, math.sqrt(a)))
            lon1, lat1 = lon2, lat2
    return total / 1000.0


def bbox(parts):
    """[min lon, min lat, max lon, max lat], or None when there are no points."""
    xs = [c[0] for p in parts for c in p]
    ys = [c[1] for p in parts for c in p]
    if not xs:
        return None
    return [min(xs), min(ys), max(xs), max(ys)]


def merge_bbox(boxes):
    boxes = [b for b in boxes if b]
    if not boxes:
        return None
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def _gap_m(a, b):
    """Approximate distance in metres between two [lon, lat] points."""
    dx = (a[0] - b[0]) * math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot(dx, a[1] - b[1]) * math.pi / 180.0 * EARTH_R


def join_parts(parts, gap_m=100.0):
    """Chain parts whose end points lie within gap_m of each other.

    Greedy: each chain grows at its tail, then at its head, taking the nearest
    unused part end each time (a part is reversed when its far end is the
    near one). Parts that touch nothing stay as they are.

    Ends are bucketed in a metre-scaled grid: longitude is multiplied by the
    cosine of the highest latitude in the data and both axes use metres, so a
    grid step is never longer than gap_m on the ground. A fixed step in
    degrees would miss joins at high latitude, where gap_m spans more than one
    cell of longitude; here the neighbour scan of plus or minus one cell is
    correct at any latitude.
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
            c = p[0] if end == 0 else p[-1]
            grid.setdefault(cell_of(c), []).append((i, end))
    used = [False] * len(parts)

    def nearest(point):
        gx, gy = cell_of(point)
        best = None
        for x in (gx - 1, gx, gx + 1):
            for y in (gy - 1, gy, gy + 1):
                for i, end in grid.get((x, y), ()):
                    if used[i]:
                        continue
                    c = parts[i][0] if end == 0 else parts[i][-1]
                    d = _gap_m(point, c)
                    if d <= gap_m and (best is None or d < best[0]):
                        best = (d, i, end)
        return best

    out = []
    for i0, first in enumerate(parts):
        if used[i0]:
            continue
        used[i0] = True
        chain = list(first)
        while True:  # grow the tail
            hit = nearest(chain[-1])
            if hit is None:
                break
            _, i, end = hit
            used[i] = True
            chain.extend(parts[i] if end == 0 else parts[i][::-1])
        while True:  # grow the head
            hit = nearest(chain[0])
            if hit is None:
                break
            _, i, end = hit
            used[i] = True
            chain[:0] = parts[i][::-1] if end == 0 else parts[i]
        out.append(chain)
    return out


def simplify_part(coords, tol_m):
    """Douglas-Peucker with an explicit stack; tol_m is in metres.

    Distances are measured on a local equirectangular plane for the segment
    being tested, scaled by the mean cosine at its two ends. A single scale for
    a whole part would understate distances when the part runs hundreds of
    kilometres north to south; taking the cosine per segment bounds the
    residual error by the change in cosine across that segment.

    When a segment spans enough latitude that its two ends differ in cosine by
    more than 1%, distances are instead measured in a tangent plane centred on
    each candidate point (east = (lon - lon_point) * cos(point latitude)).
    That is the exact local metric, so even a very long north-south segment
    cannot drop a point whose true distance exceeds the tolerance. Short
    segments, where the two methods agree to within 1%, use the cheaper shared
    scale; 1% of the tolerance is a few centimetres at the 5 m GPX tolerance.

    The end points are always kept; only interior points are dropped, and the
    kept points are the originals. The algorithm is iterative, and the plane
    origin is folded into precomputed arrays so the inner loop stays cheap
    enough for parts with hundreds of thousands of points.
    """
    n = len(coords)
    if n < 3:
        return list(coords)
    k = math.pi / 180.0 * EARTH_R
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    # Metres per degree of longitude (ck) and metres north (ys), per point.
    ck = [math.cos(math.radians(lat)) * k for lat in lats]
    ys = [lat * k for lat in lats]
    tol2 = tol_m * tol_m
    keep = bytearray(n)
    keep[0] = keep[n - 1] = 1
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        la, lb = lons[a], lons[b]
        dlon = lb - la
        ya, yb = ys[a], ys[b]
        dy = yb - ya
        ca, cb = ck[a], ck[b]
        # Relative change in cosine across the segment. Below 1% one scale for
        # the whole segment is as accurate as the tolerance needs (a point
        # within tol_m of the segment is within a few metres of its latitude,
        # so the scale error at that point is no larger than this).
        shared = abs(ca - cb) <= 0.01 * (ca if ca > cb else cb)
        cm = 0.5 * (ca + cb) if shared else 0.0
        best, idx = -1.0, -1
        for i in range(a + 1, b):
            ci = cm if shared else ck[i]
            ax = (la - lons[i]) * ci  # a, relative to the plane origin
            ay = ya - ys[i]
            dx = dlon * ci
            len2 = dx * dx + dy * dy
            if len2 == 0.0:
                d2 = ax * ax + ay * ay
            else:
                u = -(ax * dx + ay * dy) / len2
                if u <= 0.0:
                    d2 = ax * ax + ay * ay
                elif u >= 1.0:
                    ex, ey = ax + dx, ay + dy
                    d2 = ex * ex + ey * ey
                else:
                    cross = ax * dy - ay * dx
                    d2 = cross * cross / len2
            if d2 > best:
                best, idx = d2, i
        if best > tol2:
            keep[idx] = 1
            stack.append((a, idx))
            stack.append((idx, b))
    return [c for c, k_ in zip(coords, keep) if k_]


def simplify(parts, tol_m):
    return [simplify_part(p, tol_m) for p in parts]


def round_coords(parts, decimals):
    """Round lon and lat (elevation is kept); drop repeated neighbours.

    A part that rounds down to fewer than two distinct points is dropped
    entirely: a zero-length part is not useful on a map or in a GPX track
    segment, and keeping two copies of one coordinate would produce one.
    """
    out = []
    for coords in parts:
        new = []
        last = None
        for c in coords:
            r = [round(c[0], decimals), round(c[1], decimals)] + list(c[2:])
            key = (r[0], r[1])
            if key != last:
                new.append(r)
                last = key
        if len(new) >= 2:
            out.append(new)
    return out


def has_elevation(parts):
    return any(len(c) > 2 for p in parts for c in p)


def _num(v):
    """Plain decimal text (no exponent, as GPX requires) for a number."""
    text = f"{float(v):.8f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def gpx_text(parts, name, url="", attribution="", licence="", licence_text="",
             creator="long-trails dataset"):
    """GPX 1.1 with one <trk> and one <trkseg> per part."""
    desc = []
    if attribution:
        desc.append(f"Attribution: {attribution}")
    if licence_text:
        desc.append(f"Licence: {licence_text}")
    elif licence:
        desc.append(f"Licence: {licence}")
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<gpx version="1.1" creator={quoteattr(creator)} '
        'xmlns="http://www.topografix.com/GPX/1/1">',
        "<metadata>",
        f"<name>{escape(name)}</name>",
    ]
    if desc:
        out.append(f"<desc>{escape(' '.join(desc))}</desc>")
    if attribution:
        out.append(f"<copyright author={quoteattr(attribution)}>")
        if licence in LICENCE_URLS:
            out.append(f"<license>{escape(LICENCE_URLS[licence])}</license>")
        out.append("</copyright>")
    if url:
        out.append(f"<link href={quoteattr(url)}/>")
    out.append("</metadata>")
    out.append("<trk>")
    out.append(f"<name>{escape(name)}</name>")
    for coords in parts:
        out.append("<trkseg>")
        for c in coords:
            head = f'<trkpt lat="{_num(c[1])}" lon="{_num(c[0])}"'
            if len(c) > 2:
                out.append(f"{head}><ele>{_num(c[2])}</ele></trkpt>")
            else:
                out.append(f"{head}/>")
        out.append("</trkseg>")
    out.append("</trk>")
    out.append("</gpx>")
    return "\n".join(out) + "\n"
