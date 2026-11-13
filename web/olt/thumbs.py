"""PNG logo thumbnails for the list pages.

web/thumbs/<id>.png is made by web/tools/make_thumbs.py and committed. The pages
step copies it to trails/<id>/shield-thumb.png, and the list pages show that
copy at its real pixel size (read from the PNG header; no image library). A
PNG logo with no thumbnail falls back to the full-size file, with a warning.
SVG logos are not touched.
"""
import os
import shutil
import struct
import sys

WEB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THUMB_DIR = os.path.join(WEB_DIR, "thumbs")
THUMB_NAME = "shield-thumb.png"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_size(path):
    """(width, height) from the IHDR chunk at the start of a PNG file."""
    with open(path, "rb") as f:
        head = f.read(24)
    if len(head) < 24 or head[:8] != PNG_SIGNATURE or head[12:16] != b"IHDR":
        raise ValueError(f"{path} is not a PNG file")
    return struct.unpack(">II", head[16:24])


def prepare(rec, out_dir, repo_root, thumb_dir=THUMB_DIR):
    """Copy the record's PNG thumbnail into its output directory and set
    rec["derived"]["logo_img"] = {"src", "width", "height"}, the image the list
    pages show. Without a PNG logo the key is absent and any old copy is removed.
    """
    tid = rec["id"]
    tdir = os.path.join(out_dir, "trails", tid)
    dest = os.path.join(tdir, THUMB_NAME)
    rec["derived"].pop("logo_img", None)
    shield = rec["derived"]["files"].get("shield", "")
    if not shield.endswith(".png"):
        if os.path.isfile(dest):
            os.remove(dest)
        return
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
    width, height = png_size(path)
    rec["derived"]["logo_img"] = {"src": src, "width": width, "height": height}
