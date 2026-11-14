"""Load the trail records (one trail.toml per directory) with derived fields."""
import os
import tomllib

from . import elevation

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHIELD_NAMES = ("shield.svg", "shield.png")


def trail_kind(rec):
    return rec.get("kind") or "designated"


def trail_status(rec):
    """Same rule as the status column of trails.csv (tools/build_index.py)."""
    return "included" if rec.get("source", {}).get("line_file") else "record-only"


def find_files(root, tid, rec):
    """Return the data files that exist for a trail, as paths relative to root."""
    d = os.path.join(root, tid)
    files = {}

    def rel(name):
        return f"{tid}/{name}"

    line_file = rec.get("source", {}).get("line_file") or ""
    if line_file and os.path.isfile(os.path.join(d, line_file)):
        files["line"] = rel(line_file)
    if os.path.isfile(os.path.join(d, "alternates.geojson")):
        files["alternates"] = rel("alternates.geojson")
    extracts = {}
    for name in sorted(os.listdir(d)):
        if name.startswith("line-") and name.endswith(".geojson"):
            extracts[name[len("line-"):-len(".geojson")]] = rel(name)
    if extracts:
        files["extracts"] = extracts
    for name in SHIELD_NAMES:
        if os.path.isfile(os.path.join(d, name)):
            files["shield"] = rel(name)
            break
    return files


def load_record(root, tid):
    with open(os.path.join(root, tid, "trail.toml"), "rb") as f:
        rec = tomllib.load(f)
    length_km = rec.get("length_km", 0)
    rec["derived"] = {
        "kind": trail_kind(rec),
        "has_line": bool(rec.get("source", {}).get("line_file")),
        "length_mi": int(round(length_km / 1.609344)),
        "files": find_files(root, tid, rec),
        "elevation": elevation.load_file(root, tid),
        "status": trail_status(rec),
    }
    return rec


def load_records(root=ROOT):
    """Every */trail.toml under root, sorted by id."""
    ids = sorted(
        d for d in os.listdir(root)
        if os.path.isfile(os.path.join(root, d, "trail.toml"))
    )
    return [load_record(root, tid) for tid in ids]
