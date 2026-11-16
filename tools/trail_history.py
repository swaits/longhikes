"""The [[history]] table of a trail record: its rules, and which fields count as facts.

Python 3 standard library only. Used by tools/validate.py (the shape of each entry) and by
tools/check_history.py (the check that a change to a fact comes with a history entry).
The table is documented in docs/schema.md, section "[[history]]".
"""
import datetime
import re

OWN_CHECK = "the dataset's own check"
OUTCOMES = ("applied", "declined")
RECORD = "record"
ENTRY_KEYS = ("date", "change", "fields", "basis", "basis_url", "asked_by", "outcome")
ENTRY_REQUIRED = ("date", "change", "fields", "basis", "asked_by", "outcome")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
URL_RE = re.compile(r"^https?://[^\s/]+\S*$")

# Every field a record can have, as the dotted path docs/schema.md uses. A history entry
# names these. A table name on its own ("source", "hike.source") names every field in it.
_TABLES = {
    "": ("id", "name", "short_name", "short_name_url", "country", "regions", "length_km",
         "length_note", "kind", "tier", "designation", "wave", "wave_note", "inclusion"),
    "source": ("status", "publisher", "publisher_url", "url", "discovery", "format", "crs",
               "licence", "licence_text", "permission_quote", "permission_by",
               "permission_date", "permission_url", "attribution", "osm_only", "mainline",
               "decision", "decision_text", "source_checked", "redistributable",
               "line_source", "line_file", "line_absent_reason", "length_gap_note"),
    "osm": ("relation", "note"),
    "shield": ("status", "logo_source", "contact", "note", "logo_file", "logo_owner"),
    "verification": ("verified", "date", "measured_km", "difference_percent", "parts", "note"),
    "hike": ("summary", "official_url", "start", "end", "start_lonlat", "end_lonlat", "shape",
             "days", "season", "months", "high_point", "high_point_m", "terrain", "travel",
             "permit", "unfinished", "caution", "checked"),
    "hike.source": ("url", "publisher", "facts"),
    "route": ("creator", "year", "line_policy", "creator_words", "creator_words_url",
              "creator_words_by", "note"),
    "guide": ("title", "author", "access", "url", "format", "price", "price_checked",
              "publisher", "isbn"),
    "link": ("title", "publisher", "url", "note"),
}
SCHEMA_FIELDS = set()
for _table, _names in _TABLES.items():
    if _table:
        SCHEMA_FIELDS.add(_table)
    SCHEMA_FIELDS.update(f"{_table}.{n}" if _table else n for n in _names)

# What counts as a fact about the trail or its track, and what does not.
# A change to a FACT needs a new history entry (tools/check_history.py). Anything not named
# in NOT_FACTS is a fact, so a field added to the schema later is a fact until it is listed.
# A name here covers every field under it ("verification" covers "verification.parts").
NOT_FACTS = (
    "history",              # the history itself
    "verification",         # figures and dates the tools refresh when they measure a track
    "source.source_checked", "source.discovery",   # when and how the source is read again
    "source.format", "source.crs", "source.mainline",  # how the source serves its track
    "source.length_gap_note",    # explains a measured gap, and is refreshed with it
    "hike.summary",         # our own wording of what the trail is; not a fact on its own
    "hike.checked",         # the date the hiker facts were read
    "hike.source",          # which pages the hiker facts were read on
    "guide.price", "guide.price_checked",   # a price read on a date, and refreshed
    "osm.note", "shield.note", "route.note", "link",  # notes and other pages about the trail
    "wave", "wave_note",    # the dataset's own bookkeeping
)
FACTS_TEXT = (
    "name, short_name, short_name_url, country, regions, length_km, length_note, kind, tier, designation, "
    "inclusion; source.* (status, publisher, publisher_url, url, licence, licence_text, "
    "permission_*, attribution, osm_only, line_source, line_file, line_absent_reason, "
    "decision, decision_text, redistributable); osm.relation; shield.* except note; "
    "hike.* except summary, checked and source (start, end, official_url, days, season, terrain, "
    "travel, high_point, permit, unfinished, caution and the rest); route.* except note; "
    "guide.* except price. A replaced track file counts as a change to source.line_file."
)
NOT_FACTS_TEXT = (
    "history; verification.*; source.source_checked, discovery, format, crs, mainline, "
    "length_gap_note; hike.summary, hike.checked, hike.source; guide.price, "
    "guide.price_checked; osm.note, shield.note, route.note; link; wave, wave_note."
)
TRACK_FIELD = "source.line_file"


def covers(listed, path):
    """True when the field name `listed` is `path` or a table that holds it."""
    return path == listed or path.startswith(listed + ".")


def is_fact(path):
    return not any(covers(name, path) for name in NOT_FACTS)


def _leaves(obj, prefix, out):
    """Collect path -> list of values. A list of tables adds one value per table, in order."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            _leaves(value, f"{prefix}.{key}" if prefix else key, out)
    elif isinstance(obj, list) and obj and all(isinstance(x, dict) for x in obj):
        for item in obj:
            _leaves(item, prefix, out)
    else:
        out.setdefault(prefix, []).append(obj)


def leaves(rec):
    out = {}
    _leaves(rec, "", out)
    return out


def changed_paths(old, new):
    """The field paths whose values differ between two records (history excluded)."""
    a, b = leaves(old or {}), leaves(new or {})
    return sorted(p for p in set(a) | set(b)
                  if a.get(p) != b.get(p) and not covers("history", p))


def entry_covers(entry, path):
    return any(isinstance(f, str) and f != RECORD and covers(f, path) for f in entry.get("fields", []))


def is_own(entry):
    return entry.get("asked_by") == OWN_CHECK


def check_entries(tid, rec, errors):
    """Check the shape of [[history]]: at least one entry, each well formed, oldest first."""
    history = rec.get("history")
    if history is None or history == []:
        errors.append(f"{tid}: has no [[history]] entry (docs/schema.md, section [[history]])")
        return
    if not isinstance(history, list) or not all(isinstance(e, dict) for e in history):
        errors.append(f"{tid}: history must be an array of tables ([[history]])")
        return
    previous = None
    for i, e in enumerate(history, 1):
        where = f"{tid}: history entry {i}"
        for name in e:
            if name not in ENTRY_KEYS:
                errors.append(f"{where} has unknown field {name}")
        for name in ENTRY_REQUIRED:
            if name not in e:
                errors.append(f"{where} is missing {name}")
        for name in ("change", "basis", "asked_by"):
            if name in e and (not isinstance(e[name], str) or not e[name].strip()):
                errors.append(f"{where}: {name} must be a non-empty string")
        date = e.get("date")
        if "date" in e:
            if not isinstance(date, str) or not DATE_RE.match(date):
                errors.append(f"{where}: date must be YYYY-MM-DD")
            else:
                try:
                    datetime.date.fromisoformat(date)
                except ValueError:
                    errors.append(f"{where}: date {date!r} is not a real date")
                else:
                    if previous and date < previous:
                        errors.append(f"{where}: date {date} is earlier than the entry before it; "
                                      "entries run oldest first")
                    previous = date
        if "outcome" in e and e["outcome"] not in OUTCOMES:
            errors.append(f"{where}: outcome must be one of {', '.join(OUTCOMES)}, not {e['outcome']!r}")
        fields = e.get("fields")
        if "fields" in e:
            if not isinstance(fields, list) or not fields or not all(isinstance(f, str) for f in fields):
                errors.append(f"{where}: fields must be a non-empty list of field names")
                fields = None
            else:
                for f in fields:
                    if f != RECORD and f not in SCHEMA_FIELDS:
                        errors.append(f"{where}: fields names {f!r}, which is not a field of the record "
                                      "(see docs/schema.md)")
                if RECORD in fields and fields != [RECORD]:
                    errors.append(f"{where}: \"record\" cannot be listed with other fields")
        is_added = fields == [RECORD]
        if i == 1 and not is_added:
            errors.append(f"{where}: the first entry must be the one that adds the record, "
                          'with fields = ["record"]')
        if i > 1 and is_added:
            errors.append(f"{where}: only the first entry may have fields = [\"record\"]")
        if is_added and e.get("outcome") not in (None, "applied"):
            errors.append(f"{where}: the entry that adds the record must have outcome \"applied\"")
        url = e.get("basis_url")
        if url is None:
            if not is_added:
                errors.append(f"{where} is missing basis_url (the page that was read, or the issue "
                              "or pull request address)")
        elif not isinstance(url, str) or not URL_RE.match(url):
            errors.append(f"{where}: basis_url must be an http(s) address")
