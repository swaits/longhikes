#!/usr/bin/env python3
"""Make the social card of every trail: web/cards/<id>.png, 1200 x 630.

A card shows the trail's name, its length in miles and kilometres, where it is
and, where the record has a track, the track's outline. Everything is read from
the records and from a built site's map.json files (the track simplified to
30 m); nothing about a trail is written here. The site card, assets/og.png, is drawn here too, from the name and tagline in
web/site.toml. Colours and type: the cream ground, the red bar, Source Serif 4 and IBM Plex
Sans Condensed.

Run on a developer machine and commit the output, as web/tools/make_thumbs.py
does for the logo thumbnails: the site build itself draws nothing and stays
standard library only. The build image needs no new tool.

    python3 web/build.py --out _site
    uv run --no-project --with pillow --with fonttools --with brotli \\
        python web/tools/make_cards.py [--site _site] [--force] [--only id,id]

Needs Pillow, fontTools with brotli (to read the site's own woff2 fonts) and
rsvg-convert (for the mark). A card newer than its record, its track and this
script is left alone unless --force is given. Cards whose record is gone are removed.
Each is a palette PNG, 25 to 70 KB.
"""
import argparse
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.dirname(HERE)
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)

from olt import cards, records, site as site_mod  # noqa: E402

W, H = 1200, 630
SCALE = 2  # drawn at twice the size, then reduced, for smooth edges
CREAM, RED, INK, MUTED = "#f6f2e8", "#b3261e", "#272e29", "#4d564f"
MARGIN = 84
FONTS = os.path.join(WEB, "assets", "fonts")


def load_fonts(tmp):
    """{name: path} of TTF copies of the site's woff2 fonts, made in tmp."""
    from fontTools.ttLib import TTFont
    out = {}
    for key, name in (("serif", "source-serif-4-latin"), ("sans", "ibm-plex-sans-condensed-600-latin")):
        font = TTFont(os.path.join(FONTS, name + ".woff2"))
        font.flavor = None
        out[key] = os.path.join(tmp, name + ".ttf")
        font.save(out[key])
    return out


def font(path, size, weight=None):
    from PIL import ImageFont
    f = ImageFont.truetype(path, size * SCALE)
    if weight:
        f.set_variation_by_axes([weight])
    return f


def mark(tmp):
    """The site's mark, 76 px, as a PIL image."""
    from PIL import Image
    png = subprocess.run(["rsvg-convert", "-w", str(76 * SCALE), "-h", str(76 * SCALE),
                          os.path.join(WEB, "assets", "favicon.svg")], check=True, stdout=subprocess.PIPE).stdout
    return Image.open(io.BytesIO(png)).convert("RGBA")


def wrap(draw, text, fnt, width):
    """Lines of text no wider than width (in drawn pixels), broken at spaces."""
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=fnt) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line] if line else lines


# The layout. Every element is a text line or the track, with a box in card pixels (not
# drawn ones). The text column is one flow between the header and the footer; the name shrinks
# until the whole block fits the safe area. draw_card() draws what layout() returns and the
# test in web/tests/test_card_layout.py measures the same boxes, so they cannot disagree.
HEADER_BOTTOM = 128          # the mark's lower edge
SAFE_TOP, SAFE_BOTTOM = 152, 516   # the text column lives here: 32 px clear of the footer text
FOOT_Y = 548                 # top of the footer line (drawn with the ascender anchor)
COL_TRACK, COL_FULL = 520, 1030    # text column width with and without a track
TRACK_BOX = (680, 96, W - 70, 520)
# A name too long for the column even at the smallest size gets a wider column, and the track a
# narrower box to match: (column width, track box left edge).
WIDER = ((590, 720), (660, 770))
STROKE = 5
NAME_MAX, NAME_MIN, NAME_STEP = 84, 48, 2   # name size, card px; 48 is 12 px at a 1/4 thumbnail
NAME_LEAD = 1.1
GAP_NAME, GAP_LENGTH = 30, 22    # ink gap name -> length, length -> places
PLACES_LINES = 2


def wrap(measure, text, width):
    """Lines of text no wider than width, broken at spaces and after hyphens or dashes."""
    words = []
    for w in text.split():
        parts = re.split(r"(?<=[-\u2013])(?=\w)", w)
        words.append(parts)
    lines, line = [], ""
    for parts in words:
        for i, part in enumerate(parts):
            glue = " " if i == 0 else ""
            trial = f"{line}{glue}{part}" if line else part
            if measure(trial) <= width or not line:
                line = trial
            else:
                lines.append(line)
                line = part
    return lines + [line] if line else lines


def wrap_name(measure, nf, name, width):
    """A name's lines: wrapped greedily, or, for a name with a parenthetical ("Wind River High
    Route (Dixon and Wilson)"), wrapped as the name and the parenthetical on separate lines,
    whichever takes fewer lines (the second wins a tie, so the parenthetical starts a line)."""
    def fn(t):
        return measure.width(nf, t)
    plain = wrap(fn, name, width)
    if " (" not in name:
        return plain
    head, tail = name.split(" (", 1)
    split = wrap(fn, head, width) + wrap(fn, "(" + tail, width)
    return split if len(split) <= len(plain) else plain


class Measure:
    """Text measuring at the card's own pixel size (fonts are drawn at SCALE times that)."""

    def __init__(self, fonts):
        from PIL import Image, ImageDraw
        self.d = ImageDraw.Draw(Image.new("L", (8, 8)))
        self.fonts = fonts
        self._f = {}

    def font(self, key, size, weight=None):
        k = (key, size, weight)
        if k not in self._f:
            self._f[k] = font(self.fonts[key], size, weight)
        return self._f[k]

    def width(self, fnt, text):
        return self.d.textlength(text, font=fnt) / SCALE

    def ink(self, fnt, text, x, y, anchor):
        """Ink box of text drawn at (x, y) with the anchor, in card pixels."""
        x0, y0, x1, y1 = self.d.textbbox((x * SCALE, y * SCALE), text, font=fnt, anchor=anchor)
        return (x0 / SCALE, y0 / SCALE, x1 / SCALE, y1 / SCALE)

    def vextent(self, fnt):
        """(rise above the baseline, drop below it) a line in this font may need: the tallest
        capital with an accent, the deepest descender."""
        up = -self.d.textbbox((0, 0), "H\u00c9\u00d4l(", font=fnt, anchor="ls")[1] / SCALE
        down = self.d.textbbox((0, 0), "gjpqy(", font=fnt, anchor="ls")[3] / SCALE
        return up, down


def short_places(text, measure, fnt, width):
    """The places line(s): text as it is, or, where it would take more than PLACES_LINES lines,
    its first names and a count ("Colorado, Utah and 4 more")."""
    lines = wrap(lambda t: measure.width(fnt, t), text, width)
    if len(lines) <= PLACES_LINES:
        return lines
    names = [n.strip() for n in text.split(",")]
    for keep in range(len(names) - 1, 0, -1):
        more = len(names) - keep
        head = ", ".join(names[:keep])
        trial = wrap(lambda t: measure.width(fnt, t), f"{head} and {more} more", width)
        if len(trial) <= PLACES_LINES:
            return trial
    return wrap(lambda t: measure.width(fnt, t), f"{names[0]} and {len(names) - 1} more", width)[:PLACES_LINES]


def flow(measure, name, length, places, width):
    """The text column. Returns a list of items (kind, text, font, x, baseline, ink box), the name
    size, and whether it fits. The name is as large as the block allows between SAFE_TOP and
    SAFE_BOTTOM; the gaps between name, length and places are fixed ink gaps."""
    len_f = measure.font("serif", 44, 500)
    small = measure.font("sans", 30)
    place_lines = short_places(places, measure, small, width) if places else []
    len_up, len_down = measure.vextent(len_f)
    pl_up, pl_down = measure.vextent(small)
    plc_pitch = 40
    tail = GAP_NAME + len_up + len_down                 # name bottom -> length bottom
    if place_lines:
        tail += GAP_LENGTH + pl_up + (len(place_lines) - 1) * plc_pitch + pl_down
    fits = False
    for size in range(NAME_MAX, NAME_MIN - 1, -NAME_STEP):
        nf = measure.font("serif", size, 700)
        lines = wrap_name(measure, nf, name, width)
        up, down = measure.vextent(nf)
        pitch = round(size * NAME_LEAD)
        name_h = up + (len(lines) - 1) * pitch + down
        ok_w = all(measure.width(nf, ln) <= width for ln in lines)
        if ok_w and SAFE_TOP + name_h + tail <= SAFE_BOTTOM:
            fits = True
            break
    items = []
    y = SAFE_TOP + up
    for ln in lines:
        items.append(("name", ln, nf, MARGIN, y, measure.ink(nf, ln, MARGIN, y, "ls")))
        y += pitch
    y = y - pitch + down + GAP_NAME + len_up
    text = length
    items.append(("length", text, len_f, MARGIN, y, measure.ink(len_f, text, MARGIN, y, "ls")))
    y += len_down + GAP_LENGTH + pl_up
    for ln in place_lines:
        items.append(("places", ln, small, MARGIN, y, measure.ink(small, ln, MARGIN, y, "ls")))
        y += plc_pitch
    return items, size, fits


def layout(measure, rec, parts):
    """Everything drawn on a trail's card, as {"items": [(kind, text, font, x, y, anchor, box)],
    "track": [polylines in drawn px] or None, "boxes": {kind: [box]}, "name_size", "fits"}."""
    name, length, places = cards.lines(rec)
    width = COL_TRACK if parts else COL_FULL
    items, size, fits = flow(measure, name, length, places, width)
    track_x0 = TRACK_BOX[0]
    for wide, x0 in WIDER:
        if parts and not fits:
            width, track_x0 = wide, x0
            items, size, fits = flow(measure, name, length, places, width)
    items = [(k, t, f, x, y, "ls", box) for k, t, f, x, y, box in items]
    serif40 = measure.font("serif", 40, 700)
    sans32 = measure.font("sans", 32)
    items.append(("header", "Long Hikes", serif40, MARGIN + 92, 62, "la",
                  measure.ink(serif40, "Long Hikes", MARGIN + 92, 62, "la")))
    items.append(("footer", "longhikes.org", sans32, MARGIN, FOOT_Y, "la",
                  measure.ink(sans32, "longhikes.org", MARGIN, FOOT_Y, "la")))
    track = None
    if parts:
        inset = STROKE / 2 + 1
        _, y0, x1, y1 = TRACK_BOX
        x0 = track_x0
        track = project(parts, ((x0 + inset) * SCALE, (y0 + inset) * SCALE, (x1 - inset) * SCALE, (y1 - inset) * SCALE))
    return {"items": items, "track": track, "name_size": size, "fits": fits, "width": width, "track_x0": track_x0}


def boxes_of(lay):
    """[(kind, box)] of a layout: each text line's ink box, the mark, and the track's ink box."""
    out = [(k, box) for k, t, f, x, y, a, box in lay["items"]]
    out.append(("mark", (MARGIN, 52, MARGIN + 76, 52 + 76)))
    if lay["track"]:
        xs = [p[0] / SCALE for part in lay["track"] for p in part]
        ys = [p[1] / SCALE for part in lay["track"] for p in part]
        h = STROKE / 2
        out.append(("track", (min(xs) - h, min(ys) - h, max(xs) + h, max(ys) + h)))
    return out


def parts_of(map_json):
    """Every part of the track as a list of (lon, lat) lists."""
    with open(map_json, encoding="utf-8") as f:
        doc = json.load(f)
    parts = []
    for feat in doc.get("features", []):
        geom = feat.get("geometry") or {}
        if geom.get("type") == "LineString":
            parts.append(geom["coordinates"])
        elif geom.get("type") == "MultiLineString":
            parts.extend(geom["coordinates"])
    return [[(p[0], p[1]) for p in part] for part in parts if len(part) > 1]


def project(parts, box):
    """Fit the parts into box (x0, y0, x1, y1), drawn pixels: equirectangular, north up,
    scaled by the cosine of the middle latitude so shapes keep their proportions."""
    lons = [p[0] for part in parts for p in part]
    lats = [p[1] for part in parts for p in part]
    lon0, lon1, lat0, lat1 = min(lons), max(lons), min(lats), max(lats)
    k = math.cos(math.radians((lat0 + lat1) / 2))
    wide, high = max((lon1 - lon0) * k, 1e-6), max(lat1 - lat0, 1e-6)
    x0, y0, x1, y1 = box
    s = min((x1 - x0) / wide, (y1 - y0) / high)
    ox = x0 + ((x1 - x0) - wide * s) / 2
    oy = y0 + ((y1 - y0) - high * s) / 2
    return [[(ox + (lon - lon0) * k * s, oy + (lat1 - lat) * s) for lon, lat in part] for part in parts]


def finish(img, text, out_path):
    from PIL import Image
    from PIL.PngImagePlugin import PngInfo
    img = img.resize((W, H), Image.LANCZOS)
    img = img.quantize(colors=24, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    info = PngInfo()
    info.add_text("olt-card", text)
    img.save(out_path, optimize=True, pnginfo=info)


COLOUR = {"name": INK, "header": INK, "length": RED, "places": MUTED, "footer": RED}


def draw_card(rec, map_json, fonts, logo, out_path, measure=None):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (W * SCALE, H * SCALE), CREAM)
    d = ImageDraw.Draw(img)
    s = SCALE
    measure = measure or Measure(fonts)
    parts = parts_of(map_json) if map_json and os.path.isfile(map_json) else []
    lay = layout(measure, rec, parts)
    img.paste(logo, (MARGIN * s, 52 * s), logo)
    for kind, text, fnt, x, y, anchor, box in lay["items"]:
        d.text((x * s, y * s), text, font=fnt, fill=COLOUR[kind], anchor=anchor)
    for part in lay["track"] or []:
        d.line(part, fill=RED, width=STROKE * s, joint="curve")
    d.rectangle((0, (H - 14) * s, W * s, H * s), fill=RED)
    finish(img, cards.fingerprint(rec), out_path)


def site_layout(measure, site):
    """The site card: the name and the headline (from web/site.toml), the headline as large as
    fits the safe area."""
    name, headline = cards.site_lines(site)
    top = SAFE_TOP + 40
    for size in range(NAME_MAX, NAME_MIN - 1, -NAME_STEP):
        nf = measure.font("serif", size, 700)
        lines = wrap(lambda t: measure.width(nf, t), headline, COL_FULL)
        up, down = measure.vextent(nf)
        pitch = round(size * NAME_LEAD)
        if top + up + (len(lines) - 1) * pitch + down <= SAFE_BOTTOM:
            break
    items, y = [], top + up
    for ln in lines:
        items.append(("name", ln, nf, MARGIN, y, "ls", measure.ink(nf, ln, MARGIN, y, "ls")))
        y += pitch
    serif40 = measure.font("serif", 40, 700)
    items.append(("header", name, serif40, MARGIN + 92, 62, "la", measure.ink(serif40, name, MARGIN + 92, 62, "la")))
    host = (site.base_url or "").split("://")[-1]
    if host:
        sans32 = measure.font("sans", 32)
        items.append(("footer", host, sans32, MARGIN, FOOT_Y, "la", measure.ink(sans32, host, MARGIN, FOOT_Y, "la")))
    return {"items": items, "track": None, "name_size": size, "width": COL_FULL}


def draw_site_card(site, fonts, logo, out_path):
    """The site card, assets/og.png."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (W * SCALE, H * SCALE), CREAM)
    d = ImageDraw.Draw(img)
    s = SCALE
    img.paste(logo, (MARGIN * s, 52 * s), logo)
    for kind, text, fnt, x, y, anchor, box in site_layout(Measure(fonts), site)["items"]:
        d.text((x * s, y * s), text, font=fnt, fill=COLOUR[kind], anchor=anchor)
    d.rectangle((0, (H - 14) * s, W * s, H * s), fill=RED)
    finish(img, cards.site_fingerprint(site), out_path)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Make web/cards/<id>.png for every trail.")
    ap.add_argument("--site", default=os.path.join(ROOT, "_site"), help="a built site, for each trail's map.json")
    ap.add_argument("--force", action="store_true", help="redraw cards that are up to date")
    ap.add_argument("--only", default="", help="comma-separated trail ids")
    args = ap.parse_args(argv)
    if shutil.which("rsvg-convert") is None:
        sys.exit("make_cards: rsvg-convert was not found on the PATH")
    only = {x for x in args.only.split(",") if x}
    out_dir = os.path.join(WEB, "cards")
    os.makedirs(out_dir, exist_ok=True)
    recs = records.load_records(ROOT)
    me = os.path.getmtime(__file__)
    made = kept = 0
    with tempfile.TemporaryDirectory() as tmp:
        fonts = load_fonts(tmp)
        logo = mark(tmp)
        for rec in recs:
            tid = rec["id"]
            if only and tid not in only:
                continue
            dst = os.path.join(out_dir, f"{tid}.png")
            map_json = os.path.join(args.site, "trails", tid, "map.json")
            deps = [os.path.join(ROOT, tid, "trail.toml"), map_json, __file__]
            newest = max((os.path.getmtime(p) for p in deps if os.path.isfile(p)), default=me)
            if not args.force and os.path.isfile(dst) and os.path.getmtime(dst) >= newest:
                kept += 1
                continue
            draw_card(rec, map_json, fonts, logo, dst)
            made += 1
    site_cfg = site_mod.from_file(os.path.join(WEB, "site.toml"))
    og = os.path.join(WEB, "assets", "og.png")
    if (not only
            and (args.force or cards.stored_fingerprint(og) != cards.site_fingerprint(site_cfg))):
        with tempfile.TemporaryDirectory() as tmp2:
            draw_site_card(site_cfg, load_fonts(tmp2), mark(tmp2), og)
        print("site card drawn: web/assets/og.png")
    ids = {r["id"] for r in recs}
    removed = 0
    for name in sorted(os.listdir(out_dir)):
        if name.endswith(".png") and name[:-4] not in ids:
            os.remove(os.path.join(out_dir, name))
            removed += 1
    sizes = [os.path.getsize(os.path.join(out_dir, n)) for n in os.listdir(out_dir) if n.endswith(".png")]
    print(f"cards drawn {made}, kept {kept}, removed {removed}; {len(sizes)} files, "
          f"{sum(sizes) / 1e6:.1f} MB, largest {max(sizes, default=0) / 1e3:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
