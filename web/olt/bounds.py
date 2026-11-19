"""Where a place is, for the map its page opens on (web/place-bounds.toml).

A place page opens its map on the place, not on the extent of its trails: a trail that crosses the
country on its way elsewhere would otherwise make the map open on all of it. The tracks of such a
trail are still drawn in full; they run off the edge of the opening view, and zooming out shows them.
"""
import os
import tomllib

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "place-bounds.toml")
_boxes = None


def boxes():
    """key ("US-UT") -> [west, south, east, north], read once."""
    global _boxes
    if _boxes is None:
        try:
            with open(PATH, "rb") as f:
                _boxes = {k: [float(v) for v in box] for k, box in (tomllib.load(f).get("box") or {}).items()}
        except (OSError, ValueError):
            _boxes = {}
    return _boxes


def place_box(key):
    """The box of a state or province (key as in olt/facets.py), or None when none is held."""
    return boxes().get(key)


def union(keys):
    """The box that holds the places in keys, or None when there are none or any has no box: the
    page then keeps the extent of its trails rather than show part of its place.

    A group page passes the keys of its members that have trails. A country with far-flung parts
    (the United States with Alaska and Hawaii) would be handled the same way, so that it opens on the
    parts the site has trails in and not on the whole width of the map."""
    found = [place_box(k) for k in keys]
    if not found or any(b is None for b in found):
        return None
    return [min(b[0] for b in found), min(b[1] for b in found), max(b[2] for b in found), max(b[3] for b in found)]
