"""The hiker facts of a record: its optional [hike] table (docs/schema.md).

Every field is optional, and most records have no [hike] table at all, so
every function here returns "" (or an empty list) when its field is missing.
"""
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
