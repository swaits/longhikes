"""Redirects from the addresses a hiker would guess to a trail's real page.

A trail's page lives at /trails/<id>/, and about half the ids are shorter than the trail's
name (/trails/pacific-crest/), so /trails/pacific-crest-trail/ is a 404 without one of these.
trail_redirects() gives, for each record, the slug of its full name, of its common name, and of
the name plus "Trail" for a trail whose names do not say "trail", wherever that slug is not a
page of its own and only one record could mean it. The canonical address never changes.
"""
import os
import re

TRAILS = "/trails/"
MARKER = "# Guessable trail addresses (olt/redirects.py), one line each, from the records' names.\n"


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def candidates(rec):
    """The slugs a hiker might type for a record, in order, without its own id."""
    names = [rec["name"], rec.get("common_name") or ""]
    found = [slug(n) for n in names if n]
    if rec.get("kind") != "route" and not any("trail" in s.split("-") for s in found):
        found.append(slug(rec.get("common_name") or rec["name"]) + "-trail")
    seen, out = set(), []
    for s in found:
        if s and s != rec["id"] and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def trail_redirects(recs, taken=()):
    """[(slug, id)] sorted by slug: each a slug that no page has (not an id, not in taken, the
    names of other entries under /trails/) and that exactly one record's names give."""
    real = {r["id"] for r in recs} | set(taken)
    owners = {}
    for r in recs:
        for s in candidates(r):
            owners.setdefault(s, set()).add(r["id"])
    return sorted((s, next(iter(ids))) for s, ids in owners.items() if s not in real and len(ids) == 1)


def lines(pairs):
    out = []
    for s, tid in pairs:
        out.append(f"{TRAILS}{s}/   {TRAILS}{tid}/   301\n")
        out.append(f"{TRAILS}{s}    {TRAILS}{tid}/   301\n")
    return out


def append_to(out_dir, recs):
    """Add the lines to the publish directory's _redirects (written there from web/static)."""
    trails_dir = os.path.join(out_dir, "trails")
    taken = os.listdir(trails_dir) if os.path.isdir(trails_dir) else []
    pairs = trail_redirects(recs, taken)
    path = os.path.join(out_dir, "_redirects")
    text = ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            text = f.read()
    if text and not text.endswith("\n"):
        text += "\n"
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text + "\n" + MARKER + "".join(lines(pairs)))
    return pairs
