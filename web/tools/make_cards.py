#!/usr/bin/env python3
"""Make the social card of every trail: web/cards/<id>.png, 1200 x 630.

A card shows the trail's name, its length in miles and kilometres, where it is
and, where the record has a track, the track's outline. Everything is read from
the records and from a built site's map.json files (the track simplified to
30 m); nothing about a trail is written here. Colours and type follow the site
card, assets/og.png: the cream ground, the red bar, Source Serif 4 and IBM Plex
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
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.dirname(HERE)
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)

from olt import cards, records  # noqa: E402

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


def fit_title(draw, text, path, width, weight=700):
    """The largest size (up to 84, down to 44) at which text takes three lines or fewer, and its lines."""
    for size in range(84, 43, -2):
        fnt = font(path, size, weight)
        lines = wrap(draw, text, fnt, width * SCALE)
        if len(lines) <= 3 and all(draw.textlength(x, font=fnt) <= width * SCALE for x in lines):
            return size, fnt, lines
    fnt = font(path, 44, weight)
    return 44, fnt, wrap(draw, text, fnt, width * SCALE)[:3]


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


def draw_card(rec, map_json, fonts, logo, out_path):
    from PIL import Image, ImageDraw
    from PIL.PngImagePlugin import PngInfo
    img = Image.new("RGB", (W * SCALE, H * SCALE), CREAM)
    d = ImageDraw.Draw(img)
    s = SCALE
    parts = parts_of(map_json) if map_json and os.path.isfile(map_json) else []
    text_w = 520 if parts else 1030
    # brand
    img.paste(logo, (MARGIN * s, 52 * s), logo)
    d.text(((MARGIN + 92) * s, 62 * s), "Long Hikes", font=font(fonts["serif"], 40, 700), fill=INK)
    # title
    name, length, places = cards.lines(rec)
    size, fnt, lines = fit_title(d, name, fonts["serif"], text_w)
    y = 168
    for line in lines:
        d.text((MARGIN * s, y * s), line, font=fnt, fill=INK)
        y += int(size * 1.12)
    y += 14
    d.text((MARGIN * s, y * s), length, font=font(fonts["serif"], 44, 500), fill=RED)
    y += 66
    small = font(fonts["sans"], 30)
    for line in wrap(d, places, small, text_w * s)[:2]:
        d.text((MARGIN * s, y * s), line, font=small, fill=MUTED)
        y += 40
    # track outline
    if parts:
        for part in project(parts, (680 * s, 90 * s, (W - 70) * s, 520 * s)):
            d.line(part, fill=RED, width=5 * s, joint="curve")
    # foot
    d.rectangle((0, (H - 14) * s, W * s, H * s), fill=RED)
    d.text((MARGIN * s, 548 * s), "longhikes.org", font=font(fonts["sans"], 32), fill=RED)
    img = img.resize((W, H), Image.LANCZOS)
    img = img.quantize(colors=24, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    info = PngInfo()
    info.add_text("olt-card", cards.fingerprint(rec))
    img.save(out_path, optimize=True, pnginfo=info)


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
