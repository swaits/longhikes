"""Fingerprinted site assets: the stylesheet, scripts, fonts and map libraries, served
from /immutable/ under names that carry a hash of their content.

A file named for its own content never changes, so it can be cached for a year
(web/static/_headers: /immutable/* is "public, max-age=31536000, immutable") and a
changed file gets a new name, so a revisit never runs an old script against a new
page. Pages (olt/layout.py) ask for each file's address with url(); the build
(web/build.py) writes the files with publish() once the pages are written.

Only these files are fingerprinted; everything else under /assets/ (the icons, the
social card, the base-map style, licence texts) keeps its address and revalidates.

The hash is the first 10 hex digits of SHA-256 of the content as served. The
stylesheet names the fonts and the contour picture, so those are hashed first and
the stylesheet's own hash covers the addresses written into it.
"""
import hashlib
import os
import re

WEB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(WEB_DIR, "assets")
DIR = "/immutable/"  # the one directory the files are served from, flat

# Site paths (under /assets/) of the files that are fingerprinted.
STYLESHEET = "/assets/style.css"
FILES = (
    STYLESHEET,
    "/assets/app.js",
    "/assets/prefs.js",
    "/assets/contours.svg",
    "/assets/fonts/ibm-plex-sans-condensed-400-latin.woff2",
    "/assets/fonts/ibm-plex-sans-condensed-500-latin.woff2",
    "/assets/fonts/ibm-plex-sans-condensed-600-latin.woff2",
    "/assets/fonts/source-serif-4-italic-latin.woff2",
    "/assets/fonts/source-serif-4-latin.woff2",
    "/assets/vendor/maplibre-gl/maplibre-gl.css",
    "/assets/vendor/maplibre-gl/maplibre-gl.js",
    "/assets/vendor/maplibre-contour/maplibre-contour.js",
)
# What the stylesheet names, as it writes it: url("fonts/x.woff2") and url("contours.svg").
_CSS_URL = re.compile(r'url\("([^"]+)"\)')

HASH_LEN = 10
_cache = {}


def _source(path):
    return os.path.join(ASSETS_DIR, *path[len("/assets/"):].split("/"))


def _content(path):
    """The bytes the file is served with: the stylesheet with its font and picture
    addresses fingerprinted, every other file as it is."""
    with open(_source(path), "rb") as f:
        data = f.read()
    if path != STYLESHEET:
        return data

    def rewrite(m):
        target = "/assets/" + m.group(1)
        return f'url("{_name(target)}")' if target in FILES else m.group(0)
    return _CSS_URL.sub(rewrite, data.decode("utf-8")).encode("utf-8")


def _name(path):
    """The file name (no directory) of a fingerprinted file."""
    # Keyed on every file's time: the stylesheet's content depends on the fonts and picture it names.
    key = (path, tuple(os.path.getmtime(_source(p)) for p in FILES))
    if key not in _cache:
        digest = hashlib.sha256(_content(path)).hexdigest()[:HASH_LEN]
        stem, ext = os.path.splitext(os.path.basename(path))
        _cache[key] = f"{stem}.{digest}{ext}"
    return _cache[key]


def url(path):
    """The address to use for an asset: /immutable/<name>.<hash>.<ext> for a
    fingerprinted file, the path itself for any other. The stylesheet's own
    references are relative, so they resolve inside /immutable/."""
    if path not in FILES:
        return path
    return DIR + _name(path)


def publish(out_dir):
    """Write the fingerprinted files to <out>/immutable/ and take the originals out
    of <out>/assets/, so no page can reach a file under both addresses. Returns the
    number of files written. Run after the pages step has copied web/assets/."""
    dest = os.path.join(out_dir, DIR.strip("/"))
    if os.path.isdir(dest):
        for name in os.listdir(dest):
            os.remove(os.path.join(dest, name))
    os.makedirs(dest, exist_ok=True)
    for path in FILES:
        with open(os.path.join(dest, _name(path)), "wb") as f:
            f.write(_content(path))
        original = os.path.join(out_dir, "assets", *path[len("/assets/"):].split("/"))
        if os.path.isfile(original):
            os.remove(original)
    return len(FILES)
