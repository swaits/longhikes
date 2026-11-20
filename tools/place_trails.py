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


# --- Sources -----------------------------------------------------------------
# Every address and field name below was opened and confirmed on 2026-11-20 (the plan's
# table was unverified). Where the publisher differs from the plan, the comment says so.
#
# nps: the Land Resources Division boundary service on NPS ArcGIS Online, layer 2
#   (nps_boundary). Fields: UNIT_CODE (the unit id, our source_id), UNIT_NAME,
#   UNIT_TYPE, STATE. The unit type of a national park is "National Parks" (plural;
#   the plan said "National Park"). Downloaded as paged GeoJSON queries with outSR=4326.
#   United States federal work: public domain.
# wilderness-connect: Wilderness Connect (wilderness.net, University of Montana for the
#   four federal agencies) publishes one zip of the whole system at /GIS/Wilderness_Areas.zip
#   from its GIS downloads page; crediting Wilderness Connect is requested. Federal work,
#   public domain. Field names are read from the file itself (see _read_wilderness).
# cpcad: Environment and Climate Change Canada's CPCAD service (MapServer layer 0, not a
#   FeatureServer). Fields: NAME_E, TYPE_E, LOC (province code: 1 Alberta, 2 British
#   Columbia, confirmed against Peter Lougheed and Garibaldi), PARENT_ID (the id features
#   of one park share, our source_id), BIOME ("T" terrestrial). JUR_ID is not a readable
#   jurisdiction (the plan guessed it was); LOC is. Types: national parks are
#   "National Park"; BC parks are "A - Park", "B - Park", "C - Park"; Alberta parks are
#   "Provincial Park". Open Government Licence, Canada.
# gmba-v2: GMBA Mountain Inventory v2.0, standard extent, one stacked shapefile of every
#   hierarchy level from EarthEnv's data host (the EarthEnv page itself sits behind a bot
#   challenge; the data host does not). Fields: GMBA_V2_ID, DBaseName (qualified, such as
#   "Sierra Nevada (USA)"), MapName, Hier_Lvl, Path (ancestors joined by " > ", ending in
#   this range), Level_01 to Level_10. CC BY 4.0 (the inventory's LICENSE file).

import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date

NPS_QUERY = ("https://services1.arcgis.com/fBc8EJBxQRMcHlei/ArcGIS/rest/services/"
             "NPS_Land_Resources_Division_Boundary_and_Tract_Data_Service/FeatureServer/2/query")
CPCAD_QUERY = "https://maps-cartes.ec.gc.ca/arcgis/rest/services/CWS_SCF/CPCAD/MapServer/0/query"
NORTH_AMERICA = (-170.0, 14.0, -50.0, 76.0)


@dataclass
class Outline:
    kind: str
    source: str
    source_id: object
    name: str
    state_codes_hint: list
    geometry: object
    slug: str = ""
    within: tuple = ()
    path: str = ""


@dataclass
class Source:
    key: str
    url: str
    licence: str
    credit: str
    page: str
    filename: str
    read: object = None


def slugify(name):
    s = re.sub(r"\([^)]*\)", "", name.lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return re.sub(r"-+", "-", s)


def cache_dir():
    d = os.environ.get("PLACES_CACHE")
    if not d:
        d = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
                         "longhikes-places")
    os.makedirs(d, exist_ok=True)
    return d


def _download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "longhikes place_trails.py"})
    with urllib.request.urlopen(req, timeout=600) as r, open(dest + ".part", "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    os.rename(dest + ".part", dest)


def _arcgis_geojson(query_url, where, out_fields, dest):
    """Page an ArcGIS query into one cached GeoJSON file, in lon/lat."""
    features, offset = [], 0
    while True:
        params = {"where": where, "outFields": out_fields, "returnGeometry": "true",
                  "outSR": "4326", "f": "geojson", "resultRecordCount": "1000",
                  "resultOffset": str(offset), "orderByFields": "OBJECTID"}
        url = query_url + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "longhikes place_trails.py"})
        with urllib.request.urlopen(req, timeout=300) as r:
            page = json.load(r)
        got = page.get("features") or []
        features.extend(got)
        if len(got) < 1000:
            break
        offset += len(got)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)


def fetch(source, cache):
    """(path, source_version) for a source's cached file; never re-downloads a cached file."""
    dest = os.path.join(cache, source.filename)
    if os.path.isfile(dest):
        return dest, date.fromtimestamp(os.path.getmtime(dest)).isoformat()
    if source.key == "nps":
        _arcgis_geojson(NPS_QUERY, "1=1", "UNIT_CODE,UNIT_NAME,UNIT_TYPE,STATE", dest)
    elif source.key == "cpcad":
        where = ("BIOME='T' AND (TYPE_E='National Park' OR (LOC IN (1,2) AND "
                 "TYPE_E IN ('A - Park','B - Park','C - Park','Provincial Park')))")
        _arcgis_geojson(CPCAD_QUERY, where, "NAME_E,TYPE_E,LOC,PARENT_ID", dest)
    else:
        _download(source.url, dest)
    return dest, date.today().isoformat()


def _union_geoms(geoms):
    shapely = _need_shapely()
    g = shapely.union_all(list(geoms))
    return g if g.is_valid else g.buffer(0)


def _geojson_groups(path, key_of):
    """{key: (properties, unioned geometry)} from a cached GeoJSON file."""
    shapely = _need_shapely()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    groups = {}
    for feat in data.get("features", []):
        if not feat.get("geometry"):
            continue
        key = key_of(feat.get("properties") or {})
        if key is None:
            continue
        groups.setdefault(key, []).append(feat)
    return {k: (feats[0].get("properties") or {},
                _union_geoms(shapely.geometry.shape(f["geometry"]) for f in feats))
            for k, feats in groups.items()}


def _read_nps(path):
    groups = _geojson_groups(path, lambda p: (p.get("UNIT_CODE") or "").strip() or None)
    out = []
    for code, (p, geom) in groups.items():
        out.append(Outline("park", "nps", code, (p.get("UNIT_NAME") or code).strip(),
                           [s for s in re.split(r"[,/ ]+", p.get("STATE") or "") if len(s) == 2],
                           geom, path=(p.get("UNIT_TYPE") or "")))
    return out


def _clean_cpcad_name(name):
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name.strip())
    name = re.sub(r"\s+Of Canada$", "", name, flags=re.I)
    if name.isupper():
        name = name.title().replace(" Park", " Park")
    return name.strip()


def _read_cpcad(path):
    groups = _geojson_groups(path, lambda p: str(p.get("PARENT_ID")) if p.get("PARENT_ID") is not None else None)
    out = []
    for pid, (p, geom) in groups.items():
        hint = {1: "AB", 2: "BC"}.get(p.get("LOC"))
        out.append(Outline("park", "cpcad", pid, _clean_cpcad_name(p.get("NAME_E") or pid),
                           [hint] if hint else [], geom, path=(p.get("TYPE_E") or "")))
    return out


def _read_vector(path, columns=None, bbox=None):
    """Rows of a shapefile (in a zip or loose) as dicts with a lon/lat shapely geometry."""
    _need_shapely()
    import pyogrio
    import pyogrio.raw
    from pyproj import Transformer
    from shapely import from_wkb
    from shapely.ops import transform
    info = pyogrio.read_info(path)
    fields, geoms, fids = pyogrio.raw.read(path, columns=columns, bbox=bbox)
    rows = []
    crs = info.get("crs") or ""
    transformer = None
    if crs and "4326" not in str(crs):
        transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    names = [n for n in fields]
    for values in zip(*[fields[n] for n in names]) if names else []:
        rows.append(dict(zip(names, values)))
    if not names:
        rows = [{} for _ in geoms]
    for row, wkb in zip(rows, geoms):
        g = from_wkb(wkb) if wkb is not None else None
        if g is not None and transformer is not None:
            g = transform(transformer.transform, g)
        row["_geometry"] = g if g is None or g.is_valid else g.buffer(0)
    return rows


def _read_wilderness(path):
    rows = _read_vector(path)
    if not rows:
        return []
    def pick(row, candidates):
        for c in candidates:
            for k in row:
                if k.lower() == c.lower() and row[k] not in (None, ""):
                    return row[k]
        return ""
    groups = {}
    for row in rows:
        name = str(pick(row, ["Name", "WILD_NAME", "AREANAME", "AreaName"])).strip()
        wid = str(pick(row, ["WID", "ID", "AreaID", "OBJECTID"]) or name)
        if row.get("_geometry") is not None and name:
            groups.setdefault(wid, (name, []))[1].append(row["_geometry"])
    return [Outline("wilderness", "wilderness-connect", wid, name, [], _union_geoms(geoms))
            for wid, (name, geoms) in groups.items()]


def _read_gmba(path):
    """Every North American range at every level: dicts with gmba_id, name, path, geometry."""
    rows = _read_vector(path, columns=["GMBA_V2_ID", "DBaseName", "MapName", "Hier_Lvl", "Path"],
                        bbox=NORTH_AMERICA)
    out = []
    for row in rows:
        if row.get("_geometry") is None:
            continue
        out.append({"gmba_id": str(row.get("GMBA_V2_ID")),
                    "name": str(row.get("DBaseName") or row.get("MapName") or ""),
                    "path": str(row.get("Path") or ""),
                    "level": row.get("Hier_Lvl"), "geometry": row["_geometry"]})
    return out


SOURCES = {
    "nps": Source("nps", NPS_QUERY, "Public domain (United States federal work)",
                  "National Park Service, Land Resources Division",
                  "https://irma.nps.gov/DataStore/Reference/Profile/2224545",
                  "nps-boundary.geojson", _read_nps),
    "wilderness-connect": Source(
        "wilderness-connect", "https://wilderness.net/GIS/Wilderness_Areas.zip",
        "Public domain (United States federal work); credit requested",
        "Wilderness Connect, University of Montana (wilderness.net)",
        "https://wilderness.net/visit-wilderness/gis-gps.php",
        "Wilderness_Areas.zip", _read_wilderness),
    "cpcad": Source("cpcad", CPCAD_QUERY, "Open Government Licence, Canada",
                    "Environment and Climate Change Canada, CPCAD",
                    "https://open.canada.ca/data/dataset/6c343726-1e92-451a-876a-76e17d398a1c",
                    "cpcad-parks.geojson", _read_cpcad),
    "gmba-v2": Source(
        "gmba-v2", "https://data.earthenv.org/mountains/standard/GMBA_Inventory_v2.0_standard.zip",
        "CC BY 4.0", "GMBA Mountain Inventory v2 (Snethlage et al. 2022), via EarthEnv",
        "https://www.earthenv.org/mountains", "GMBA_Inventory_v2.0_standard.zip", _read_gmba),
}
# --- Allow-list and catalogue ------------------------------------------------

def load_allowlist(path):
    if not path or not os.path.isfile(path):
        return {"park": [], "range": []}
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return {"park": data.get("park") or [], "range": data.get("range") or []}


def default_allowlist_path():
    return os.path.join(ROOT, "tools", "place_allowlist.toml")


def assign_slugs(outlines):
    """Slugs from names, unique within a kind; a collision gets its state code."""
    by_kind = {}
    for o in outlines:
        if not o.slug:
            o.slug = slugify(o.name)
        by_kind.setdefault((o.kind, o.slug), []).append(o)
    for group in by_kind.values():
        if len(group) > 1:
            for o in group:
                hint = (o.state_codes_hint or ["x"])[0].lower()
                o.slug = f"{o.slug}-{hint}"
    return outlines


def catalogue(cache, allowlist=None):
    """The outlines to measure: parks whole, wilderness whole, ranges allow-listed only."""
    allowlist = allowlist if allowlist is not None else load_allowlist(default_allowlist_path())
    extras = {str(p.get("source_id")): p for p in allowlist["park"]
              if isinstance(p.get("source_id"), str)}
    joined = [p for p in allowlist["park"] if isinstance(p.get("source_id"), list)]
    joined_ids = {str(s) for p in joined for s in p["source_id"]}
    out = []
    path, _ver = fetch(SOURCES["nps"], cache)
    for o in SOURCES["nps"].read(path):
        if str(o.source_id) in joined_ids:
            continue
        extra = extras.get(str(o.source_id))
        if o.path == "National Parks" or extra:
            if extra:
                o.slug = extra.get("slug") or o.slug
                o.name = extra.get("name") or o.name
            out.append(o)
    for p in joined:
        parts = [o for o in SOURCES["nps"].read(path) if str(o.source_id) in [str(s) for s in p["source_id"]]]
        if parts:
            out.append(Outline("park", "nps", [str(s) for s in p["source_id"]],
                               p.get("name") or parts[0].name,
                               sorted({h for o in parts for h in o.state_codes_hint}),
                               _union_geoms(o.geometry for o in parts),
                               slug=p.get("slug") or ""))
    path, _ver = fetch(SOURCES["cpcad"], cache)
    out.extend(SOURCES["cpcad"].read(path))
    path, _ver = fetch(SOURCES["wilderness-connect"], cache)
    out.extend(SOURCES["wilderness-connect"].read(path))
    wanted = {str(r.get("gmba_id")): r for r in allowlist["range"]}
    if wanted:
        for g in gmba_ranges(cache):
            spec = wanted.get(g["gmba_id"])
            if spec:
                out.append(Outline("range", "gmba-v2", g["gmba_id"],
                                   spec.get("name") or g["name"], [], g["geometry"],
                                   slug=spec.get("slug") or "",
                                   within=tuple(spec.get("within") or ()), path=g["path"]))
    return assign_slugs(out)


_GMBA_CACHE = {}


def gmba_ranges(cache):
    if cache not in _GMBA_CACHE:
        path, _ver = fetch(SOURCES["gmba-v2"], cache)
        _GMBA_CACHE[cache] = SOURCES["gmba-v2"].read(path)
    return _GMBA_CACHE[cache]


def source_versions(cache):
    return {key: fetch(src, cache)[1] for key, src in SOURCES.items()}


# --- Records, measuring, the proposal ----------------------------------------

def load_records(root=ROOT):
    """Every record as {id, name, regions, country, track} (track None with no line file)."""
    import build_index
    records = []
    for tid in build_index.trail_dirs(root):
        rec = build_index.load_toml(os.path.join(root, tid, "trail.toml"))
        records.append({"id": tid, "name": rec.get("name") or tid,
                        "regions": list(rec.get("regions") or []),
                        "country": rec.get("country") or "",
                        "rec": rec, "track": main_track(os.path.join(root, tid))})
    return records


@dataclass
class PlaceHit:
    outline: object
    trails: list = field(default_factory=list)
    where: list = field(default_factory=list)
    page: bool = False


@dataclass
class NearItem:
    trail: str
    key: tuple
    km: float
    inside: object = None


@dataclass
class Proposal:
    per_trail: dict = field(default_factory=dict)
    per_place: dict = field(default_factory=dict)
    no_track: list = field(default_factory=list)
    near: list = field(default_factory=list)
    names: dict = field(default_factory=dict)


def _measure(records, outlines):
    """{(trail id, outline index): (km, clipped geometry)} for every piece inside."""
    shapely = _need_shapely()
    if not outlines:
        return {}
    tree = shapely.STRtree([o.geometry for o in outlines])
    hits = {}
    for rec in records:
        track = rec.get("track")
        if track is None:
            continue
        for idx in tree.query(track, predicate="intersects"):
            clipped = track.intersection(outlines[idx].geometry)
            km = _geodesic_km(clipped)
            if km > 0:
                hits[(rec["id"], int(idx))] = (km, clipped)
    return hits


def propose(records, outlines):
    p = Proposal(names={r["id"]: r.get("name") or r["id"] for r in records})
    p.no_track = [r["id"] for r in records if r.get("track") is None]
    for r in records:
        p.per_trail[r["id"]] = []
    hits = _measure(records, outlines)
    by_id = {r["id"]: r for r in records}
    for (tid, idx), (km, clipped) in sorted(hits.items()):
        o = outlines[idx]
        key = (o.kind, o.slug or slugify(o.name))
        if abs(km - MIN_KM) <= 0.5:
            p.near.append(NearItem(tid, key, km, clipped))
        if km < MIN_KM:
            continue
        p.per_trail[tid].append((key, km))
        hit = p.per_place.setdefault(key, PlaceHit(o))
        hit.trails.append((tid, km))
    for hit in p.per_place.values():
        hit.trails.sort(key=lambda t: (-t[1], t[0]))
        hit.page = len(hit.trails) >= 3
        counts = {}
        for tid, _km in hit.trails:
            for code in by_id[tid].get("regions") or []:
                counts[code] = counts.get(code, 0) + 1
        n = len(hit.trails)
        hit.where = sorted(c for c, k in counts.items() if k * 2 >= n) or list(hit.outline.state_codes_hint)
    for lst in p.per_trail.values():
        lst.sort(key=lambda t: (-t[1], t[0]))
    p.near.sort(key=lambda x: (abs(x.km - MIN_KM), x.trail))
    return p


def range_candidates(records, all_ranges, allowlisted=()):
    """GMBA ranges that 3 or more tracks cross (1 mile or more), minus the allow-list."""
    outlines = [Outline("range", "gmba-v2", g["gmba_id"], g["name"], [], g["geometry"],
                        path=g.get("path") or "") for g in all_ranges
                if g["gmba_id"] not in set(allowlisted)]
    hits = _measure(records, outlines)
    by_range = {}
    for (tid, idx), (km, _c) in hits.items():
        if km >= MIN_KM:
            by_range.setdefault(idx, []).append((tid, km))
    out = []
    for idx, trails in by_range.items():
        if len(trails) >= 3:
            o = outlines[idx]
            parents = [s for s in (o.path.split(" > ") if o.path else [])][:-1]
            out.append({"gmba_id": o.source_id, "name": o.name, "path": o.path,
                        "parents": parents, "trails": sorted(trails, key=lambda t: -t[1])})
    out.sort(key=lambda c: (-len(c["trails"]), c["name"]))
    return out


def _mi(km):
    return km / 1.609344


def proposal_json(p):
    return {
        "per_trail": {tid: [{"kind": k[0], "slug": k[1], "km": round(km, 3)} for k, km in lst]
                      for tid, lst in p.per_trail.items()},
        "per_place": {f"{k[0]}/{k[1]}": {
            "kind": k[0], "slug": k[1], "name": h.outline.name, "source": h.outline.source,
            "source_id": h.outline.source_id, "where": h.where, "page": h.page,
            "within": list(h.outline.within), "box": box_of(h.outline.geometry),
            "trails": [{"id": t, "km": round(km, 3)} for t, km in h.trails]}
            for k, h in sorted(p.per_place.items())},
        "no_track": list(p.no_track),
        "near": [{"trail": n.trail, "kind": n.key[0], "slug": n.key[1], "km": round(n.km, 3)}
                 for n in p.near],
    }


def render_proposal(p, path):
    """proposal.md beside proposal.json and near-threshold.geojson. Reviewers only:
    the km figures here are internal and never reach the site."""
    lines = ["# Place proposal", "",
             "Measured from each trail's main track against the published outlines. "
             "A trail is in a place at 1 mile (1.609 km) or more inside. Review only: "
             "nothing is written to the records until this is accepted.", ""]
    pages = [h for h in p.per_place.values() if h.page]
    lines += [f"Places with 3 or more trails (a page each): {len(pages)} of {len(p.per_place)} "
              f"places with any trail. Trails with a track: "
              f"{len(p.per_trail) - len(p.no_track)}; with no track: {len(p.no_track)}.", ""]
    if p.near:
        lines += ["## Near the 1 mile line (check these first)", ""]
        for n in p.near:
            lines.append(f"- {n.trail} in {n.key[0]}/{n.key[1]}: {n.km:.2f} km "
                         f"({_mi(n.km):.2f} mi) inside. The clipped piece is in near-threshold.geojson.")
        lines.append("")
    lines += ["## By trail", ""]
    for tid in sorted(p.per_trail):
        lst = p.per_trail[tid]
        if tid in p.no_track:
            lines.append(f"- {tid} ({p.names.get(tid, tid)}): no track, needs a person")
        elif not lst:
            lines.append(f"- {tid} ({p.names.get(tid, tid)}): in no park, range or wilderness")
        else:
            places = "; ".join(f"{k[0]}/{k[1]} {km:.1f} km ({_mi(km):.1f} mi)" for k, km in lst)
            lines.append(f"- {tid} ({p.names.get(tid, tid)}): {places}")
    lines += ["", "## By place", ""]
    for key in sorted(p.per_place, key=lambda k: (k[0], -len(p.per_place[k].trails), k[1])):
        h = p.per_place[key]
        mark = "page" if h.page else "no page (under 3 trails)"
        lines.append(f"### {key[0]}/{key[1]}: {h.outline.name} ({mark})")
        lines.append(f"Source {h.outline.source} id {h.outline.source_id}; where {h.where}"
                     + (f"; within {list(h.outline.within)}" if h.outline.within else "")
                     + (f"; GMBA path: {h.outline.path}" if h.outline.path and key[0] == "range" else ""))
        for tid, km in h.trails:
            lines.append(f"- {tid}: {km:.1f} km ({_mi(km):.1f} mi)")
        lines.append("")
    if p.no_track:
        lines += ["## Trails with no track (each needs a person)", ""]
        lines += [f"- {tid} ({p.names.get(tid, tid)})" for tid in p.no_track]
        lines.append("")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    with open(os.path.join(os.path.dirname(os.path.abspath(path)), "proposal.json"),
              "w", encoding="utf-8") as f:
        json.dump(proposal_json(p), f, indent=1)
    if p.near:
        shapely = _need_shapely()
        feats = [{"type": "Feature",
                  "properties": {"trail": n.trail, "place": f"{n.key[0]}/{n.key[1]}",
                                 "km": round(n.km, 3)},
                  "geometry": shapely.geometry.mapping(n.inside)} for n in p.near if n.inside]
        with open(os.path.join(os.path.dirname(os.path.abspath(path)), "near-threshold.geojson"),
                  "w", encoding="utf-8") as f:
            json.dump({"type": "FeatureCollection", "features": feats}, f)


def render_candidates(candidates, path, names=None):
    lines = ["# Range candidates", "",
             "GMBA ranges at every hierarchy level that 3 or more tracks cross by 1 mile "
             "or more, and that are not on the allow-list. Keep, drop or rename each; "
             "the kept ones join tools/place_allowlist.toml.", ""]
    for c in candidates:
        lines.append(f"### GMBA {c['gmba_id']}: {c['name']}")
        lines.append(f"Parents: {' > '.join(c['parents']) or 'none'}")
        for tid, km in c["trails"]:
            lines.append(f"- {tid}: {km:.1f} km ({_mi(km):.1f} mi)")
        lines.append("")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    with open(path + ".json", "w", encoding="utf-8") as f:
        json.dump([{**c, "trails": [{"id": t, "km": round(km, 3)} for t, km in c["trails"]]}
                   for c in candidates], f, indent=1)


def _out_dir(arg):
    if arg:
        return arg
    return os.path.join(ROOT, "refresh", date.today().isoformat(), "places")


HELP = __doc__ + """
Subcommands:
    propose [--out DIR] [--allowlist FILE]     measure every track, write proposal.md/json
    candidates [--out DIR] [--allowlist FILE]  GMBA ranges 3+ tracks cross, not allow-listed
    apply PROPOSAL.json [--exclude FILE]       write the records and places.toml
    stated ... / stamp ...                     hand placements for trackless trails
    --check                                    re-measure and list every difference
Cache: $PLACES_CACHE, default $XDG_CACHE_HOME/longhikes-places.
"""


def _opt(argv, name, default=None):
    if name in argv:
        return argv[argv.index(name) + 1]
    return default


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("--help", "-h", "help"):
        print(HELP)
        return 0
    _need_shapely()
    cmd = argv[0]
    if cmd == "propose":
        allow = load_allowlist(_opt(argv, "--allowlist", default_allowlist_path()))
        outlines = catalogue(cache_dir(), allow)
        records = load_records()
        p = propose(records, outlines)
        dest = os.path.join(_out_dir(_opt(argv, "--out")), "proposal.md")
        render_proposal(p, dest)
        print(f"wrote {dest}: {len(p.per_place)} places, "
              f"{sum(1 for h in p.per_place.values() if h.page)} with 3 or more trails, "
              f"{len(p.no_track)} trails with no track, {len(p.near)} near the line")
        return 0
    if cmd == "candidates":
        allow = load_allowlist(_opt(argv, "--allowlist", default_allowlist_path()))
        records = load_records()
        found = range_candidates(records, gmba_ranges(cache_dir()),
                                 {str(r.get("gmba_id")) for r in allow["range"]})
        dest = os.path.join(_out_dir(_opt(argv, "--out")), "range-candidates.md")
        render_candidates(found, dest)
        print(f"wrote {dest}: {len(found)} candidate ranges")
        return 0
    print(f"place_trails.py: no subcommand {cmd!r} yet", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
