#!/usr/bin/env python3
"""Fetch a trail's track from an OpenStreetMap route relation.

Reads the relation and every member way (with node coordinates) through the
Overpass API, following sub-relations to any depth, and writes, in the
trail's directory:

    line.geojson        main ways, one LineString per way, in member order
    alternates.geojson  ways with a side role (only when there are some)
    release.txt         source, licence, attribution and date read

Python standard library only. Run from anywhere:
    python3 tools/osm_track.py RELATION_ID --id TRAIL_ID           write the files
    python3 tools/osm_track.py RELATION_ID --id TRAIL_ID --dry     print figures only
    python3 tools/osm_track.py RELATION_ID --id TRAIL_ID --out DIR write to DIR/TRAIL_ID
    python3 tools/osm_track.py RELATION_ID --id TRAIL_ID --force   replace existing files

The trail directory (and its trail.toml) must exist first. It prints what the
record's [verification] and [osm] sections need: ways in main and in
alternates, measured length of the main track, and the number of parts left
after joining way ends within 100 m (the rule tools/elevation.py uses).

Roles. A member way or sub-relation with an empty or main-type role (see
MAIN_ROLES) is main. Anything with a side role (SIDE_ROLES) is alternate, and
so is every way inside a side sub-relation. An unknown role is treated as
side, with a warning. The count per role is printed. A way listed more than
once is kept once, at its first place; a way that is main in one place and
side in another (a side relation sharing ways with the main route) is main.

The output depends only on the relation's content, so the same relation
version gives the same files (release.txt carries the date read).
"""
import argparse
import datetime
import importlib.util
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ENDPOINTS = ["https://overpass-api.de/api/interpreter",
             "https://overpass.kumi.systems/api/interpreter"]
USER_AGENT = "osm-track-fetch/1.0 (python-urllib)"
TIMEOUT_S = 300
RETRY_STATUS = (429, 502, 503, 504)
RETRY_WAITS_S = (10, 30, 60)       # per endpoint, between tries
JOIN_GAP_M = 100.0                  # same distance as tools/elevation.py
EARTH_R = 6371008.8                 # metres; same as tools/elevation.py

MAIN_ROLES = {"", "main", "forward", "backward"}
SIDE_ROLES = {"alternate", "alternative", "excursion", "approach", "connection",
              "link", "side_trail", "spur", "detour", "variant"}

HEADER = ('{"type":"FeatureCollection","name":"lines","crs":{"type":"name","properties":'
          '{"name":"urn:ogc:def:crs:OGC:1.3:CRS84"}},"features":[')


class TrackError(Exception):
    """A reason to stop, shown to the user without a traceback."""


def _load_validate_haversine():
    spec = importlib.util.spec_from_file_location(
        "validate_for_osm_track", os.path.join(ROOT, "tools", "validate.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.haversine_km


haversine_km = _load_validate_haversine()   # the validator's own length rule


# ---------------------------------------------------------------- joining
# Mirrors join_parts in tools/elevation.py (which needs numpy, so it cannot be
# imported here). tools/tests/test_osm_track.py checks the two agree.

def _gap_m(a, b):
    dx = (a[0] - b[0]) * math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot(dx, a[1] - b[1]) * math.pi / 180.0 * EARTH_R


def join_parts(parts, gap_m=JOIN_GAP_M):
    """Chain parts whose end points lie within gap_m of each other."""
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


# ---------------------------------------------------------------- fetching

def query_for(relation_id):
    return (f"[out:json][timeout:{TIMEOUT_S}];rel({int(relation_id)});out meta;"
            ">>;out body qt;")


def fetch(relation_id, opener=urllib.request.urlopen, sleep=time.sleep,
          endpoints=ENDPOINTS):
    """Overpass JSON for the relation and everything below it. One request at a time."""
    body = urllib.parse.urlencode({"data": query_for(relation_id)}).encode()
    last = None
    for url in endpoints:
        for attempt in range(len(RETRY_WAITS_S) + 1):
            req = urllib.request.Request(url, data=body, headers={
                "User-Agent": USER_AGENT, "Accept": "application/json"})
            try:
                with opener(req, timeout=TIMEOUT_S) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                last = f"{url}: HTTP {e.code}"
                if e.code not in RETRY_STATUS:
                    raise TrackError(f"Overpass refused the request ({last})") from e
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
                last = f"{url}: {e}"
            if attempt < len(RETRY_WAITS_S):
                wait = RETRY_WAITS_S[attempt]
                print(f"  {last}; trying again in {wait} s", file=sys.stderr)
                sleep(wait)
        print(f"  giving up on {url}", file=sys.stderr)
    raise TrackError(f"Overpass did not answer ({last})")


# ---------------------------------------------------------------- parsing

def parse(doc, relation_id, warn=None):
    """Turn an Overpass JSON response into the track.

    Returns a dict: version, timestamp, main and side (lists of way dicts with
    osm_id, name, highway, coords), roles (a Counter-like dict of
    "type:role" -> count). Raises TrackError for a relation that is not a
    route, or that has no way members.
    """
    warn = warn or (lambda m: print("warning: " + m, file=sys.stderr))
    nodes, ways, rels = {}, {}, {}
    for el in doc.get("elements", []):
        kind, eid = el.get("type"), el.get("id")
        if kind == "node" and "lat" in el:
            nodes[eid] = (el["lon"], el["lat"])
        elif kind == "way":
            ways[eid] = el
        elif kind == "relation":
            if eid not in rels or "version" in el:
                rels[eid] = el
    root = rels.get(int(relation_id))
    if root is None:
        raise TrackError(f"relation {relation_id} is not in the response (does it exist?)")
    rtype = (root.get("tags") or {}).get("type")
    if rtype not in ("route", "superroute"):
        raise TrackError(f"relation {relation_id} is type={rtype!r}, not type=route")

    roles, main, side = {}, [], []
    seen_main, seen_side = set(), set()

    def count(kind, role):
        key = f"{kind}:{role or '(empty)'}"
        roles[key] = roles.get(key, 0) + 1

    def classify(role, inherited_side, what):
        if role in MAIN_ROLES:
            return inherited_side
        if role not in SIDE_ROLES:
            warn(f"unknown role {role!r} on {what}; treated as side")
        return True

    def walk(rel, is_side, stack):
        for m in rel.get("members", []):
            role = m.get("role", "")
            if m.get("type") == "way":
                count("way", role)
                wid = m["ref"]
                is_way_side = classify(role, is_side, f"way {wid}")
                kept = seen_side if is_way_side else seen_main
                if wid in kept:
                    continue
                kept.add(wid)
                way = ways.get(wid)
                if way is None:
                    warn(f"way {wid} is not in the response; skipped")
                    continue
                coords = []
                for n in way.get("nodes", []):
                    if n in nodes:
                        lon, lat = nodes[n]
                        pt = [round(lon, 6), round(lat, 6)]
                        coords.append(pt)
                    else:
                        warn(f"node {n} of way {wid} is missing; skipped")
                if len(coords) < 2:
                    warn(f"way {wid} has fewer than 2 points; skipped")
                    continue
                tags = way.get("tags") or {}
                rec = {"osm_id": str(wid), "coords": coords}
                if tags.get("name"):
                    rec["name"] = tags["name"]
                if tags.get("highway"):
                    rec["highway"] = tags["highway"]
                (side if is_way_side else main).append(rec)
            elif m.get("type") == "relation":
                count("relation", role)
                sub = rels.get(m["ref"])
                if sub is None:
                    warn(f"sub-relation {m['ref']} is not in the response; skipped")
                    continue
                if sub["id"] in stack:
                    warn(f"sub-relation {sub['id']} contains itself; skipped")
                    continue
                walk(sub, classify(role, is_side, f"relation {sub['id']}"),
                     stack | {sub["id"]})

    walk(root, False, {root["id"]})
    if not (seen_main or seen_side):
        raise TrackError(f"relation {relation_id} has no way members")
    # A way that is main anywhere is main: a side relation (a link trail, say)
    # often shares ways with the main route.
    side[:] = [w for w in side if int(w["osm_id"]) not in seen_main]
    if not main and not side:
        raise TrackError(f"relation {relation_id} has no usable ways")
    return {"version": root.get("version"), "timestamp": root.get("timestamp"),
            "main": main, "side": side, "roles": roles,
            "name": (root.get("tags") or {}).get("name", "")}


# ---------------------------------------------------------------- output

def geojson_text(ways):
    feats = []
    for w in ways:
        props = {"osm_id": w["osm_id"]}
        for key in ("name", "highway"):
            if key in w:
                props[key] = w[key]
        feats.append(json.dumps(
            {"type": "Feature", "properties": props,
             "geometry": {"type": "LineString", "coordinates": w["coords"]}},
            separators=(",", ":"), ensure_ascii=False))
    return HEADER + ",".join(feats) + "]}\n"


def release_text(trail_id, relation_id, date):
    return (f"{trail_id}\n\n"
            f"Source: https://www.openstreetmap.org/relation/{relation_id}\n"
            "Licence: ODbL-1.0 (see trail.toml and SOURCES.md in this repository)\n"
            "Attribution: OpenStreetMap contributors (ODbL)\n"
            f"Source read: {date}\n"
            "Published copy: coordinates rounded to 6 decimal places and written as "
            "compact JSON. Geometry is otherwise as served.\n")


def figures(track):
    main = track["main"]
    return {"main_ways": len(main), "alternate_ways": len(track["side"]),
            "measured_km": sum(haversine_km(w["coords"]) for w in main),
            "parts": len(join_parts([w["coords"] for w in main])) if main else 0}


# ---------------------------------------------------------------- command line

def run(args, fetcher=fetch, today=None, out=print):
    tdir = os.path.join(os.path.abspath(args.out), args.id)
    if not os.path.isdir(tdir):
        raise TrackError(f"{tdir} does not exist: create the trail directory and "
                         "trail.toml first")
    names = ("line.geojson", "alternates.geojson", "release.txt")
    if not args.dry and not args.force:
        have = [n for n in names if os.path.exists(os.path.join(tdir, n))]
        if have:
            raise TrackError(f"{', '.join(have)} already in {tdir}: use --force to "
                             "replace")
    track = parse(fetcher(args.relation), args.relation)
    fig = figures(track)
    for key in sorted(track["roles"]):
        out(f"role {key}: {track['roles'][key]}")
    out(f"relation {args.relation} {track['name']!r}: version {track['version']}, "
        f"timestamp {track['timestamp']}")
    out(f"main ways: {fig['main_ways']}")
    out(f"alternate ways: {fig['alternate_ways']}")
    out(f"measured_km: {fig['measured_km']:.1f}")
    out(f"parts (ends within {JOIN_GAP_M:.0f} m): {fig['parts']}")
    if args.dry:
        out("dry run: nothing written")
        return track
    date = (today or datetime.date.today()).isoformat()
    files = {"release.txt": release_text(args.id, args.relation, date)}
    if track["main"]:
        files["line.geojson"] = geojson_text(track["main"])
    else:
        out("warning: no main ways; line.geojson not written")
    if track["side"]:
        files["alternates.geojson"] = geojson_text(track["side"])
    elif os.path.exists(os.path.join(tdir, "alternates.geojson")):
        out("warning: no side ways now, but an old alternates.geojson is still there")
    for name, text in files.items():
        with open(os.path.join(tdir, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    out("wrote " + ", ".join(files) + f" in {tdir}")
    return track


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fetch a trail's track from an OSM route relation.")
    ap.add_argument("relation", type=int, help="OSM relation id")
    ap.add_argument("--id", required=True, help="trail id (the directory name)")
    ap.add_argument("--out", default=ROOT, help="directory holding the trail directories "
                    "(default: the repository root)")
    ap.add_argument("--dry", action="store_true", help="print the figures, write nothing")
    ap.add_argument("--force", action="store_true", help="replace existing files")
    args = ap.parse_args(argv)
    try:
        run(args)
    except TrackError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
