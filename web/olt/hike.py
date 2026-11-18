"""The hiker facts of a record: its optional [hike] table (docs/schema.md).

Every field is optional, and most records have no [hike] table at all, so
every function here returns "" (or an empty list) when its field is missing.
"""
import math
import re

from . import words

# Words after which a full stop does not end a sentence ("Mt. Rainier", "U.S. Forest Service").
_ABBREVIATIONS = {"mt", "st", "ft", "dr", "mr", "mrs", "ms", "jr", "sr", "no", "vs", "ca", "approx",
                  "u.s", "e.g", "i.e", "etc", "hwy", "rd", "mi", "km"}
_SENTENCE_END = re.compile(r"[.!?](?=\s+[A-Z0-9“\"(])")


def table(rec):
    value = rec.get("hike")
    return value if isinstance(value, dict) else {}


def has(rec):
    return bool(table(rec))


def summary(rec):
    return (table(rec).get("summary") or "").strip()


def first_sentence(text):
    """The first sentence of a text: "A. B." -> "A.". Initials and common
    abbreviations ("Mt.", "U.S.") do not end a sentence."""
    text = (text or "").strip()
    for m in _SENTENCE_END.finditer(text):
        word = re.search(r"([\w.]+)$", text[:m.start()])
        w = word.group(1).lower() if word else ""
        if w in _ABBREVIATIONS or (len(w) == 1 and w.isalpha()):
            continue
        return text[:m.end()]
    return text


def one_line(rec):
    """The one-line description: the first sentence of the summary, or ""."""
    return first_sentence(summary(rec))


def days(rec):
    return words.fmt_days(table(rec).get("days"))


def days_max(rec):
    """The most days it usually takes, or None."""
    d = table(rec).get("days")
    if isinstance(d, (int, float)):
        d = [d]
    d = [x for x in (d or []) if isinstance(x, (int, float)) and x > 0]
    return max(d) if d else None


def shape(rec):
    return table(rec).get("shape", "")


def terrain(rec):
    return [t for t in table(rec).get("terrain", []) if t in words.TERRAIN]


def official_url(rec):
    url = table(rec).get("official_url", "")
    return url if isinstance(url, str) and url.startswith(("http://", "https://")) else ""


def ends(rec):
    """(label, text) for where it starts and ends, or None.

    point-to-point (or no shape): "Start and end", "A to B"; loop: "Loop", "Starts and
    ends at A"; network: "Network of trails", "Most walks start at A".
    """
    h = table(rec)
    start, end, sh = h.get("start", ""), h.get("end", ""), h.get("shape", "")
    if sh == "loop":
        return ("Loop", f"Starts and ends at {start}" if start else "Starts and ends at the same place")
    if sh == "network":
        return ("Network of trails", f"Usual start: {start}" if start else "Several ways to start and end")
    if start and end:
        return ("Start and end", (start, end))
    if start:
        return ("Start", start)
    if end:
        return ("End", end)
    return None


def sources(rec):
    return [s for s in table(rec).get("source", []) if isinstance(s, dict)]


def _lonlat(value):
    """A [lon, lat] pair as floats, or None when it is missing or not a place on Earth."""
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    lon, lat = value[0], value[1]
    if isinstance(lon, bool) or isinstance(lat, bool):
        return None
    if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
        return None
    lon, lat = float(lon), float(lat)
    if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
        return None
    return [lon, lat]


def start_point(rec):
    """[lon, lat] of the place named in [hike].start, or None."""
    return _lonlat(table(rec).get("start_lonlat"))


def end_point(rec):
    """[lon, lat] of the place named in [hike].end, or None. A loop has none."""
    return _lonlat(table(rec).get("end_lonlat"))


def sketch_points(rec):
    """The points a map may sketch for a trail with no track: [start, end]
    when both are on file, or the one point of a loop (shape "loop", or the
    same place for both ends), which is its start and its end. Empty when the
    trail has a track, or when only one end of a point-to-point trail is known:
    one end alone says nothing a reader can use, so that trail gets no map.

    A sketch is only ever these points. It is never a track: nothing here
    feeds a download, a GPX status or an elevation figure.
    """
    derived = rec.get("derived", {})
    if derived.get("has_line") or "line" in derived.get("files", {}):
        return []
    start, end = start_point(rec), end_point(rec)
    if start and end:
        return [start] if start == end else [start, end]
    if start and shape(rec) == "loop":
        return [start]
    return []


def sketch_end(rec):
    """"start" or "end": which end a one-point sketch marks. "" otherwise."""
    if len(sketch_points(rec)) != 1:
        return ""
    return "start" if start_point(rec) else "end"


def termini(rec):
    """The markers of the trail page's map for a trail with no track, from the
    record only: [{"role": "start" | "end" | "both", "lonlat": [lon, lat],
    "place": name or "", "label": text}]. A loop has one marker that is both
    its start and its end. Empty whenever sketch_points is."""
    points = sketch_points(rec)
    if not points:
        return []
    h = table(rec)

    def name(key):
        v = h.get(key)
        return v.strip() if isinstance(v, str) else ""

    def marker(role, point, place):
        head = {"start": "Start", "end": "End", "both": "Start and end"}[role]
        return {"role": role, "lonlat": point, "place": place,
                "label": f"{head}: {place}" if place else head}
    if len(points) == 1:
        return [marker("both", points[0], name("start") or name("end"))]
    return [marker("start", points[0], name("start")), marker("end", points[1], name("end"))]


def sketch_bbox(points, *, pad=False):
    """[min lon, min lat, max lon, max lat] of sketch points, or None.

    pad: widen for framing a map. One point gets about a county of ground;
    two points get a margin around the pair.
    """
    if not points:
        return None
    box = [min(p[0] for p in points), min(p[1] for p in points),
           max(p[0] for p in points), max(p[1] for p in points)]
    if not pad:
        return box
    if len(points) == 1:
        lat_pad = 0.35
        lon_pad = 0.35 / max(math.cos(math.radians(points[0][1])), 0.25)
    else:
        lat_pad = max((box[3] - box[1]) * 0.12, 0.05)
        lon_pad = max((box[2] - box[0]) * 0.12, 0.05)
    return [box[0] - lon_pad, box[1] - lat_pad, box[2] + lon_pad, box[3] + lat_pad]
