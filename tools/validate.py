#!/usr/bin/env python3
"""Validate every trail directory in this repository.

Python 3 standard library only. Run from anywhere:
    python3 tools/validate.py
Prints "OK <n> trails" and exits 0, or prints one error per line and exits 1.
"""
import sys

sys.dont_write_bytecode = True

import importlib.util
import json
import math
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_BYTES = 50 * 1024 * 1024
ALLOWED_LICENCES = {
    "us-gov-public-domain", "CC-BY-4.0", "CC-BY", "ODbL-1.0",
    "CC-BY-NC-ND-4.0", "none-stated", "restricted", "unknown",
}
DATA_LICENCES = {"us-gov-public-domain", "CC-BY-4.0", "CC-BY", "ODbL-1.0"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

spec = importlib.util.spec_from_file_location(
    "build_index", os.path.join(ROOT, "tools", "build_index.py"))
build_index = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_index)
load_toml = build_index.load_toml


def haversine_km(coords):
    total, R = 0.0, 6371.0088
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        p1, p2 = math.radians(lat1), math.radians(lat2)
        a = (math.sin(math.radians(lat2 - lat1) / 2) ** 2
             + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
        total += 2 * R * math.asin(min(1.0, math.sqrt(a)))
    return total


def check_geometry(geom, where, errors):
    """Check ranges and minimum part size; return measured length in km."""
    if geom is None:
        return 0.0
    gtype = geom.get("type")
    if gtype == "GeometryCollection":
        return sum(check_geometry(g, where, errors) for g in geom.get("geometries", []))
    if gtype not in ("LineString", "MultiLineString", "Point", "MultiPoint", "Polygon", "MultiPolygon"):
        errors.append(f"{where}: unknown geometry type {gtype!r}")
        return 0.0
    parts = []
    coords = geom.get("coordinates")
    if gtype == "LineString":
        parts = [coords]
    elif gtype == "MultiLineString":
        parts = coords
    elif gtype == "Point":
        parts = [[coords]]
    elif gtype in ("MultiPoint", "Polygon"):
        parts = [coords] if coords else []
    elif gtype == "MultiPolygon":
        parts = [ring for poly in (coords or []) for ring in poly]

    def walk(c):
        if isinstance(c, (int, float)):
            return
        if isinstance(c, list) and c and isinstance(c[0], (int, float)):
            lon, lat = float(c[0]), float(c[1])
            if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
                errors.append(f"{where}: coordinate out of range [{lon}, {lat}]")
            return
        for x in c or []:
            walk(x)

    length = 0.0
    for part in parts or []:
        if gtype in ("LineString", "MultiLineString") and len(part) < 2:
            errors.append(f"{where}: line part has fewer than 2 points")
        walk(part)
        if gtype in ("LineString", "MultiLineString"):
            length += haversine_km(part)
    return length


def main():
    errors = []
    trail_ids = build_index.trail_dirs(ROOT)
    if not trail_ids:
        print("no trail directories found")
        return 1
    trails = []
    for tid in trail_ids:
        tdir = os.path.join(ROOT, tid)
        toml_path = os.path.join(tdir, "trail.toml")
        try:
            rec = load_toml(toml_path)
        except Exception as e:  # noqa: BLE001 - report and continue
            errors.append(f"{tid}: trail.toml does not parse: {e}")
            continue
        trails.append(rec)

        for field in ("id", "name", "short_name", "country", "regions",
                      "length_km", "tier", "designation"):
            if field not in rec or rec[field] in ("", None, []):
                errors.append(f"{tid}: missing required field {field}")
        if rec.get("id") != tid:
            errors.append(f"{tid}: id {rec.get('id')!r} does not match directory name")
        if rec.get("country") not in ("US", "CA"):
            errors.append(f"{tid}: country must be US or CA")
        if not isinstance(rec.get("length_km"), (int, float)) or rec.get("length_km", 0) <= 0:
            errors.append(f"{tid}: length_km must be a positive number")

        src = rec.get("source", {})
        for field in ("status", "publisher", "url", "licence", "licence_text",
                      "attribution", "line_source"):
            if not src.get(field):
                errors.append(f"{tid}: missing required field source.{field}")
        if src.get("licence") not in ALLOWED_LICENCES:
            errors.append(f"{tid}: licence {src.get('licence')!r} is not in the allowed list")
        if not str(src.get("url", "")).startswith(("https://", "http://")):
            errors.append(f"{tid}: source.url must be an http(s) URL")
        if not DATE_RE.match(str(src.get("source_checked", ""))):
            errors.append(f"{tid}: source.source_checked must be a date (YYYY-MM-DD)")
        if "redistributable" not in src:
            errors.append(f"{tid}: missing required field source.redistributable")

        data_files = sorted(f for f in os.listdir(tdir) if f.endswith(".geojson"))
        if data_files:
            if src.get("redistributable") is not True:
                errors.append(f"{tid}: data files present but source.redistributable is not true")
            if src.get("licence") not in DATA_LICENCES:
                errors.append(
                    f"{tid}: data files present but licence {src.get('licence')!r} "
                    "does not allow redistribution")
            release = os.path.join(tdir, "release.txt")
            if not os.path.isfile(release):
                errors.append(f"{tid}: data files present but release.txt is missing")
            elif not re.search(r"\d{4}-\d{2}-\d{2}", open(release, encoding="utf-8").read()):
                errors.append(f"{tid}: release.txt has no release date (YYYY-MM-DD)")
        elif src.get("line_file"):
            errors.append(f"{tid}: source.line_file names a file but no data file is present")

        measured = 0.0
        for fn in data_files:
            path = os.path.join(tdir, fn)
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:  # noqa: BLE001
                errors.append(f"{tid}/{fn}: GeoJSON does not parse: {e}")
                continue
            if data.get("type") != "FeatureCollection":
                errors.append(f"{tid}/{fn}: top level must be a FeatureCollection")
            file_length = 0.0
            for feat in data.get("features", []):
                file_length += check_geometry(feat.get("geometry"), f"{tid}/{fn}", errors)
            if fn == (src.get("line_file") or ""):
                measured = file_length

        line_file = src.get("line_file") or ""
        if line_file:
            if not os.path.isfile(os.path.join(tdir, line_file)):
                errors.append(f"{tid}: declared line file {line_file} does not exist")
            length_km = rec.get("length_km") or 0
            if length_km and measured:
                gap = abs(measured - length_km) / length_km
                if gap > 0.15 and not str(src.get("length_gap_note", "")).strip():
                    errors.append(
                        f"{tid}: measured line {measured:.1f} km differs from recorded "
                        f"{length_km} km by {gap * 100:.1f}% and source.length_gap_note "
                        "does not explain the gap")
        elif not str(src.get("line_absent_reason", "")).strip():
            errors.append(f"{tid}: no line file, and source.line_absent_reason is empty")

        shield = rec.get("shield", {})
        if not shield.get("status"):
            errors.append(f"{tid}: missing required field shield.status")
        logo_file = shield.get("logo_file") or ""
        on_disk = [f for f in ("shield.svg", "shield.png") if os.path.isfile(os.path.join(tdir, f))]
        if on_disk:
            if logo_file not in on_disk:
                errors.append(f"{tid}: logo file on disk {on_disk} but shield.logo_file is {logo_file!r}")
            if not str(shield.get("logo_owner", "")).strip():
                errors.append(f"{tid}: logo present but shield.logo_owner is empty")
            if not str(shield.get("logo_source", "")).strip() and not str(shield.get("logo_owner", "")).strip():
                errors.append(f"{tid}: logo present but its source and holder are not named")
        if logo_file and not os.path.isfile(os.path.join(tdir, logo_file)):
            errors.append(f"{tid}: declared logo file {logo_file} does not exist")

        osm = rec.get("osm", {})
        if "relation" not in osm:
            errors.append(f"{tid}: missing required field osm.relation")
        if not rec.get("verification", {}).get("verified") in (True, False):
            errors.append(f"{tid}: missing required field verification.verified")

    for dirpath, dirnames, filenames in os.walk(ROOT):
        if ".git" in dirpath:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            if os.path.getsize(path) > MAX_BYTES:
                errors.append(f"{os.path.relpath(path, ROOT)}: file is over 50 MB")

    # generated files must be up to date
    try:
        expected_csv = build_index.csv_text(trails)
        with open(os.path.join(ROOT, "trails.csv"), encoding="utf-8") as f:
            if f.read() != expected_csv:
                errors.append("trails.csv is out of date: run python3 tools/build_index.py")
        expected_idx = build_index.index_geojson_text(trails, ROOT)
        with open(os.path.join(ROOT, "index.geojson"), encoding="utf-8") as f:
            if f.read() != expected_idx:
                errors.append("index.geojson is out of date: run python3 tools/build_index.py")
        expected_readme = build_index.render_readme(os.path.join(ROOT, "README.md"), trails)
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
            if f.read() != expected_readme:
                errors.append("README.md trail table is out of date: run python3 tools/build_index.py")
    except FileNotFoundError as e:
        errors.append(f"generated file missing ({e.filename}): run python3 tools/build_index.py")

    if errors:
        for e in errors:
            print(f"ERROR {e}")
        print(f"{len(errors)} error(s)")
        return 1
    print(f"OK {len(trail_ids)} trails")
    return 0


if __name__ == "__main__":
    sys.exit(main())
