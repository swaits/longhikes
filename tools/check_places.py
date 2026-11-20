"""Checks for places.toml and the place fields on each record.

    places.toml   [[place]]  slug, kind, name, where, within, source, source_id,
                             source_version, box (docs/schema.md, "places.toml")
    trail.toml    [[place]]  kind, slug, basis, km or source; places_checked, places_track

Each function appends one message per problem to `errors`. Used by tools/validate.py.
Python 3 standard library only.
"""
import datetime
import hashlib
import os
import re
import tomllib

KINDS = ("park", "range", "wilderness")
SOURCES = ("nps", "wilderness-connect", "cpcad", "gmba-v2")
REGISTRY_KEYS = {"slug", "kind", "name", "where", "within", "source", "source_id",
                 "source_version", "box"}
REGISTRY_REQUIRED = ("slug", "kind", "name", "where", "source", "source_id",
                     "source_version", "box")
PLACE_KEYS = {"kind", "slug", "basis", "km", "source"}
ID_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
HASH_RE = re.compile(r"[0-9a-f]{16}")

# Ship 1 validates shape only. Ship 2 turns this on once every record is placed,
# so a new trail or a new track cannot ship unplaced.
REQUIRE_PLACES_CHECKED = True


def track_hash(path):
    """The first 16 hex digits of the SHA-256 of the file's bytes."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _is_date(value):
    if isinstance(value, datetime.date):
        return True
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        return False
    try:
        datetime.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _text(table, field, where, errors):
    value = table.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{where} {field} must be a non-empty string")
        return ""
    return value


def check_registry(entries, errors):
    """Check the shape of places.toml's entries: fields, kinds, slugs, boxes, within."""
    seen = {}
    by_key = {}
    for i, e in enumerate(entries, 1):
        where = f"places.toml: entry {i}"
        if not isinstance(e, dict):
            errors.append(f"{where} must be a table ([[place]])")
            continue
        where = f"places.toml: {e.get('kind', '?')}/{e.get('slug', f'entry {i}')}"
        for name in sorted(set(e) - REGISTRY_KEYS):
            errors.append(f"{where} has unknown field {name}")
        for name in REGISTRY_REQUIRED:
            if name not in e:
                errors.append(f"{where} is missing required field {name}")
        slug = _text(e, "slug", where, errors) if "slug" in e else ""
        if slug and not ID_RE.fullmatch(slug):
            errors.append(f"{where} slug must be lower-case words joined by hyphens")
        kind = e.get("kind")
        if "kind" in e and kind not in KINDS:
            errors.append(f"{where} kind must be park, range or wilderness, not {kind!r}")
        if "name" in e:
            _text(e, "name", where, errors)
        where_codes = e.get("where")
        if "where" in e and (not isinstance(where_codes, list) or not where_codes
                             or not all(isinstance(c, str) and c for c in where_codes)):
            errors.append(f"{where} where must be a non-empty list of state or province codes")
        source = e.get("source")
        if "source" in e and source not in SOURCES:
            errors.append(f"{where} source must be one of {', '.join(SOURCES)}, not {source!r}")
        sid = e.get("source_id")
        if "source_id" in e:
            ok = (isinstance(sid, str) and sid.strip()) or (
                isinstance(sid, list) and sid and all(isinstance(s, str) and s.strip() for s in sid))
            if not ok:
                errors.append(f"{where} source_id must be a string or a non-empty list of strings")
        if "source_version" in e:
            _text(e, "source_version", where, errors)
        box = e.get("box")
        if "box" in e:
            ok = (isinstance(box, list) and len(box) == 4
                  and all(isinstance(v, (int, float)) for v in box)
                  and -180.0 <= box[0] < box[2] <= 180.0 and -90.0 <= box[1] < box[3] <= 90.0)
            if not ok:
                errors.append(f"{where} box must be [west, south, east, north] inside the world, west before east and south before north")
        within = e.get("within", [])
        if not isinstance(within, list) or not all(isinstance(s, str) and s for s in within):
            errors.append(f"{where} within must be a list of parent place slugs")
        key = (kind, slug)
        if slug and kind in KINDS:
            if key in seen:
                errors.append(f"{where} slug {slug!r} is used twice in kind {kind}")
            seen[key] = e
            by_key[key] = e
    # within: parents exist, are ranges, and never circle
    for (kind, slug), e in by_key.items():
        where = f"places.toml: {kind}/{slug}"
        for parent in e.get("within", []) or []:
            if ("range", parent) not in by_key:
                errors.append(f"{where} within names {parent!r}, which is not an existing range in places.toml")
    def walk(slug, trail):
        for parent in (by_key.get(("range", slug), {}).get("within") or []):
            if parent in trail:
                errors.append(f"places.toml: within circles back to {parent} ({' -> '.join(trail + [parent])})")
                return
            walk(parent, trail + [parent])
    for (kind, slug) in by_key:
        if kind == "range":
            walk(slug, [slug])


def check_record(tid, rec, tdir, registry, errors):
    """Check one record's [[place]] tables, places_checked and places_track."""
    places = rec.get("place", [])
    if places is None:
        places = []
    if not isinstance(places, list) or not all(isinstance(p, dict) for p in places):
        errors.append(f"{tid}: place must be an array of tables ([[place]])")
        places = []
    line_file = str((rec.get("source") or {}).get("line_file") or "")
    has_track = bool(line_file)
    seen = set()
    for i, p in enumerate(places, 1):
        where = f"{tid}: place {i}"
        for name in sorted(set(p) - PLACE_KEYS):
            errors.append(f"{where} has unknown field {name}")
        kind, slug, basis = p.get("kind"), p.get("slug"), p.get("basis")
        if kind not in KINDS:
            errors.append(f"{where} kind must be park, range or wilderness, not {kind!r}")
        if not isinstance(slug, str) or not slug:
            errors.append(f"{where} slug must be a non-empty string")
        elif kind in KINDS and (kind, slug) not in registry:
            errors.append(f"{where} {kind}/{slug} is not in places.toml")
        if kind in KINDS and (kind, slug) in registry:
            lies = [str(c) for c in registry[(kind, slug)].get("where") or []]
            regions = [str(c) for c in rec.get("regions") or []]
            if lies and regions and not set(lies) & set(regions):
                errors.append(f"{where} {kind}/{slug} lies in {', '.join(lies)}, none of the "
                              f"record's regions ({', '.join(regions)}); a place must lie in at "
                              f"least one of the trail's states or provinces")
        if (kind, slug) in seen:
            errors.append(f"{where} lists {kind}/{slug} more than once; a place is listed once per record")
        seen.add((kind, slug))
        if basis not in ("track", "stated"):
            errors.append(f"{where} basis must be track or stated, not {basis!r}")
            continue
        if basis == "track":
            if not has_track:
                errors.append(f"{where} basis is track but the record has no track")
            km = p.get("km")
            if not isinstance(km, (int, float)) or isinstance(km, bool) or km <= 0:
                errors.append(f"{where} basis track needs km, the measured length inside")
            if "source" in p:
                errors.append(f"{where} basis track must not have a source; source is for stated")
        else:
            if has_track:
                errors.append(f"{where} basis stated is only for a trail with no track; this record has one, so it must be re-measured")
            if "km" in p:
                errors.append(f"{where} basis stated must not have km; km is a measurement")
            source = p.get("source")
            if not isinstance(source, str) or not source.startswith(("https://", "http://")):
                errors.append(f"{where} basis stated needs a source that is an http(s) address")
    checked = rec.get("places_checked")
    if checked is None:
        if REQUIRE_PLACES_CHECKED:
            errors.append(f"{tid}: places_checked is missing; run tools/place_trails.py (a trail in no park, range or wilderness still carries the date)")
    elif not _is_date(checked):
        errors.append(f"{tid}: places_checked must be a date (YYYY-MM-DD)")
    stamp = rec.get("places_track")
    if has_track:
        if checked is not None or REQUIRE_PLACES_CHECKED:
            if stamp is None:
                errors.append(f"{tid}: places_track is missing; a record with a track records the track its places were measured from")
        if stamp is not None:
            if not isinstance(stamp, str) or not HASH_RE.fullmatch(stamp):
                errors.append(f"{tid}: places_track must be 16 hex digits")
            else:
                path = os.path.join(tdir, line_file)
                if os.path.isfile(path) and track_hash(path) != stamp:
                    errors.append(f"{tid}: the track has changed since its places were measured (places_track does not match {line_file}); run tools/place_trails.py")
    elif stamp is not None:
        errors.append(f"{tid}: places_track is present but the record has no track")


def check(root, trails, errors):
    """Load places.toml, check it and every record, then the cross-checks."""
    path = os.path.join(root, "places.toml")
    if not os.path.isfile(path):
        errors.append("places.toml: missing")
        return
    try:
        with open(path, "rb") as f:
            entries = tomllib.load(f).get("place") or []
    except Exception as e:  # noqa: BLE001 - report and continue
        errors.append(f"places.toml: does not parse: {e}")
        return
    if not isinstance(entries, list):
        errors.append("places.toml: place must be an array of tables ([[place]])")
        return
    check_registry(entries, errors)
    registry = {(e.get("kind"), e.get("slug")): e for e in entries if isinstance(e, dict)}
    named = set()
    for rec in trails:
        tid = rec.get("id", "?")
        check_record(tid, rec, os.path.join(root, tid), registry, errors)
        for p in rec.get("place") or []:
            if isinstance(p, dict):
                named.add((p.get("kind"), p.get("slug")))
    for e in entries:
        if isinstance(e, dict):
            for parent in e.get("within") or []:
                named.add(("range", parent))
    for (kind, slug) in sorted(registry, key=str):
        if (kind, slug) not in named:
            errors.append(f"places.toml: {kind}/{slug} is named by no record")
