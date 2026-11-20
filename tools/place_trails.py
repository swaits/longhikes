#!/usr/bin/env python3
"""Place every trail: measure tracks against published park, wilderness and range outlines.

This tool is not part of the site build. It is the only file in the repository that may use
libraries outside the Python standard library (shapely, pyproj, pyogrio). Install them in
the venv this tool names, never system-wide:

    python3 -m venv .venv-places
    .venv-places/bin/pip install -r tools/place_trails.requirements.txt
    .venv-places/bin/python tools/place_trails.py --help

A trail is in a place when at least 1 mile (1.609344 km) of its main track lies inside the
outline. Alternates never count. Outlines are downloaded into a cache outside the repo
($PLACES_CACHE, default $XDG_CACHE_HOME/longhikes-places) and are never committed.
"""
import json
import os
import sys
import tomllib

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import check_places  # noqa: E402

MIN_KM = 1.609344  # exactly 1 mile

_GEOD = None
_SHAPELY = None


def _need_shapely():
    """Import shapely and pyproj, or exit with the install line."""
    global _GEOD, _SHAPELY
    if _SHAPELY is None:
        try:
            import shapely
            from pyproj import Geod
        except ImportError:
            sys.exit("place_trails.py needs shapely, pyproj and pyogrio, which the site build "
                     "never uses. Install them in this tool's venv:\n"
                     "    python3 -m venv .venv-places\n"
                     "    .venv-places/bin/pip install -r tools/place_trails.requirements.txt")
        _SHAPELY = shapely
        _GEOD = Geod(ellps="WGS84")
    return _SHAPELY


def line_file_of(rec_dir):
    with open(os.path.join(rec_dir, "trail.toml"), "rb") as f:
        return str(tomllib.load(f).get("source", {}).get("line_file") or "")


def track_hash(rec_dir):
    """The record's track hash: the same value the validator checks."""
    return check_places.track_hash(os.path.join(rec_dir, line_file_of(rec_dir)))


def main_track(rec_dir):
    """The record's main track as a shapely MultiLineString, or None with no track.

    Only the file source.line_file names is read; alternates.geojson and any
    line-<source>.geojson are never touched."""
    shapely = _need_shapely()
    name = line_file_of(rec_dir)
    if not name:
        return None
    with open(os.path.join(rec_dir, name), encoding="utf-8") as f:
        data = json.load(f)
    lines = []
    for feat in data.get("features", []):
        geom = shapely.geometry.shape(feat["geometry"])
        if geom.geom_type == "LineString":
            lines.append(geom)
        elif geom.geom_type == "MultiLineString":
            lines.extend(geom.geoms)
        elif geom.geom_type == "GeometryCollection":
            lines.extend(g for g in geom.geoms if g.geom_type in ("LineString", "MultiLineString"))
    if not lines:
        return None
    flat = []
    for g in lines:
        flat.extend(g.geoms if g.geom_type == "MultiLineString" else [g])
    return shapely.geometry.MultiLineString(flat)


def _geodesic_km(geom):
    """Length in km of every line part of a lon/lat geometry, on the WGS84 ellipsoid."""
    if geom.is_empty:
        return 0.0
    if geom.geom_type == "LineString":
        coords = list(geom.coords)
        total = 0.0
        for (x1, y1), (x2, y2) in zip(coords, coords[1:]):
            total += _GEOD.inv(x1, y1, x2, y2)[2]
        return total / 1000.0
    if geom.geom_type in ("MultiLineString", "GeometryCollection"):
        return sum(_geodesic_km(g) for g in geom.geoms)
    return 0.0  # points where a track only touches a boundary


def km_inside(track, outline):
    """Kilometres of `track` inside `outline`, summed over every piece, holes respected."""
    _need_shapely()
    return _geodesic_km(track.intersection(outline))


def box_of(outline):
    """[west, south, east, north], rounded to 2 decimals as places.toml stores it."""
    return [round(float(v), 2) for v in outline.bounds]


HELP = __doc__ + """
Subcommands (see the plan, Ship 1): propose, candidates, apply, stated, stamp, --check.
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("--help", "-h", "help"):
        print(HELP)
        return 0
    print(f"place_trails.py: no subcommand {argv[0]!r} yet", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
