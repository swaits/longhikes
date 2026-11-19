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


def built_text(rec):
    """"290 mi built" for an unfinished trail whose holder states the built length; else "". Markup."""
    if not rec.get("built_km"):
        return Markup("")
    return Markup(f"{words.length(rec['built_km'], 'inline')} built")


def system_text(rec):
    """"Whole system: 1,584 mi, counting all designated trail ..." where the holder publishes a
    larger figure; else "". Markup. The note says what the figure counts (system_note)."""
    if not rec.get("system_km"):
        return Markup("")
    return Markup(f"Whole system: {words.length(rec['system_km'], 'inline')}, "
                  f"counting {esc(str(rec.get('system_note', '')).strip().rstrip('.'))}")


def partial_short_text(rec):
    """The short form for lists: "Track measures 1.2 mi (2.0 km) of 684 mi (1,100 km) published",
    in the reader's unit order (words.length). Markup."""
    v = rec["verification"]
    word = "of" if v["difference_percent"] < 0 else "against"
    return Markup(f"Track measures {words.length(v['measured_km'], measured=True)} {word} "
                  f"{words.length(rec['length_km'], mi=rec['derived']['length_mi'])} published")


# A search result shows about 60 characters of a title and about 155 of a description; a
# social preview shows about 125 characters of a description. The site name is shown by
# the search engine on its own line, so " \u00b7 <site name>" is added to the <title> only when
# the whole title still has TITLE_LIMIT characters or fewer.
TITLE_LIMIT = 60
DESCRIPTION_LIMIT = 155
SHARE_DESCRIPTION_LIMIT = 125


def title_room(site):
    """How many characters a page's own title may have: TITLE_LIMIT, with or without the site name."""
    return TITLE_LIMIT


def fit_title(options, site):
    """The first of options (richest first) that fits title_room; else the last, the shortest."""
    return next((o for o in options if len(o) <= title_room(site)), options[-1])


def title_tag(title, site):
    """The text of <title>: "<title> \u00b7 <site name>" where that is TITLE_LIMIT characters or
    fewer, else the title alone."""
    full = f"{title} \u00b7 {site.name}"
    return full if len(full) <= TITLE_LIMIT else title


_DANGLING = {"and", "or", "but", "nor", "with", "to", "of", "the", "a", "an", "in", "on", "at", "by",
             "for", "from", "as", "than", "that", "which", "is", "are", "was", "were", "about",
             "across", "through", "over", "under", "between", "into", "near", "via"}
_ABBREVIATIONS = {"st", "mt", "mts", "ft", "no", "vs", "u.s", "d.c", "dr", "jr", "sr", "approx", "e.g", "i.e"}


def cut_clean(text, limit):
    """text if it fits, else cut at the end of a word within limit characters and closed with a
    full stop, never with an ellipsis: a cut never leaves a comma, a colon or a conjunction (or other
    joining word) last."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    head = text[:limit - 1]
    if text[limit - 1] != " ":
        head = head.rsplit(" ", 1)[0] if " " in head else head
    head = head.rstrip(" ,;:.")
    while True:
        word = head.rsplit(" ", 1)[-1].lower().rstrip(",;:")
        if " " in head and (word in _DANGLING or head[-1] in ",;:"):
            head = head.rsplit(" ", 1)[0].rstrip(" ,;:.")
        else:
            break
    return head + "."


def share_description(text, limit=SHARE_DESCRIPTION_LIMIT):
    """text for a social preview: at most `limit` characters, cut from the search description at the
    end of its last whole sentence that fits (one past a quarter of the limit), else at the end of a
    word, closed with a full stop (cut_clean). Never an ellipsis."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    best = 0
    for m in re.finditer(r"[.!?](?= )", text[:limit + 1]):
        if m.end() > limit:
            break
        last = text[:m.start()].rsplit(" ", 1)[-1].lower().rstrip(".")
        if last in _ABBREVIATIONS:
            continue
        best = m.end()
    if best >= limit // 4:
        return text[:best]
    return cut_clean(text, limit)


def plain_name(rec):
    """The name hikers use (common_name) where the record has one, else its name. Plain text."""
    return rec.get("common_name") or rec["name"]


def cut_at_word(text, limit):
    """text if it fits, else cut at a word with an ellipsis, within limit characters."""
    if len(text) <= limit:
        return text
    return text[:limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:.") + "\u2026"


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


# Services the maintainers search with. A search is a note for maintainers (the record's own notes), not
# something a visitor is told on the page.
INTERNAL_SERVICE = re.compile(r"\b(Overpass|Nominatim|Geofabrik)\b")


def visitor_text(text):
    """text without the sentences that name a maintainers' search service."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(p for p in parts if not INTERNAL_SERVICE.search(p))


def not_added_yet(rec):
    """True when the record says only that no track has been added yet: a public track exists, or may,
    and the page must not give a reason of the kind "no track may be passed on"."""
    src = rec.get("source", {})
    return src.get("status") == "osm-only" or src.get("line_absent_reason", "").startswith("No track has been added")


def sells_gpx(rec):
    """True when a guide the author sells names a GPX or GPS track in what it holds (its format or
    title); a route sold only as a book or map set has no GPX to sell."""
    return any(g.get("access") == "purchase" and re.search(r"GPX|GPS", f'{g.get("format", "")} {g.get("title", "")}', re.I)
               for g in rec.get("guide", []))


def absent_reason_short(rec):
    """line_absent_reason without the opening "No line is included." or "No track is included." (the status already says so)."""
    reason = visitor_text(rec.get("source", {}).get("line_absent_reason", ""))
    if not_added_yet(rec):
        return visitor_text(reason.split(". ")[0].rstrip(".") + ".") if reason else reason
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


def logo_img(rec, alt, eager=False, listed=False):
    """The logo <img>: the PNG thumbnail at its real size when there is one (olt/thumbs.py), else the file.

    listed: the list-size thumbnail (twice the size a list shows a logo at), when there is one."""
    logo = (rec["derived"].get("list_img") if listed else None) or rec["derived"].get("logo_img")
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
        img = logo_img(rec, alt, eager, listed=not size)
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
    "Licence - Canada. The full credit is beside each trail map.")

def save_button(rec, *, row=True):
    """The control that saves a trail to the visitor's saved trails, or takes it off.

    A real <button>, never inside a link, named for the trail ("Save Pacific
    Crest Trail") whatever its state; app.js sets aria-pressed (and the word
    "Save" or "Saved" on a trail page) from the saved list, lh-saved in
    localStorage. row: the star alone, placed under the logo of a list row
    (style.css .save--row); otherwise the button beside a trail page's actions.
    Hidden without JavaScript, which saving needs (.js-only).
    """
    tid = esc(rec["id"])
    label = f'<span class="vh">Save {name(rec)}</span>'
    if row:
        return Markup(f'<button class="save save--row js-only" type="button" data-save="{tid}" '
                      f'aria-pressed="false" title="Save">{ICON_STAR}{label}</button>')
    return Markup(f'<button class="button button--quiet save save--page js-only" type="button" data-save="{tid}" '
                  f'aria-pressed="false">{ICON_STAR}<span class="save__word" aria-hidden="true">Save</span>{label}</button>')


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
# The mark of a saved trail. Its fill is set by style.css (outline when not
# saved, filled when saved), so one drawing serves every state.
ICON_STAR = Markup('<svg class="star" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
                   '<path d="M12 2.8l2.85 5.78 6.38.93-4.62 4.5 1.09 6.35L12 17.36l-5.7 3 1.09-6.35-4.62-4.5 '
                   '6.38-.93z" stroke-linejoin="round"/></svg>')
# The three themes, for the theme menu in the header: auto (half dark, as the
# device decides), light (a sun) and dark (a moon).
ICON_THEME = {
    "auto": Markup('<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
                   '<circle cx="12" cy="12" r="8.25" fill="none" stroke="currentColor" stroke-width="1.7"/>'
                   '<path d="M12 3.75a8.25 8.25 0 0 1 0 16.5z" fill="currentColor"/></svg>'),
    "light": Markup('<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
                    '<circle cx="12" cy="12" r="4.25" fill="none" stroke="currentColor" stroke-width="1.7"/>'
                    '<path d="M12 2.5v2.75M12 18.75v2.75M2.5 12h2.75M18.75 12h2.75M5.28 5.28l1.95 1.95'
                    'M16.77 16.77l1.95 1.95M5.28 18.72l1.95-1.95M16.77 7.23l1.95-1.95" fill="none" '
                    'stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>'),
    "dark": Markup('<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
                   '<path d="M19.75 14.6A8 8 0 0 1 9.4 4.25a8.25 8.25 0 1 0 10.35 10.35z" fill="none" '
                   'stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>'),
}
