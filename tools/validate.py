#!/usr/bin/env python3
"""Validate every trail directory in this repository.

Python 3 standard library only. Run from anywhere:
    python3 tools/validate.py
Prints "OK <n> trails" and exits 0, or prints one error per line and exits 1.
"""
import sys

sys.dont_write_bytecode = True

import datetime
import importlib.util
import json
import math
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_BYTES = 50 * 1024 * 1024
ALLOWED_LICENCES = {
    "us-gov-public-domain", "CC-BY-4.0", "CC-BY", "ODbL-1.0", "stated-permission",
    "CC-BY-NC-ND-4.0", "none-stated", "restricted", "unknown",
}
DATA_LICENCES = {"us-gov-public-domain", "CC-BY-4.0", "CC-BY", "ODbL-1.0", "stated-permission"}
LINE_POLICIES = {"open", "sold", "withheld", "unclear"}
NO_LINE_POLICIES = {"sold", "withheld", "unclear"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HIKE_SHAPES = {"point-to-point", "loop", "network"}
HIKE_TERRAIN = {"alpine", "forest", "desert", "coast", "prairie", "canyon", "tundra",
                "lakes", "farmland"}
HIKE_FACTS = {"summary", "official_url", "start", "end", "shape", "days", "season",
              "high_point", "high_point_m", "terrain", "permit", "unfinished", "caution",
              "months", "travel", "start_lonlat", "end_lonlat"}
LONLAT_BOUNDS = (-180.0, -50.0, 24.0, 75.0)  # lon min, lon max, lat min, lat max
HIKE_TRAVEL = {"trail", "trail-and-road", "some-cross-country", "mostly-cross-country"}
HIKE_KEYS = HIKE_FACTS | {"checked"}
ELEVATION_KEYS = {"highest", "lowest", "ascent_m", "descent_m", "track_km", "published_km",
                  "coverage", "parts", "orientation", "profile", "part_starts_km", "source"}
ELEVATION_REQUIRED = ELEVATION_KEYS - {"part_starts_km"}
ELEVATION_SOURCE_REQUIRED = ("model", "attribution", "zoom", "sample_spacing_m", "smoothing",
                             "computed")
ELEVATION_ORIENTATIONS = {"south-to-north", "west-to-east"}

spec = importlib.util.spec_from_file_location(
    "build_index", os.path.join(ROOT, "tools", "build_index.py"))
build_index = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_index)
load_toml = build_index.load_toml

spec = importlib.util.spec_from_file_location(
    "trail_history", os.path.join(ROOT, "tools", "trail_history.py"))
trail_history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trail_history)


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


PERMISSION_FIELDS = ("permission_quote", "permission_by", "permission_date", "permission_url")


def check_stated_permission(tid, src, errors):
    """A track shared by stated permission quotes the statement, says who made it, when and where.

    The four permission_* fields are required for that licence and refused for every other one."""
    if src.get("licence") != "stated-permission":
        for field in PERMISSION_FIELDS:
            if field in src:
                errors.append(f"{tid}: source.{field} belongs to the stated-permission licence only")
        return
    text = src.get("licence_text")
    if not isinstance(text, str) or not text.strip():
        errors.append(f"{tid}: licence stated-permission needs a non-empty source.licence_text")
    for field in ("permission_quote", "permission_by"):
        value = src.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{tid}: licence stated-permission needs a non-empty source.{field}")
    date = src.get("permission_date")
    if not isinstance(date, str) or not DATE_RE.match(date):
        errors.append(f"{tid}: licence stated-permission needs source.permission_date as YYYY-MM-DD")
    else:
        try:
            datetime.date.fromisoformat(date)
        except ValueError:
            errors.append(f"{tid}: source.permission_date {date!r} is not a real date")
    url = src.get("permission_url")
    if not isinstance(url, str) or not re.match(r"^https?://[^\s/]+\S*$", url):
        errors.append(f"{tid}: licence stated-permission needs source.permission_url as an http(s) address")


SHIELD_STATUSES = ("use-real-logo", "no-logo-exists", "logo-not-found")
SHIELD_FILES = ("shield.svg", "shield.png")


def check_shield(tid, shield, tdir, errors):
    """The [shield] table: status, logo file and the words that go with each state.

    use-real-logo: a logo file is included, and names its holder or source.
    no-logo-exists: the trail has no emblem of its own; no file; the note says where that was checked.
    logo-not-found: an emblem exists or may exist, but no usable artwork was found at an allowed
    source; no file; the note says where it was looked for or seen.
    """
    status = shield.get("status")
    if not status:
        errors.append(f"{tid}: missing required field shield.status")
    elif status not in SHIELD_STATUSES:
        errors.append(f"{tid}: shield.status {status!r} is not one of {', '.join(SHIELD_STATUSES)}")
    logo_file = shield.get("logo_file") or ""
    on_disk = [f for f in SHIELD_FILES if os.path.isfile(os.path.join(tdir, f))]
    if logo_file and logo_file not in SHIELD_FILES:
        errors.append(f"{tid}: shield.logo_file {logo_file!r} is not shield.svg or shield.png")
    if status == "use-real-logo" and not logo_file:
        errors.append(f"{tid}: shield.status is use-real-logo but shield.logo_file names no file "
                      "(a trail with no usable artwork is logo-not-found, or no-logo-exists when it has no emblem)")
    if status in ("no-logo-exists", "logo-not-found"):
        if logo_file or on_disk:
            errors.append(f"{tid}: shield.status is {status} but a logo file is included; "
                          "a trail with a logo file is use-real-logo")
        if not str(shield.get("note", "")).strip():
            errors.append(f"{tid}: shield.status is {status} and shield.note does not say where an emblem was looked for")
    if on_disk:
        if logo_file not in on_disk:
            errors.append(f"{tid}: logo file on disk {on_disk} but shield.logo_file is {logo_file!r}")
        if not str(shield.get("logo_owner", "")).strip():
            errors.append(f"{tid}: logo present but shield.logo_owner is empty")
        if not str(shield.get("logo_source", "")).strip() and not str(shield.get("logo_owner", "")).strip():
            errors.append(f"{tid}: logo present but its source and holder are not named")
    if logo_file and not os.path.isfile(os.path.join(tdir, logo_file)):
        errors.append(f"{tid}: declared logo file {logo_file} does not exist")


def check_guides(tid, guides, errors):
    """[[guide]]: a route needs at least one (checked with the route); any trail may have its holder's own."""
    if guides is None:
        return
    if not isinstance(guides, list):
        errors.append(f"{tid}: guide must be an array of tables")
        return
    for i, g in enumerate(guides, 1):
        for field in ("title", "author", "access", "url"):
            if not str(g.get(field, "")).strip():
                errors.append(f"{tid}: guide {i} is missing {field}")
        if g.get("access") not in ("free", "purchase"):
            errors.append(
                f"{tid}: guide {i} access must be \"free\" or \"purchase\", "
                f"not {g.get('access')!r}")
        if not str(g.get("url", "")).startswith(("https://", "http://")):
            errors.append(f"{tid}: guide {i} url must be an http(s) URL")
        if (str(g.get("price", "")).strip()
                and not DATE_RE.match(str(g.get("price_checked", "")))):
            errors.append(
                f"{tid}: guide {i} has a price but no price_checked date "
                "(YYYY-MM-DD)")


def check_hike(tid, rec, errors):
    """Check the optional [hike] table and its [[hike.source]] tables."""
    hike = rec.get("hike")
    if hike is None:
        return
    if not isinstance(hike, dict):
        errors.append(f"{tid}: hike must be a table")
        return

    def text(name):
        value = hike[name]
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{tid}: hike.{name} must be a non-empty string")
            return False
        return True

    for name in sorted(set(hike) - HIKE_KEYS - {"source"}):
        errors.append(f"{tid}: hike.{name} is not a known field")
    for name in ("summary", "official_url", "start", "end", "season", "high_point",
                 "permit", "unfinished", "caution"):
        if name in hike:
            text(name)
    if "official_url" in hike and not str(hike["official_url"]).startswith(("https://", "http://")):
        errors.append(f"{tid}: hike.official_url must be an http(s) URL")
    if "shape" in hike and hike["shape"] not in HIKE_SHAPES:
        errors.append(
            f"{tid}: hike.shape must be one of {', '.join(sorted(HIKE_SHAPES))}, "
            f"not {hike['shape']!r}")
    if "days" in hike:
        days = hike["days"]
        ints = (isinstance(days, list) and len(days) == 2
                and all(isinstance(d, int) and not isinstance(d, bool) and d > 0 for d in days))
        if not ints:
            errors.append(f"{tid}: hike.days must be two positive integers [fewest, most]")
        elif days[0] > days[1]:
            errors.append(f"{tid}: hike.days {days} has the fewest days after the most")
    if "travel" in hike and hike["travel"] not in HIKE_TRAVEL:
        errors.append(
            f"{tid}: hike.travel must be one of {', '.join(sorted(HIKE_TRAVEL))}, "
            f"not {hike['travel']!r}")

    def lonlat(name):
        value = hike[name]
        if (not isinstance(value, list) or len(value) != 2
                or not all(isinstance(x, (int, float)) and not isinstance(x, bool)
                           for x in value)):
            errors.append(f"{tid}: hike.{name} must be two numbers, [longitude, latitude]")
            return None
        lon, lat = float(value[0]), float(value[1])
        if not (LONLAT_BOUNDS[0] <= lon <= LONLAT_BOUNDS[1]
                and LONLAT_BOUNDS[2] <= lat <= LONLAT_BOUNDS[3]):
            errors.append(
                f"{tid}: hike.{name} [{lon}, {lat}] is out of range: longitude must be "
                f"{LONLAT_BOUNDS[0]} to {LONLAT_BOUNDS[1]} and latitude "
                f"{LONLAT_BOUNDS[2]} to {LONLAT_BOUNDS[3]}")
            return None
        return (lon, lat)

    end_points = {}
    for name, place in (("start_lonlat", "start"), ("end_lonlat", "end")):
        if name in hike:
            if place not in hike and not rec.get("source", {}).get("line_file"):
                errors.append(f"{tid}: hike.{name} is present but hike.{place} is not")
            point = lonlat(name)
            if point is not None:
                end_points[name] = point
    if len(end_points) == 2:
        length = rec.get("length_km")
        if isinstance(length, (int, float)) and not isinstance(length, bool) and length > 0:
            straight = haversine_km([end_points["start_lonlat"], end_points["end_lonlat"]])
            if straight > length * 1.02:
                errors.append(
                    f"{tid}: hike.start_lonlat and hike.end_lonlat are {straight:.1f} km "
                    f"apart, which is more than length_km {length}")

    if "months" in hike:
        months = hike["months"]
        ok = (isinstance(months, list) and months
              and all(isinstance(m, int) and not isinstance(m, bool) and 1 <= m <= 12
                      for m in months))
        if not ok:
            errors.append(f"{tid}: hike.months must be a list of month numbers from 1 to 12")
        elif len(set(months)) != len(months):
            errors.append(f"{tid}: hike.months repeats a month")
    if "high_point_m" in hike:
        metres = hike["high_point_m"]
        if (not isinstance(metres, int) or isinstance(metres, bool)
                or not -100 <= metres <= 6200):
            errors.append(f"{tid}: hike.high_point_m must be an integer from -100 to 6200")
    if "terrain" in hike:
        terrain = hike["terrain"]
        if not isinstance(terrain, list) or not 1 <= len(terrain) <= 3:
            errors.append(f"{tid}: hike.terrain must be a list of one to three words")
        else:
            for word in terrain:
                if word not in HIKE_TERRAIN:
                    errors.append(
                        f"{tid}: hike.terrain word {word!r} is not one of "
                        f"{', '.join(sorted(HIKE_TERRAIN))}")
            if len(set(terrain)) != len(terrain):
                errors.append(f"{tid}: hike.terrain repeats a word")
    if not DATE_RE.match(str(hike.get("checked", ""))):
        errors.append(f"{tid}: hike.checked must be a date (YYYY-MM-DD)")
    else:
        try:
            datetime.date.fromisoformat(hike["checked"])
        except ValueError:
            errors.append(f"{tid}: hike.checked {hike['checked']!r} is not a real date")

    sources = hike.get("source")
    covered = set()
    if not isinstance(sources, list) or not sources:
        errors.append(f"{tid}: hike is present but there is no [[hike.source]] table")
        sources = []
    for i, s in enumerate(sources, 1):
        if not isinstance(s, dict):
            errors.append(f"{tid}: hike source {i} must be a table")
            continue
        for name in sorted(set(s) - {"url", "publisher", "facts"}):
            errors.append(f"{tid}: hike source {i} has unknown field {name}")
        if not str(s.get("url", "")).startswith(("https://", "http://")):
            errors.append(f"{tid}: hike source {i} url must be an http(s) URL")
        if not str(s.get("publisher", "")).strip():
            errors.append(f"{tid}: hike source {i} is missing publisher")
        facts = s.get("facts")
        if not isinstance(facts, list) or not facts:
            errors.append(f"{tid}: hike source {i} facts must be a non-empty list")
            continue
        for fact in facts:
            if fact not in HIKE_FACTS:
                errors.append(f"{tid}: hike source {i} names {fact!r}, which is not a hike field")
            elif fact == "high_point":
                covered.update(("high_point", "high_point_m"))
            else:
                covered.add(fact)
    for name in sorted(set(hike) & HIKE_KEYS - {"checked"}) if sources else []:
        if name not in covered:
            errors.append(f"{tid}: hike.{name} is not named in the facts of any hike source")


def check_elevation(tid, tdir, rec, errors):
    """Check <id>/elevation.json where it is present."""
    path = os.path.join(tdir, "elevation.json")
    if not os.path.isfile(path):
        return
    where = f"{tid}/elevation.json"
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception as e:  # noqa: BLE001
        errors.append(f"{where}: does not parse: {e}")
        return
    if not isinstance(doc, dict):
        errors.append(f"{where}: top level must be an object")
        return
    if not os.path.isfile(os.path.join(tdir, "line.geojson")):
        errors.append(f"{where}: present but the trail has no track (line.geojson)")
    for name in sorted(ELEVATION_REQUIRED - set(doc)):
        errors.append(f"{where}: missing {name}")
    for name in sorted(set(doc) - ELEVATION_KEYS):
        errors.append(f"{where}: {name} is not a known field")

    def number(value, low, high):
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and low <= value <= high)

    points = {}
    for name in ("highest", "lowest"):
        p = doc.get(name)
        if name not in doc:
            continue
        if not isinstance(p, dict) or set(p) != {"m", "lon", "lat"}:
            errors.append(f"{where}: {name} must hold m, lon and lat")
            continue
        if not number(p["m"], -500, 9000):
            errors.append(f"{where}: {name}.m must be a number from -500 to 9000 metres")
        if not number(p["lon"], -180, 180) or not number(p["lat"], -90, 90):
            errors.append(f"{where}: {name} has a longitude or latitude out of range")
        points[name] = p["m"]
    if len(points) == 2 and number(points["highest"], -500, 9000) and number(points["lowest"], -500, 9000):
        if points["highest"] < points["lowest"]:
            errors.append(f"{where}: highest {points['highest']} is below lowest {points['lowest']}")
    for name in ("ascent_m", "descent_m"):
        if name in doc and not number(doc[name], 0, 2_000_000):
            errors.append(f"{where}: {name} must be a number from 0 to 2000000")
    track_km = doc.get("track_km")
    if "track_km" in doc and not number(track_km, 0.01, 100_000):
        errors.append(f"{where}: track_km must be a positive number of kilometres")
        track_km = None
    published = doc.get("published_km")
    if "published_km" in doc:
        if published != rec.get("length_km"):
            errors.append(f"{where}: published_km {published!r} is not the record's length_km "
                          f"{rec.get('length_km')!r}")
        elif published and track_km and "coverage" in doc:
            if not number(doc["coverage"], 0, 10) or abs(doc["coverage"] - track_km / published) > 0.01:
                errors.append(f"{where}: coverage {doc['coverage']!r} is not track_km / published_km")
    parts = doc.get("parts")
    if "parts" in doc and (not isinstance(parts, int) or isinstance(parts, bool) or parts < 1):
        errors.append(f"{where}: parts must be a whole number of 1 or more")
        parts = None
    if doc.get("orientation") not in ELEVATION_ORIENTATIONS and "orientation" in doc:
        errors.append(f"{where}: orientation must be one of "
                      f"{', '.join(sorted(ELEVATION_ORIENTATIONS))}")
    if "part_starts_km" in doc:
        starts = doc["part_starts_km"]
        if (not isinstance(starts, list) or not all(number(x, 0, 100_000) for x in starts)
                or starts != sorted(starts)
                or (parts is not None and len(starts) != parts - 1)):
            errors.append(f"{where}: part_starts_km must be a list, never decreasing, with one "
                          "entry for each part after the first")
    elif parts and parts > 1:
        errors.append(f"{where}: {parts} parts but no part_starts_km")

    profile = doc.get("profile")
    if "profile" in doc:
        ok = (isinstance(profile, list) and 2 <= len(profile) <= 1500
              and all(isinstance(p, list) and len(p) == 2 and number(p[0], 0, 100_000)
                      and number(p[1], -500, 9000) for p in profile))
        if not ok:
            errors.append(f"{where}: profile must be 2 to 1500 [distance_km, elevation_m] pairs")
        else:
            dists = [p[0] for p in profile]
            starts = doc.get("part_starts_km") if isinstance(doc.get("part_starts_km"), list) else []
            # distances increase; the first point of a later part may repeat the
            # distance of the point before it (the gap between two parts)
            if any(b < a or (b == a and b not in starts) for a, b in zip(dists, dists[1:])):
                errors.append(f"{where}: profile distances must increase")
            if track_km and dists[-1] > track_km + 0.1:
                errors.append(f"{where}: profile runs past track_km")
            if len(points) == 2:
                top, bottom = max(p[1] for p in profile), min(p[1] for p in profile)
                if top > points["highest"] + 1 or bottom < points["lowest"] - 1:
                    errors.append(f"{where}: profile lies outside the highest and lowest points")

    src = doc.get("source")
    if "source" in doc:
        if not isinstance(src, dict):
            errors.append(f"{where}: source must be an object")
        else:
            for name in ELEVATION_SOURCE_REQUIRED:
                if src.get(name) in (None, ""):
                    errors.append(f"{where}: source.{name} is missing")
            if not isinstance(src.get("zoom"), int) or not 0 <= src.get("zoom", -1) <= 15:
                errors.append(f"{where}: source.zoom must be a whole number from 0 to 15")
            if not number(src.get("sample_spacing_m"), 1, 1000):
                errors.append(f"{where}: source.sample_spacing_m must be a number of metres")
            if not DATE_RE.match(str(src.get("computed", ""))):
                errors.append(f"{where}: source.computed must be a date (YYYY-MM-DD)")


def check_short_name(tid, rec, errors):
    """short_name is optional; where present it needs short_name_url, the page where it was seen in use."""
    name, url = rec.get("short_name"), rec.get("short_name_url")
    if "short_name" in rec:
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{tid}: short_name must be a non-empty string (leave it out when no abbreviation is in use)")
        elif name != name.strip():
            errors.append(f"{tid}: short_name has a leading or trailing space")
        elif "." in name:
            errors.append(f"{tid}: short_name must be written without full stops (\"AT\", not \"A.T.\")")
        if "short_name_url" not in rec:
            errors.append(f"{tid}: short_name needs short_name_url, the page where it was seen in use")
    elif "short_name_url" in rec:
        errors.append(f"{tid}: short_name_url without short_name")
    if "short_name_url" in rec and not (isinstance(url, str) and url.startswith(("https://", "http://"))):
        errors.append(f"{tid}: short_name_url must be an http(s) URL")


LINK_FIELDS = ("title", "publisher", "url")
LINK_KEYS = {"title", "publisher", "url", "note"}


def _page(url):
    """A URL without its scheme and trailing slash, for telling whether two are the same page."""
    return re.sub(r"^https?://", "", str(url).strip()).rstrip("/")


def check_links(tid, rec, errors):
    """[[link]]: other pages about this one trail. Optional."""
    links = rec.get("link")
    if links is None:
        return
    if not isinstance(links, list) or not all(isinstance(l, dict) for l in links):
        errors.append(f"{tid}: link must be an array of tables ([[link]])")
        return
    own = {_page(u) for u in (rec.get("hike", {}).get("official_url"),
                              rec.get("source", {}).get("publisher_url")) if u}
    seen = set()
    for i, l in enumerate(links, 1):
        for field in LINK_FIELDS:
            if not isinstance(l.get(field), str) or not l[field].strip():
                errors.append(f"{tid}: link {i} is missing {field}")
        if "note" in l and (not isinstance(l["note"], str) or not l["note"].strip()):
            errors.append(f"{tid}: link {i} note must be a non-empty string")
        for name in l:
            if name not in LINK_KEYS:
                errors.append(f"{tid}: link {i} has unknown field {name}")
        url = l.get("url")
        if not isinstance(url, str) or not url:
            continue
        if not url.startswith(("https://", "http://")):
            errors.append(f"{tid}: link {i} url must be an http(s) URL")
        page = _page(url)
        if page in seen:
            errors.append(f"{tid}: link {i} repeats the url of an earlier link")
        seen.add(page)
        if page in own:
            errors.append(f"{tid}: link {i} is the official site or the publisher's page; "
                          "that belongs in hike.official_url or source.publisher_url")


LEFT_OUT_FILE = "left-out.toml"
LEFT_OUT_REASONS = {
    "below-floor", "rail-trail-or-towpath", "driving-route", "not-mainly-walking",
    "network", "cannot-be-walked-through", "mostly-unbuilt",
    "not-published-as-route", "waiting",
}
LEFT_OUT_KEYS = {
    "id", "name", "country", "regions", "length_mi", "length_km", "length_note",
    "reason", "note", "source_url", "decided", "was_listed", "waiting_for",
}
LEFT_OUT_REQUIRED = ("id", "name", "country", "regions", "reason", "note",
                     "decided", "was_listed")
LEFT_OUT_REGIONS = {
    "AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DC", "DE", "FL", "GA", "HI",
    "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA", "MD", "ME", "MI", "MN",
    "MO", "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM", "NV", "NY", "OH",
    "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA",
    "WI", "WV", "WY",
    "AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT",
    "all provinces and territories", "contiguous United States",
}
KM_PER_MI = 1.609344


def _left_out_name_key(name):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(name).lower()).split())


def check_left_out_entries(entries, trails, errors, where=LEFT_OUT_FILE):
    """Check the entries of left-out.toml against the listed trails.

    entries is the file's [[trail]] list; trails the records in the dataset.
    """
    if not isinstance(entries, list) or not entries:
        errors.append(f"{where}: must hold at least one [[trail]] entry")
        return
    listed_ids = {r.get("id") for r in trails}
    listed_names = {_left_out_name_key(r.get("name", "")) for r in trails}
    seen_ids, seen_names = set(), set()
    names = []
    for i, e in enumerate(entries, 1):
        if not isinstance(e, dict):
            errors.append(f"{where}: entry {i} must be a table ([[trail]])")
            continue
        who = e.get("id") or f"entry {i}"
        for field in LEFT_OUT_REQUIRED:
            value = e.get(field)
            if value in ("", None, []) or (isinstance(value, str) and not value.strip()):
                errors.append(f"{where}: {who} is missing required field {field}")
        for name in sorted(set(e) - LEFT_OUT_KEYS):
            errors.append(f"{where}: {who} has unknown field {name}")
        for field in ("id", "name", "note"):
            value = e.get(field)
            if field in e and (not isinstance(value, str) or not value.strip()):
                errors.append(f"{where}: {who} {field} must be a non-empty string")
        eid = e.get("id")
        if isinstance(eid, str) and eid:
            if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", eid):
                errors.append(f"{where}: {eid!r} is not a plain id of lower case words and hyphens")
            if eid in seen_ids:
                errors.append(f"{where}: duplicate id {eid}")
            seen_ids.add(eid)
            if eid in listed_ids:
                errors.append(f"{where}: {eid} matches a trail that is listed in the dataset")
        ename = e.get("name")
        if isinstance(ename, str) and ename.strip():
            names.append(ename)
            key = _left_out_name_key(ename)
            if key in seen_names:
                errors.append(f"{where}: duplicate name {ename}")
            seen_names.add(key)
            if key in listed_names:
                errors.append(f"{where}: {ename} matches a trail that is listed in the dataset")
        if "country" in e and e.get("country") not in ("US", "CA"):
            errors.append(f"{where}: {who} country must be US or CA")
        regions = e.get("regions")
        if "regions" in e and regions not in ("", None, []):
            if not isinstance(regions, list) or not regions:
                errors.append(f"{where}: {who} regions must be a non-empty list of region codes")
            else:
                for code in regions:
                    if code not in LEFT_OUT_REGIONS:
                        errors.append(f"{where}: {who} region {code!r} is not a known state or province code")
                if len(set(map(str, regions))) != len(regions):
                    errors.append(f"{where}: {who} regions repeats a code")
        if "reason" in e and e.get("reason") not in LEFT_OUT_REASONS and str(e.get("reason")).strip():
            errors.append(
                f"{where}: {who} reason must be one of "
                f"{', '.join(sorted(LEFT_OUT_REASONS))}, not {e.get('reason')!r}")
        decided = e.get("decided")
        if "decided" in e and str(decided).strip():
            if not isinstance(decided, str) or not DATE_RE.match(decided):
                errors.append(f"{where}: {who} decided must be a date (YYYY-MM-DD)")
            else:
                try:
                    datetime.date.fromisoformat(decided)
                except ValueError:
                    errors.append(f"{where}: {who} decided {decided!r} is not a real date")
        if "was_listed" in e and e.get("was_listed") not in ("", None):
            if not isinstance(e.get("was_listed"), bool):
                errors.append(f"{where}: {who} was_listed must be true or false")
        url = e.get("source_url")
        if "source_url" in e:
            if not isinstance(url, str) or not url.startswith(("https://", "http://")):
                errors.append(f"{where}: {who} source_url must be an http(s) URL")
        elif "no page" not in str(e.get("note", "")).lower():
            errors.append(
                f"{where}: {who} has no source_url, and its note does not say that no page exists")
        if e.get("reason") == "waiting":
            waiting_for = e.get("waiting_for")
            if not isinstance(waiting_for, str) or not waiting_for.strip():
                errors.append(f"{where}: {who} reason is waiting, so waiting_for must say what would change the decision")
        elif "waiting_for" in e:
            errors.append(f"{where}: {who} waiting_for belongs to reason waiting only")
        lengths = {}
        for field in ("length_mi", "length_km"):
            if field in e:
                value = e[field]
                if (not isinstance(value, (int, float)) or isinstance(value, bool)
                        or value <= 0):
                    errors.append(f"{where}: {who} {field} must be a positive number")
                else:
                    lengths[field] = float(value)
        if len(lengths) == 2:
            km_from_mi = lengths["length_mi"] * KM_PER_MI
            if abs(km_from_mi - lengths["length_km"]) > max(1.5, 0.02 * lengths["length_km"]):
                errors.append(
                    f"{where}: {who} length_mi {e['length_mi']} and length_km "
                    f"{e['length_km']} do not agree")
        if "length_note" in e:
            note = e["length_note"]
            if not isinstance(note, str) or not note.strip():
                errors.append(f"{where}: {who} length_note must be a non-empty string")
    if names != sorted(names, key=str.lower):
        errors.append(f"{where}: entries must be sorted by name")


def check_left_out(root, trails, errors):
    """Check left-out.toml at the top level: trails considered and left out."""
    path = os.path.join(root, LEFT_OUT_FILE)
    if not os.path.isfile(path):
        errors.append(f"{LEFT_OUT_FILE}: missing")
        return
    try:
        doc = load_toml(path)
    except Exception as e:  # noqa: BLE001 - report and continue
        errors.append(f"{LEFT_OUT_FILE}: does not parse: {e}")
        return
    for name in sorted(set(doc) - {"trail"}):
        errors.append(f"{LEFT_OUT_FILE}: unknown top level field {name}")
    check_left_out_entries(doc.get("trail"), trails, errors)


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

        for field in ("id", "name", "country", "regions",
                      "length_km", "tier", "designation"):
            if field not in rec or rec[field] in ("", None, []):
                errors.append(f"{tid}: missing required field {field}")
        check_short_name(tid, rec, errors)
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
        check_stated_permission(tid, src, errors)
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

        check_shield(tid, rec.get("shield", {}), tdir, errors)

        osm = rec.get("osm", {})
        if "relation" not in osm:
            errors.append(f"{tid}: missing required field osm.relation")
        if not rec.get("verification", {}).get("verified") in (True, False):
            errors.append(f"{tid}: missing required field verification.verified")

        kind = rec.get("kind")
        route = rec.get("route")
        guides = rec.get("guide")
        if kind is not None and kind != "route":
            errors.append(f"{tid}: kind must be \"route\" when present, not {kind!r}")
        if kind == "route":
            if not isinstance(route, dict):
                errors.append(f"{tid}: kind is \"route\" but there is no [route] table")
                route = {}
            if not str(route.get("creator", "")).strip():
                errors.append(f"{tid}: route.creator is missing")
            policy = route.get("line_policy")
            if policy not in LINE_POLICIES:
                errors.append(
                    f"{tid}: route.line_policy must be one of "
                    f"{', '.join(sorted(LINE_POLICIES))}, not {policy!r}")
            if (str(route.get("creator_words", "")).strip()
                    and not str(route.get("creator_words_url", "")).strip()):
                errors.append(
                    f"{tid}: route.creator_words is present but "
                    "route.creator_words_url is missing")
            if not isinstance(guides, list) or not guides:
                errors.append(f"{tid}: kind is \"route\" but there is no [[guide]] table")
            if policy in NO_LINE_POLICIES:
                if src.get("line_file"):
                    errors.append(
                        f"{tid}: line_policy is {policy}, so source.line_file must be empty")
                for name in ("line.geojson", "alternates.geojson"):
                    if os.path.isfile(os.path.join(tdir, name)):
                        errors.append(
                            f"{tid}: line_policy is {policy}, so {name} must not be present")
                if osm.get("relation"):
                    errors.append(
                        f"{tid}: line_policy is {policy}, so osm.relation must be 0")
                if not str(src.get("line_absent_reason", "")).strip():
                    errors.append(
                        f"{tid}: line_policy is {policy}, so source.line_absent_reason "
                        "must say why no line is included")
        else:
            if route is not None:
                errors.append(f"{tid}: [route] table present but kind is not \"route\"")

        check_guides(tid, guides, errors)
        check_links(tid, rec, errors)
        check_hike(tid, rec, errors)
        check_elevation(tid, tdir, rec, errors)
        trail_history.check_entries(tid, rec, errors)

    check_left_out(ROOT, trails, errors)

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
