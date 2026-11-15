#!/usr/bin/env python3
"""Build trails.csv, index.geojson and the trail table in README.md.

Python 3 standard library only. Run from anywhere:
    python3 tools/build_index.py
"""
import csv
import io
import json
import math
import os
import sys

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11: minimal fallback for this repo's TOML subset
    tomllib = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BEGIN = "<!-- BEGIN TRAIL TABLE -->"
END = "<!-- END TRAIL TABLE -->"
COUNT_BEGIN = "<!-- BEGIN COUNTS -->"
COUNT_END = "<!-- END COUNTS -->"
ROUTE_BEGIN = "<!-- BEGIN ROUTE TABLE -->"
ROUTE_END = "<!-- END ROUTE TABLE -->"
DESIGNATED = "designated"


def load_toml(path):
    if tomllib is not None:
        with open(path, "rb") as f:
            return tomllib.load(f)
    rec, table = {}, None
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[[") and line.endswith("]]"):
            # array of tables, for example [[guide]]
            table = {}
            rec.setdefault(line[2:-2].strip(), []).append(table)
            continue
        if line.startswith("[") and line.endswith("]"):
            table = rec.setdefault(line[1:-1].strip(), {})
            continue
        key, _, val = line.partition("=")
        val = val.strip()
        if val.startswith('"'):
            out = json.loads(val)
        elif val in ("true", "false"):
            out = val == "true"
        elif val.startswith("["):
            out = json.loads(val)
        else:
            try:
                out = int(val)
            except ValueError:
                out = float(val)
        (table if table is not None else rec)[key.strip()] = out
    return rec


def trail_dirs(root=ROOT):
    return sorted(
        d for d in os.listdir(root)
        if os.path.isfile(os.path.join(root, d, "trail.toml"))
    )


def load_trails(root=ROOT):
    trails = []
    for tid in trail_dirs(root):
        trails.append(load_toml(os.path.join(root, tid, "trail.toml")))
    return trails


def trail_kind(t):
    return t.get("kind") or DESIGNATED


def line_policy(t):
    return t.get("route", {}).get("line_policy", "") if trail_kind(t) == "route" else ""


def csv_text(trails):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["id", "name", "country", "regions", "length_km", "status",
                "line_source", "licence", "kind", "line_policy"])
    for t in trails:
        src = t.get("source", {})
        status = "included" if src.get("line_file") else "record-only"
        w.writerow([t["id"], t["name"], t["country"], ";".join(t.get("regions", [])),
                    t["length_km"], status, src.get("line_source", ""),
                    src.get("licence", ""), trail_kind(t), line_policy(t)])
    return buf.getvalue()


def _seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    u = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + u * dx), py - (ay + u * dy))


def simplify(points, tol):
    """Douglas-Peucker. points are (lon, lat); tol is in degrees (scaled)."""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = points[a]
        bx, by = points[b]
        best, idx = -1.0, -1
        for i in range(a + 1, b):
            d = _seg_dist(points[i][0], points[i][1], ax, ay, bx, by)
            if d > best:
                best, idx = d, i
        if idx > 0 and best > tol:
            keep[idx] = True
            stack.append((a, idx))
            stack.append((idx, b))
    return [p for p, k in zip(points, keep) if k]


def simplify_line(coords, tol_m=100.0):
    if len(coords) < 3:
        return coords
    lat0 = math.radians(coords[len(coords) // 2][1])
    sx = 111320.0 * max(0.2, math.cos(lat0))
    sy = 110540.0
    pts = [(lon * sx, lat * sy) for lon, lat in coords]
    kept = simplify(pts, tol_m)
    keep_set = set(kept)
    out = [c for c, p in zip(coords, pts) if p in keep_set]
    # set membership can drop duplicate points; fall back if too short
    return out if len(out) >= 2 else [coords[0], coords[-1]]


def index_geojson_text(trails, root=ROOT):
    features = []
    for t in trails:
        src = t.get("source", {})
        line_file = src.get("line_file") or ""
        if not line_file:
            continue
        path = os.path.join(root, t["id"], line_file)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for feat in data.get("features", []):
            geom = feat.get("geometry") or {}
            gtype = geom.get("type")
            if gtype == "LineString":
                coords = simplify_line(geom["coordinates"])
                new_geom = {"type": "LineString", "coordinates": coords}
            elif gtype == "MultiLineString":
                parts = [simplify_line(c) for c in geom["coordinates"] if len(c) >= 2]
                if not parts:
                    continue
                new_geom = {"type": "MultiLineString", "coordinates": parts}
            else:
                continue
            props = {"id": t["id"], "name": t["name"], "kind": trail_kind(t)}
            if trail_kind(t) == "route":
                props["line_policy"] = line_policy(t)
            features.append({
                "type": "Feature",
                "properties": props,
                "geometry": new_geom,
            })
    fc = {"type": "FeatureCollection", "features": features}
    return json.dumps(fc, ensure_ascii=False, separators=(",", ":")) + "\n"


def _cell(value):
    return str(value).replace("|", "\\|")


def readme_table(trails):
    lines = [
        "| ID | Trail | Country | States / provinces | Length (km) | Track | Licence |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for t in trails:
        if trail_kind(t) != DESIGNATED:
            continue
        src = t.get("source", {})
        line = "yes" if src.get("line_file") else "no"
        regions = ", ".join(t.get("regions", []))
        lines.append(
            f"| {t['id']} | {_cell(t['name'])} | {t['country']} | {regions} | "
            f"{t['length_km']} | {line} | {src.get('licence','')} |"
        )
    return "\n".join(lines)


def first_guide(t):
    guides = t.get("guide") or []
    if not guides:
        return ""
    g = guides[0]
    title = _cell(g.get("title", ""))
    url = g.get("url", "")
    access = g.get("access", "")
    return f"[{title}]({url}) ({access})" if url else f"{title} ({access})"


def readme_route_table(trails):
    lines = [
        "| ID | Route | Country | States / provinces | Length (km) | Author | Track policy | Track | First guide |",
        "| --- | --- | --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for t in trails:
        if trail_kind(t) != "route":
            continue
        src = t.get("source", {})
        line = "yes" if src.get("line_file") else "no"
        regions = ", ".join(t.get("regions", []))
        lines.append(
            f"| {t['id']} | {_cell(t['name'])} | {t['country']} | {regions} | "
            f"{t['length_km']} | {_cell(t.get('route', {}).get('creator', ''))} | "
            f"{line_policy(t)} | {line} | {first_guide(t)} |"
        )
    return "\n".join(lines)


def counts_line(trails):
    total = len(trails)
    with_line = sum(1 for t in trails if t.get("source", {}).get("line_file"))
    routes = [t for t in trails if trail_kind(t) == "route"]
    routes_with_line = sum(1 for t in routes if t.get("source", {}).get("line_file"))
    return (
        f"{total} trails, {with_line} with a track and {total - with_line} with no track included. "
        f"Of these, {len(routes)} are routes: {routes_with_line} with a track "
        f"and {len(routes) - routes_with_line} without."
    )


def replace_block(text, begin, end, body, path):
    if begin not in text or end not in text:
        raise SystemExit(f"README markers {begin!r} and {end!r} not found in {path}")
    before, rest = text.split(begin, 1)
    _, after = rest.split(end, 1)
    return before + begin + "\n\n" + body + "\n\n" + end + after


def render_readme(readme_path, trails):
    with open(readme_path, encoding="utf-8") as f:
        text = f.read()
    text = replace_block(text, COUNT_BEGIN, COUNT_END, counts_line(trails), readme_path)
    text = replace_block(text, BEGIN, END, readme_table(trails), readme_path)
    text = replace_block(text, ROUTE_BEGIN, ROUTE_END, readme_route_table(trails), readme_path)
    return text


def main():
    trails = load_trails()
    csv_path = os.path.join(ROOT, "trails.csv")
    idx_path = os.path.join(ROOT, "index.geojson")
    readme_path = os.path.join(ROOT, "README.md")
    csv_data = csv_text(trails)
    idx_data = index_geojson_text(trails)
    readme_data = render_readme(readme_path, trails)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        f.write(csv_data)
    with open(idx_path, "w", encoding="utf-8") as f:
        f.write(idx_data)
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_data)
    with_line = sum(1 for t in trails if t.get("source", {}).get("line_file"))
    print(f"Wrote trails.csv, index.geojson and README table: "
          f"{len(trails)} trails, {with_line} with a track.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
