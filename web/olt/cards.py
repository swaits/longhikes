"""Per-trail social cards (1200 x 630 PNG), the image link previews show for a trail page.

web/cards/<id>.png is made by web/tools/make_cards.py and committed, the way
the logo thumbnails are (olt/thumbs.py): the site build is standard library
only and draws nothing. The pages step copies each card to trails/<id>/card.png.
A trail with no card file falls back to the site card, with a warning.
"""
import hashlib
import os
import shutil
import struct
import sys

from . import facets, words

WEB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARD_DIR = os.path.join(WEB_DIR, "cards")
CARD_NAME = "card.png"


def prepare(rec, out_dir, card_dir=CARD_DIR):
    """Copy the record's card next to its page. Returns (site path, alt text), or ("", "")
    when there is none, which leaves the page on the site card."""
    tid = rec["id"]
    dest = os.path.join(out_dir, "trails", tid, CARD_NAME)
    src = os.path.join(card_dir, f"{tid}.png")
    if not os.path.isfile(src):
        print(f"warning: {tid}: no card at {os.path.relpath(src, WEB_DIR)}; the page uses the site card "
              f"(run web/tools/make_cards.py)", file=sys.stderr)
        if os.path.isfile(dest):
            os.remove(dest)
        return "", ""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(src, dest)
    return f"/trails/{tid}/{CARD_NAME}", f"{rec['name']}: its track, and its length in miles and kilometres"


def card_name(rec):
    """The name a card shows: the one hikers use where the record has it."""
    return rec.get("common_name") or rec["name"]


def where(rec):
    """The places a card shows: up to three names, else a count."""
    names = [facets.place_name(k) for k in facets.place_keys(rec)]
    return ", ".join(names) if len(names) <= 3 else f"{len(names)} states and provinces"


def lines(rec):
    """The three texts a card shows: its name, its length in miles and kilometres, its places."""
    return (card_name(rec),
            f"{words.fmt_int(rec['derived']['length_mi'])} miles · {words.fmt_int(rec['length_km'])} km",
            where(rec))


def fingerprint(rec):
    """A short hash of what a card shows. make_cards.py stores it in the PNG (text chunk
    "olt-card"), and a test compares it, so a record that changes shows up as a stale card."""
    return hashlib.sha1("\n".join(lines(rec)).encode("utf-8")).hexdigest()[:12]


def stored_fingerprint(path):
    """The "olt-card" text chunk of a card file, or ""."""
    with open(path, "rb") as f:
        data = f.read()
    pos = 8
    while pos + 8 <= len(data):
        size, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + size]
        if kind == b"tEXt" and body.startswith(b"olt-card\x00"):
            return body.split(b"\x00", 1)[1].decode("latin-1")
        if kind == b"IEND":
            break
        pos += 12 + size
    return ""


def site_lines(site):
    """The two texts the site card shows: the site's name and its headline (the tagline, as
    the home page prints it, with a full stop)."""
    return site.name, site.tagline.rstrip(".") + "."


def site_fingerprint(site):
    """Like fingerprint(), for the site card assets/og.png."""
    return hashlib.sha1("\n".join(site_lines(site)).encode("utf-8")).hexdigest()[:12]
