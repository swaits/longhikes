#!/usr/bin/env python3
"""Build the static site data: downloads, map geometry, overview, trails.json and the bulk archives.

Python 3 standard library only. Run from anywhere:
    python3 web/build.py [--out _site] [--only id,id,...] [--force]
"""
import sys

sys.dont_write_bytecode = True

import argparse
import concurrent.futures
import hashlib
import json
import multiprocessing
import os
import shutil
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from olt import fingerprint, geo, hike, records, redirects  # noqa: E402

GPX_TOL_M = 5.0
MAP_TOL_M = 30.0
OVERVIEW_TOL_M = 750.0
# Source files whose change means every trail's output is stale.
CODE_FILES = [os.path.join(HERE, "build.py"),
              os.path.join(HERE, "olt", "geo.py"),
              os.path.join(HERE, "olt", "hike.py"),
              os.path.join(HERE, "olt", "records.py"),
              # what those import (a test, test_build.py, keeps this list closed under imports)
              os.path.join(HERE, "olt", "words.py"),
              os.path.join(HERE, "olt", "elevation.py"),
              os.path.join(HERE, "olt", "markup.py")]
# Incremental-build cache, deliberately outside the publish directory.
CACHE_DIR = os.path.join(HERE, ".cache")
# Files copied verbatim into the root of the publish directory (_headers, ...).
STATIC_DIR = os.path.join(HERE, "static")


class Stats:
    def __init__(self):
        self.processed = 0
        self.skipped_trails = 0
        self.written = 0
        self.skipped = 0


def write_text(path, text, stats):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    stats.written += 1


def write_json(path, obj, stats, indent=None):
    write_text(path, json.dumps(obj, ensure_ascii=False, separators=(",", ":"),
                                indent=indent) + "\n", stats)


def copy_file(src, dst, stats):
    shutil.copyfile(src, dst)
    stats.written += 1


def copy_static(static_dir, out_dir, stats):
    """Copy everything under static_dir verbatim into out_dir.

    The directory tree is preserved; static_dir itself may be missing.
    """
    if not os.path.isdir(static_dir):
        return
    for base, _, names in os.walk(static_dir):
        rel = os.path.relpath(base, static_dir)
        target = out_dir if rel == "." else os.path.join(out_dir, rel)
        os.makedirs(target, exist_ok=True)
        for name in sorted(names):
            copy_file(os.path.join(base, name), os.path.join(target, name), stats)


def mtime(path):
    return os.path.getmtime(path)


def dir_mtime(path):
    """Newest mtime of the files directly inside a directory."""
    return max(mtime(os.path.join(path, n)) for n in os.listdir(path)
               if os.path.isfile(os.path.join(path, n)))


_WARNINGS = None  # in a worker process: the warnings it raised, which the parent prints


def warn(message):
    if _WARNINGS is not None:
        _WARNINGS.append(message)
        return
    print(f"warning: {message}", file=sys.stderr)


def multiline_feature(parts, props):
    return {"type": "Feature", "properties": props,
            "geometry": {"type": "MultiLineString", "coordinates": parts}}


def sketch_features(rec):
    """GeoJSON features sketching a trail with no track from its start and
    end points, or the one on file: a straight LineString when both are known, and a MultiPoint
    for the rings at the ends. Marked sketch, never a track: no download,
    no GPX status and no elevation ever come from these."""
    points = hike.sketch_points(rec)
    if not points:
        return []
    props = {"id": rec["id"], "name": rec["name"], "kind": rec["derived"]["kind"],
             "country": rec["country"], "length_km": rec["length_km"], "sketch": True}
    features = []
    if len(points) == 2:
        features.append({"type": "Feature", "properties": dict(props),
                         "geometry": {"type": "LineString", "coordinates": points}})
    features.append({"type": "Feature", "properties": dict(props),
                     "geometry": {"type": "MultiPoint", "coordinates": points}})
    return features


def termini_features(rec):
    """GeoJSON for the trail page's map of a trail with no track: one Point per marker (the start
    and the end, or one point for a loop), labelled with the record's own place names. Never a
    line: nothing here can be read as the route."""
    props = {"id": rec["id"], "name": rec["name"], "kind": rec["derived"]["kind"],
             "country": rec["country"], "length_km": rec["length_km"], "sketch": True}
    return [{"type": "Feature",
             "properties": dict(props, role=m["role"], place=m["place"], label=m["label"]),
             "geometry": {"type": "Point", "coordinates": m["lonlat"]}}
            for m in hike.termini(rec)]


def trail_outputs(tid, files, rec=None):
    """Names of the data files written into _site/trails/<id>/ for these files."""
    names = []
    if "line" in files:
        names += [f"{tid}.geojson", f"{tid}.gpx"]
    if "alternates" in files:
        names += [f"{tid}-alternates.geojson", f"{tid}-alternates.gpx"]
    for src in files.get("extracts", {}):
        names.append(f"{tid}-{src}.geojson")
    if "line" in files or "alternates" in files:
        names.append("map.json")
    if rec is not None and "line" not in files and hike.sketch_points(rec):
        names.append("sketch.json")
    if "shield" in files:
        names.append(os.path.basename(files["shield"]))
    return names


def is_data_file(name):
    """Files this script owns in a trail's output directory (the pages step's
    index.html, trail.toml and release.txt are not among them)."""
    return name in ("map.json", "sketch.json") or name.endswith((".geojson", ".gpx")) or name in records.SHIELD_NAMES


def remove_stale(tdir, expected):
    """Delete data files in a trail's output directory that this build does not produce."""
    for name in os.listdir(tdir):
        path = os.path.join(tdir, name)
        if name not in expected and is_data_file(name) and os.path.isfile(path):
            os.remove(path)


def read_cache(cache_path):
    try:
        with open(cache_path, encoding="utf-8") as f:
            cache = json.load(f)
    except (OSError, ValueError):
        return None
    return cache if isinstance(cache, dict) else None


def up_to_date(rec, files, tdir, cache_path, code_mtime):
    """True when the outputs are complete, newer than the sources, and the cache
    records exactly the set of outputs this record now calls for."""
    names = trail_outputs(rec["id"], files, rec)
    cache = read_cache(cache_path)
    if cache is None or cache.get("outputs") != sorted(names):
        return False
    if cache.get("creator") != gpx_creator():  # the site was renamed: the GPX creator is stale
        return False
    if "line" in files and "bbox" not in cache:
        return False
    paths = [os.path.join(tdir, n) for n in names] + [cache_path]
    if not all(os.path.isfile(p) for p in paths):
        return False
    newest_in = max(code_mtime, dir_mtime(os.path.join(ROOT, rec["id"])))
    return all(mtime(p) >= newest_in for p in paths)


def download(tdir, name, role, note, fmt):
    return {"file": name, "format": fmt, "role": role,
            "bytes": os.path.getsize(os.path.join(tdir, name)), "note": note}


def build_set(tid, key, path, stem, gpx_name, tdir, gpx_args, stats):
    """Write one line file's outputs. Returns (parts, map parts), or None when
    the file has no line (or nothing is left of it after rounding)."""
    parts = geo.read_parts(path)
    fine, coarse = geo.simplify_multi(parts, [GPX_TOL_M, MAP_TOL_M])  # one walk serves both
    simple = geo.round_coords(fine, 6)
    small = geo.round_coords(coarse, 5)
    if not parts or not simple or not small:
        warn(f"{tid}: the {key} file {os.path.relpath(path, ROOT)} has no line; "
             f"treated as having no {key}")
        return None
    copy_file(path, os.path.join(tdir, f"{stem}.geojson"), stats)
    write_text(os.path.join(tdir, f"{stem}.gpx"),
               geo.gpx_text(simple, gpx_name, **gpx_args), stats)
    return parts, small


def compute_trail(rec, files, tdir, stats):
    """Write the outputs of one trail from its source files. Returns (files, cache): the files
    that produced output, and what the pages need of the line (bbox, point count, elevation)."""
    tid = rec["id"]
    src = rec.get("source", {})
    cache = {}
    gpx_args = dict(url=src.get("url", ""), attribution=src.get("attribution", ""),
                    licence=src.get("licence", ""), licence_text=src.get("licence_text", ""),
                    creator=gpx_creator(),
                    permission=({k: src[k] for k in ("permission_quote", "permission_by", "permission_date", "permission_url")
                                 if k in src} if src.get("licence") == "stated-permission" else None))
    maps = []
    if "line" in files:
        built = build_set(tid, "line", os.path.join(ROOT, files["line"]), tid,
                          rec["name"], tdir, gpx_args, stats)
        if built is None:
            del files["line"]
        else:
            parts, small = built
            maps.append(multiline_feature(small, {"role": "main"}))
            cache = {"bbox": geo.bbox(parts), "points": geo.point_count(parts),
                     "elevation": geo.has_elevation(parts)}
    if "alternates" in files:
        built = build_set(tid, "alternates", os.path.join(ROOT, files["alternates"]),
                          f"{tid}-alternates", rec["name"] + " (alternates)",
                          tdir, gpx_args, stats)
        if built is None:
            del files["alternates"]
        else:
            maps.append(multiline_feature(built[1], {"role": "alternate"}))
    if maps:
        # The bbox covers the coordinates as published (rounded), not the source's.
        box = geo.merge_bbox([geo.bbox(m["geometry"]["coordinates"]) for m in maps])
        fc = {"type": "FeatureCollection", "bbox": box, "features": maps}
        write_json(os.path.join(tdir, "map.json"), fc, stats)
    sketches = termini_features(rec) if "line" not in files else []
    if sketches:
        box = hike.sketch_bbox(hike.sketch_points(rec), pad=True)
        write_json(os.path.join(tdir, "sketch.json"),
                   {"type": "FeatureCollection", "bbox": box, "features": sketches}, stats)
    return files, cache


def copy_sources(tid, files, tdir, stats):
    """Copy the trail's files that are published as they are (the full-resolution GeoJSON,
    the extracts and the logo) from the repository."""
    for key, stem in (("line", tid), ("alternates", f"{tid}-alternates")):
        if key in files:
            copy_file(os.path.join(ROOT, files[key]), os.path.join(tdir, f"{stem}.geojson"), stats)
    for source, rel in files.get("extracts", {}).items():
        copy_file(os.path.join(ROOT, rel), os.path.join(tdir, f"{tid}-{source}.geojson"), stats)
    if "shield" in files:
        name = os.path.basename(files["shield"])
        copy_file(os.path.join(ROOT, files["shield"]), os.path.join(tdir, name), stats)


# What the trail's derived outputs are made from: these files' contents (and those of the trail's
# own directory) decide them, so a change to any of them makes a new key. Kept by content, not by
# modification time, so a store restored from a CI cache or made in another checkout is as good as one
# made here.
STORE_VERSION = "2"  # 2: archives have fixed member times
_code_digest = None


def code_digest():
    global _code_digest
    if _code_digest is None:
        h = hashlib.sha256(STORE_VERSION.encode())
        for path in CODE_FILES:
            with open(path, "rb") as f:
                h.update(hashlib.sha256(f.read()).digest())
        _code_digest = h.hexdigest()
    return _code_digest


def trail_key(tid):
    """Hash of everything the trail's derived outputs depend on."""
    h = hashlib.sha256(code_digest().encode())
    h.update(gpx_creator().encode())
    d = os.path.join(ROOT, tid)
    for name in sorted(os.listdir(d)):
        path = os.path.join(d, name)
        if os.path.isfile(path):
            h.update(name.encode() + b"\0")
            with open(path, "rb") as f:
                h.update(hashlib.sha256(f.read()).digest())
    return h.hexdigest()


def store_dir():
    return os.path.join(CACHE_DIR, "store")


def derived_names(names):
    """The outputs that are computed (the rest are copies of repository files)."""
    return [n for n in names if n.endswith(".gpx") or n in ("map.json", "sketch.json")]


def restore_from_store(tid, key, tdir):
    """Copy the trail's stored derived outputs into tdir. Returns the stored meta
    {"files", "cache", "warnings"}, or None when there is no entry for this key."""
    entry = os.path.join(store_dir(), tid, key)
    try:
        with open(os.path.join(entry, "meta.json"), encoding="utf-8") as f:
            meta = json.load(f)
        for name in meta["derived"]:
            shutil.copyfile(os.path.join(entry, name), os.path.join(tdir, name))
    except (OSError, ValueError, KeyError):
        return None
    return meta


def save_to_store(tid, key, tdir, names, files, cache, warnings):
    """Keep the trail's derived outputs under their key; older keys of the trail are dropped.
    Written beside and moved into place, so a half-written entry is never read."""
    base = os.path.join(store_dir(), tid)
    tmp = os.path.join(base, f".tmp-{os.getpid()}")
    try:
        shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(tmp)
        derived = derived_names(names)
        for name in derived:
            shutil.copyfile(os.path.join(tdir, name), os.path.join(tmp, name))
        with open(os.path.join(tmp, "meta.json"), "w", encoding="utf-8") as f:
            json.dump({"derived": derived, "files": files, "cache": cache, "warnings": warnings}, f)
        final = os.path.join(base, key)
        if not os.path.isdir(final):
            os.rename(tmp, final)
        for name in os.listdir(base):
            if name != key and not name.startswith(".tmp-"):
                shutil.rmtree(os.path.join(base, name), ignore_errors=True)
    except OSError:
        pass  # the store is only a shortcut
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def build_trail(rec, out_dir, code_mtime, force, stats):
    """Write one trail's files. Returns (downloads, cache). The record's
    derived.files is replaced by the files that actually produced output.

    A trail whose outputs are already in out_dir and newer than its sources is left alone;
    one whose sources and code are unchanged since the store (CACHE_DIR/store) last saw them
    has its derived outputs copied from there; any other is computed."""
    global _WARNINGS
    tid = rec["id"]
    files = dict(rec["derived"]["files"])
    src = rec.get("source", {})
    tdir = os.path.join(out_dir, "trails", tid)
    cache_path = os.path.join(CACHE_DIR, f"{tid}.json")
    os.makedirs(tdir, exist_ok=True)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    if rec["derived"]["has_line"] and "line" not in files:
        warn(f"{tid}: the record names a line file ({src.get('line_file')}) "
             f"but it is missing; treated as having no line")
    names = trail_outputs(tid, files, rec)
    cache = {}

    if not names:
        pass  # record only: nothing to write
    elif not force and up_to_date(rec, files, tdir, cache_path, code_mtime):
        stats.skipped_trails += 1
        stats.skipped += len(names)
        cache = read_cache(cache_path)
    else:
        key = trail_key(tid)
        meta = None if force else restore_from_store(tid, key, tdir)
        if meta is not None:
            stats.skipped_trails += 1
            files, cache = meta["files"], meta["cache"]
            for message in meta["warnings"]:
                warn(message)
            copy_sources(tid, files, tdir, stats)
        else:
            stats.processed += 1
            outer, _WARNINGS = _WARNINGS, []
            try:
                files, cache = compute_trail(rec, files, tdir, stats)
                raised = _WARNINGS
            finally:
                _WARNINGS = outer
            for message in raised:
                warn(message)
            copy_sources(tid, files, tdir, stats)
        names = trail_outputs(tid, files, rec)
        cache = dict(cache, outputs=sorted(names), creator=gpx_creator())
        if meta is None and names:
            save_to_store(tid, key, tdir, names, files,
                          {k: v for k, v in cache.items() if k not in ("outputs", "creator")}, raised)
        if names:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f)

    # Drop what an earlier build wrote and this one no longer produces.
    remove_stale(tdir, set(names))
    if not names or "line" not in files:
        cache = {k: v for k, v in (cache or {}).items() if k not in ("bbox", "points", "elevation")}
    if not names and os.path.isfile(cache_path):
        os.remove(cache_path)
    rec["derived"]["files"] = files

    # download list (from the files now on disk)
    downloads = []
    if "line" in files:
        downloads.append(download(tdir, f"{tid}.geojson", "main",
                                  "Full resolution, as published in this dataset", "GeoJSON"))
        downloads.append(download(tdir, f"{tid}.gpx", "main",
                                  "Simplified to 5 m, 6 decimals", "GPX"))
    if "alternates" in files:
        downloads.append(download(tdir, f"{tid}-alternates.geojson", "alternates",
                                  "Alternate and connector tracks, full resolution", "GeoJSON"))
        downloads.append(download(tdir, f"{tid}-alternates.gpx", "alternates",
                                  "Alternate and connector tracks, simplified to 5 m", "GPX"))
    for source in files.get("extracts", {}):
        downloads.append(download(tdir, f"{tid}-{source}.geojson", "extract",
                                  f"Track as served by source '{source}', full resolution", "GeoJSON"))
    return downloads, cache or {}


def overview_parts(tdir):
    """A trail's line for the overview map: its 30 m map line, joined, simplified to 750 m.
    Kept in the store by the content of the map file, which is all it comes from."""
    try:
        with open(os.path.join(tdir, "map.json"), "rb") as f:
            raw = f.read()
    except OSError:
        return []
    tid = os.path.basename(tdir)
    kept = os.path.join(store_dir(), "overview", f"{tid}.{hashlib.sha256(code_digest().encode() + raw).hexdigest()}.json")
    try:
        with open(kept, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        pass
    parts = []
    for feat in json.loads(raw)["features"]:
        if feat["properties"].get("role") == "main":
            parts = feat["geometry"]["coordinates"]
            break
    parts = geo.join_parts(parts)  # many trails are thousands of short parts
    parts = geo.round_coords(geo.simplify(parts, OVERVIEW_TOL_M), 4)
    try:
        folder = os.path.dirname(kept)
        os.makedirs(folder, exist_ok=True)
        for old in os.listdir(folder):
            if old.startswith(tid + ".") and old.count(".") == 2:
                os.remove(os.path.join(folder, old))
        with open(kept + f".{os.getpid()}", "w", encoding="utf-8") as f:
            json.dump(parts, f)
        os.replace(kept + f".{os.getpid()}", kept)
    except OSError:
        pass  # the store is only a shortcut
    return parts


def overview_geojson(recs, out_dir, parts_of=None):
    """One MultiLineString per included trail, simplified from the 30 m map line.
    A trail with no track but a known start or end appears as sketch features.
    parts_of: {id: overview_parts(...)} already worked out (in a worker process)."""
    features = []
    for rec in recs:
        if "line" not in rec["derived"]["files"]:
            features.extend(sketch_features(rec))
            continue
        if parts_of is not None and rec["id"] in parts_of:
            parts = parts_of[rec["id"]]
        else:
            parts = overview_parts(os.path.join(out_dir, "trails", rec["id"]))
        if not parts:
            continue
        props = {"id": rec["id"], "name": rec["name"], "kind": rec["derived"]["kind"],
                 "country": rec["country"], "length_km": rec["length_km"]}
        features.append(multiline_feature(parts, props))
    return {"type": "FeatureCollection", "features": features}


def prune_removed_trails(out_dir, ids):
    """Remove trails/<id>/ output (and cache entries) for ids no longer in the dataset."""
    trails = os.path.join(out_dir, "trails")
    if os.path.isdir(trails):
        for name in os.listdir(trails):
            path = os.path.join(trails, name)
            if os.path.isdir(path) and name not in ids:
                shutil.rmtree(path)
    if os.path.isdir(CACHE_DIR):
        for name in os.listdir(CACHE_DIR):
            if name.endswith(".json") and name[:-5] not in ids:
                os.remove(os.path.join(CACHE_DIR, name))


# Bulk archives under /data/: name -> (file extension inside, what the README calls them).
ARCHIVES = {
    "all-gpx.zip": (".gpx", "GPX"),
    "all-geojson.zip": (".geojson", "GeoJSON"),
}
# Files at the top of every archive, from the repository root (left out when missing).
ARCHIVE_DOCS = ("trails.csv", "SOURCES.md")


def archive_members(name, recs, out_dir, root):
    """[(name inside the archive, source path)] for one bulk archive, in a stable order:
    each trail's line files and release.txt as <id>/<file>, then trails.csv and SOURCES.md."""
    ext = ARCHIVES[name][0]
    members = []
    for rec in recs:
        tid = rec["id"]
        files = rec["derived"]["files"]
        stems = ([tid] if "line" in files else []) + ([f"{tid}-alternates"] if "alternates" in files else [])
        for stem in stems:
            members.append((f"{tid}/{stem}{ext}", os.path.join(out_dir, "trails", tid, stem + ext)))
        release = os.path.join(root, tid, "release.txt")
        if os.path.isfile(release):
            members.append((f"{tid}/release.txt", release))
    for doc in ARCHIVE_DOCS:
        path = os.path.join(root, doc)
        if os.path.isfile(path):
            members.append((doc, path))
    return members


def archive_readme(name):
    ext, kind = ARCHIVES[name]
    if ext == ".gpx":
        what = "simplified to 5 m"
        resolution = ("The GPX files are simplified to 5 m, with coordinates to 6 decimal places.\n"
                      "The full-resolution tracks are in all-geojson.zip.\n")
    else:
        what = "full resolution"
        resolution = ("The GeoJSON files are the full-resolution tracks, as published in this dataset.\n"
                      "The simplified GPX files (5 m) are in all-gpx.zip.\n")
    rows = [(f"<id>/<id>{ext}", f"the main track, {what}"),
            (f"<id>/<id>-alternates{ext}", f"alternate and connector tracks, {what}, where the\n"
                                            "source serves them separately"),
            ("<id>/release.txt", "the source, licence and date the track files came from")]
    width = max(len(p) for p, _ in rows) + 3
    files = ""
    for path, what_it_is in rows:
        files += "  " + path.ljust(width) + what_it_is.replace("\n", "\n" + " " * (width + 2)) + "\n"
    return (f"{site_name() or 'Long trails'}: every track, as {kind}\n\n"
            "For each trail or route whose record includes a track:\n\n"
            f"{files}\n"
            "and at the top:\n\n"
            "  trails.csv    one row per record, with its licence\n"
            "  SOURCES.md    each source, its terms, and the trails that use it\n\n"
            "Terms. Each track keeps its source's terms and needs its source's credit, as\n"
            "given in its <id>/release.txt (the Licence and Attribution lines) and in\n"
            "trails.csv (the licence column). Tracks from OpenStreetMap are\n"
            "© OpenStreetMap contributors, under the ODbL. The records themselves are\n"
            "public domain (CC0-1.0).\n\n"
            f"{resolution}")


ARCHIVE_TIME = (1980, 1, 1, 0, 0, 0)  # the earliest time a zip can hold


def build_archive(name, recs, out_dir, stats):
    """Write /data/<name> (zip, deflate) unless it already holds exactly these files
    and is newer than every one of them and than this script."""
    path = os.path.join(out_dir, "data", name)
    members = archive_members(name, recs, out_dir, ROOT)
    members = [(arc, src) for arc, src in members if os.path.isfile(src)]
    expected = ["README.txt"] + [arc for arc, _ in members]
    newest = max([mtime(__file__)] + [mtime(src) for _, src in members])
    if os.path.isfile(path) and mtime(path) >= newest:
        try:
            with zipfile.ZipFile(path) as zf:
                if zf.namelist() == expected:
                    stats.skipped += 1
                    return
        except (OSError, zipfile.BadZipFile):
            pass
    # The store keeps an archive by what goes into it, so one whose files have not changed (in
    # content: it does not matter when they were written) is copied, not compressed again.
    digest = hashlib.sha256(code_digest().encode() + archive_readme(name).encode())
    for arc, src in members:
        digest.update(arc.encode() + b"\0")
        with open(src, "rb") as f:
            digest.update(hashlib.sha256(f.read()).digest())
    kept = os.path.join(store_dir(), "archives", f"{name}.{digest.hexdigest()}")
    tmp = path + ".tmp"  # written beside, then moved over: never a half-written archive
    try:
        try:
            shutil.copyfile(kept, tmp)
            with zipfile.ZipFile(tmp) as zf:
                restored = zf.namelist() == expected
        except (OSError, zipfile.BadZipFile):
            restored = False
        if restored:
            os.replace(tmp, path)
            stats.skipped += 1
            return
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Every member gets the same fixed time and mode, so the same files always make the
            # same bytes, whenever and wherever the archive is made (and so the store can hand
            # one made elsewhere to a build here).
            info = zipfile.ZipInfo("README.txt", date_time=ARCHIVE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, archive_readme(name))
            for arc, src in members:
                info = zipfile.ZipInfo(arc, date_time=ARCHIVE_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                with open(src, "rb") as source, zf.open(info, "w") as member:
                    shutil.copyfileobj(source, member, 1 << 20)
        try:
            os.makedirs(os.path.dirname(kept), exist_ok=True)
            for old in os.listdir(os.path.dirname(kept)):
                if old.startswith(name + "."):
                    os.remove(os.path.join(os.path.dirname(kept), old))
            shutil.copyfile(tmp, kept + ".tmp")
            os.replace(kept + ".tmp", kept)
        except OSError:
            pass  # the store is only a shortcut
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    stats.written += 1


def import_pages():
    try:
        from olt import pages
    except ImportError:
        return None
    return pages


def gpx_creator():
    """The creator attribute of every GPX file: the site's name."""
    return site_name() or "long-trails dataset"


def site_name():
    """The site's name from web/site.toml, or "" when olt.site is absent or unreadable."""
    try:
        from olt import site
        return site.load().name
    except Exception:  # module absent or settings unreadable
        return ""


def describe_site():
    """One-line description of what is built, from web/site.toml when olt.site exists."""
    name = site_name()
    return f"the {name} site" if name else "the static site"


# Several trails at once ---------------------------------------------------------------------
# The work on a trail (reading its track, simplifying it twice, writing GPX) is the bulk of a
# cold build, and trails do not depend on one another, so they are spread over worker processes.
# The workers are forked, so they share the loaded records; a result is what the parent needs
# back, and the parent applies it in record order, so the output is the same as one process's.

PARALLEL_FROM = 16  # fewer trails than this: not worth the workers
_JOB = None


def usable_cores():
    """The cores this process may run on (os.process_cpu_count is new in Python 3.13)."""
    try:
        return len(os.sched_getaffinity(0)) or 1
    except AttributeError:
        return os.cpu_count() or 1


def job_count():
    """Worker processes: LONGHIKES_JOBS if set, else the cores this process may use (at most 8)."""
    env = os.environ.get("LONGHIKES_JOBS", "")
    if env.isdigit():
        return max(1, int(env))
    return min(usable_cores(), 8)


def fork_context():
    if "fork" in multiprocessing.get_all_start_methods():
        return multiprocessing.get_context("fork")
    return None


def build_one(rec, out_dir, code_mtime, force, stats):
    """build_trail, and the trail's line for the overview map when it has one."""
    downloads, cache = build_trail(rec, out_dir, code_mtime, force, stats)
    parts = None
    if "line" in rec["derived"]["files"]:
        parts = overview_parts(os.path.join(out_dir, "trails", rec["id"]))
    return downloads, cache, parts


def _trail_job(i):
    global _WARNINGS
    recs, out_dir, code_mtime, force_all, only = _JOB
    rec = recs[i]
    _WARNINGS = []
    stats = Stats()
    result = build_one(rec, out_dir, code_mtime, force_all or rec["id"] in only, stats)
    return i, result, rec["derived"]["files"], vars(stats), _WARNINGS


def tree_size(tid):
    return sum(e.stat().st_size for e in os.scandir(os.path.join(ROOT, tid)) if e.is_file())


def build_trails(recs, out_dir, code_mtime, args, only, stats):
    """[(downloads, cache, overview parts)] for every record, in record order."""
    ctx = fork_context()
    jobs = min(job_count(), len(recs))
    if ctx is None or jobs < 2 or len(recs) < PARALLEL_FROM:
        return [build_one(rec, out_dir, code_mtime, args.force or rec["id"] in only, stats)
                for rec in recs]
    global _JOB
    _JOB = (recs, out_dir, code_mtime, args.force, only)
    results = [None] * len(recs)
    order = sorted(range(len(recs)), key=lambda i: -tree_size(recs[i]["id"]))  # biggest first
    # A process pool, not multiprocessing.Pool: a worker that raises, or is killed, makes the
    # build fail (BrokenProcessPool) where Pool would wait for it for ever.
    try:
        with concurrent.futures.ProcessPoolExecutor(jobs, mp_context=ctx) as pool:
            try:
                futures = [pool.submit(_trail_job, i) for i in order]
                for done in concurrent.futures.as_completed(futures):
                    i, result, files, counts, warnings = done.result()
                    recs[i]["derived"]["files"] = files
                    results[i] = result
                    for name, n in counts.items():
                        setattr(stats, name, getattr(stats, name) + n)
                    for message in warnings:
                        warn(message)
            except BaseException:
                pool.shutdown(wait=False, cancel_futures=True)
                raise
    finally:
        _JOB = None
    return results


def _archive_job(name):
    stats = Stats()
    build_archive(name, _JOB[0], _JOB[1], stats)
    return vars(stats)


def start_archives(recs, out_dir, stats):
    """Build the bulk archives, in worker processes when they can be. Returns what finish_archives needs."""
    global _JOB
    ctx = fork_context()
    if ctx is None or job_count() < 2:
        for name in ARCHIVES:
            build_archive(name, recs, out_dir, stats)
        return None
    _JOB = (recs, out_dir)
    pool = concurrent.futures.ProcessPoolExecutor(min(len(ARCHIVES), job_count()), mp_context=ctx)
    return pool, [pool.submit(_archive_job, name) for name in ARCHIVES]


def finish_archives(started, stats):
    global _JOB
    if started is None:
        return
    pool, pending = started
    try:
        for result in pending:
            for name, n in result.result().items():
                setattr(stats, name, getattr(stats, name) + n)
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
        _JOB = None


def main(argv=None):
    ap = argparse.ArgumentParser(description=f"Build the data and pages for {describe_site()}.")
    ap.add_argument("--out", default="_site", help="output directory (default _site)")
    ap.add_argument("--only", default="",
                    help="comma-separated trail ids to rebuild; site-wide files still cover every trail")
    ap.add_argument("--force", action="store_true", help="rebuild everything")
    args = ap.parse_args(argv)

    start = time.time()
    out_dir = os.path.abspath(args.out)
    recs = records.load_records(ROOT)
    only = {x for x in args.only.split(",") if x}
    unknown = only - {r["id"] for r in recs}
    if unknown:
        raise SystemExit(f"unknown trail id(s): {', '.join(sorted(unknown))}")

    code_mtime = max(mtime(p) for p in CODE_FILES)
    stats = Stats()
    os.makedirs(os.path.join(out_dir, "data"), exist_ok=True)
    # Older builds kept the cache in the publish directory; it must never ship.
    legacy_cache = os.path.join(out_dir, ".cache")
    if os.path.isdir(legacy_cache):
        shutil.rmtree(legacy_cache)

    # Every trail goes through build_trail so the site-wide files are complete.
    # --only forces a rebuild of the chosen trails; the rest are rebuilt only
    # when stale or missing from the cache.
    overview = {}
    for rec, (downloads, cache, parts) in zip(recs, build_trails(recs, out_dir, code_mtime, args, only, stats)):
        d = rec["derived"]
        d["downloads"] = downloads
        if parts is not None:
            overview[rec["id"]] = parts
        if cache.get("bbox"):
            box = cache["bbox"]
            d["bbox"] = box
            d["center"] = [round((box[0] + box[2]) / 2, 5), round((box[1] + box[3]) / 2, 5)]
            d["points"] = cache["points"]

    if not only:
        prune_removed_trails(out_dir, {r["id"] for r in recs})

    write_json(os.path.join(out_dir, "data", "overview.geojson"),
               overview_geojson(recs, out_dir, overview), stats)
    write_json(os.path.join(out_dir, "data", "trails.json"), recs, stats)
    for name in ("trails.csv", "index.geojson"):
        copy_file(os.path.join(ROOT, name), os.path.join(out_dir, "data", name), stats)
    # The archives need only the trails' files, which are all written: they are made alongside the pages.
    archives = start_archives(recs, out_dir, stats)

    copy_static(STATIC_DIR, out_dir, stats)
    # The guessable trail addresses (/trails/pacific-crest-trail/) follow the fixed ones in _redirects.
    redirects.append_to(out_dir, recs)

    pages = import_pages()
    if pages is None:
        print("pages step skipped: olt.pages not found")
    else:
        pages.render_site(recs, out_dir, ROOT)
        # The pages name the stylesheet, scripts, fonts and map libraries by content hash
        # (olt/fingerprint.py); this writes those files, under /immutable/.
        fingerprint.publish(out_dir)

    finish_archives(archives, stats)
    total = 0
    for base, _, names in os.walk(out_dir):
        total += sum(os.path.getsize(os.path.join(base, n)) for n in names)
    print(f"trails processed {stats.processed}, up to date {stats.skipped_trails}; "
          f"files written {stats.written}, skipped {stats.skipped}; "
          f"output {total / 1e6:.1f} MB; {time.time() - start:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
