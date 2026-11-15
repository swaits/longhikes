"""Pieces shared by the home page and the trail pages: record summaries and small components."""
import re

from . import words
from .markup import Markup, esc


def trail_path(rec):
    return f"/trails/{rec['id']}/"


def kind(rec):
    return rec["derived"]["kind"]


def is_route(rec):
    return kind(rec) == "route"


def has_line(rec):
    return rec["derived"]["has_line"]


# A line whose measured length is further than this from the published length
# (either way, in percent) needs a length_gap_note (docs/schema.md).
LENGTH_LIMIT = 15.0


def line_differs(rec):
    """True when the record has a track, the track was measured, and the measured
    length differs from the published length by more than 15%. The one test of
    a partial track used by every page."""
    v = rec.get("verification", {})
    diff = v.get("difference_percent")
    return bool(has_line(rec) and v.get("verified") and diff is not None
                and abs(diff) > LENGTH_LIMIT)


def line_short(rec):
    """line_differs, and the measured track is the shorter: the track is partial."""
    return line_differs(rec) and rec["verification"]["difference_percent"] < 0


def partial_short_text(rec):
    """The short form for lists: "Track measures 1.2 mi (2.0 km) of 684 mi (1,100 km) published",
    in the reader's unit order (words.length). Markup."""
    v = rec["verification"]
    word = "of" if v["difference_percent"] < 0 else "against"
    return Markup(f"Track measures {words.length(v['measured_km'], measured=True)} {word} "
                  f"{words.length(rec['length_km'], mi=rec['derived']['length_mi'])} published")


def name(rec):
    """The record's name as HTML text, marked with its language when it is not
    English (web/site.toml [name_lang], copied to derived.name_lang by pages.py).
    Every place a page shows a record's name as text goes through here."""
    lang = rec.get("derived", {}).get("name_lang", "")
    text = esc(rec["name"])
    return Markup(f'<span lang="{esc(lang)}">{text}</span>') if lang else text


def countries(rec):
    """Every country the record touches: its own, and the country of each of its regions.
    In "US", "CA" order."""
    found = {rec["country"]} | {words.region_country(c) for c in rec.get("regions", [])}
    return [c for c in ("US", "CA") if c in found] + sorted(found - {"US", "CA", ""})


_OSM_CREDIT = re.compile(r"(?<!©)(?<!© )(?<!&copy; )OpenStreetMap contributors")


def credit_text(attribution):
    """The credit to show and copy: the record's attribution verbatim, with
    "© " before "OpenStreetMap contributors" where it is not already there."""
    return _OSM_CREDIT.sub("© OpenStreetMap contributors", attribution or "")


def sentence(text):
    """Text ending in a full stop, without doubling one already there."""
    text = (text or "").rstrip()
    return text if not text or text.endswith((".", "!", "?")) else text + "."


def policy(rec):
    return rec.get("route", {}).get("line_policy", "")


def shield_url(rec):
    shield = rec["derived"]["files"].get("shield")
    return f"/trails/{rec['id']}/{shield.rsplit('/', 1)[-1]}" if shield else ""


def designated_year(rec):
    """"National Scenic Trail (2009)" -> "2009"; "" when the designation has no year in brackets."""
    m = re.search(r"\((\d{4})\)", rec.get("designation", ""))
    return m.group(1) if m else ""


def short_source(rec):
    """A short name for where the included track came from, for lists."""
    src = rec.get("source", {})
    if src.get("osm_only"):
        name = "OpenStreetMap"
    else:
        name = re.split(r" \(|, | with ", src.get("line_source", ""))[0]
        if "OpenStreetMap" in src.get("attribution", "") and "OpenStreetMap" not in name:
            name += " and OpenStreetMap"
    return name


def licence_label(rec):
    src = rec.get("source", {})
    text = words.label(words.LICENCES, src.get("licence", ""))
    if "ODbL" in src.get("attribution", "") and src.get("licence") != "ODbL-1.0":
        text += " and ODbL 1.0"
    return text


def rich(text):
    """Escape record text, setting `backticked` spans (Overpass queries and the like) as code."""
    parts = esc(text).split("`")
    if len(parts) % 2 == 0:  # unbalanced backticks: leave the text as it is
        return esc(text)
    return Markup("".join(f"<code>{p}</code>" if i % 2 else p for i, p in enumerate(parts)))


def absent_reason_short(rec):
    """line_absent_reason without the opening "No line is included." or "No track is included." (the status already says so)."""
    reason = rec.get("source", {}).get("line_absent_reason", "")
    return re.sub(r"^No (?:line|track) is included\.\s*", "", reason) or reason


def badges(rec, *, route_tag=True):
    """The badges a hiker needs on a row or a trail page: Route (linked to what a route is)
    and National Scenic Trail. An official trail has no badge for its kind.
    route_tag=False leaves the Route badge out (the Routes list, where every row is one)."""
    out = []
    if route_tag and is_route(rec):
        out.append('<a class="tag tag--route" href="/routes/">Route</a>')
    if rec.get("tier") == "national":
        out.append('<span class="tag tag--nst">National Scenic Trail</span>')
    return Markup("".join(out))


def policy_chip(value):
    lab, short = words.label(words.POLICIES, value), words.meaning(words.POLICIES, value)
    return Markup(f'<span class="policy policy--{esc(value)}" title="Track policy: {esc(short)}">'
                  f'<span class="vh">Track policy: </span>{esc(lab)}</span>')


def logo_img(rec, alt, eager=False):
    """The logo <img>: the PNG thumbnail at its real size when there is one (olt/thumbs.py), else the file."""
    logo = rec["derived"].get("logo_img")
    src, dims = (logo["src"], f' width="{logo["width"]}" height="{logo["height"]}"') if logo \
        else (shield_url(rec), "")
    loading = "" if eager else ' loading="lazy"'
    return f'<img src="{esc(src)}" alt="{esc(alt)}"{dims}{loading} decoding="async">'


# The site's own mark (assets/favicon.svg, its mountain) for a plate with no logo and no abbreviation to show.
PLATE_MARK = Markup('<svg class="plate__mark" viewBox="0 0 32 32" focusable="false">'
                    '<path d="M3.5 25.5 13 7.5l5.2 9.3 2.9-4.6 7.4 13.3z" fill="currentColor"/></svg>')


def plate(rec, *, size="", link=False, eager=False, alt=None):
    """The logo on a light plate, or a dashed plate when there is no logo file: the trail's abbreviation if it has one, else the site's mark.

    link: the logo links to the full-size file. eager: not lazy-loaded (the record page header).
    alt: the image's text; by default "<name> logo" on a sized plate and "" on a list plate.
    A linked image with alt="" gets its link text from a visually hidden span instead.
    """
    url = shield_url(rec)
    cls = f"plate plate--{size}" if size else "plate"
    if url:
        if alt is None:
            alt = f"{rec['name']} logo" if size else ""
        img = logo_img(rec, alt, eager)
        if link:
            label = "" if alt else f'<span class="vh">Full-size logo: {name(rec)}</span>'
            img = f'<a href="{esc(url)}">{img}{label}</a>'
        return Markup(f'<div class="{cls}">{img}</div>')
    inner = esc(rec.get("short_name", "")) or PLATE_MARK
    return Markup(f'<div class="{cls} plate--none" aria-hidden="true"><span>{inner}</span></div>')


# Map credits. The base map is OpenFreeMap on every map. The trail maps add
# relief and contours drawn from the Terrain Tiles elevation data: their credit
# is the one tools/elevation.py gives (ATTRIBUTION; test_pages checks the two
# agree), plus Mexico, which the maps near the border show.
BASE_MAP_CREDIT = Markup("OpenFreeMap, &copy;&nbsp;OpenMapTiles, data &copy;&nbsp;OpenStreetMap contributors.")
ELEVATION_CREDIT = (
    "Terrain Tiles, accessed from https://registry.opendata.aws/terrain-tiles. "
    "United States 3DEP (formerly NED) and global GMTED2010 and SRTM terrain data "
    "courtesy of the U.S. Geological Survey. Canada terrain data contains "
    "information licensed under the Open Government Licence - Canada. ArcticDEM "
    "terrain data DEM(s) were created from DigitalGlobe, Inc., imagery and funded "
    "under National Science Foundation awards 1043681, 1559691, and 1542736. "
    "Global ETOPO1 terrain data U.S. National Oceanic and Atmospheric "
    "Administration."
)
MAP_ELEVATION_CREDIT = ELEVATION_CREDIT + " Mexico terrain data source: INEGI, Continental relief, 2016."
# The trail maps' own caption line: the full credit of everything they can draw.
TRAIL_MAP_CREDIT = Markup(f"Base map: {BASE_MAP_CREDIT} Relief and contours: {esc(MAP_ELEVATION_CREDIT)}")
# The site footer's short form; the elevation figures on every list come from the same data.
FOOTER_MAP_CREDIT = Markup(
    f"Base maps: {BASE_MAP_CREDIT} Elevation, relief and contours: Terrain Tiles, with data courtesy of "
    "the U.S. Geological Survey, NOAA, ArcticDEM and INEGI; Canada terrain data under the Open Government "
    "Licence - Canada. The full credit is under each trail map.")

SWATCH_LINE = Markup('<span class="swatch swatch--line" aria-hidden="true"></span>')
SWATCH_ROUTE = Markup('<span class="swatch swatch--route" aria-hidden="true"></span>')
SWATCH_ALT = Markup('<span class="swatch swatch--alt" aria-hidden="true"></span>')
SWATCH_NONE = Markup('<span class="swatch swatch--none" aria-hidden="true"></span>')
# A trail with no track, sketched from its start (and end) points only.
SWATCH_SKETCH = Markup('<span class="swatch swatch--sketch" aria-hidden="true"></span>')

ICON_DOWNLOAD = Markup('<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">'
                       '<path d="M8 1.5v9M4 7l4 4 4-4M2.5 14.5h11" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>')
ICON_EXTERNAL = Markup('<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">'
                       '<path d="M6 3H3v10h10v-3M9 2.5h4.5V7M13.5 2.5 7 9" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>')
