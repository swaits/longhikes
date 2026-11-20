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
#   FeatureServer). Fields: NAME_E, TYPE_E, LOC (province code, see CPCAD_LOC), PARENT_ID
#   (the id features of one park share, our source_id), BIOME ("T" terrestrial). JUR_ID is not
#   a readable jurisdiction (the plan guessed it was); LOC is. Types: see CPCAD_PARK_TYPES.
#   Open Government Licence, Canada.
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
# CPCAD's LOC code is the province or territory (1 and 2 were read from Peter Lougheed and
# Garibaldi; the rest follow the service's alphabetical order and were checked on
# Killarney and Algonquin, 9, and Frontenac National Park, 11).
CPCAD_LOC = {1: "AB", 2: "BC", 3: "MB", 4: "NB", 5: "NL", 6: "NT", 7: "NS", 8: "NU",
             9: "ON", 10: "PE", 11: "QC", 12: "SK", 13: "YT"}


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
    where_hand: tuple = ()


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
    import unicodedata
    s = re.sub(r"\([^)]*\)", "", name.lower())
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"['\u2019]", "", s)
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


# The park designations CPCAD uses for national and provincial parks. The first run asked for
# provincial parks of Alberta and British Columbia only (LOC IN (1,2)), which left Ontario
# (LOC 9, "Provincial Park") and Quebec (LOC 11, "Quebec's national park") out entirely: a
# bug in the query, not a gap in the data. Territorial parks, conservation reserves, municipal
# and private areas are not asked for.
CPCAD_PARK_TYPES = ("National Park", "National Park Reserve", "Quebec's national park",
                    "Quebec's national park reserve", "Provincial Park", "Wildland Provincial Park",
                    "Wilderness Park", "A - Park", "B - Park", "C - Park")


def cpcad_where():
    types = ", ".join("'" + t.replace("'", "''") + "'" for t in CPCAD_PARK_TYPES)
    return f"BIOME='T' AND TYPE_E IN ({types})"


def fetch(source, cache):
    """(path, source_version) for a source's cached file; never re-downloads a cached file."""
    dest = os.path.join(cache, source.filename)
    if os.path.isfile(dest):
        return dest, date.fromtimestamp(os.path.getmtime(dest)).isoformat()
    if source.key == "nps":
        _arcgis_geojson(NPS_QUERY, "1=1", "UNIT_CODE,UNIT_NAME,UNIT_TYPE,STATE", dest)
    elif source.key == "cpcad":
        _arcgis_geojson(CPCAD_QUERY, cpcad_where(), "NAME_E,TYPE_E,LOC,PARENT_ID", dest)
    else:
        _download(source.url, dest)
    return dest, date.today().isoformat()


def clear_cache(cache):
    """Delete every cached source file so the next fetch downloads it again. fetch() keeps
    a cached file for good; --refresh is how the monthly check measures against the outlines
    as published today, not the ones first downloaded."""
    gone = []
    for src in SOURCES.values():
        dest = os.path.join(cache, src.filename)
        if os.path.isfile(dest):
            os.remove(dest)
            gone.append(src.filename)
    _GMBA_CACHE.clear()
    return gone


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


def state_codes(text):
    """Two-letter state codes from a source's state field: "CA", "ID-MT-WY", "AR/OK", "FL 6/"."""
    return [c for c in re.split(r"[,/\- ]+", text or "") if len(c) == 2 and c.isalpha()]


def _read_nps(path):
    groups = _geojson_groups(path, lambda p: (p.get("UNIT_CODE") or "").strip() or None)
    out = []
    for code, (p, geom) in groups.items():
        out.append(Outline("park", "nps", code, (p.get("UNIT_NAME") or code).strip(),
                           state_codes(p.get("STATE")),
                           geom, path=(p.get("UNIT_TYPE") or "")))
    return out


def _clean_cpcad_name(name):
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name.strip())
    name = re.sub(r"\s+Of Canada$", "", name, flags=re.I)
    if name.isupper():
        name = name.title()
    name = re.sub(r"(?<=\s)(And|Of|The|Du|De)(?=\s)", lambda m: m.group(0).lower(), name)
    return name.strip()


def _read_cpcad(path):
    groups = _geojson_groups(path, lambda p: str(p.get("PARENT_ID")) if p.get("PARENT_ID") is not None else None)
    locs = {}
    with open(path, encoding="utf-8") as f:
        for feat in json.load(f).get("features", []):
            p = feat.get("properties") or {}
            if p.get("PARENT_ID") is not None and p.get("LOC") in CPCAD_LOC:
                locs.setdefault(str(p["PARENT_ID"]), set()).add(CPCAD_LOC[p["LOC"]])
    out = []
    for pid, (p, geom) in groups.items():
        out.append(Outline("park", "cpcad", pid, _clean_cpcad_name(p.get("NAME_E") or pid),
                           sorted(locs.get(pid, ())), geom, path=(p.get("TYPE_E") or "")))
    return out


def _read_vector(path, columns=None, bbox=None):
    """Rows of a shapefile (in a zip or loose) as dicts with a lon/lat shapely geometry."""
    _need_shapely()
    import pyogrio
    import pyogrio.raw
    from pyproj import Transformer
    from shapely import from_wkb
    from shapely.ops import transform
    if str(path).endswith(".zip"):
        import zipfile
        with zipfile.ZipFile(path) as z:
            shp = [n for n in z.namelist() if n.lower().endswith(".shp")]
        if len(shp) == 1:
            path = f"/vsizip/{path}/{shp[0]}"
    info = pyogrio.read_info(path)
    meta, _fids, geoms, cols = pyogrio.raw.read(path, columns=columns, bbox=bbox)
    rows = []
    crs = info.get("crs") or meta.get("crs") or ""
    transformer = None
    if crs and "4326" not in str(crs):
        transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    names = [str(n) for n in (meta.get("fields") if meta.get("fields") is not None else [])]
    for values in zip(*cols) if names else []:
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
        state = str(pick(row, ["STATE", "State"]) or "")
        hint = state_codes(state)
        if row.get("_geometry") is not None and name:
            groups.setdefault(wid, (name, hint, []))[2].append(row["_geometry"])
    return [Outline("wilderness", "wilderness-connect", wid, name, hint, _union_geoms(geoms))
            for wid, (name, hint, geoms) in groups.items()]


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
                    "cpcad-parks-2.geojson", _read_cpcad),
    "gmba-v2": Source(
        "gmba-v2", "https://data.earthenv.org/mountains/standard/GMBA_Inventory_v2.0_standard.zip",
        "CC BY 4.0", "GMBA Mountain Inventory v2 (Snethlage et al. 2022), via EarthEnv",
        "https://www.earthenv.org/mountains", "GMBA_Inventory_v2.0_standard.zip", _read_gmba),
}
# --- Where a place is -----------------------------------------------------------

_BOXES = None


def state_boxes():
    """{"WY": [west, south, east, north]} from web/place-bounds.toml, keyed by the codes
    records write for regions (the file's "US-WY" without the country)."""
    global _BOXES
    if _BOXES is None:
        with open(os.path.join(ROOT, "web", "place-bounds.toml"), "rb") as f:
            raw = tomllib.load(f).get("box") or {}
        _BOXES = {k.split("-", 1)[1]: [float(v) for v in box] for k, box in raw.items()}
    return _BOXES


def where_of(outline, grid=24, share=0.2):
    """The states or provinces the place itself lies in, as records write them.

    A hand value (outline.where_hand, from the allow-list or the registry) wins. Next
    comes the source's own state field (NPS and Wilderness Connect STATE, CPCAD LOC),
    which is the publisher's word. Where a source has none (GMBA ranges), the outline is
    sampled on a grid and a state counts when 20% or more of the samples fall in its box
    in web/place-bounds.toml. The boxes overlap along borders, so a range beside a border
    can pick up a neighbour: the allow-list's `where` corrects that."""
    boxes = state_boxes()
    if outline.where_hand:
        return sorted(c for c in outline.where_hand)
    hint = sorted({c for c in outline.state_codes_hint if c in boxes})
    if hint:
        return hint
    shapely = _need_shapely()
    geom = outline.geometry
    west, south, east, north = geom.bounds
    xs = [west + (east - west) * (i + 0.5) / grid for i in range(grid)]
    ys = [south + (north - south) * (j + 0.5) / grid for j in range(grid)]
    pts = [(x, y) for x in xs for y in ys if shapely.contains_xy(geom, x, y)]
    if not pts:
        rp = geom.representative_point()
        pts = [(rp.x, rp.y)]
    out = []
    for code, (w, sth, e, n) in boxes.items():
        k = sum(1 for x, y in pts if w <= x <= e and sth <= y <= n)
        if k / len(pts) >= share:
            out.append(code)
    return sorted(out)


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


# Places the source offers that are never listed, with the reason beside each. Keyed by
# (kind, source, source id). A trail that merely passes through one is not "in" it in the
# way a place page means.
DENY = {
    ("range", "gmba-v2", "12330"): "Longfellow Mountains is an obscure source name, no hiker's, and "
                                   "its outline spills over into New Hampshire",
    ("range", "gmba-v2", "15906"): "Finger Lakes is a lake district, not a mountain range",
    ("range", "gmba-v2", "11356"): "Gore Range holds the same trails as the Mosquito "
                                   "Range, so the two would be one page twice",
    ("range", "gmba-v2", "17612"): "Mosquito Range holds the same trails as the Gore "
                                   "Range, so the two would be one page twice",
    ("range", "gmba-v2", "17240"): "Great Western Divide is a ridge inside Sequoia and Kings Canyon "
                                   "National Parks, whose page lists all of its trails",
    ("wilderness", "wilderness-connect", "507"): "Russian Wilderness holds the same trails as "
                                   "the two neighbouring wilderness pages",
    ("park", "nps", "JEFF"): "Gateway Arch National Park is the memorial grounds in "
                             "downtown St. Louis; a trail crossing it is an urban pass-through",
}


def apply_denylist(outlines, deny=None):
    deny = DENY if deny is None else deny
    return [o for o in outlines
            if (o.kind, o.source, str(o.source_id)) not in {(k, s, str(i)) for (k, s, i) in deny}]


def grow_outline(geom, km, clip=None):
    """The outline pushed out by `km` on every side (and clipped to the box [w, s, e, n]
    where one is given); the original is always kept whole. For a range whose published
    outline is tighter than the range as hikers know it. Each use is a reviewed entry in
    the allow-list (grow_km, grow_clip) with its reason."""
    import math
    shapely = _need_shapely()
    k = math.cos(math.radians(geom.centroid.y))
    fwd = lambda c: c * [k, 1.0]
    back = lambda c: c / [k, 1.0]
    grown = shapely.transform(shapely.transform(geom, fwd).buffer(km / 111.32), back)
    if clip:
        grown = grown.intersection(shapely.geometry.box(*clip))
    return _union_geoms([geom, grown])


def merge_same_name(outlines):
    """One name within a kind and source is one place: the outlines are unioned and the
    place carries every id. The source lists some ranges twice under different ids."""
    merged, order = {}, []
    for o in outlines:
        # An explicit slug tells two ranges of one display name apart (the White Mountains
        # of New Hampshire and of Arizona); the two Palisades ids share a slug and merge.
        key = (o.kind, o.source, " ".join(o.name.lower().split()), o.slug or "")
        # Two wilderness areas or parks of one name in different places are two places
        # (assign_slugs tells them apart by state); a range is one wherever its pieces lie.
        if key in merged and o.kind != "range" and not any(
                o.geometry.intersects(m.geometry) for m in merged[key]):
            key = key + (str(o.source_id),)
        if key not in merged:
            merged[key] = [o]
            order.append(key)
        else:
            merged[key].append(o)
    out = []
    for key in order:
        group = merged[key]
        if len(group) == 1:
            out.append(group[0])
            continue
        first = group[0]
        ids = sorted({str(i) for o in group
                      for i in (o.source_id if isinstance(o.source_id, list) else [o.source_id])})
        first.source_id = ids
        first.geometry = _union_geoms(o.geometry for o in group)
        first.within = tuple(sorted({w for o in group for w in o.within}))
        first.state_codes_hint = sorted({h for o in group for h in o.state_codes_hint})
        first.where_hand = first.where_hand or next((o.where_hand for o in group if o.where_hand), ())
        out.append(first)
    return out


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
                o.where_hand = tuple(extra.get("where") or ())
            out.append(o)
    for p in joined:
        parts = [o for o in SOURCES["nps"].read(path) if str(o.source_id) in [str(s) for s in p["source_id"]]]
        if parts:
            out.append(Outline("park", "nps", [str(s) for s in p["source_id"]],
                               p.get("name") or parts[0].name,
                               sorted({h for o in parts for h in o.state_codes_hint}),
                               _union_geoms(o.geometry for o in parts),
                               slug=p.get("slug") or "", where_hand=tuple(p.get("where") or ())))
    path, _ver = fetch(SOURCES["cpcad"], cache)
    out.extend(SOURCES["cpcad"].read(path))
    path, _ver = fetch(SOURCES["wilderness-connect"], cache)
    out.extend(SOURCES["wilderness-connect"].read(path))
    wanted = {str(r.get("gmba_id")): r for r in allowlist["range"]}
    if wanted:
        for g in gmba_ranges(cache):
            spec = wanted.get(g["gmba_id"])
            if spec:
                geom = g["geometry"]
                if spec.get("grow_km"):
                    geom = grow_outline(geom, float(spec["grow_km"]), spec.get("grow_clip"))
                out.append(Outline("range", "gmba-v2", g["gmba_id"],
                                   spec.get("name") or g["name"], [], geom,
                                   slug=spec.get("slug") or "",
                                   within=tuple(spec.get("within") or ()), path=g["path"],
                                   where_hand=tuple(spec.get("where") or ())))
    return assign_slugs(merge_same_name(apply_denylist(out)))


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
    versions: dict = field(default_factory=dict)


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


def propose(records, outlines, reviewed_where=None):
    """Measure every track against every outline. A place counts for a trail only when it
    lies in at least one of the trail's states or provinces (the validator's rule): a track
    that strays over a border, or a relation that carries a neighbour's section, does not
    place the trail in the neighbour's park. reviewed_where is the registry's reviewed
    `where` by (kind, slug); it wins over the outline's own."""
    reviewed_where = reviewed_where or {}
    lies_cache = {}

    def lies(idx, regions):
        if not regions:
            return True
        if idx not in lies_cache:
            o = outlines[idx]
            lies_cache[idx] = set(reviewed_where.get((o.kind, o.slug or slugify(o.name)))
                                  or where_of(o))
        return not lies_cache[idx] or bool(lies_cache[idx] & set(regions))

    p = Proposal(names={r["id"]: r.get("name") or r["id"] for r in records})
    p.no_track = [r["id"] for r in records if r.get("track") is None]
    for r in records:
        p.per_trail[r["id"]] = []
    hits = _measure(records, outlines)
    by_id = {r["id"]: r for r in records}
    for (tid, idx), (km, clipped) in sorted(hits.items()):
        o = outlines[idx]
        key = (o.kind, o.slug or slugify(o.name))
        if not lies(idx, by_id[tid].get("regions")):
            continue
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
        hit.where = where_of(hit.outline)
    sets = {k: {t for t, _km in h.trails} for k, h in p.per_place.items()}
    names = {k: h.outline.name for k, h in p.per_place.items()}
    gone = doubled_places(sets, names)
    for k in gone:
        del p.per_place[k]
    if gone:
        for tid in p.per_trail:
            p.per_trail[tid] = [(k, km) for k, km in p.per_trail[tid] if k not in gone]
        p.near = [n for n in p.near if n.key not in gone]
    # Parents are never stored on a record (the build closes membership over within):
    # a range drops out of a trail's list when the trail is also in one of its
    # descendants, by the GMBA Path. Place counts stay as measured.
    paths = {}
    for o in outlines:
        if o.kind == "range" and o.path:
            paths[(o.kind, o.slug or slugify(o.name))] = o.path
    for tid, lst in p.per_trail.items():
        here = {paths[k] for k, _km in lst if k in paths}
        p.per_trail[tid] = [(k, km) for k, km in lst
                            if k not in paths
                            or not any(other != paths[k] and other.startswith(paths[k] + " > ")
                                       for other in here)]
    for lst in p.per_trail.values():
        lst.sort(key=lambda t: (-t[1], t[0]))
    p.near.sort(key=lambda x: (abs(x.km - MIN_KM), x.trail))
    return p


_NAME_FILLER = {"national", "park", "parks", "wilderness", "area", "preserve", "and", "the", "of"}


def _core_name(name):
    return {w for w in re.split(r"[^a-z0-9]+", name.lower()) if w and w not in _NAME_FILLER}


_RANGE_WORDS = {"mountains", "mountain", "range", "ranges"}


def _stem(name):
    """The words of a name that say which place it is: the kind words of a park, a wilderness
    area and a range (National Park, Wilderness, Mountains, Range) taken away."""
    return _core_name(name) - _RANGE_WORDS


def doubled_places(sets, names):
    """Places that would be a second page for a park: the same trails exactly, and a name
    that matches. A wilderness area is a double when one name's words contain the other's
    (Sequoia-Kings Canyon Wilderness beside Sequoia and Kings Canyon); a mountain range
    when the names are the same once the kind words are taken away (Great Smoky Mountains
    beside Great Smoky Mountains National Park, Olympic Mountains beside Olympic National
    Park). The park is kept; the others are returned. sets is {(kind, slug): set of trail
    ids}, tracked and stated together; names {(kind, slug): name}."""
    drop = set()
    for wk, wset in sets.items():
        if wk[0] not in ("wilderness", "range") or not wset:
            continue
        wc = _core_name(names.get(wk, wk[1]))
        ws = _stem(names.get(wk, wk[1]))
        for pk, pset in sets.items():
            if pk[0] != "park" or pset != wset:
                continue
            pc = _core_name(names.get(pk, pk[1]))
            ps = _stem(names.get(pk, pk[1]))
            if wk[0] == "wilderness":
                if wc and pc and (wc <= pc or pc <= wc):
                    drop.add(wk)
            elif ws and ws == ps:
                drop.add(wk)
    return drop


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
        "versions": dict(p.versions),
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


# --- Writing records and the registry; stated, stamp, --check ----------------

_KIND_ORDER = {"park": 0, "range": 1, "wilderness": 2}


def _doc_of(root, rid):
    import refresh
    path = os.path.join(root, rid, "trail.toml")
    with open(path, encoding="utf-8") as f:
        return refresh.Doc(f.read()), path


def _save(doc, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc.text())


def _set_top(doc, rec, key, new):
    span = doc.span("")
    if key in rec:
        if rec[key] != new:
            doc.set_value(span, key, new, rec[key], True)
    else:
        doc.set_value(span, key, new, None, False)


def _remove_place_blocks(doc, rec):
    for _ in list(rec.get("place") or []):
        start, end = doc.span("place", 0)
        header = start - 1
        lo = header
        while lo > 0 and doc.lines[lo - 1].strip() == "":
            lo -= 1
            break
        # the span runs to the next header; the blank lines and comment lines at its end
        # belong to what follows (the history's heading comment), so they stay
        while end > header + 1 and (doc.lines[end - 1].strip() == ""
                                    or doc.lines[end - 1].lstrip().startswith("#")):
            end -= 1
        del doc.lines[lo:end]


def _history_entry(today, change, basis, basis_url):
    import trail_history
    entry = {"date": today, "change": change, "fields": ["place"], "basis": basis}
    if basis_url:
        entry["basis_url"] = basis_url
    entry["asked_by"] = trail_history.OWN_CHECK
    entry["outcome"] = "applied"
    return entry


def _place_names(keys, names):
    return ", ".join(names.get(k, f"{k[0]}/{k[1]}") for k in keys)


def write_registry(root, entries):
    """Rewrite places.toml sorted by kind then slug, keeping the comments above
    the first entry. Only places some record names are passed in."""
    import refresh
    path = os.path.join(root, "places.toml")
    head = []
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            for line in f.read().splitlines():
                if line.startswith("[[place]]"):
                    break
                head.append(line)
    lines = list(head)
    while lines and lines[-1].strip() == "":
        lines.pop()
    for e in sorted(entries, key=lambda e: (_KIND_ORDER.get(e["kind"], 9), e["slug"])):
        lines += ["", "[[place]]"]
        for key in ("slug", "kind", "name", "where", "within", "source", "source_id",
                    "source_version", "box"):
            if key in e and e[key] not in (None, [], ()):
                lines.append(f"{key} = {refresh._scalar(e[key])}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).strip("\n") + "\n")


def registry_entries(root):
    path = os.path.join(root, "places.toml")
    if not os.path.isfile(path):
        return []
    with open(path, "rb") as f:
        return tomllib.load(f).get("place") or []


def apply(proposal_path, root, today, exclude=frozenset()):
    """Write an accepted proposal: [[place]] tables, stamps, history, the registry.
    exclude holds (trail id, kind, slug) a reviewer rejected. Returns ids written."""
    with open(proposal_path, encoding="utf-8") as f:
        data = json.load(f)
    versions = data.get("versions") or {}
    per_place = data.get("per_place") or {}
    names = {(v["kind"], v["slug"]): v["name"] for v in per_place.values()}
    written = []
    named = set()
    trackless = set(data.get("no_track") or [])
    for tid in sorted(data.get("per_trail") or {}):
        tdir = os.path.join(root, tid)
        if tid in trackless or not os.path.isfile(os.path.join(tdir, "trail.toml")):
            continue  # a trail with no track is placed by a person (stated, stamp)
        doc, path = _doc_of(root, tid)
        rec = doc.data()
        new_places = [p for p in data["per_trail"][tid]
                      if (tid, p["kind"], p["slug"]) not in exclude]
        old = {(p.get("kind"), p.get("slug")): p for p in rec.get("place") or []}
        new_keys = {(p["kind"], p["slug"]) for p in new_places}
        for k in new_keys:
            named.add(k)
        fact_change = new_keys != set(old) or any(
            (old[k].get("basis"), old[k].get("source")) != ("track", None) for k in new_keys & set(old))
        _remove_place_blocks(doc, rec)
        for p in sorted(new_places, key=lambda p: (_KIND_ORDER.get(p["kind"], 9), p["slug"])):
            doc.append_block("place", {"kind": p["kind"], "slug": p["slug"],
                                       "basis": "track", "km": round(float(p["km"]), 1)})
        _set_top(doc, rec, "places_checked", today)
        if line_file_of(tdir):
            _set_top(doc, rec, "places_track", track_hash(tdir))
        if fact_change:
            added = sorted(new_keys - set(old))
            removed = sorted(set(old) - new_keys)
            parts = []
            if added:
                parts.append(f"placed in {_place_names(added, names)}")
            if removed:
                parts.append(f"no longer placed in {_place_names(removed, names)}")
            sources = sorted({per_place[f"{k[0]}/{k[1]}"]["source"] for k in new_keys | set(old)
                              if f"{k[0]}/{k[1]}" in per_place}) or sorted(versions)[:1]
            basis_bits = ", ".join(f"the {SOURCES[s].credit} outlines ({s}, {versions.get(s, 'as downloaded')})"
                                   for s in sources if s in SOURCES)
            entry = _history_entry(
                today, f"The trail was {' and '.join(parts) or 'given its places'}.",
                f"Measured from the trail's main track against {basis_bits} by tools/place_trails.py.",
                SOURCES[sources[0]].page if sources and sources[0] in SOURCES else "")
            doc.append_history(entry)
        new_text = doc.text()
        with open(path, encoding="utf-8") as f:
            if f.read() != new_text:
                _save(doc, path)
                written.append(tid)
    entries = []
    for key, v in per_place.items():
        k = (v["kind"], v["slug"])
        if k not in named:
            continue
        old = next((x for x in registry_entries(root)
                    if (x.get("kind"), x.get("slug")) == k), {})
        # a reviewed where in the registry is kept: a re-run never rewrites it
        entry = {"slug": v["slug"], "kind": v["kind"], "name": v["name"],
                 "where": old.get("where") or v["where"],
                 "source": v["source"], "source_id": v["source_id"],
                 "source_version": versions.get(v["source"], ""), "box": v["box"]}
        if v.get("within"):
            entry["within"] = list(v["within"])
        entries.append(entry)
    # a parent range (within) is in the registry though no record names it: records never
    # store parents, and the build closes membership over within
    todo = [("range", w) for x in entries for w in (x.get("within") or ())]
    have = {(x["kind"], x["slug"]) for x in entries}
    while todo:
        k = todo.pop()
        if k in have:
            continue
        v = per_place.get(f"{k[0]}/{k[1]}")
        if v is None:
            raise ValueError(f"{k[0]}/{k[1]} is the parent of a placed range but was not measured")
        have.add(k)
        entry = {"slug": v["slug"], "kind": v["kind"], "name": v["name"], "where": v["where"],
                 "source": v["source"], "source_id": v["source_id"],
                 "source_version": versions.get(v["source"], ""), "box": v["box"]}
        if v.get("within"):
            entry["within"] = list(v["within"])
            todo.extend(("range", w) for w in v["within"])
        entries.append(entry)
    parent_keys = set(have)
    # keep registry entries a record still names (stated placements apply never
    # touches), and every within parent of a kept entry
    import build_index
    still_named = set(named)
    for tid in build_index.trail_dirs(root):
        rec = build_index.load_toml(os.path.join(root, tid, "trail.toml"))
        for pl in rec.get("place") or []:
            still_named.add((pl.get("kind"), pl.get("slug")))
    have = {(x["kind"], x["slug"]) for x in entries}
    for e in registry_entries(root):
        if (e.get("kind"), e.get("slug")) not in have:
            entries.append(e)
    entries = [e for e in entries if (e["kind"], e["slug"]) in still_named | parent_keys]
    write_registry(root, entries)
    return written


def add_stated(root, rid, kind, slug, source_url, quote, today):
    """Place a trackless trail from a cited source, with its history entry."""
    add_stated_many(root, rid, [{"kind": kind, "slug": slug, "source": source_url, "quote": quote}], today)


def add_stated_many(root, rid, items, today):
    """Place a trackless trail in every place of `items` from cited sources, with one
    history entry for the record. An item is {kind, slug, source, quote}; with
    "summary": True the quote is the sentence of the record's own description and the source is
    the page that description was taken from, and the history says so."""
    if not items:
        raise ValueError("stated needs at least one place")
    for it in items:
        if not str(it["source"]).startswith(("https://", "http://")):
            raise ValueError("stated needs an http(s) source address")
        if not str(it["quote"]).strip():
            raise ValueError("stated needs the sentence that puts the trail in the place")
    tdir = os.path.join(root, rid)
    if line_file_of(tdir):
        raise ValueError(f"{rid} has a track; stated is only for a trail with no track")
    registry = {(e.get("kind"), e.get("slug")): e for e in registry_entries(root)}
    doc, path = _doc_of(root, rid)
    rec = doc.data()
    seen = {(p.get("kind"), p.get("slug")) for p in rec.get("place") or []}
    names = []
    for it in items:
        key = (it["kind"], it["slug"])
        if key not in registry:
            raise ValueError(f"{it['kind']}/{it['slug']} is not in places.toml; add its registry entry first")
        if key in seen:
            raise ValueError(f"{rid} already names {it['kind']}/{it['slug']}")
        seen.add(key)
        names.append(registry[key].get("name") or it["slug"])
    for it in items:
        doc.append_block("place", {"kind": it["kind"], "slug": it["slug"], "basis": "stated",
                                   "source": it["source"]})
    _set_top(doc, rec, "places_checked", today)
    if len(names) == 1:
        where = names[0]
    else:
        where = ", ".join(names[:-1]) + " and " + names[-1]
    groups = {}
    for it, name in zip(items, names):
        groups.setdefault((it["source"], it["quote"], bool(it.get("summary"))), []).append(name)
    parts = []
    for (source, quote, summary), who in groups.items():
        lead = "The trail's own description says" if summary else "The page says"
        tail = f" ({', '.join(who)})" if len(groups) > 1 else ""
        parts.append(f'{lead}: "{quote}"{tail}')
    doc.append_history(_history_entry(
        today, f"The trail was placed in {where} from published pages, as it has no track to measure.",
        " ".join(parts), items[0]["source"]))
    _save(doc, path)


def stamp_none(root, rid, today):
    """Mark a trackless trail checked and in no place: places_checked only, no history."""
    doc, path = _doc_of(root, rid)
    rec = doc.data()
    if rec.get("place"):
        raise ValueError(f"{rid} already names places; stamp is for a trail in none")
    _set_top(doc, rec, "places_checked", today)
    _save(doc, path)


def check(root, cache, outlines=None, versions=None, records=None):
    """Re-measure every track against the current outlines; one difference per line."""
    if outlines is None:
        outlines = catalogue(cache)
    if versions is None:
        versions = source_versions(cache)
    if records is None:
        records = load_records(root)
    p = propose(records, outlines, {(e.get("kind"), e.get("slug")): e.get("where")
                                    for e in registry_entries(root)})
    diffs = []
    current_counts = {}
    for r in records:
        for pl in (r.get("rec") or {}).get("place") or []:
            current_counts[(pl.get("kind"), pl.get("slug"))] = \
                current_counts.get((pl.get("kind"), pl.get("slug")), 0) + 1
    for r in records:
        rec = r.get("rec") or {}
        if r.get("track") is None:
            continue
        old = {(pl.get("kind"), pl.get("slug")): pl for pl in rec.get("place") or []
               if pl.get("basis") == "track"}
        new = dict(p.per_trail.get(r["id"], []))
        for k in sorted(set(new) - set(old)):
            diffs.append(f"{r['id']}: gained {k[0]}/{k[1]}")
        for k in sorted(set(old) - set(new)):
            diffs.append(f"{r['id']}: lost {k[0]}/{k[1]}")
        for k in sorted(set(old) & set(new)):
            if abs(float(old[k].get("km") or 0) - new[k]) > 0.1:
                diffs.append(f"{r['id']}: {k[0]}/{k[1]} measurement changed (a boundary or the track moved)")
        tdir = os.path.join(root, r["id"])
        if rec.get("places_track") and line_file_of(tdir) and track_hash(tdir) != rec["places_track"]:
            diffs.append(f"{r['id']}: the track has changed since its places were measured")
    new_counts = {k: len(h.trails) for k, h in p.per_place.items()}
    for k in sorted(set(current_counts) | set(new_counts)):
        was, now = current_counts.get(k, 0) >= 3, new_counts.get(k, 0) >= 3
        if was != now:
            diffs.append(f"{k[0]}/{k[1]}: crossed the 3-trail line "
                         f"({'up to' if now else 'down to'} {new_counts.get(k, 0)} trails)")
    final, shown = {}, {}
    for e in registry_entries(root):
        shown[(e.get("kind"), e.get("slug"))] = e.get("name") or e.get("slug")
    for r in records:
        for pl in (r.get("rec") or {}).get("place") or []:
            final.setdefault((pl.get("kind"), pl.get("slug")), set()).add(r["id"])
    for k in sorted(doubled_places(final, shown)):
        diffs.append(f"{k[0]}/{k[1]}: holds exactly the trails of a park of the same name; "
                     f"list the park only")
    for e in registry_entries(root):
        v = versions.get(e.get("source"))
        if v and e.get("source_version") and e["source_version"] != v:
            diffs.append(f"{e.get('kind')}/{e.get('slug')}: source_version changed "
                         f"from {e['source_version']} to {v}")
    return diffs


def _read_exclude(path):
    out = set()
    if path:
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) == 2 and "/" in parts[1]:
                    kind, slug = parts[1].split("/", 1)
                    out.add((parts[0], kind, slug))
    return out


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
    --check [--refresh]                        re-measure and list every difference;
                                               --refresh downloads every outline again first
                                               (the monthly workflow always passes it)
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
    if "--refresh" in argv:
        clear_cache(cache_dir())
    if cmd == "propose":
        allow = load_allowlist(_opt(argv, "--allowlist", default_allowlist_path()))
        outlines = catalogue(cache_dir(), allow)
        records = load_records()
        p = propose(records, outlines, {(e.get("kind"), e.get("slug")): e.get("where")
                                        for e in registry_entries(ROOT)})
        p.versions = source_versions(cache_dir())
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
    if cmd == "apply":
        if len(argv) < 2:
            print("apply needs a proposal.json", file=sys.stderr)
            return 2
        written = apply(argv[1], ROOT, date.today().isoformat(),
                        _read_exclude(_opt(argv, "--exclude")))
        print(f"wrote {len(written)} records: {', '.join(written)}")
        return 0
    if cmd == "stated":
        # stated <id> <kind> <slug> <source url> <quote>
        if len(argv) < 6:
            print("stated needs: id kind slug source-url quote", file=sys.stderr)
            return 2
        try:
            add_stated(ROOT, argv[1], argv[2], argv[3], argv[4], argv[5], date.today().isoformat())
        except ValueError as e:
            print(f"stated: {e}", file=sys.stderr)
            return 1
        return 0
    if cmd == "stamp":
        if len(argv) < 2:
            print("stamp needs a trail id", file=sys.stderr)
            return 2
        try:
            stamp_none(ROOT, argv[1], date.today().isoformat())
        except ValueError as e:
            print(f"stamp: {e}", file=sys.stderr)
            return 1
        return 0
    if cmd == "--check":
        diffs = check(ROOT, cache_dir())
        for d in diffs:
            print(d)
        print(f"{len(diffs)} difference(s)" if diffs else "no differences")
        return 1 if diffs else 0
    print(f"place_trails.py: no subcommand {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
