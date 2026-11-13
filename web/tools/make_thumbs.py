#!/usr/bin/env python3
"""Make the small PNG logo thumbnails the site shows in lists.

For every <id>/shield.png in the repository root, writes web/thumbs/<id>.png,
scaled to fit within 256 x 256 px (never enlarged), metadata stripped and
transparency kept. Needs ImageMagick 7 (`magick`) on the PATH; runs optipng
too when it is installed. Run on a developer machine and commit the output:
the site build itself is standard library only and does not run this.

    python3 web/tools/make_thumbs.py [--force]

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
MAX_SIDE = 256


def sources():
    """{id: path} for each <id>/shield.png directly under the repository root."""
    found = {}
    for name in sorted(os.listdir(ROOT)):
        path = os.path.join(ROOT, name, "shield.png")
        if not name.startswith((".", "_")) and os.path.isfile(path):
            found[name] = path
    return found


def make_thumb(src, dst):
    """Write one thumbnail with ImageMagick, then optimise it when optipng is present."""
    cmd = ["magick", src, "-strip", "-resize", f"{MAX_SIDE}x{MAX_SIDE}>",
           "PNG32:" + dst]
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
    ap = argparse.ArgumentParser(description="Make web/thumbs/<id>.png from each <id>/shield.png.")
    ap.add_argument("--force", action="store_true", help="rebuild thumbnails that are up to date")
    args = ap.parse_args(argv)

    if shutil.which("magick") is None:
        sys.exit("make_thumbs: 'magick' (ImageMagick 7) was not found on the PATH; install ImageMagick and retry")

    os.makedirs(THUMBS, exist_ok=True)
    srcs = sources()
    written = skipped = removed = 0
    total = 0
    for tid, src in srcs.items():
        dst = os.path.join(THUMBS, f"{tid}.png")
        if not args.force and os.path.isfile(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            skipped += 1
            continue
        make_thumb(src, dst)
        size = os.path.getsize(dst)
        total += size
        written += 1
        print(f"wrote {os.path.relpath(dst, ROOT)} ({size} bytes)")

    for name in sorted(os.listdir(THUMBS)):
        if name.endswith(".png") and name[:-4] not in srcs:
            os.remove(os.path.join(THUMBS, name))
            removed += 1
            print(f"removed {os.path.relpath(os.path.join(THUMBS, name), ROOT)} (no source)")

    print(f"total: {written} written ({total} bytes), {skipped} up to date, {removed} removed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
