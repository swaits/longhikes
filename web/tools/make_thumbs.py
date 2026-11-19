#!/usr/bin/env python3
"""Make the small PNG logo thumbnails the site shows in lists.

For every <id>/shield.png (or, where there is no PNG, <id>/shield.svg) in the
repository root, writes web/thumbs/<id>.png, scaled to fit within 256 x 256 px
(a PNG is never enlarged; an SVG is drawn at that size, so a thumbnail is never
blurred), metadata stripped and transparency kept. A vector logo can weigh
hundreds of kilobytes (the Bartram Trail's is 345 KB); its thumbnail a few tens. Needs ImageMagick 7 (`magick`) on the PATH; runs optipng
too when it is installed. Run on a developer machine and commit the output:
the site build itself is standard library only and does not run this.

    python3 web/tools/make_thumbs.py [--force]

It also writes web/thumbs-list/<id>.png, the same logo fitted within LIST_W x LIST_H
(twice the largest box the lists draw a logo in, 7 rem plate less its padding and
border: about 99 x 62 CSS px), for the lists, so a list does not download 256 px
images to show them at a third of that. The trail page header and the Logos page
keep the 256 px thumbnail.
A thumbnail newer than its source is left alone unless --force is given.
Thumbnails whose source no longer exists are removed.
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
THUMBS = os.path.join(os.path.dirname(HERE), "thumbs")
LIST_THUMBS = os.path.join(os.path.dirname(HERE), "thumbs-list")
MAX_SIDE = 256
LIST_W, LIST_H = 200, 124  # 2 x (99 x 62 CSS px), for high-density screens


def sources():
    """{id: path} for each <id>/shield.png, or <id>/shield.svg when there is no PNG,
    directly under the repository root."""
    found = {}
    for name in sorted(os.listdir(ROOT)):
        if name.startswith((".", "_")):
            continue
        for ext in ("png", "svg"):
            path = os.path.join(ROOT, name, f"shield.{ext}")
            if os.path.isfile(path):
                found[name] = path
                break
    return found


def make_thumb(src, dst, box=(MAX_SIDE, MAX_SIDE)):
    """Write one thumbnail with ImageMagick, then optimise it when optipng is present."""
    if src.endswith(".svg"):
        # Drawn at 384 dpi (so the drawing is larger than the thumbnail), then fitted.
        cmd = ["magick", "-background", "none", "-density", "384", src, "-strip",
               "-resize", f"{box[0]}x{box[1]}>", "PNG32:" + dst]
    else:
        cmd = ["magick", src, "-strip", "-resize", f"{box[0]}x{box[1]}>", "PNG32:" + dst]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        if os.path.exists(dst):
            os.remove(dst)
        sys.exit(f"make_thumbs: magick failed on {os.path.relpath(src, ROOT)}: "
                 f"{e.stderr.decode(errors='replace').strip()}")
    if shutil.which("optipng"):
        subprocess.run(["optipng", "-quiet", "-o2", dst], check=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Make web/thumbs/<id>.png from each <id>/shield.png (or .svg).")
    ap.add_argument("--force", action="store_true", help="rebuild thumbnails that are up to date")
    args = ap.parse_args(argv)

    if shutil.which("magick") is None:
        sys.exit("make_thumbs: 'magick' (ImageMagick 7) was not found on the PATH; install ImageMagick and retry")

    srcs = sources()
    written = skipped = removed = 0
    total = 0
    for out_dir, box in ((THUMBS, (MAX_SIDE, MAX_SIDE)), (LIST_THUMBS, (LIST_W, LIST_H))):
        os.makedirs(out_dir, exist_ok=True)
        for tid, src in srcs.items():
            dst = os.path.join(out_dir, f"{tid}.png")
            if not args.force and os.path.isfile(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
                skipped += 1
                continue
            make_thumb(src, dst, box)
            size = os.path.getsize(dst)
            total += size
            written += 1
            print(f"wrote {os.path.relpath(dst, ROOT)} ({size} bytes)")

        for name in sorted(os.listdir(out_dir)):
            if name.endswith(".png") and name[:-4] not in srcs:
                os.remove(os.path.join(out_dir, name))
                removed += 1
                print(f"removed {os.path.relpath(os.path.join(out_dir, name), ROOT)} (no source)")

    print(f"total: {written} written ({total} bytes), {skipped} up to date, {removed} removed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
