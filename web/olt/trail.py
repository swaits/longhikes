"""One page per record: /trails/<id>/.

The main sections say what the record says, in plain words. Every field of
the record, with its exact value, is in the table at the end of the page
(raw_record); the main flow carries no coded values.
"""
import os
import re
import urllib.parse

from . import common, words
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
    """True for record values that only say there is no line ("none (no line included)")."""
    text = str(value or "").strip().lower()
    return text.startswith(("none (no line", "no line included", "no line to measure"))


def region_names(rec):
    """The regions for the title block, each linked to its region page."""
    regions = rec.get("regions", [])
    if len(regions) <= 3:
        parts = []
        for code_ in regions:
            if code_ == words.ALL_CANADA:
                href = "/regions/#canada-wide"
            else:
                href = f"/regions/{words.region_key(code_, rec['country']).lower()}/"
            parts.append(f'<a href="{esc(href)}">{esc(words.region_name(code_))}</a>')
        return Markup(", ".join(parts))
    return common.regions_html(rec, linked=True)


_ORG_CUT = re.compile(r", who |, with | publishes |; (?=[a-z])| \((?=[a-z])| \((?=[^)]*geometry)")


def org_name(text):
    """The organisation or person a record names, without the record's own remarks:
    "Green Mountain Club (publishes the trail); its ArcGIS ..." -> "Green Mountain Club"."""
    name = _ORG_CUT.split(text or "", maxsplit=1)[0].strip()
    return name[:1].upper() + name[1:]


# Page head ------------------------------------------------------------------

def page_head(rec):
    route = common.is_route(rec)
    country = words.COUNTRIES.get(rec["country"], rec["country"])
    crumbs = [f'<li><a href="/">Trails</a></li>',
              f'<li><a href="/?country={esc(rec["country"])}">{esc(country)}</a></li>']
    if route:
        crumbs.append('<li><a href="/?kind=route">Person-defined routes</a></li>')
    crumbs.append(f'<li aria-current="page">{common.name(rec)}</li>')
    if route:
        r = rec["route"]
        lead = "By " + r["creator"] + (f", {r['year']}" if r.get("year") else "")
    else:
        lead = rec.get("designation", "")
    sub = f'{esc(lead)} &middot; {region_names(rec)}, {esc(country)}'
    has_plate = bool(common.shield_url(rec))
    plate = common.plate(rec, size="lg", link=True, eager=True) if has_plate else ""
    return f"""<div class="page-head">
  <div class="container">
    <nav class="breadcrumb" aria-label="Breadcrumb"><ol>{"".join(crumbs)}</ol></nav>
    <header class="titleblock{" titleblock--with-plate" if has_plate else ""}">
      {plate}
      <div class="titleblock__text">
        <p class="cluster">{common.tags(rec)}</p>
        <h1>{common.name(rec)} <span class="titleblock__abbr">{esc(rec.get("short_name", ""))}</span></h1>
        <p class="titleblock__sub">{sub}</p>
      </div>
    </header>
    {tally(rec)}
  </div>
</div>"""


def tally(rec):
    v = rec.get("verification", {})
    note = rec.get("length_note", "")
    if note.replace(",", "") in (f"{rec['length_km']} km", f"{rec['length_km']} km published"):
        note = ""  # the note only repeats the number
    items = [("Published length", words.length(rec["length_km"], "stack", rec["derived"]["length_mi"]), note)]
    if v.get("verified") and "measured_km" in v:
        diff = v.get("difference_percent", 0)
        items.append(("Measured line", words.length(v["measured_km"], "stack", measured=True),
                      f"{words.fmt_percent(diff)} against published"))
    else:
        items.append(("Measured line", Markup('<span class="tally__none">Not measured</span>'),
                      "No line was downloaded and measured"))
    if common.has_line(rec):
        text = "In the dataset, partial" if common.line_short(rec) else "In the dataset"
        link = Markup(f'<a href="#download">{esc(text)}</a>') if rec["derived"].get("downloads") else text
        items.append(("Line", link, "Licence: " + common.licence_label(rec)))
    else:
        items.append(("Line", "Record only", "The reason is given below"))
    if common.is_route(rec):
        p = common.policy(rec)
        items.append(("Line policy", words.label(words.POLICIES, p), words.meaning(words.POLICIES, p)))
    else:
        t = rec.get("tier", "")
        items.append(("Tier", words.label(words.TIERS, t), words.meaning(words.TIERS, t)))
    cells = "".join(f'<div><dt>{esc(a)}</dt><dd>{esc(b)}{f"<small>{esc(c)}</small>" if c else ""}</dd></div>'
                    for a, b, c in items)
    return Markup(f'<dl class="tally tally--trail">{cells}</dl>')


# Map or empty frame ---------------------------------------------------------

def map_figure(rec):
    src = rec["source"]
    has_alt = "alternates" in rec["derived"]["files"]
    route = common.is_route(rec)
    legend = f'<li>{common.SWATCH_ROUTE if route else common.SWATCH_LINE}Main line</li>'
    if has_alt:
        legend += f"<li>{common.SWATCH_ALT}Alternates and connectors</li>"
    bbox = rec["derived"].get("map_bbox") or rec["derived"].get("bbox")
    bbox_attr = f' data-bbox="{",".join(str(v) for v in bbox)}"' if bbox else ""
    credit = common.sentence(common.credit_text(src.get("attribution", "")))
    return f"""<figure class="mapfig mapfig--detail detail__map" data-map="trail" data-src="/trails/{esc(rec["id"])}/map.json" data-route="{"yes" if route else "no"}"{bbox_attr}>
  <div class="mapfig__frame">
    <span class="mapfig__corner mapfig__corner--nw" aria-hidden="true"></span>
    <div class="map" role="region" aria-label="Map of the {esc(rec["name"])}">
      <div class="map__fallback"></div>
      <div class="map__canvas"></div>
      <p class="map__status" role="status">The map needs JavaScript. Download the line from this page.</p>
    </div>
    <span class="mapfig__corner mapfig__corner--se" aria-hidden="true"></span>
  </div>
  <figcaption class="mapfig__caption">
    <ul class="legend" aria-label="Legend">{legend}</ul>
    <p>Line: {esc(src.get("line_source", ""))}, read {esc(src.get("source_checked", ""))}, drawn simplified to 30&nbsp;m. Credit: {esc(credit)} Base map: OpenFreeMap, &copy;&nbsp;OpenMapTiles, data &copy;&nbsp;OpenStreetMap contributors.</p>
  </figcaption>
</figure>"""


def free_guides(rec):
    return [g for g in rec.get("guide", []) if g.get("access") == "free"]


def empty_frame(rec):
    src = rec["source"]
    reason = src.get("line_absent_reason", "")
    actions = []
    if common.is_route(rec):
        p = common.policy(rec)
        titles = {
            "open": "Get the line from the creator",
            "sold": "The line is sold as a guide",
            "withheld": "The creator does not publish a line",
            "unclear": "Whether the line may be shared is not settled",
        }
        title = titles.get(p, "No line in this dataset")
        rule = words.POLICIES.get(p, ("", "", ""))[2]
        if p == "open" and free_guides(rec):
            g = free_guides(rec)[0]
            actions.append(f'<a class="button button--primary" href="{esc(g["url"])}">'
                           f'{esc(g["title"])} {common.ICON_EXTERNAL}</a>')
        if not actions:
            actions.append('<a class="button button--link" href="#guides-title">See where to get the route</a>')
        elif len(rec.get("guide", [])) > 1:
            actions.append('<a class="button button--link" href="#guides-title">All guides</a>')
    else:
        title = "No line in this dataset"
        reason = common.absent_reason_short(rec)
        rule = "A trail may be listed as a record only, with no line, when no line for it may be shared. The record says why."
        if src.get("publisher_url"):
            actions.append(f'<a class="button button--link" href="{esc(src["publisher_url"])}">'
                           f'Publisher&rsquo;s page {common.ICON_EXTERNAL}</a>')
        elif src.get("url"):
            actions.append(f'<a class="button button--link" href="{esc(src["url"])}">'
                           f'The source {common.ICON_EXTERNAL}</a>')
    actions_html = f'<p class="cluster">{"".join(actions)}</p>' if actions else ""
    return f"""<figure class="mapfig mapfig--empty detail__map" aria-labelledby="noline-title">
  <div class="mapfig__frame">
    <span class="mapfig__corner mapfig__corner--nw" aria-hidden="true">No line in this dataset</span>
    <div class="map map--empty">
      <div class="map__message">
        <p class="kicker">Record only</p>
        <h2 id="noline-title">{esc(title)}</h2>
        <p>{common.rich(reason)}</p>
        <p class="note">{esc(rule)}</p>
        {actions_html}
      </div>
    </div>
    <span class="mapfig__corner mapfig__corner--se" aria-hidden="true">Nothing drawn</span>
  </div>
  <figcaption class="mapfig__caption"><p>No map is drawn: the dataset holds no line for this {"route" if common.is_route(rec) else "trail"}, and does not guess one.</p></figcaption>
</figure>"""


# Aside: downloads, guides, links --------------------------------------------

def ordered_downloads(items):
    """GPX first, then GeoJSON, then anything else, each keeping its order."""
    rank = {f: i for i, f in enumerate(FORMAT_ORDER)}
    return sorted(items, key=lambda d: rank.get(d["format"], len(rank)))


def download_group(rec, label, swatch, note, items, gid):
    """One group of download buttons. GPX comes first and is the primary button. Each
    link's accessible name starts with the group: "Main line: GPX, 1.1 MB"."""
    buttons = "".join(
        f'<a class="button{" button--primary" if d["format"] == "GPX" else ""}" '
        f'href="/trails/{esc(rec["id"])}/{esc(d["file"])}" download="{esc(d["file"])}">'
        f'{common.ICON_DOWNLOAD}<span class="vh">{esc(label)}: </span>{esc(d["format"])}<span class="vh">,</span> '
        f'<span class="button__meta">{esc(words.fmt_bytes(d["bytes"]))}</span></a>'
        for d in ordered_downloads(items))
    return f"""<li class="download">
  <p class="download__what">{swatch}<strong id="{gid}">{esc(label)}</strong><small>{esc(note)}</small></p>
  <div class="download__files">{buttons}</div>
</li>"""


def partial_notice(rec):
    """The notice above the buttons when the line differs from the published length
    by more than 15%: the record's own numbers, then its length_gap_note."""
    if not common.line_differs(rec):
        return ""
    v = rec["verification"]
    diff = v["difference_percent"]
    head = "Partial line" if diff < 0 else "Longer than the published length"
    gap = rec["source"].get("length_gap_note", "")
    return f"""<div class="notice notice--partial">
      <h3>{head}</h3>
      <p>The line in the dataset measures {esc(words.fmt_km1(v["measured_km"]))}&nbsp;km against a published {esc(words.fmt_km(rec["length_km"]))}&nbsp;km ({esc(words.fmt_percent(diff))}).</p>
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
            note = (f"{words.fmt_km1(v['measured_km'])} km measured"
                    + (f" in {parts} part{'s' if parts != 1 else ''}" if parts else "") + f" · {note}")
        groups.append(download_group(rec, "Main line", common.SWATCH_ROUTE if common.is_route(rec) else common.SWATCH_LINE,
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
                                     "The line as this source serves it, before the sources were combined",
                                     [d], f"dl-x{i}"))
    licence = src.get("licence", "")
    licence_html = esc(words.label(words.LICENCES, licence))
    if licence in words.LICENCE_URLS:
        licence_html = ext_link(words.LICENCE_URLS[licence], words.label(words.LICENCES, licence))
    if "ODbL" in src.get("attribution", "") and licence != "ODbL-1.0":
        licence_html = Markup(f'{licence_html}; OpenStreetMap parts {ext_link(words.LICENCE_URLS["ODbL-1.0"], "ODbL 1.0")}')
    osm_note = ("<p class=\"note\">Lines from OpenStreetMap need the credit &ldquo;&copy;&nbsp;OpenStreetMap contributors&rdquo; "
                "and stay under the ODbL (share-alike).</p>") if "ODbL" in src.get("attribution", "") + licence else ""
    release = (f'<p class="note"><a href="/trails/{esc(rec["id"])}/release.txt">release.txt</a>: '
               f"the source, licence and date the line files came from.</p>"
               if rec["derived"].get("release") else "")
    return f"""<section class="panel" id="download" aria-labelledby="download-title">
  <h2 class="panel__head" id="download-title">Download the line</h2>
  <div class="panel__body">
    {partial_notice(rec)}
    <p class="note">GPX is simplified to 5&nbsp;m for devices. GeoJSON is the full-resolution line as published in this dataset. Neither carries elevation.</p>
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


def guides_panel(rec):
    guides = rec.get("guide", [])
    if not guides:
        return ""
    cards = "".join(guide_card(g, i) for i, g in enumerate(guides, 1))
    return f"""<section class="panel" aria-labelledby="guides-title">
  <h2 class="panel__head" id="guides-title">Where to get the route</h2>
  <div class="panel__body">
    <ul class="guides">{cards}</ul>
    <p class="note">Links go to the creator&rsquo;s or publisher&rsquo;s own page for each guide.</p>
  </div>
</section>"""


def _is_url(value):
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def links_panel(rec):
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
        what = "Where the included line came from" if common.has_line(rec) else "Where to ask for the line"
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
        add(sh["logo_source"], owner, "The page the logo was taken from")
    add(f"/trails/{rec['id']}/trail.toml", "trail.toml", "The record itself, as data")
    if rec["derived"].get("release"):
        add(f"/trails/{rec['id']}/release.txt", "release.txt", "Source, licence and date of the line files")

    def describe(url, whats):
        text = "; ".join([whats[0]] + [w[:1].lower() + w[1:] for w in whats[1:]])
        return f"{host(url)} · {text}" if _is_url(url) else text

    lis = "".join(f'<li>{ext_link(u, t)}<small>{esc(describe(u, w))}</small></li>' for u, (t, w) in items.items())
    return f"""<section class="panel" aria-labelledby="links-title">
  <h2 class="panel__head" id="links-title">Links</h2>
  <div class="panel__body"><ul class="linklist">{lis}</ul></div>
</section>"""


# Main column ----------------------------------------------------------------

def policy_scale(current):
    items = []
    for p in ("open", "sold", "withheld", "unclear"):
        lab, short, rule = words.POLICIES[p]
        here = ' aria-current="true"' if p == current else ""
        mark = '<span class="policy-scale__here">This route</span>' if p == current else ""
        items.append(f'<li{here}>{common.policy_chip(p)}<span>{esc(short)}. {esc(rule)}</span>{mark}</li>')
    return Markup(f'<ol class="policy-scale" aria-label="Line policies for person-defined routes">{"".join(items)}</ol>')


def route_block(rec):
    r = rec["route"]
    p = r.get("line_policy", "")
    rows = [
        fact("Creator", r.get("creator", "")),
        fact("First published", str(r["year"])) if r.get("year") else
        fact("First published", "Not recorded", "No page read states a year"),
        fact("Line policy", words.label(words.POLICIES, p), words.meaning(words.POLICIES, p)),
    ]
    quote = ""
    if r.get("creator_words"):
        by = r.get("creator_words_by") or r.get("creator", "")
        not_creator = ('<span class="tag tag--quiet">Not the creator&rsquo;s words</span>'
                       if r.get("creator_words_by") else '<span class="tag tag--quiet">The creator&rsquo;s words</span>')
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


def record_block(rec):
    k = common.kind(rec)
    tier = rec.get("tier", "")
    wave = str(rec.get("wave", ""))
    country = words.COUNTRIES.get(rec["country"], rec["country"])
    names = ", ".join(words.region_name(c) for c in rec.get("regions", []) if c != words.ALL_CANADA)
    names_html = f' <span class="muted">({esc(names)})</span>' if names else ""
    where = Markup(f'{common.regions_html(rec, linked=True)}{names_html}, {esc(country)}')
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
               f'<small>{esc(rec.get("length_note", ""))}. A check value, not measured from the line.</small></dd></div>'),
        fact("Short name", rec.get("short_name", "")),
        fact("Record ID", Markup(code(rec["id"])), "Stable: the directory name, never changed"),
    ]
    return block("record-title", "The record", facts(*rows))


def gauge(diff):
    span = GAUGE_MAX - GAUGE_MIN
    pos = (min(max(diff, GAUGE_MIN), GAUGE_MAX) - GAUGE_MIN) / span * 100
    off = "low" if diff < GAUGE_MIN else "high" if diff > GAUGE_MAX else ""
    inside = abs(diff) <= GAUGE_LIMIT
    side = "shorter than" if diff < 0 else "longer than" if diff > 0 else "the same as"
    label = (f"Measured line is {abs(diff):.1f} percent {side} the published length, "
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
        gap_html = '<p class="note">Why the lengths differ: see the notice in <a href="#download">Download the line</a>.</p>'
    elif gap:
        gap_html = f'<div class="notice"><h3>Why the lengths differ</h3><p>{common.rich(gap)}</p></div>'
    else:
        gap_html = ""
    if v.get("verified") and "measured_km" in v:
        diff = v.get("difference_percent", 0)
        parts = v.get("parts")
        compare = f"""<dl class="compare">
  <div><dt>Published</dt><dd>{words.length(rec["length_km"], "stack", rec["derived"]["length_mi"])}</dd></div>
  <div><dt>Measured</dt><dd>{words.length(v["measured_km"], "stack", measured=True)}<small>geodesic, from the line</small></dd></div>
  <div><dt>Difference</dt><dd>{esc(words.fmt_percent(diff))}<small>measured minus published</small></dd></div>
  <div><dt>Parts</dt><dd>{esc(parts if parts is not None else "Not recorded")}<small>pieces left after joining ends within 100 m</small></dd></div>
</dl>"""
        content = Markup(compare) + gauge(diff) + record_text(v.get("note", "")) + Markup(gap_html)
        extra = Markup(f' <span class="tag">Checked {esc(v.get("date", ""))}</span>') if v.get("date") else ""
        verified_row = facts(fact("Measured", "Yes", "The line was downloaded and measured"))
        return block("verify-title", "Verification", verified_row + content, extra)
    if not common.has_line(rec) and restates_no_line(v.get("note", "")) and not gap:
        return ""  # "No line to measure": the record only restates that there is no line
    rows = facts(fact("Measured", "No", "No line was downloaded and measured"))
    return block("verify-title", "Verification", rows + record_text(v.get("note", "")) + Markup(gap_html))


def source_block(rec):
    src = rec["source"]
    line = common.has_line(rec)
    status = src.get("status", "")
    licence = src.get("licence", "")
    licence_value = words.label(words.LICENCES, licence)
    licence_html = (ext_link(words.LICENCE_URLS[licence], licence_value) if licence in words.LICENCE_URLS
                    else esc(licence_value))
    source_help = '<small>Where to ask for the line: a layer or relation page</small>' if line else ""

    def keep(value):
        """Rows of a record with no line are left out when they only restate that."""
        return line or not restates_no_line(value)

    rows = [
        fact("Line in this dataset", src.get("line_file"), "The main line file of the record") if line else "",
        fact("Source status", words.label(words.SOURCE_STATUS, status), words.meaning(words.SOURCE_STATUS, status)),
        fact("Publisher", src.get("publisher", "")),
        Markup(f'<div><dt>Publisher&rsquo;s page</dt><dd>{ext_link(src["publisher_url"])}</dd></div>') if src.get("publisher_url") else "",
        Markup(f'<div><dt>Source</dt><dd>{ext_link(src["url"])}{source_help}</dd></div>') if src.get("url") else "",
        fact("Line source", src.get("line_source", "")) if keep(src.get("line_source")) else "",
        fact("Format", src.get("format", "")) if keep(src.get("format")) else "",
        fact("Main line", src.get("mainline", ""), "How the main line is told apart from alternates, connectors and side trails"),
        fact("Coordinates", src.get("crs", ""), "What the source stores; published files are longitude/latitude (EPSG:4326)") if line else "",
        Markup(f'<div><dt>Licence</dt><dd>{licence_html}</dd></div>'),
        fact("Credit", common.credit_text(src.get("attribution", "")), "The credit line to show, as the source asks")
        if keep(src.get("attribution")) else "",
        fact("May be passed on", yes_no(src.get("redistributable")),
             "The source's terms allow its line to be passed on" if src.get("redistributable") else
             "The source's terms do not allow its line to be passed on") if line else "",
        fact("OpenStreetMap only", yes_no(src.get("osm_only")),
             "OpenStreetMap is the only source of the included line" if src.get("osm_only") else "") if line else "",
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
        return block("logo-title", "Logo", Markup(
            f'<p class="record-text"><strong>{esc(lead)}.</strong>{" " + common.rich(note) if note else ""}</p>'))
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
  <p>A route&rsquo;s creator can ask for its record to be corrected or removed, and the record will be corrected or removed. Say which route: {code(rec["id"])}. See <a href="/about/">About</a>.</p>
</div>""")
    if site.issues_url:
        parts.append(f"""<p class="prose">Found an error? <a href="{esc(site.issues_url)}">Open an issue</a> with the record ID ({code(rec["id"])}), what is wrong, and where the correct information can be checked: a source page, a map, or a measured line.</p>""")
    if not parts:
        return ""
    return block("correct-title", "Corrections", Markup("".join(parts)))


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
    km = words.fmt_km(rec["length_km"])
    mi = words.fmt_int(rec["derived"]["length_mi"])
    where = ", ".join(words.region_name(c) for c in rec.get("regions", [])[:3])
    if len(rec.get("regions", [])) > 3:
        where += " and more"
    kind = "person-defined route" if common.is_route(rec) else "long trail"
    text = f"{rec['name']}: a {km} km ({mi} mi) {kind} in {where}. "
    if common.has_line(rec):
        text += "Download its line as GeoJSON or GPX, with the source, licence and credit."
    else:
        text += "Record only: " + common.absent_reason_short(rec)
    return text if len(text) <= 300 else text[:297].rsplit(" ", 1)[0] + "…"


def render(rec, site):
    """Return (title, description, body HTML, needs_map) for one record."""
    has_map = common.has_line(rec)
    aside = downloads_panel(rec) + guides_panel(rec) + links_panel(rec)
    main = (route_block(rec) if common.is_route(rec) else "") + record_block(rec) + verification_block(rec) \
        + source_block(rec) + osm_block(rec) + logo_block(rec) + correction_block(rec, site) + raw_record(rec)
    body = f"""{page_head(rec)}
<div class="container detail">
  {map_figure(rec) if has_map else empty_frame(rec)}
  <aside class="detail__aside" aria-label="{"Downloads and links" if has_map else "Where to get it, and links"}">
    {aside}
  </aside>
  <div class="detail__main">
    {main}
  </div>
</div>"""
    return rec["name"], description(rec), body, has_map


def release_path(repo_root, rec):
    path = os.path.join(repo_root, rec["id"], "release.txt")
    return path if os.path.isfile(path) else ""
