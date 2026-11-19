"""PNG logo thumbnails for the list and trail pages.

Two sizes: web/thumbs/<id>.png (up to 256 px) for the trail page header and the Logos
page, and web/thumbs-list/<id>.png (up to 200 x 124 px, twice the largest box a list
draws a logo in) for the lists; a logo with no list thumbnail uses the first.

web/thumbs/<id>.png is made by web/tools/make_thumbs.py and committed, from a
PNG logo or (where the logo is a vector) an SVG one. The pages step copies it to
trails/<id>/shield-thumb.png, and the pages show that copy at its real pixel size
(read from the PNG header; no image library), so every logo <img> has a width and
height. A logo with no thumbnail falls back to the full-size file, with a
warning: a PNG at its own size, an SVG at the size its own viewBox gives
(svg_size), scaled to fit within THUMB_MAX.
"""
import os
import re
import shutil
import struct
import sys

WEB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THUMB_DIR = os.path.join(WEB_DIR, "thumbs")
LIST_THUMB_DIR = os.path.join(WEB_DIR, "thumbs-list")  # web/thumbs-list/<id>.png: for the lists, twice the size they are shown at
THUMB_NAME = "shield-thumb.png"
LIST_THUMB_NAME = "shield-list.png"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
THUMB_MAX = 256  # the longest side of a thumbnail, as make_thumbs.py draws it


def png_size(path):
    """(width, height) from the IHDR chunk at the start of a PNG file."""
    with open(path, "rb") as f:
        head = f.read(24)
    if len(head) < 24 or head[:8] != PNG_SIGNATURE or head[12:16] != b"IHDR":
        raise ValueError(f"{path} is not a PNG file")
    return struct.unpack(">II", head[16:24])


_SVG_TAG = re.compile(r"<svg\b[^>]*>", re.S)
_NUMBER = r"(-?\d*\.?\d+(?:e-?\d+)?)"


def svg_size(path):
    """(width, height), in whole pixels fitting within THUMB_MAX x THUMB_MAX, for an
    SVG file: the shape of its viewBox, or of its width and height where it has no
    viewBox. The <img> sets only the shape (the page's CSS sizes the plate)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        tag = _SVG_TAG.search(f.read(4096))
    if not tag:
        raise ValueError(f"{path} is not an SVG file")
    tag = tag.group(0)
    box = re.search(r'viewBox\s*=\s*"\s*' + (r"[\s,]+".join([_NUMBER] * 4)) + r'\s*"', tag)
    if box:
        w, h = float(box.group(3)), float(box.group(4))
    else:
        dims = [re.search(r'\b' + k + r'\s*=\s*"\s*' + _NUMBER, tag) for k in ("width", "height")]
        if not all(dims):
            raise ValueError(f"{path} gives neither a viewBox nor a width and height")
        w, h = float(dims[0].group(1)), float(dims[1].group(1))
    if w <= 0 or h <= 0:
        raise ValueError(f"{path} has an empty size")
    scale = THUMB_MAX / max(w, h)
    return max(1, round(w * scale)), max(1, round(h * scale))


def prepare(rec, out_dir, repo_root, thumb_dir=THUMB_DIR, list_thumb_dir=LIST_THUMB_DIR):
    """Copy the record's PNG thumbnail into its output directory and set
    rec["derived"]["logo_img"] = {"src", "width", "height"}, the image the pages
    show. Without a logo the key is absent and any old copy is removed.
    """
    tid = rec["id"]
    tdir = os.path.join(out_dir, "trails", tid)
    dest = os.path.join(tdir, THUMB_NAME)
    rec["derived"].pop("logo_img", None)
    rec["derived"].pop("list_img", None)
    list_dest = os.path.join(tdir, LIST_THUMB_NAME)
    shield = rec["derived"]["files"].get("shield", "")
    if not shield.endswith((".png", ".svg")):
        for stale in (dest, list_dest):
            if os.path.isfile(stale):
                os.remove(stale)
        return
    list_thumb = os.path.join(list_thumb_dir, f"{tid}.png")
    if os.path.isfile(list_thumb):
        shutil.copyfile(list_thumb, list_dest)
        w, h = png_size(list_dest)
        rec["derived"]["list_img"] = {"src": f"/trails/{tid}/{LIST_THUMB_NAME}", "width": w, "height": h}
    elif os.path.isfile(list_dest):
        os.remove(list_dest)
    thumb = os.path.join(thumb_dir, f"{tid}.png")
    if os.path.isfile(thumb):
        shutil.copyfile(thumb, dest)
        path, src = dest, f"/trails/{tid}/{THUMB_NAME}"
    else:
        print(f"warning: {tid}: no thumbnail at {os.path.relpath(thumb, WEB_DIR)}; "
              f"the full-size logo is shown (run web/tools/make_thumbs.py)", file=sys.stderr)
        if os.path.isfile(dest):
            os.remove(dest)
        path, src = os.path.join(repo_root, shield), f"/trails/{tid}/{os.path.basename(shield)}"
    width, height = svg_size(path) if path.endswith(".svg") else png_size(path)
    rec["derived"]["logo_img"] = {"src": src, "width": width, "height": height}
