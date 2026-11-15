"""One page per record: /trails/<id>/.

The main sections say what the record says, in plain words. Every field of
the record, with its exact value, is in the table at the end of the page
(raw_record); the main flow carries no coded values.
"""
import os
import re
import urllib.parse

from . import common, elevation, facets, hike, words
from .layout import OUTDOOR_STYLE
from .markup import Markup, esc

EXTRACT_SOURCES = {"osm": "OpenStreetMap", "usfs": "USDA Forest Service", "nps": "National Park Service"}
GAUGE_MIN, GAUGE_MAX, GAUGE_LIMIT = -40.0, 40.0, common.LENGTH_LIMIT
# Download formats in the order a hiker most likely wants them: GPX for devices first.
FORMAT_ORDER = ("GPX", "GeoJSON")


# Small building blocks ------------------------------------------------------

def code(value):
    return Markup(f'<code class="raw">{esc(value)}</code>')


def fact(label, value, note=""):
    """One label/value row of a facts list. note: smaller text under the value.

    Plain-string values and notes are record text: escaped, with `backticked` spans set as code.
    """
    value_html = value if isinstance(value, Markup) else common.rich(value)
    note_html = f"<small>{note if isinstance(note, Markup) else common.rich(note)}</small>" if note else ""
    return Markup(f"<div><dt>{esc(label)}</dt><dd>{value_html}{note_html}</dd></div>")


def facts(*rows):
    rows = [r for r in rows if r]
    return Markup('<dl class="facts">' + "".join(rows) + "</dl>") if rows else Markup("")


def ext_link(url, text=None):
    return Markup(f'<a href="{esc(url)}">{esc(text or url)}</a>')


def host(url):
    netloc = urllib.parse.urlsplit(url).netloc
    return netloc[4:] if netloc.startswith("www.") else netloc


def yes_no(value):
    return "Yes" if value else "No"


def block(id_, title, content, extra=""):
    """A section of the main column. Its heading carries the id; the section is not a
    landmark (no aria-labelledby): a page has many of them."""
    return Markup(f'<section class="block">'
                  f'<h2 id="{id_}">{esc(title)}{extra}</h2>{content}</section>')


def record_text(text, cls=""):
    return Markup(f'<p class="record-text{(" " + cls) if cls else ""}">{common.rich(text)}</p>')


def restates_no_line(value):
    """True for record values that only say there is no track ("none (no line included)")."""
    text = str(value or "").strip().lower()
    return text.startswith(("none (no line", "no line included", "no line to measure",
                            "none (no track", "no track included", "no track to measure"))


def region_names(rec):
    """The states and provinces for the glance, each linked to its place page; codes when there are many."""
    keys = facets.place_keys(rec)
    parts = []
    for key in keys:
        name = facets.place_name(key)
        text = esc(name) if len(keys) <= 3 or key == facets.ACROSS_CANADA else \
            Markup(f'<abbr title="{esc(name)}">{esc(key.split("-", 1)[1])}</abbr>')
        parts.append(f'<a href="{esc(facets.place_path(key))}">{text}</a>')
    return Markup((", " if len(keys) <= 3 else " ").join(parts))


_ORG_CUT = re.compile(r", who |, with | publishes |; (?=[a-z])| \((?=[a-z])| \((?=[^)]*geometry)")


def org_name(text):
    """The organisation or person a record names, without the record's own remarks:
    "Green Mountain Club (publishes the trail); its ArcGIS ..." -> "Green Mountain Club"."""
    name = _ORG_CUT.split(text or "", maxsplit=1)[0].strip()
    return name[:1].upper() + name[1:]


# Page head ------------------------------------------------------------------

def kind_word(rec):
    return "route" if common.is_route(rec) else "trail"


def place_text(rec):
    """Where it is, for a sentence: "in Oregon, United States", "across 14 states of the
    United States", "across 9 states and provinces of the United States and Canada"."""
    codes = rec.get("regions", [])
    countries = [words.COUNTRIES.get(c, c) for c in common.countries(rec)] or \
        [words.COUNTRIES.get(rec["country"], rec["country"])]
    country = words.join_names(countries)
    if words.ALL_CANADA in codes or not codes:
        return f"across {country}" if words.ALL_CANADA in codes else f"in {country}"
    if len(codes) > 3:
        unit = {"United States": "states", "Canada": "provinces and territories"}.get(country, "states and provinces")
        the = words.join_names(("the " + c) if c == "United States" else c for c in countries)
        return f"across {len(codes)} {unit} of {the}"
    return f"in {words.join_names(words.region_name(c) for c in codes)}, {country}"


def fallback_lede(rec):
    """A one-sentence description built from the record, for a record without a [hike] summary."""
    length_html = words.length(rec["length_km"], "inline", rec["derived"]["length_mi"])
    return Markup(f"A {kind_word(rec)} of {length_html} {esc(place_text(rec))}.")


def lead_line(rec):
    """Who made or designated it: "Route by Steve Roper, 1970", or the trail's designation."""
    if common.is_route(rec):
        return facets.route_by(rec)
    return rec.get("designation", "")


def route_definition():
    """What a route is, one tap away from the Kind line of a route's page (no script needed)."""
    return Markup(f'<details class="define"><summary>What is a route?</summary>'
                  f'<p>{esc(facets.ROUTE_DEFINITION)} <a href="/routes/">Every route</a>.</p></details>')


def official_link(rec):
    """(url, label) of the trail's own page: the [hike] official site, else the
    publisher's page for the trail, else a route's free guide; None when the record has none."""
    url = hike.official_url(rec)
    if url:
        return url, "Official site"
    src = rec.get("source", {})
    if src.get("publisher_url"):
        who = org_name(src.get("publisher", ""))
        return src["publisher_url"], (f"{who} website" if who else "The trail's website")
    if common.is_route(rec):
        for g in rec.get("guide", []):
            if g.get("url"):
                return g["url"], "The route's guide"
    return None


def page_head(rec):
    route = common.is_route(rec)
    crumbs = ['<li><a href="/regions/">Places</a></li>']
    keys = facets.place_keys(rec)
    groups = facets.place_groups(rec)
    if keys and keys[0] in facets.GROUP_OF:
        g = facets.GROUP_OF[keys[0]]
        crumbs.append(f'<li><a href="/regions/#{esc(g)}">{esc(facets.GROUP_NAME[g])}</a></li>')
        crumbs.append(f'<li><a href="{esc(facets.place_path(keys[0]))}">{esc(facets.place_name(keys[0]))}</a></li>')
    elif groups:
        crumbs.append(f'<li><a href="/regions/#across-canada">{esc(facets.ACROSS_CANADA_NAME)}</a></li>')
    crumbs.append(f'<li aria-current="page">{common.name(rec)}</li>')
    has_plate = bool(common.shield_url(rec))
    abbr = rec.get("short_name", "")
    abbr_html = f' <span class="titleblock__abbr">{esc(abbr)}</span>' if abbr else ""
    plate = common.plate(rec, size="lg", link=True, eager=True) if has_plate else ""
    summary = hike.summary(rec)
    lede = common.rich(summary) if summary else fallback_lede(rec)
    actions = []
    official = official_link(rec)
    if official:
        actions.append(f'<a class="button button--link" href="{esc(official[0])}">{esc(official[1])} {common.ICON_EXTERNAL}</a>')
    elif more_links(rec):
        # No page of its own: the first of the pages about the trail stands in, named by its publisher.
        first = more_links(rec)[0]
        actions.append(f'<a class="button button--link" href="{esc(first["url"])}">'
                       f'{esc(first["publisher"])} {common.ICON_EXTERNAL}</a>')
    if rec["derived"].get("downloads"):
        actions.append(f'<a class="button button--primary" href="#download">{common.ICON_DOWNLOAD}Download the GPX</a>')
    else:
        actions.append(f'<a class="button button--quiet" href="#track">GPX: {esc(facets.GPX_STATUS[facets.gpx(rec)])}</a>')
    tag_html = common.badges(rec)
    kicker = f'<p class="cluster">{tag_html}</p>' if tag_html else ""
    lead = lead_line(rec)
    define = route_definition() if route else ""
    return f"""<div class="page-head">
  <div class="container">
    <nav class="breadcrumb" aria-label="Breadcrumb"><ol>{"".join(crumbs)}</ol></nav>
    <header class="titleblock{" titleblock--with-plate" if has_plate else ""}">
      {plate}
      <div class="titleblock__text">
        {kicker}
        <h1>{common.name(rec)}{abbr_html}</h1>
        {f'<p class="titleblock__sub">{common.rich(lead)}</p>' if lead else ""}
        {define}
      </div>
    </header>
    <p class="trail-lede">{lede}</p>
    <p class="cluster trail-actions">{"".join(actions)}</p>
    {links_panel(rec)}
  </div>
</div>"""


def glance_row(label, value, note="", wide=False):
    note_html = f"<small>{note if isinstance(note, Markup) else esc(note)}</small>" if note else ""
    value_html = value if isinstance(value, Markup) else esc(value)
    return Markup(f'<div{" class=\"glance__wide\"" if wide else ""}><dt>{esc(label)}</dt>'
                  f'<dd>{value_html}{note_html}</dd></div>')


def glance(rec):
    """The hiker's facts at a glance, under the attribute names every page uses."""
    h = hike.table(rec)
    rows = [glance_row(facets.LENGTH, words.length(rec["length_km"], "stack", rec["derived"]["length_mi"]))]
    rows.append(glance_row(facets.TIME, facets.time_text(rec), facets.estimate_note(rec)))
    season = facets.season_text(rec)
    if season:
        rows.append(glance_row(facets.SEASON, season))
    if facets.walking(rec):
        rows.append(glance_row(facets.WALKING, facets.WALKING_VALUES[facets.walking(rec)]))
    elev = elevation.get(rec)
    if h.get("high_point") or h.get("high_point_m"):
        # A named, sourced high point is better than a computed number.
        value = Markup(esc(h.get("high_point", "")))
        if h.get("high_point_m"):
            value = Markup(f'{value}{"<br>" if h.get("high_point") else ""}{words.elevation(h["high_point_m"])}')
        rows.append(glance_row("High point", value))
    elif elev:
        rows.append(glance_row("High point", words.elevation(elev["highest"]["m"]),
                               elevation.COMPUTED_NOTE))
    if elev:
        low = elev["lowest"]
        low_note = ("Sea level. " if elevation.is_sea_level(low) else "") + elevation.COMPUTED_NOTE
        rows.append(glance_row("Low point", words.elevation(low["m"]), low_note))
        climb = Markup(str(words.elevation(elev["ascent_m"])))
        if elevation.show_descent(elev):
            climb = Markup(f'{climb}<br>Descent: {words.elevation(elev["descent_m"])}')
        if facets.shape(rec) == "loop":
            climb_note = elevation.COMPUTED_NOTE
        else:
            climb_note = f"Computed from the track, {elevation.direction_words(elev)}."
        rows.append(glance_row("Climb", climb, climb_note))
    ends = hike.ends(rec)
    if ends:
        label, text = ends
        if isinstance(text, tuple):
            text = Markup(f'{esc(text[0])}<span class="glance__to"> to </span>{esc(text[1])}')
        if facets.shape(rec):
            text = Markup(f'<strong>{esc(facets.SHAPES[facets.shape(rec)])}.</strong> {esc(text) if not isinstance(text, Markup) else text}')
            label = facets.SHAPE
        rows.append(glance_row(label, text, wide=True))
    elif facets.shape(rec):
        rows.append(glance_row(facets.SHAPE, facets.SHAPES[facets.shape(rec)]))
    terrain = facets.terrain(rec)
    if terrain:
        rows.append(glance_row(facets.TERRAIN, ", ".join(words.TERRAIN[t] for t in terrain), wide=True))
    if h.get("permit"):
        rows.append(glance_row("Permits", common.sentence(h["permit"]), wide=True))
    country = " and ".join(words.COUNTRIES.get(c, c) for c in common.countries(rec))
    rows.append(glance_row(facets.WHERE, Markup(f'{region_names(rec)}, {esc(country)}'), wide=True))
    status = facets.gpx(rec)
    if facets.gpx_here(rec):
        text = facets.GPX_STATUS[status]
        value = Markup(f'<a href="#download">{esc(text)}</a>') if rec["derived"].get("downloads") else text
        note = common.partial_short_text(rec) if common.line_differs(rec) else ""
    else:
        value = Markup(f'<a href="#track">{esc(facets.GPX_STATUS[status])}</a>')
        note = ""
    rows.append(glance_row(facets.GPX, value, note, wide=True))
    halves = [i for i, r in enumerate(rows) if 'class="glance__wide"' not in r]
    if len(halves) % 2:  # an odd one out takes the full width rather than leave a gap beside it
        i = halves[-1]
        rows[i] = Markup(rows[i].replace("<div>", '<div class="glance__wide">', 1))
    caution = ""
    if h.get("caution"):
        caution = f'<p class="glance__warn"><strong>Know before you go.</strong> {common.rich(common.sentence(h["caution"]))}</p>'
    unfinished = ""
    if h.get("unfinished"):
        unfinished = f'<p class="glance__warn"><strong>Not finished.</strong> {common.rich(common.sentence(h["unfinished"]))}</p>'
    missing = [name for name, have in ((facets.SEASON, season), (facets.TERRAIN, terrain),
                                       (facets.WALKING, facets.walking(rec))) if not have]
    pending = ""
    if missing:
        names = words.join_names([missing[0]] + [m.lower() for m in missing[1:]])
        verb = "is" if len(missing) == 1 else "are"
        pending = f'<p class="note">{esc(names)} {verb} not on file for this trail yet.</p>'
    elev_caveat = elevation.coverage_caveat(elev) if elev else ""
    elev_note = f'<p class="note">{esc(elev_caveat)}</p>' if elev_caveat else ""
    return f"""<section class="glance detail__glance" aria-labelledby="glance-title">
  <h2 class="glance__title" id="glance-title">At a glance</h2>
  <dl class="glance__facts">{"".join(rows)}</dl>
  {unfinished}{caution}{elev_note}{pending}
</section>"""


# Map or empty frame ---------------------------------------------------------

def map_figure(rec):
    src = rec["source"]
    has_alt = "alternates" in rec["derived"]["files"]
    route = common.is_route(rec)
    legend = f'<li>{common.SWATCH_ROUTE if route else common.SWATCH_LINE}Main track</li>'
    if has_alt:
        legend += f"<li>{common.SWATCH_ALT}Alternates and connectors</li>"
    bbox = rec["derived"].get("map_bbox") or rec["derived"].get("bbox")
    bbox_attr = f' data-bbox="{",".join(str(v) for v in bbox)}"' if bbox else ""
    credit = common.sentence(common.credit_text(src.get("attribution", "")))
    return f"""<figure class="mapfig mapfig--detail detail__map" data-map="trail" data-src="/trails/{esc(rec["id"])}/map.json" data-route="{"yes" if route else "no"}"{bbox_attr} data-outdoor="{OUTDOOR_STYLE}">
  <div class="mapfig__frame">
    <span class="mapfig__corner mapfig__corner--nw" aria-hidden="true"></span>
    <div class="map" role="region" aria-label="Map of the {esc(rec["name"])}">
      <div class="map__fallback"></div>
      <div class="map__canvas"></div>
      <p class="map__status" role="status">The map needs JavaScript. Download the GPX or GeoJSON file from this page.</p>
    </div>
    <span class="mapfig__corner mapfig__corner--se" aria-hidden="true"></span>
  </div>
  <figcaption class="mapfig__caption">
    <ul class="legend" aria-label="Legend">{legend}</ul>
    <p>Track: {esc(src.get("line_source", ""))}, read {esc(src.get("source_checked", ""))}, drawn simplified to 30&nbsp;m. Credit: {esc(credit)} {common.TRAIL_MAP_CREDIT}</p>
  </figcaption>
</figure>"""


def elevation_figure(rec):
    """The elevation profile under the map, drawn as SVG at build time. With too
    many parts (olt/elevation.py) there is no line to draw in walking order, so
    the section says that and states the figures instead."""
    elev = elevation.get(rec)
    if not elev:
        return ""
    loop = facets.shape(rec) == "loop"
    sentence = elevation.summary_sentence(elev, loop)
    caveat = elevation.coverage_caveat(elev)
    caveat_html = f'<p class="note">{esc(caveat)}</p>' if caveat else ""
    if not elevation.show_profile(elev):
        return f"""<section class="elev detail__profile" aria-labelledby="elevation-title">
  <h2 class="elev__title" id="elevation-title">Elevation profile</h2>
  <div class="elev__body">
    <p>{esc(elevation.parts_caveat(elev))}</p>
    <p>{esc(sentence)}</p>
    {caveat_html}
  </div>
</section>"""
    parts = elev.get("parts") or 1
    breaks = (f" The line breaks where the track does: it has {parts} parts, and no climb "
              "is counted across a gap.") if parts > 1 else ""
    return f"""<section class="elev detail__profile" aria-labelledby="elevation-title">
  <h2 class="elev__title" id="elevation-title">Elevation profile</h2>
  <figure class="elev__figure">
    {elevation.profile_svg(elev, loop)}
    <figcaption><p>{esc(sentence)}{esc(breaks)}</p>{caveat_html}</figcaption>
  </figure>
</section>"""


def free_guides(rec):
    return [g for g in rec.get("guide", []) if g.get("access") == "free"]


ROUTE_NO_GPX = {
    # GPX status -> (heading, what this site does about it)
    "free": ("Get the GPX from its author",
             "A GPX is included here only where the author's terms allow passing it on, or where "
             "OpenStreetMap maps the route. Otherwise the author's own page is the place to get it."),
    "sold": ("The author sells the route as a guide",
             "No GPX is included here from any source, OpenStreetMap included, so the author's work is respected."),
    "unpublished": ("The author does not publish a track",
                    "No GPX is included here from any source, OpenStreetMap included, so the author's choice is respected."),
    "elsewhere": ("No GPX here",
                  "No GPX is included here until it is clear that the author allows it."),
}


def _no_gpx_parts(rec):
    """(title, status, reason, rule, actions_html): why there is no GPX here
    and where to get one, for the empty frame and the sketch map alike."""
    src = rec["source"]
    reason = src.get("line_absent_reason", "")
    actions = []
    status = facets.gpx(rec)
    if common.is_route(rec):
        title, rule = ROUTE_NO_GPX.get(status, ROUTE_NO_GPX["elsewhere"])
        if status == "free" and free_guides(rec):
            g = free_guides(rec)[0]
            actions.append(f'<a class="button button--primary" href="{esc(g["url"])}">'
                           f'{esc(g["title"])} {common.ICON_EXTERNAL}</a>')
        if not actions:
            actions.append('<a class="button button--link" href="#guides-title">See where to get the route</a>')
        elif len(rec.get("guide", [])) > 1:
            actions.append('<a class="button button--link" href="#guides-title">All guides</a>')
    else:
        title = "No GPX here"
        reason = common.absent_reason_short(rec)
        rule = "A trail is listed without a GPX when no track for it may be passed on."
        official = official_link(rec)
        if official:
            actions.append(f'<a class="button button--link" href="{esc(official[0])}">'
                           f'{esc(official[1])} {common.ICON_EXTERNAL}</a>')
        places = [official[1][:1].lower() + official[1][1:] if official[1] == "Official site"
                  else "the " + official[1]] if official else []
        if src.get("url") and (not official or src["url"] != official[0]):
            osm = host(src["url"]).endswith("openstreetmap.org")
            label = "See it on OpenStreetMap" if osm else "Where to ask for the track"
            places.append("OpenStreetMap, where the trail is mapped" if osm else "the track's source")
            actions.append(f'<a class="button button--link" href="{esc(src["url"])}">'
                           f'{esc(label)} {common.ICON_EXTERNAL}</a>')
        if places:
            places[0] = places[0].replace("official site", "the official site")
            lead = f"For a track, try {words.join_names(places)}."
            reason = Markup(f'{esc(lead)}</p><p class="note"><strong>Why there is none here:</strong> '
                            f'{common.rich(reason)}')
    actions_html = f'<p class="cluster">{"".join(actions)}</p>' if actions else ""
    return title, status, reason, rule, actions_html


def empty_frame(rec):
    """The map frame of a trail with no GPX here and no known start or end point."""
    title, status, reason, rule, actions_html = _no_gpx_parts(rec)
    return f"""<figure class="mapfig mapfig--empty detail__map" id="track" aria-labelledby="noline-title">
  <div class="mapfig__frame">
    <span class="mapfig__corner mapfig__corner--nw" aria-hidden="true">No GPX here</span>
    <div class="map map--empty">
      <div class="map__message">
        <p class="kicker">GPX: {esc(facets.GPX_STATUS[status])}</p>
        <h2 id="noline-title">{esc(title)}</h2>
        <p class="map__reason">{reason if isinstance(reason, Markup) else common.rich(reason)}</p>
        <p class="note">{esc(rule)}</p>
        {actions_html}
      </div>
    </div>
    <span class="mapfig__corner mapfig__corner--se" aria-hidden="true">Nothing drawn</span>
  </div>
  <figcaption class="mapfig__caption"><p>No map is drawn: there is no track for this trail here, and the site does not guess one.</p></figcaption>
</figure>"""


def sketch_figure(rec):
    """A real map for a trail with no track but a known start or end: a dotted
    straight line between the two, or one ring. It says plainly that the line only
    joins the start and the end, and keeps the words about where to get a track."""
    points = hike.sketch_points(rec)
    box = hike.sketch_bbox(points, pad=True)
    bbox_attr = f' data-bbox="{",".join(str(v) for v in box)}"' if box else ""
    route = common.is_route(rec)
    h = hike.table(rec)
    start = h.get("start") if isinstance(h.get("start"), str) else ""
    end = h.get("end") if isinstance(h.get("end"), str) else ""
    start, end = start.strip(), end.strip()
    if len(points) == 2:
        if start and end:
            where = (f"The dotted line runs straight from {esc(start)} to {esc(end)}. "
                     "It only joins the start and the end; that is not the trail&rsquo;s path.")
        elif start:
            where = (f"The dotted line runs straight from {esc(start)} to where it ends. "
                     "It only joins the start and the end; that is not the trail&rsquo;s path.")
        else:
            where = ("The dotted line runs straight between its start and its end. "
                     "It only joins the two; that is not the trail&rsquo;s path.")
        legend_text = "No GPX here: start and end only"
    else:
        if hike.sketch_end(rec) == "end":
            where = (f"The ring marks {esc(end)}, where it ends. " if end else "The ring marks where it ends. ")
            where += "No position is on file for the start, so no line is drawn."
            legend_text = "No GPX here: end only"
        elif h.get("shape") == "loop":
            where = (f"The ring marks {esc(start)}, where the loop starts and ends. " if start
                     else "The ring marks where the loop starts and ends. ")
            where += "It shows where the trail is, not its path."
            legend_text = "No GPX here: start only"
        else:
            where = (f"The ring marks {esc(start)}, where it starts. " if start else "The ring marks where it starts. ")
            where += "No position is on file for the end, so no line is drawn."
            legend_text = "No GPX here: start only"
    _title, status, reason, rule, actions_html = _no_gpx_parts(rec)
    reason_html = reason if isinstance(reason, Markup) else common.rich(reason)
    return f"""<figure class="mapfig mapfig--detail detail__map" id="track" data-map="sketch" data-src="/trails/{esc(rec["id"])}/sketch.json" data-route="{"yes" if route else "no"}"{bbox_attr} data-outdoor="{OUTDOOR_STYLE}">
  <div class="mapfig__frame">
    <span class="mapfig__corner mapfig__corner--nw" aria-hidden="true"></span>
    <div class="map" role="region" aria-label="Map showing the start and end of the {esc(rec["name"])}; no GPX here">
      <div class="map__fallback"></div>
      <div class="map__canvas"></div>
      <p class="map__status" role="status">The map needs JavaScript. The ends of the trail are named below it.</p>
    </div>
    <span class="mapfig__corner mapfig__corner--se" aria-hidden="true"></span>
  </div>
  <figcaption class="mapfig__caption mapfig__caption--sketch">
    <ul class="legend" aria-label="Legend"><li>{common.SWATCH_SKETCH}{esc(legend_text)}</li></ul>
    <div class="sketch-note">
    <p><strong>No GPX here.</strong> {where}</p>
    <p>{reason_html}</p>
    <p class="note">{esc(rule)}</p>
    {actions_html}
    <p>{common.TRAIL_MAP_CREDIT}</p>
    </div>
  </figcaption>
</figure>"""


# Aside: downloads, guides, links --------------------------------------------

def ordered_downloads(items):
    """GPX first, then GeoJSON, then anything else, each keeping its order."""
    rank = {f: i for i, f in enumerate(FORMAT_ORDER)}
    return sorted(items, key=lambda d: rank.get(d["format"], len(rank)))


def download_group(rec, label, swatch, note, items, gid):
    """One group of download buttons. GPX comes first and is the primary button. Each
    link's accessible name starts with the group: "Main track: GPX, 1.1 MB"."""
    buttons = "".join(
        f'<a class="button{" button--primary" if d["format"] == "GPX" else ""}" '
        f'href="/trails/{esc(rec["id"])}/{esc(d["file"])}" download="{esc(d["file"])}">'
        f'{common.ICON_DOWNLOAD}<span class="vh">{esc(label)}: </span>{esc(d["format"])}<span class="vh">,</span> '
        f'<span class="button__meta">{esc(words.fmt_bytes(d["bytes"]))}</span></a>'
        for d in ordered_downloads(items))
    return f"""<li class="download">
  <p class="download__what">{swatch}<strong id="{gid}">{esc(label)}</strong><small>{note if isinstance(note, Markup) else esc(note)}</small></p>
  <div class="download__files">{buttons}</div>
</li>"""


def partial_notice(rec):
    """The notice above the buttons when the track differs from the published length
    by more than 15%: the record's own numbers, then its length_gap_note."""
    if not common.line_differs(rec):
        return ""
    v = rec["verification"]
    diff = v["difference_percent"]
    head = "Partial track" if diff < 0 else "Longer than the published length"
    gap = rec["source"].get("length_gap_note", "")
    return f"""<div class="notice notice--partial">
      <h3>{head}</h3>
      <p>The track in the dataset measures {words.length(v["measured_km"], measured=True)} against a published {words.length(rec["length_km"], mi=rec["derived"]["length_mi"])} ({esc(words.fmt_percent(diff))}).</p>
      {f"<p>{common.rich(gap)}</p>" if gap else ""}
    </div>"""


def downloads_panel(rec):
    downloads = rec["derived"].get("downloads", [])
    if not downloads:
        return ""
    src = rec["source"]
    v = rec.get("verification", {})
    groups = []
    main = [d for d in downloads if d["role"] == "main"]
    if main:
        note = f"{src.get('line_source', '')}"
        if v.get("verified") and "measured_km" in v:
            parts = v.get("parts")
            note = Markup(f"{words.length(v['measured_km'], measured=True)} measured"
                          + esc((f" in {parts} part{'s' if parts != 1 else ''}" if parts else "") + f" · {note}"))
        groups.append(download_group(rec, "Main track", common.SWATCH_ROUTE if common.is_route(rec) else common.SWATCH_LINE,
                                     note, main, "dl-main"))
    alts = [d for d in downloads if d["role"] == "alternates"]
    if alts:
        groups.append(download_group(rec, "Alternates and connectors", common.SWATCH_ALT,
                                     "Served separately by the source", alts, "dl-alt"))
    for i, d in enumerate(d for d in downloads if d["role"] == "extract"):
        key = d["file"][len(rec["id"]) + 1:-len(".geojson")]
        name = EXTRACT_SOURCES.get(key, key)
        # No swatch: extracts are not drawn on the map.
        groups.append(download_group(rec, f"Extract: {name}", "",
                                     "The track as this source serves it, before the sources were combined",
                                     [d], f"dl-x{i}"))
    licence = src.get("licence", "")
    licence_html = esc(words.label(words.LICENCES, licence))
    if licence in words.LICENCE_URLS:
        licence_html = ext_link(words.LICENCE_URLS[licence], words.label(words.LICENCES, licence))
    if "ODbL" in src.get("attribution", "") and licence != "ODbL-1.0":
        licence_html = Markup(f'{licence_html}; OpenStreetMap parts {ext_link(words.LICENCE_URLS["ODbL-1.0"], "ODbL 1.0")}')
    osm_note = ("<p class=\"note\">Tracks from OpenStreetMap need the credit &ldquo;&copy;&nbsp;OpenStreetMap contributors&rdquo; "
                "and stay under the ODbL (share-alike).</p>") if "ODbL" in src.get("attribution", "") + licence else ""
    release = (f'<p class="note"><a href="/trails/{esc(rec["id"])}/release.txt">release.txt</a>: '
               f"the source, licence and date the track files came from.</p>"
               if rec["derived"].get("release") else "")
    return f"""<section class="panel" id="download" aria-labelledby="download-title">
  <h2 class="panel__head" id="download-title">Download GPX and GeoJSON</h2>
  <div class="panel__body">
    {partial_notice(rec)}
    <p class="note">GPX is simplified to 5&nbsp;m for devices. GeoJSON is the full-resolution track as published in this dataset. Neither carries elevation.</p>
    <ul class="downloads">{"".join(groups)}</ul>
    <div class="credit">
      <p class="credit__label" id="credit-label">Credit the source</p>
      <p class="credit__text" id="credit-text">{esc(common.credit_text(src.get("attribution", "")))}</p>
      <div class="credit__row">
        <span class="credit__licence">Licence: {licence_html}</span>
        <button class="button button--quiet" type="button" data-copy="#credit-text" data-copy-status="#credit-done" aria-describedby="credit-label" hidden>Copy credit</button>
      </div>
      <p class="credit__done" id="credit-done" role="status"></p>
      {osm_note}
    </div>
    {release}
  </div>
</section>"""


def guide_card(g, i):
    rows = [fact("Author", g.get("author", ""))]
    if g.get("publisher"):
        rows.append(fact("Publisher", g["publisher"]))
    if g.get("isbn"):
        rows.append(Markup(f'<div><dt>ISBN</dt><dd><span class="nowrap">{esc(g["isbn"])}</span></dd></div>'))
    rows.append(fact("Format", g.get("format", "")))
    if g.get("price"):
        rows.append(fact("Price", g["price"], f"As the page stated it on {g.get('price_checked', '')}"
                         if g.get("price_checked") else ""))
    access = g.get("access", "")
    return f"""<li class="guide">
  <p class="guide__tags"><span class="access access--{esc(access)}">{esc(words.ACCESS.get(access, access))}</span></p>
  <h3 id="guide-{i}">{esc(g.get("title", ""))}</h3>
  {facts(*rows)}
  <a class="button button--link" href="{esc(g.get("url", ""))}" aria-describedby="guide-{i}">Guide page on {esc(host(g.get("url", "")))} {common.ICON_EXTERNAL}</a>
</li>"""


def more_links(rec):
    return [l for l in rec.get("link", []) if isinstance(l, dict) and l.get("url")]


def links_panel(rec):
    """Other pages about this trail, under the buttons at the head of the page and quieter than them."""
    links = more_links(rec)
    # With no official site, the first link stands in for that button and is not repeated here.
    if not official_link(rec):
        links = links[1:]
    if not links:
        return ""
    items = "".join(
        f'<li><a href="{esc(l["url"])}">{esc(l.get("title", ""))} {common.ICON_EXTERNAL}</a>'
        f' <span class="morelinks__by">{esc(l.get("publisher", ""))}</span>'
        + (f'<small>{esc(l["note"])}</small>' if l.get("note") else "") + "</li>"
        for l in links)
    return (f'<section class="morelinks" aria-labelledby="morelinks-title">'
            f'<h2 id="morelinks-title">More about this trail</h2><ul>{items}</ul></section>')


def guides_panel(rec):
    guides = rec.get("guide", [])
    if not guides:
        return ""
    cards = "".join(guide_card(g, i) for i, g in enumerate(guides, 1))
    return f"""<section class="panel" aria-labelledby="guides-title">
  <h2 class="panel__head" id="guides-title">Where to get the route</h2>
  <div class="panel__body">
    <ul class="guides">{cards}</ul>
    <p class="note">Links go to the author&rsquo;s or publisher&rsquo;s own page for each guide.</p>
  </div>
</section>"""


def _is_url(value):
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def links_block(rec):
    """Every link the record holds, each titled with the organisation or person the
    record names for it, with the host name and what the link is as secondary text."""
    src = rec["source"]
    osm = rec.get("osm", {})
    sh = rec.get("shield", {})
    publisher = org_name(src.get("publisher", ""))
    items = {}  # url -> [title, [what it is, ...]]; one entry per URL, titled by its first use

    def add(url, title, what):
        if url in items:
            items[url][1].append(what)
        else:
            items[url] = [title, [what]]

    kind = "route" if common.is_route(rec) else "trail"
    if src.get("publisher_url"):
        add(src["publisher_url"], publisher or host(src["publisher_url"]), f"The publisher's page for the {kind}")
    if osm.get("relation"):
        add(f"https://www.openstreetmap.org/relation/{osm['relation']}",
            f"OpenStreetMap relation {osm['relation']}", f"The {kind} as mapped in OpenStreetMap")
    if src.get("url"):
        what = "Where the included track came from" if common.has_line(rec) else "Where to ask for the track"
        title = "OpenStreetMap" if host(src["url"]).endswith("openstreetmap.org") else (publisher or host(src["url"]))
        add(src["url"], title, what)
    for g in rec.get("guide", []):
        if g.get("url") in items:
            add(g["url"], "", "A guide to the route")
    words_url = rec.get("route", {}).get("creator_words_url")
    if words_url:
        by = rec["route"].get("creator_words_by") or rec["route"].get("creator", "")
        add(words_url, by or host(words_url), "Where the quoted words were read")
    if _is_url(sh.get("logo_source")):
        owner = sh.get("logo_owner") or sh.get("contact") or host(sh["logo_source"])
        # Only a record with a logo file took its logo from that page; without
        # one the page is merely where the holder shows it.
        add(sh["logo_source"], owner, "The page the logo was taken from" if common.shield_url(rec)
            else "The logo holder's site; the logo is not included here")
    add(f"/trails/{rec['id']}/trail.toml", "trail.toml", "The record itself, as data")
    if rec["derived"].get("release"):
        add(f"/trails/{rec['id']}/release.txt", "release.txt", "Source, licence and date of the track files")

    def describe(url, whats):
        text = "; ".join([whats[0]] + [w[:1].lower() + w[1:] for w in whats[1:]])
        return f"{host(url)} · {text}" if _is_url(url) else text

    lis = "".join(f'<li>{ext_link(u, t)}<small>{esc(describe(u, w))}</small></li>' for u, (t, w) in items.items())
    return block("links-title", "Links", Markup(f'<ul class="linklist">{lis}</ul>'))


# Main column ----------------------------------------------------------------

def policy_scale(current):
    items = []
    for p in ("open", "sold", "withheld", "unclear"):
        lab, short, rule = words.POLICIES[p]
        here = ' aria-current="true"' if p == current else ""
        mark = '<span class="policy-scale__here">This route</span>' if p == current else ""
        items.append(f'<li{here}>{common.policy_chip(p)}<span>{esc(short)}. {esc(rule)}</span>{mark}</li>')
    return Markup(f'<ol class="policy-scale" aria-label="Track policies for routes">{"".join(items)}</ol>')


def route_block(rec):
    r = rec["route"]
    p = r.get("line_policy", "")
    rows = [
        fact("Author", r.get("creator", ""), "Who worked the route out (route.creator)"),
        fact("First published", str(r["year"])) if r.get("year") else
        fact("First published", "Not recorded", "No page read states a year"),
        fact("Track policy", words.label(words.POLICIES, p), words.meaning(words.POLICIES, p)),
    ]
    quote = ""
    if r.get("creator_words"):
        by = r.get("creator_words_by") or r.get("creator", "")
        not_creator = ('<span class="tag tag--quiet">Not the author&rsquo;s words</span>'
                       if r.get("creator_words_by") else '<span class="tag tag--quiet">The author&rsquo;s words</span>')
        url = r.get("creator_words_url", "")
        quote = f"""<figure class="quote">
  <blockquote{f' cite="{esc(url)}"' if url else ""}><p>{esc(r["creator_words"])}</p></blockquote>
  <figcaption>
    <p class="quote__who"><strong>{esc(by)}</strong> {not_creator}</p>
    {f'<p>Read on {ext_link(url)}.</p>' if url else ""}
  </figcaption>
</figure>"""
    note = f'<h3 class="block__sub">About the route</h3>{record_text(r["note"])}' if r.get("note") else ""
    return block("route-title", "The route", facts(*rows) + Markup(quote) + policy_scale(p) + Markup(note))


def listing_note(rec):
    """The Listing row's note. A held record is listed but not settled; its wave_note
    (quoted, never paraphrased) says what. Other records show their wave_note as it is."""
    wave = str(rec.get("wave", ""))
    note = rec.get("wave_note", "")
    if wave != "held":
        return note or words.meaning(words.WAVES, wave)
    meaning = words.meaning(words.WAVES, wave)
    if note:
        return Markup(f"{esc(meaning)}. The record&rsquo;s note: &ldquo;{common.rich(note)}&rdquo;")
    return f"{meaning}. The record has no note saying what."


def abbreviation_fact(rec):
    """The abbreviation with the page it was seen on."""
    if not rec.get("short_name"):
        return ""
    url = rec.get("short_name_url", "")
    host = re.sub(r"^www\.", "", urllib.parse.urlsplit(url).hostname or "") or url
    notes = []
    if url:
        notes.append(f'Seen in use at <a href="{esc(url)}">{esc(host)}</a>.')
    return fact("Abbreviation", rec["short_name"], Markup(" ".join(notes)) if notes else "")


def record_block(rec):
    k = common.kind(rec)
    tier = rec.get("tier", "")
    wave = str(rec.get("wave", ""))
    country = words.COUNTRIES.get(rec["country"], rec["country"])
    names = ", ".join(words.region_name(c) for c in rec.get("regions", []) if c != words.ALL_CANADA)
    names_html = f' <span class="muted">({esc(names)})</span>' if names else ""
    codes = Markup(" ".join(f'<a href="{esc(facets.place_path(k))}">{esc(k.split("-", 1)[1] if k != facets.ACROSS_CANADA else facets.ACROSS_CANADA_NAME)}</a>'
                            for k in facets.place_keys(rec)))
    where = Markup(f'{codes}{names_html}, {esc(country)}')
    rows = [
        fact("Kind", words.label(words.KINDS, k), words.meaning(words.KINDS, k)),
        fact("Designation", rec.get("designation", "")),
        fact("Tier", words.label(words.TIERS, tier), words.meaning(words.TIERS, tier)),
        fact("Listing", words.label(words.WAVES, wave), listing_note(rec)),
    ]
    if rec.get("inclusion"):
        inc = rec["inclusion"]
        rows.append(fact("Inclusion", words.label(words.INCLUSION, inc), words.meaning(words.INCLUSION, inc)))
    rows += [
        Markup(f'<div><dt>Where</dt><dd>{where}</dd></div>'),
        Markup(f'<div><dt>Published length</dt><dd>{words.length(rec["length_km"], "inline", rec["derived"]["length_mi"])}'
               f'<small>{esc(rec.get("length_note", ""))}. A check value, not measured from the track.</small></dd></div>'),
        abbreviation_fact(rec),
        fact("Record ID", Markup(code(rec["id"])), "Stable: the directory name, never changed"),
    ]
    return block("record-title", "The record", facts(*rows))


def gauge(diff):
    span = GAUGE_MAX - GAUGE_MIN
    pos = (min(max(diff, GAUGE_MIN), GAUGE_MAX) - GAUGE_MIN) / span * 100
    off = "low" if diff < GAUGE_MIN else "high" if diff > GAUGE_MAX else ""
    inside = abs(diff) <= GAUGE_LIMIT
    side = "shorter than" if diff < 0 else "longer than" if diff > 0 else "the same as"
    label = (f"Measured track is {abs(diff):.1f} percent {side} the published length, "
             f"{'inside' if inside else 'outside'} the 15 percent limit.")
    mark_text = words.fmt_percent(diff) + (" (off the scale)" if off else "")
    ticks = (GAUGE_MIN, -GAUGE_LIMIT, 0, GAUGE_LIMIT, GAUGE_MAX)  # placed by .gauge__tick--N in style.css
    scale = "".join(f'<span class="gauge__tick--{i}">{esc(words.fmt_percent(v).replace(".0%", "%") if v else "0")}</span>'
                    for i, v in enumerate(ticks))
    return Markup(f"""<figure class="gauge{f" gauge--off-{off}" if off else ""}">
  <div class="gauge__track" role="img" aria-label="{esc(label)}">
    <span class="gauge__band"></span>
    <span class="gauge__zero"></span>
    <span class="gauge__mark" style="--pos: {pos:.2f}%" data-label="{esc(mark_text)}"></span>
  </div>
  <div class="gauge__scale" aria-hidden="true">{scale}</div>
  <figcaption class="gauge__legend">
    <span><span class="gauge__key" aria-hidden="true"></span>Within 15% of the published length</span>
    <span><span class="gauge__key gauge__key--out" aria-hidden="true"></span>Beyond 15%: the record must say why</span>
  </figcaption>
</figure>""")


def verification_block(rec):
    v = rec.get("verification", {})
    src = rec["source"]
    gap = src.get("length_gap_note", "")
    if gap and common.line_differs(rec) and rec["derived"].get("downloads"):
        # The download panel's notice carries the note, beside the files it is about.
        gap_html = '<p class="note">Why the lengths differ: see the notice in <a href="#download">Download GPX and GeoJSON</a>.</p>'
    elif gap:
        gap_html = f'<div class="notice"><h3>Why the lengths differ</h3><p>{common.rich(gap)}</p></div>'
    else:
        gap_html = ""
    if v.get("verified") and "measured_km" in v:
        diff = v.get("difference_percent", 0)
        parts = v.get("parts")
        compare = f"""<dl class="compare">
  <div><dt>Published</dt><dd>{words.length(rec["length_km"], "stack", rec["derived"]["length_mi"])}</dd></div>
  <div><dt>Measured</dt><dd>{words.length(v["measured_km"], "stack", measured=True)}<small>geodesic, from the track</small></dd></div>
  <div><dt>Difference</dt><dd>{esc(words.fmt_percent(diff))}<small>measured minus published</small></dd></div>
  <div><dt>Parts</dt><dd>{esc(parts if parts is not None else "Not recorded")}<small>pieces left after joining ends within 100 m</small></dd></div>
</dl>"""
        content = Markup(compare) + gauge(diff) + record_text(v.get("note", "")) + Markup(gap_html)
        extra = Markup(f' <span class="tag">Checked {esc(v.get("date", ""))}</span>') if v.get("date") else ""
        verified_row = facts(fact("Measured", "Yes", "The track was downloaded and measured"))
        return block("verify-title", "Verification", verified_row + content, extra)
    if not common.has_line(rec) and restates_no_line(v.get("note", "")) and not gap:
        return ""  # "No line to measure": the record only restates that there is no track
    rows = facts(fact("Measured", "No", "No track was downloaded and measured"))
    return block("verify-title", "Verification", rows + record_text(v.get("note", "")) + Markup(gap_html))


def _coord(point):
    lat, lon = point.get("lat"), point.get("lon")
    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        return f"At {lat:.5f}, {lon:.5f} (latitude, longitude)"
    return ""


def _fmt_number(value):
    if isinstance(value, float) and value.is_integer():
        return f"{int(value):,}"
    return f"{value:,}" if isinstance(value, (int, float)) else str(value)


def elevation_block(rec):
    """How the elevation figures were computed, the model's credit, and every value."""
    elev = elevation.get(rec)
    if not elev:
        return ""
    src = elev.get("source") or {}
    model = src.get("model", "")
    loop = facets.shape(rec) == "loop"
    direction = elevation.direction_words(elev)
    climb_note = elevation.COMPUTED_NOTE if loop else \
        f"Computed from the track, {direction}. Walking the other way swaps climb and descent."
    low_note = _coord(elev["lowest"])
    if elevation.is_sea_level(elev["lowest"]):
        low_note = ("Sea level. " + low_note).strip()
    coverage = elev.get("coverage")
    coverage_text = (f"{coverage:.3f} ({elevation.coverage_percent(elev)} of the published length)"
                     if isinstance(coverage, (int, float)) else str(coverage))
    starts = elev.get("part_starts_km") or []
    rows = [
        fact("Highest point on the track", words.elevation(elev["highest"]["m"]), _coord(elev["highest"])),
        fact("Lowest point on the track", words.elevation(elev["lowest"]["m"]), low_note),
        fact("Total climb", words.elevation(elev["ascent_m"]), climb_note),
        fact("Total descent", words.elevation(elev["descent_m"]), climb_note),
        fact("Length sampled", words.length(elev["track_km"], "inline", measured=True),
             "The length of the track, not the published length"),
        fact("Published length", words.length(elev["published_km"], "inline")),
        fact("Coverage", coverage_text, elevation.coverage_caveat(elev) or
             "Length sampled divided by the published length"),
        fact("Parts", str(elev.get("parts", "")),
             "Pieces left after joining track ends within 100 m, counted for the elevation sampling. "
             "It can differ from the count under Verification, which was made with another joining rule. "
             "No climb is counted across a gap."),
    ]
    if starts:
        rows.append(fact("Part starts", words.distances(starts),
                         "The distance along the profile where each part after the first begins"))
    if not elevation.show_profile(elev):
        rows.append(fact("Profile", "Not drawn", elevation.parts_caveat(elev)))
    rows += [
        fact("Elevation model", model) if model else "",
        Markup(f'<div><dt>Model page</dt><dd>{ext_link(src["url"])}</dd></div>') if src.get("url") else "",
        fact("Model credit", src.get("attribution", ""), "The credit to show, as the model gives it")
        if src.get("attribution") else "",
        fact("Tiles", f"Zoom {_fmt_number(src['zoom'])}, about {_fmt_number(src['ground_m_per_pixel_at_40n'])} m "
                      "per cell at 40 degrees north")
        if src.get("zoom") is not None and src.get("ground_m_per_pixel_at_40n") is not None else "",
        fact("Sampling", f"Every {_fmt_number(src['sample_spacing_m'])} m along the track")
        if src.get("sample_spacing_m") is not None else "",
        fact("Smoothing", src.get("smoothing", "")) if src.get("smoothing") else "",
        fact("Computed", str(src["computed"])) if src.get("computed") else "",
        fact("Method version", str(src["method_version"])) if src.get("method_version") is not None else "",
    ]
    spacing = src.get("sample_spacing_m")
    sampled = (f"A point was taken every {_fmt_number(spacing)} m along each part of the track, "
               "and its elevation was read from the model. ") if spacing is not None else ""
    smoothing = src.get("smoothing", "")
    method = (f"These figures were computed from the trail&rsquo;s track and {esc(model)}, "
              f"not read from a page about the trail. {esc(sampled)}"
              + (f"Smoothing and counting: {esc(smoothing.rstrip('.').lower()[:1] + smoothing.rstrip('.')[1:])}."
                 if smoothing else ""))
    limits = src.get("limits", "")
    limits_html = (f'<h3 class="block__sub">Limits</h3>{record_text(limits)}') if limits else ""
    content = Markup(f'<p class="record-text">{method}</p>') + facts(*rows) + Markup(limits_html)
    return block("elevation-data-title", "Elevation", content)


def source_block(rec):
    src = rec["source"]
    line = common.has_line(rec)
    status = src.get("status", "")
    licence = src.get("licence", "")
    licence_value = words.label(words.LICENCES, licence)
    licence_html = (ext_link(words.LICENCE_URLS[licence], licence_value) if licence in words.LICENCE_URLS
                    else esc(licence_value))
    source_help = '<small>Where to ask for the track: a layer or relation page</small>' if line else ""

    def keep(value):
        """Rows of a record with no track are left out when they only restate that."""
        return line or not restates_no_line(value)

    rows = [
        fact("Track in this dataset", src.get("line_file"), "The main track file of the record") if line else "",
        fact("Source status", words.label(words.SOURCE_STATUS, status), words.meaning(words.SOURCE_STATUS, status)),
        fact("Publisher", src.get("publisher", "")),
        Markup(f'<div><dt>Publisher&rsquo;s page</dt><dd>{ext_link(src["publisher_url"])}</dd></div>') if src.get("publisher_url") else "",
        Markup(f'<div><dt>Source</dt><dd>{ext_link(src["url"])}{source_help}</dd></div>') if src.get("url") else "",
        fact("Track source", src.get("line_source", "")) if keep(src.get("line_source")) else "",
        fact("Format", src.get("format", "")) if keep(src.get("format")) else "",
        fact("Main track", src.get("mainline", ""), "How the main track is told apart from alternates, connectors and side trails"),
        fact("Coordinates", src.get("crs", ""), "What the source stores; published files are longitude/latitude (EPSG:4326)") if line else "",
        Markup(f'<div><dt>Licence</dt><dd>{licence_html}</dd></div>'),
        fact("Credit", common.credit_text(src.get("attribution", "")), "The credit line to show, as the source asks")
        if keep(src.get("attribution")) else "",
        fact("May be passed on", yes_no(src.get("redistributable")),
             "The source's terms allow its track to be passed on" if src.get("redistributable") else
             "The source's terms do not allow its track to be passed on") if line else "",
        fact("OpenStreetMap only", yes_no(src.get("osm_only")),
             "OpenStreetMap is the only source of the included track" if src.get("osm_only") else "") if line else "",
        fact("Source checked", src.get("source_checked", "")),
        fact("Newer release?", src["discovery"], "How to tell whether the source has a newer release") if src.get("discovery") else "",
    ]
    if src.get("decision") or src.get("decision_text"):
        rows.append(fact("Decision", src.get("decision_text", "") or words.DECISIONS.get(src.get("decision", ""), src.get("decision", ""))))
    licence_text = (f'<h3 class="block__sub">What the source says</h3>{record_text(src["licence_text"])}'
                    '<p class="note">With the page it was read on. Not legal advice.</p>') if src.get("licence_text") else ""
    return block("source-title", "Source and licence", facts(*rows) + Markup(licence_text))


def osm_block(rec):
    osm = rec.get("osm", {})
    rel = osm.get("relation", 0)
    if rel:
        value = Markup(f'<div><dt>Relation</dt><dd>{ext_link(f"https://www.openstreetmap.org/relation/{rel}", str(rel))}</dd></div>')
    elif common.has_line(rec):
        value = fact("Relation", "None recorded", "No relation found, or not searched")
    else:
        value = ""  # no line and no relation: nothing to say beyond the note
    return block("osm-title", "OpenStreetMap", facts(value, fact("Note", osm.get("note", ""))))


def logo_block(rec):
    sh = rec.get("shield", {})
    status = sh.get("status", "")
    if not common.shield_url(rec):
        # No logo file: one line, the status and the record's note.
        lead = {"no-logo-exists": "No logo", "logo-not-found": "Logo not found",
                "use-real-logo": "Logo not included"}.get(status, "No logo file")
        note = sh.get("note", "")
        # "use-real-logo" without a file: the trail has a logo, but no copy is here.
        why = ""
        if status == "use-real-logo":
            holder = sh.get("logo_owner") or sh.get("contact") or ""
            why = (f" The trail has a logo{', held by ' + str(esc(holder)) if holder else ''}, "
                   "but no copy of it is in this dataset.")
        return block("logo-title", "Logo", Markup(
            f'<p class="record-text"><strong>{esc(lead)}.</strong>{why}{" " + common.rich(note) if note else ""}</p>'))
    rows = [
        fact("Status", words.label(words.SHIELD_STATUS, status), words.meaning(words.SHIELD_STATUS, status)),
        fact("Holder", sh.get("logo_owner", "")) if sh.get("logo_owner") else "",
        fact("Contact", sh.get("contact", "")) if sh.get("contact") and sh.get("contact") != sh.get("logo_owner") else "",
        Markup(f'<div><dt>Taken from</dt><dd>{ext_link(sh["logo_source"])}</dd></div>') if _is_url(sh.get("logo_source"))
        else fact("Taken from", sh.get("logo_source") or "Not recorded"),
        fact("File", sh.get("logo_file", "")),
        fact("Note", sh.get("note", "")),
    ]
    federal = ("<p>Some logos are official emblems of United States National Scenic or Historic Trails. "
               "Those emblems are federal insignia; their use here is for identification only.</p>"
               if rec.get("tier") == "national" or "National Historic Trail" in rec.get("designation", "") else "")
    notice = f"""<div class="notice">
  <h3>Shown only to identify the trail</h3>
  <p>This logo belongs to {esc(sh.get("logo_owner", "its holder"))}. It is not covered by this dataset&rsquo;s licences, and no right to use it for any other purpose is given or implied.</p>
  {federal}
  <p>A holder who wants a logo removed, replaced or credited differently can ask; see <a href="/logos/">Logos</a>.</p>
</div>"""
    return block("logo-title", "Logo", Markup(notice) + facts(*rows))


def correction_block(rec, site):
    parts = []
    if common.is_route(rec):
        parts.append(f"""<div class="notice">
  <h3>If you made this route</h3>
  <p>The author of a route can ask for its record to be corrected or removed, and the record will be corrected or removed. Say which route: {code(rec["id"])}. See <a href="/about/">About</a>.</p>
</div>""")
    if site.is_github:
        report = esc(site.correction_url(rec["id"], rec.get("name", "")))
        edit = esc(site.edit_url(rec["id"]))
        history = esc(site.history_url(rec["id"]))
        parts.append(f"""<p class="prose">This record is a text file anyone can correct. Please say where a correction can be checked: a source page, a map, or a measured track.</p>
<ul class="linklist">
  <li><a href="{report}">Report a problem</a><small>No git needed: a short form, with this record ({code(rec["id"])}) filled in</small></li>
  <li><a href="{edit}">Edit this record</a><small>The record file (trail.toml) on GitHub</small></li>
  <li><a href="{history}">History</a><small>Changes to this record on GitHub</small></li>
</ul>""")
    elif site.repo_url:
        parts.append(f"""<p class="prose">Found an error? Report it in the <a href="{esc(site.repo_url)}">source repository</a>, with the record ID ({code(rec["id"])}), what is wrong, and where the correct information can be checked: a source page, a map, or a measured track.</p>""")
    if not parts:
        return ""
    return block("correct-title", "Corrections", Markup("".join(parts)))


def hike_sources_block(rec):
    """Where the hiker facts at the top of the page were read."""
    h = hike.table(rec)
    if not h:
        return ""
    items = ""
    for src in hike.sources(rec):
        url = src.get("url", "")
        who = src.get("publisher") or (host(url) if url else "Source")
        facts_ = [words.HIKE_FACTS.get(f, f) for f in src.get("facts", [])]
        what = ("For " + words.join_names(facts_)) if facts_ else ""
        link = ext_link(url, who) if url else esc(who)
        detail = " · ".join(x for x in (host(url) if url else "", what) if x)
        items += f"<li>{link}{f'<small>{esc(detail)}</small>' if detail else ''}</li>"
    body = f'<ul class="linklist">{items}</ul>' if items else \
        '<p class="record-text">The record names no page for these facts.</p>'
    checked = f'<p class="note">Checked {esc(h["checked"])}.</p>' if h.get("checked") else ""
    return block("hike-title", "Where the hiking facts come from", Markup(body + checked))


def about_data(rec, site):
    """Everything about where the page's data comes from: collapsed, below the hiker's part."""
    blocks = ((route_block(rec) if common.is_route(rec) else "") + record_block(rec) + hike_sources_block(rec)
              + verification_block(rec) + elevation_block(rec) + source_block(rec) + osm_block(rec) + logo_block(rec)
              + links_block(rec) + correction_block(rec, site) + raw_record(rec))
    return f"""<details class="about-data" id="about-data">
  <summary><h2 id="about-data-title">About this data</h2>
  <span class="about-data__hint">Where the track and the facts come from, licence, checks, the logo, corrections, and every field of the record</span></summary>
  <div class="about-data__body detail__main">
    {blocks}
  </div>
</details>"""


def page_foot(rec, site):
    """The plain lines under the hiker's part: not for navigation, and how to report a problem."""
    report = ""
    if site.repo_url:
        report = (f' Something wrong on this page? '
                  f'<a href="{esc(site.correction_url(rec["id"], rec.get("name", "")))}">Report a problem</a>.')
    return (f'<p class="page-foot">Not for navigation: check the trail&rsquo;s own maps '
            f'and current conditions before you go.{report}</p>')


def flatten(obj, prefix=""):
    """(field, value) for every leaf of a record: "source.licence", "guide[0].title", "regions[1]"."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flatten(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from flatten(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def raw_value(value):
    """A value as the record stores it: true/false, numbers as written, "" for an empty string."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value if value else '""'
    return str(value)


def raw_record(rec):
    """Every field of the record with its exact value, as the last block of the page."""
    fields = {k: v for k, v in rec.items() if k != "derived"}
    rows = "".join(f'<tr><th scope="row"><code>{esc(field)}</code></th><td>{esc(raw_value(value))}</td></tr>'
                   for field, value in flatten(fields))
    return Markup(f"""<details class="rawrecord">
  <summary>Every field of the record, with its exact value</summary>
  <p class="note">As stored in <a href="/trails/{esc(rec["id"])}/trail.toml">trail.toml</a>.
  The <a href="/data/schema/">record schema</a> says what each field means.</p>
  <div class="table-wrap"><table class="rawrecord__table">
    <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
</details>""")


# The page -------------------------------------------------------------------

def description(rec):
    one = hike.one_line(rec)
    if one:
        text = one
    else:
        km = words.fmt_km(rec["length_km"])
        mi = words.fmt_int(rec["derived"]["length_mi"])
        text = f"{rec['name']}: a {kind_word(rec)} of {mi} mi ({km} km) {place_text(rec)}."
    text += (" Download its GPX here." if common.has_line(rec)
             else " Where to get its GPX.")
    return text if len(text) <= 300 else text[:297].rsplit(" ", 1)[0] + "…"


# Ways onward ------------------------------------------------------------------

ONWARD_MAX = 6


def _onward_list(title, recs, more_href, more_text, heading_id):
    items = "".join(
        f'<li><a href="{esc(common.trail_path(r))}">{common.name(r)}</a>'
        f'<span class="onward__len">{words.length(r["length_km"], "short", r["derived"]["length_mi"])}'
        f'{" · Route" if common.is_route(r) else ""}</span></li>'
        for r in recs[:ONWARD_MAX])
    more = (f'<p class="onward__more"><a href="{esc(more_href)}">{esc(more_text)}</a></p>'
            if more_href else "")
    return (f'<section class="onward__part" aria-labelledby="{heading_id}">'
            f'<h3 id="{heading_id}">{esc(title)}</h3><ul class="onward__list">{items}</ul>{more}</section>')


def onward(rec, records):
    """Ways onward at the foot of the page: other trails in the same state or province
    (up to three of them), and for a route, other routes by the same author."""
    if not records:
        return ""
    others = [r for r in records if r["id"] != rec["id"]]
    parts = []
    for i, key in enumerate(k for k in facets.place_keys(rec) if k != facets.ACROSS_CANADA):
        if i >= 3:
            break
        here = sorted((r for r in others if key in facets.place_keys(r)), key=lambda r: -r["length_km"])
        if not here:
            continue
        name = facets.place_name(key)
        more = (facets.place_path(key), f"All {len(here) + 1} trails in {name}") if len(here) > ONWARD_MAX else \
            (facets.place_path(key), f"{name} on the map")
        parts.append(_onward_list(f"More in {name}", here, more[0], more[1], f"onward-{key.lower()}"))
    who = facets.author(rec)
    if who:
        same = sorted((r for r in others if facets.author(r) == who), key=lambda r: -r["length_km"])
        if same:
            parts.append(_onward_list(f"More routes by {who}", same, "/routes/", "Every route", "onward-author"))
    if not parts:
        return ""
    return (f'<nav class="onward" aria-labelledby="onward-title"><h2 id="onward-title">Where next</h2>'
            f'<div class="onward__grid">{"".join(parts)}</div></nav>')


def render(rec, site, records=None):
    """Return (title, description, body HTML, needs_map) for one trail.
    records: every trail, for the ways onward at the foot (left out when None)."""
    has_track = common.has_line(rec)
    sketch = hike.sketch_points(rec) if not has_track else []
    has_map = has_track or bool(sketch)
    aside = downloads_panel(rec) + guides_panel(rec)
    aside_html = (f'<aside class="detail__aside" aria-label="{"Downloads" if has_track else "Where to get the route"}">'
                  f'{aside}</aside>') if aside else ""
    profile = elevation_figure(rec)
    body = f"""{page_head(rec)}
<div class="container detail{"" if aside else " detail--no-aside"}{"" if has_map else " detail--no-map"}{" detail--with-profile" if profile else ""}">
  {glance(rec)}
  {map_figure(rec) if has_track else sketch_figure(rec) if sketch else empty_frame(rec)}
  {profile}
  {aside_html}
</div>
<div class="container trail-more">
  {onward(rec, records)}
  {page_foot(rec, site)}
  {about_data(rec, site)}
</div>"""
    return rec["name"], description(rec), body, has_map


def release_path(repo_root, rec):
    path = os.path.join(repo_root, rec["id"], "release.txt")
    return path if os.path.isfile(path) else ""
