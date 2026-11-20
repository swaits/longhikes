"""One page per record: /trails/<id>/.

The main sections say what the record says, in plain words. Every field of
the record, with its exact value, is in the table at the end of the page
(raw_record); the main flow carries no coded values.
"""
import math
import os
import re
import urllib.parse

from . import browse, common, elevation, facets, hike, regions, related, seo, sketch, words
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


def credit_html(rec, credit, author_links=None):
    """A route's credit as HTML, each author's name in it a link to their page (olt/authors.py link_map)."""
    text = str(esc(credit))
    for name, href in (author_links or {}).get(facets.author(rec), []):
        n = str(esc(name))
        if n in text:
            text = text.replace(n, f'<a href="{esc(href)}">{n}</a>', 1)
    return Markup(text)


def lead_html(rec, lead, author_links=None):
    """The lead line as HTML; on a route, the author's name in it links to the author's page
    (author_links: {credit: [(name, path)]} from olt/authors.py)."""
    links = (author_links or {}).get(facets.author(rec)) if common.is_route(rec) else None
    if not links:
        return common.rich(lead)
    text = str(esc(lead))
    for name, href in links:
        n = str(esc(name))
        if n in text:
            text = text.replace(n, f'<a href="{esc(href)}">{n}</a>', 1)
    return Markup(text)


def route_definition():
    """What a route is, one tap away from the Kind line of a route's page (no script needed)."""
    return Markup(f'<details class="define"><summary>What is a route?</summary>'
                  f'<p>{esc(facets.ROUTE_DEFINITION)} <a href="/routes/">Every route</a>.</p></details>')


# What a guide's address is, by the record's `link_is`, as the link's words.
LINK_IS_TEXT = {
    "publisher": "The publisher's page for this book",
    "author": "The author's page for this guide",
    "library": "Library record (out of print)",
    "seller": "Bookseller's page",
}


def _same_page(a, b):
    """True when two addresses are the same page (scheme, www and a trailing slash aside)."""
    def key(u):
        parts = urllib.parse.urlsplit(str(u or "").strip())
        return (parts.netloc.lower().removeprefix("www."), parts.path.rstrip("/"), parts.query)
    return bool(a) and bool(b) and key(a) == key(b)


def guide_link_text(g):
    """What the guide's link says it is; today's words when the record does not say."""
    return LINK_IS_TEXT.get(g.get("link_is")) or f"Guide page on {host(g.get('url', ''))}"


def sold_guide_page(rec, url):
    """The purchase guide whose address `url` is, or whose host it shares when that guide's page
    is the publisher's or a bookseller's: a page that sells the guide is not the route's own page.
    None when `url` is the route's own."""
    for g in rec.get("guide", []):
        if g.get("access") != "purchase" or not g.get("url"):
            continue
        if _same_page(g["url"], url) or (host(g["url"]) == host(url)
                                         and g.get("link_is") in ("publisher", "seller")):
            return g
    return None


GUIDE_LABELS = set(LINK_IS_TEXT.values()) | {"The guide's page", "The route's guide"}


def see_kind(rec):
    """What a page with no GPX here sends the reader to: "guide" when its link is a guide's,
    "" when it has no link at all, else "official"."""
    link = official_link(rec)
    if not link:
        return ""
    return "guide" if link[1] in GUIDE_LABELS else "official"


def _see_clause(rec):
    """", so see the official site", or ", so see the guide" when the page on offer is a guide's."""
    link = official_link(rec)
    if not link:
        return ""
    return ", so see the guide" if link[1] in GUIDE_LABELS else ", so see the official site"


def official_link(rec):
    """(url, label) of the trail's own page: the [hike] official site, else the
    publisher's page for the trail, else a route's free guide; None when the record has none.
    An "official site" that is the page selling a guide to the route is labelled as that page."""
    url = hike.official_url(rec)
    if url:
        sold = sold_guide_page(rec, url)
        if sold:
            return url, LINK_IS_TEXT.get(sold.get("link_is")) or "The guide's page"
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


# The kinds of country, as an adjective before "country": "forest and alpine country".
TERRAIN_ADJECTIVE = {"alpine": "alpine", "forest": "forest", "desert": "desert", "coast": "coastal",
                     "prairie": "prairie", "canyon": "canyon", "tundra": "tundra", "lakes": "lake",
                     "farmland": "farmland"}
# What the walking is (docs/schema.md `travel`).
WALKING_ALONE = {
    "trail": "It is on built or maintained trail all or nearly all the way.",
    "trail-and-road": "It is on trail, with long stretches on roads.",
    "some-cross-country": "It is mostly on trail or road, with stretches that have no trail.",
    "mostly-cross-country": "It has no trail for most of the way.",
}
# An author's name that reads as a name in a sentence: no nickname in quotes, no note, no company.
PLAIN_AUTHOR = re.compile(r"[^\"();]{1,40}")
# A designation that is only a kind of trail and a year: "National Scenic Trail (1968)".
DESIGNATION_YEAR = re.compile(r"^(National [A-Z][a-z]+ Trail) \((?:(designated|certified) )?(\d{4})\)$")
GPX_CLAUSE = {
    "here": "this page has a GPX of the track to download",
    "partial": "this page has a GPX of part of the track to download",
    "free": "its author publishes a GPX free of charge, which this site does not host",
    "sold": "its author sells a GPX, which this site does not host",
    "unpublished": "no GPX of it is published",
}


def gpx_clause(rec):
    """The clause of the "In brief" paragraph about the GPX; "" when the status has none."""
    status = facets.gpx(rec)
    if status == "sold" and not common.sells_gpx(rec):
        return "its author sells it as a guide, and this site has no GPX for it"
    return GPX_CLAUSE.get(status, "")


def _name_html(rec):
    """The name for the start of a sentence: "The Appalachian Trail", with no "The" before a
    name that has one or is not in English; marked with its language when it is not English."""
    plain = common.plain_name(rec)
    lang = rec.get("derived", {}).get("name_lang", "")
    if rec.get("common_name") or not lang:
        text = esc(plain)
    else:
        text = f'<span lang="{esc(lang)}">{esc(plain)}</span>'
    if lang or plain.lower().startswith("the "):
        return Markup(text)
    return Markup("The " + text)


MAX_BRIEF = 4  # sentences in the "In brief" paragraph
PINNED = -1    # the priority of a sentence that is kept besides those (an estimated season)
MONTH_WORDS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
SEASON_WORDS = ("spring", "summer", "fall", "autumn", "winter", "late", "early", "mid", "from", "about")
SENTENCE_VERBS = re.compile(r"\b(is|are|can|start|starts|hikes?|hiked|travelled|traveled|bring|brings|closed|best)\b", re.I)


def season_sentence(rec):
    """("range", "The usual season is May to July") for a season that is a range of months or
    seasons, ("sentence", "Northbound hikes start late February to early April") for one the record
    already words as a sentence, or None when the record has none or it is too long to say briefly.
    The caller adds the full stop. Only the record's own words are used."""
    if facets.season_estimated(rec):
        # Never worded as a fact, and never joined to the GPX clause with "and".
        phrase = facets.season_phrase(rec).rstrip(". ")
        phrase = phrase.lower() if phrase.lower() == "all year" else phrase
        if facets.season_pages_differ(rec):
            return ("estimate", f"The pages differ on the season; it is judged to be about {phrase}")
        return ("estimate", f"No source gives a season; the climate suggests about {phrase}")
    text = facets.season_text(rec).strip().rstrip(". ")
    if not text:
        return None
    if re.search(r"[;:]", text):  # "Spring and fall; summers tend to be humid": the range, then a note
        head = re.split(r"[;:]", text, maxsplit=1)[0].strip()
        if not SENTENCE_VERBS.search(head) or len(text) > 110:
            text = head
    if len(text) > 110:  # a long note that does not break at a clause stays in "At a glance"
        return None
    if text.lower() == "all year":
        return ("sentence", "It can be walked all year")
    if SENTENCE_VERBS.search(text) and not text.lower().startswith(("from", "about", "early", "late", "mid")) or \
            text.split()[0].lower() in ("northbound", "the", "best", "hikers"):
        return ("sentence", text[:1].upper() + text[1:])
    first = text.split()[0].lower().split("-")[0]
    if first in SEASON_WORDS:
        text = text[:1].lower() + text[1:]
    return ("range", f"The usual season is {text}")


def permit_sentence(rec):
    """The record's permit text as one sentence, when it is short and says one thing; else ""."""
    text = common.sentence(hike.table(rec).get("permit", ""))
    if not text or len(text) > 75 or text.count(".") > 1 or ";" in text:
        return ""
    return text


def built_clause(rec):
    """", with about 290 miles (467 km) built" for an unfinished trail whose holder states the built
    length; else "". HTML-safe text."""
    if not rec.get("built_km"):
        return ""
    mi = words.fmt_int(words.km_to_mi(rec["built_km"]))
    return f", with {esc(mi)} miles ({esc(words.fmt_km(rec['built_km']))} km) built"


def brief_sentences(rec):
    """The "In brief" paragraph as a list of sentences in HTML, from the record's own fields only.
    A fact the record lacks is left out. At most MAX_BRIEF sentences, in the order a searcher
    wants them: what it is and where, how long and how long it takes, the highest point and climb,
    when to go, and whether there is a GPX. Facts that do not fit stay in "At a glance"."""
    h = hike.table(rec)
    route = common.is_route(rec)
    shape = facets.shape(rec)
    mi = words.fmt_int(rec["derived"]["length_mi"])
    km = words.fmt_km(rec["length_km"])
    terrain = [TERRAIN_ADJECTIVE[t] for t in facets.terrain(rec)]
    walking = facets.walking(rec)
    country = f"{words.join_names(terrain)} country" if terrain else ""
    items = []  # (priority, display position, sentence); the lowest priorities are kept

    # What it is, how long, where.
    tail = ""
    name = common.plain_name(rec)
    if route:
        who, year = facets.author(rec), rec.get("route", {}).get("year")
        if not PLAIN_AUTHOR.fullmatch(who or "") or who.lower().startswith("the "):
            who = ""  # a nickname, a company or a note: the line under the heading names the author in full
        noun = f"{'loop ' if shape == 'loop' else ''}route" if shape != "network" else "route network"
        noun += f" by {who}" if who else ""
        tail = f", dating from {year}," if who and year else ""
    else:
        found = DESIGNATION_YEAR.match(rec.get("designation", "").strip())
        noun = {"loop": "loop trail", "network": "trail network"}.get(shape, "trail")
        if found:
            # "National Scenic Trail (1968)": the kind and the year, unless the name already says the kind
            if found.group(1).lower() not in name.lower():
                noun = found.group(1)
            tail = f", {found.group(2) or 'designated'} in {found.group(3)},"
    article = "an" if mi.startswith("8") else "a"  # "an 81-mile", "an 800-mile"
    through = f" through {country}" if country else ""
    items.append((0, 0, f"{_name_html(rec)} is {article} {esc(mi)}-mile ({esc(km)} km) {esc(noun)}"
                        f"{esc(tail)}{esc(through)} {esc(place_text(rec))}{built_clause(rec)}."))
    unfinished = common.sentence(h.get("unfinished", ""))
    if unfinished and unfinished not in hike.summary(rec):  # the lede above may already say it
        items.append((4, 1, esc(unfinished)))

    # Where it starts and ends, and how long it usually takes.
    start, end = h.get("start", ""), h.get("end", "")
    days = hike.days(rec)
    # A place name that starts a sentence in the record reads mid-sentence in lower case.
    mid = lambda text: text[:1].lower() + text[1:] if text.startswith(("The ", "Near ")) else text  # noqa: E731
    at = lambda text: "near " + text[5:] if text.startswith("Near ") else "at " + text  # noqa: E731
    from_start, to_end = mid(start), mid(end)
    if shape == "loop":
        where = f"It starts and ends {at(start)}" if start else ""
    elif shape == "network":
        where = f"Most walks start {at(start)}" if start else ""
    elif start and end:
        where = f"It runs from {from_start}{',' if ',' in start else ''} to {to_end}"
    elif start:
        where = f"It starts {at(start)}"
    elif end:
        where = f"It ends {at(end)}"
    else:
        where = ""
    if where and days:
        items.append((1, 2, f"{esc(where)}, and walking all of it usually takes {esc(days)}."))
    elif where:
        items.append((1, 2, f"{esc(where)}."))
    elif days:
        items.append((1, 2, f"Walking all of it usually takes {esc(days)}."))

    # What the walking is.
    if walking and walking != "trail":  # the usual case needs no sentence
        items.append((5, 3, esc(WALKING_ALONE[walking])))

    # Highest point and climb, with the record's own caveat where the figures come from the track.
    elev = elevation.get(rec)
    high_name, high_m = h.get("high_point", ""), h.get("high_point_m")
    high = ""
    if high_name.startswith(("Near ", "Between ", "Above ", "Along ")):
        high_name = high_name[:1].lower() + high_name[1:]  # "Its highest point is near Owen Creek"
    if high_name and high_m:
        high = f"{high_name}, at {elevation.plain_elevation(high_m)}"
    elif high_name:
        high = high_name
    elif high_m:
        high = elevation.plain_elevation(high_m)
    climb = f"the track climbs {elevation.plain_elevation(elev['ascent_m'])} in total" if elev else ""
    how = "computed from the track"
    if elev and elevation.coverage_kind(elev) == "partial":
        how = (f"computed from the part of the track on file, {elevation.coverage_percent(elev)} "
               f"of the published length")
    elif elev and elevation.coverage_kind(elev) == "over":
        how = (f"computed from a track longer than the published length "
               f"({elevation.coverage_percent(elev)} of it), so the climb is overstated")
    if high and climb:
        items.append((2, 4, f"Its highest point is {esc(high)}, and {esc(climb)}, {esc(how)}."))
    elif high:
        items.append((2, 4, f"Its highest point is {esc(high)}."))
    elif elev:
        items.append((2, 4, f"Its highest point is {esc(elevation.plain_elevation(elev['highest']['m']))}, "
                            f"and {esc(climb)}, {esc(how)}."))

    # When to walk it and whether this site has a GPX: one sentence where the season is a plain range.
    clause = gpx_clause(rec) or ("this site has no GPX for it" + _see_clause(rec))
    season = season_sentence(rec)
    if season and season[0] != "estimate" and not re.search(r"[,;]", season[1]):
        # "The usual season is May to July, and this page has a GPX of the track to download."
        items.append((3, 5, f"{esc(season[1])}, and {esc(clause)}."))
    else:
        if season:
            # An estimated season is always said, so it is never left for a reader to take as a fact
            # by omission: it is the one sentence that may stand beyond MAX_BRIEF.
            items.append((PINNED if season[0] == "estimate" else 3.5, 5, esc(season[1]) + "."))
        items.append((3, 6, esc(clause[:1].upper() + clause[1:]) + "."))
    permit = permit_sentence(rec)
    if permit:
        items.append((6, 7, esc(permit)))

    # At most MAX_BRIEF sentences: the lowest priorities are kept, shown in reading order.
    pinned = [i for i in items if i[0] == PINNED]
    rest = sorted((i for i in items if i[0] != PINNED), key=lambda i: (i[0], i[1]))[:MAX_BRIEF]
    kept = sorted(rest + pinned, key=lambda i: i[1])
    return [text for _, _, text in kept]


def brief(rec, label=True):
    """The "In brief" paragraph of a trail: Markup. label: it opens with "In brief." (a trail page has
    its own "In brief" heading over it and leaves the label out)."""
    lead = "<strong>In brief.</strong> " if label else ""
    return Markup(f'<p class="trail-brief">{lead}{" ".join(brief_sentences(rec))}</p>')


def checked_line(rec):
    """"Last checked 2026-11-08", as a <time>, in the page's small print; "" when the record has no date."""
    date = seo.checked(rec)
    if not date:
        return ""
    return Markup(f'<p class="note trail-checked">Last checked <time datetime="{esc(date)}">{esc(date)}</time></p>')


# A name longer than this (in characters) is set a step smaller in the page's head.
LONG_NAME = 48


def page_head(rec, author_links=None):
    route = common.is_route(rec)
    crumbs = ['<li><a href="/regions/">Places</a></li>']
    keys = facets.place_keys(rec)
    groups = facets.place_groups(rec)
    if keys and keys[0] in facets.GROUP_OF:
        g = facets.GROUP_OF[keys[0]]
        crumbs.append(f'<li><a href="{esc(regions.group_path(g))}">{esc(facets.GROUP_NAME[g])}</a></li>')
        crumbs.append(f'<li><a href="{esc(facets.place_path(keys[0]))}">{esc(facets.place_name(keys[0]))}</a></li>')
    elif groups:
        crumbs.append(f'<li><a href="/regions/#across-canada">{esc(facets.ACROSS_CANADA_NAME)}</a></li>')
    crumbs.append(f'<li aria-current="page">{common.name(rec)}</li>')
    has_plate = bool(common.shield_url(rec))
    abbr = rec.get("short_name", "")
    abbr_html = f' <span class="titleblock__abbr">{esc(abbr)}</span>' if abbr else ""
    # The name hikers use leads the page; the recorded name stays, just under it.
    common_name = rec.get("common_name", "")
    heading = esc(common_name) if common_name else common.name(rec)
    full_name = f'<p class="titleblock__sub">Full name: {common.name(rec)}</p>' if common_name else ""
    plate = common.plate(rec, size="lg", link=True, eager=True) if has_plate else ""
    tag_html = common.badges(rec)
    kicker = f'<p class="cluster">{tag_html}</p>' if tag_html else ""
    lead = lead_line(rec)
    define = route_definition() if route else ""
    # The actions belong to the head: on a wide screen they stand at its right, over the column of
    # facts; on a narrow one they are one row under the name (style.css .trail-head).
    return f"""<div class="page-head page-head--trail">
  <div class="container trail-head">
    <nav class="breadcrumb" aria-label="Breadcrumb"><ol>{"".join(crumbs)}</ol></nav>
    <header class="titleblock{" titleblock--with-plate" if has_plate else ""}{" titleblock--long" if len(common_name or rec["name"]) > LONG_NAME else ""}">
      {plate}
      <div class="titleblock__text">
        {kicker}
        <h1>{heading}{abbr_html}</h1>
        {full_name}{f'<p class="titleblock__sub">{lead_html(rec, lead, author_links)}</p>' if lead else ""}
        {define}
      </div>
    </header>
    {action_buttons(rec)}
  </div>
</div>"""


def action_buttons(rec):
    """The trail's actions, in its head: the GPX (or where to get it), the trail's own page, Save."""
    actions = []
    if rec["derived"].get("downloads"):
        actions.append(f'<a class="button button--primary trail-actions__gpx" href="#download">{common.ICON_DOWNLOAD}Download the GPX</a>')
    else:
        actions.append(f'<a class="button button--quiet trail-actions__gpx" href="#track">GPX: {esc(facets.gpx_status_text(rec))}</a>')
    official = official_link(rec)
    if official:
        actions.append(f'<a class="button button--link" href="{esc(official[0])}">{esc(official[1])} {common.ICON_EXTERNAL}</a>')
    elif more_links(rec):
        # No page of its own: the first of the pages about the trail stands in, named by its publisher.
        first = more_links(rec)[0]
        actions.append(f'<a class="button button--link" href="{esc(first["url"])}">'
                       f'{esc(first["publisher"])} {common.ICON_EXTERNAL}</a>')
    actions.append(str(common.save_button(rec, row=False)))
    return f'<p class="trail-actions">{"".join(actions)}</p>'


def strip(rec):
    """The key facts in one tight line, for a phone: length, time and where (style.css shows it there
    only; At a glance has the same facts in full)."""
    codes = " ".join(esc(c.split("-")[-1]) for c in rec.get("regions", []))
    return f"""<dl class="trail-strip" aria-label="Key facts">
    <div><dt>{facets.LENGTH}</dt><dd>{words.length(rec["length_km"], "inline", rec["derived"]["length_mi"])}</dd></div>
    <div><dt>{facets.TIME}</dt><dd>{esc(facets.time_text(rec))}</dd></div>
    <div><dt>{facets.WHERE}</dt><dd>{codes}</dd></div>
  </dl>"""


def trail_text(rec):
    """The words under the map: the summary in full, the "In brief" paragraph and the date of the
    last check, then the other pages about the trail."""
    summary = hike.summary(rec)
    lede = common.rich(summary) if summary else fallback_lede(rec)
    return f"""<section class="trail-text" aria-labelledby="brief-title">
  <h2 id="brief-title" class="vh">In brief</h2>
  <p class="trail-summary">{lede}</p>
  {brief(rec)}
  {checked_line(rec)}
</section>
{links_panel(rec)}"""


def shape_label(rec, records):
    """"Loop" (linked to the loops list when it is shown), "End to end" or "Network"."""
    label = facets.SHAPES[facets.shape(rec)]
    if facets.shape(rec) == "loop":
        return list_anchor(records, "loops", label) or esc(label)
    return esc(label)


def glance_row(label, value, note="", wide=False):
    note_html = f"<small>{note if isinstance(note, Markup) else esc(note)}</small>" if note else ""
    value_html = value if isinstance(value, Markup) else esc(value)
    cls = " glance__length" if label == facets.LENGTH else ""
    return Markup(f'<div{" class=\"glance__wide" + cls + chr(34) if wide else (" class=" + chr(34) + cls.strip() + chr(34) if cls else "")}><dt>{esc(label)}</dt>'
                  f'<dd>{value_html}{note_html}</dd></div>')


def list_anchor(records, key, text):
    """text linked to the list's page when that list is shown today (browse.is_shown); else None."""
    link = related.list_link(records, key) if records else None
    return Markup(f'<a href="{esc(link[0])}">{esc(text)}</a>') if link else None


# The time lists, by the band a trail falls in (facets.time_band).
TIME_LISTS = {"week": "a-week-or-less", "two-weeks": "one-to-two-weeks"}


def length_note(rec, records):
    """A link under the length to the list its length puts it in: the shortest or the longest."""
    for key, text in (("under-100-miles", f"More trails under {browse.SHORT_MI} miles"),
                      ("longest", f"More trails of {browse.LONG_MI:,} miles or more")):
        if related.list_link(records, key) and browse.by_key(key).test(rec):
            return list_anchor(records, key, text)
    return ""


def length_asides(rec, records):
    """What sits quietly under the length: the built figure of an unfinished trail, the holder's
    larger figure with what it counts, then the link to the list the length puts the trail in.
    Each is a line of its own."""
    lines = [common.built_text(rec), common.system_text(rec), length_note(rec, records) or ""]
    return Markup("".join(f'<span class="glance__aside">{line}</span>' for line in lines if line))


def time_note(rec, records):
    """The estimate's note, then a link to the list of trails that take as long."""
    note = facets.estimate_note(rec)
    key = TIME_LISTS.get(facets.time_band(rec))
    if not key or not related.list_link(records, key):
        return note
    text = f"More trails of {browse.by_key(key).title.lower()}"
    return Markup(f"{note} {list_anchor(records, key, text)}" if note else str(list_anchor(records, key, text)))


# A trail with no permit sentence in its record has no row for it, as with season, terrain and walking:
# the panel's note says the fact is not on file, so a missing row is not read as "no permit needed".
PERMITS = "Permits"


def glance(rec, records=None):
    """The hiker's facts at a glance, under the attribute names every page uses.

    records: every trail, so that terrain, shape, time and length link to the
    lists they put the trail in (left out when None)."""
    h = hike.table(rec)
    # The length leads, set large. A built or a whole-system figure under it is a line across the
    # whole panel, so the row is as wide as the panel.
    rows = [glance_row(facets.LENGTH, words.length(rec["length_km"], "stack", rec["derived"]["length_mi"]),
                       length_asides(rec, records), wide=bool(rec.get("built_km") or rec.get("system_km")))]
    rows.append(glance_row(facets.TIME, facets.time_text(rec), time_note(rec, records)))
    season = facets.season_text(rec)
    if season:
        rows.append(glance_row(facets.SEASON, season, facets.season_note(rec)))
    if facets.walking(rec):
        walking = facets.WALKING_VALUES[facets.walking(rec)]
        if facets.walking(rec) in facets.CROSS_COUNTRY:
            walking = list_anchor(records, "off-trail", walking) or walking
        rows.append(glance_row(facets.WALKING, walking))
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
            text = Markup(f'<strong>{shape_label(rec, records)}.</strong> {esc(text) if not isinstance(text, Markup) else text}')
            label = facets.SHAPE
        rows.append(glance_row(label, text, wide=True))
    elif facets.shape(rec):
        rows.append(glance_row(facets.SHAPE, shape_label(rec, records)))
    terrain = facets.terrain(rec)
    if terrain:
        names = Markup(", ".join(str(list_anchor(records, f"terrain-{t}", words.TERRAIN[t]) or esc(words.TERRAIN[t]))
                                 for t in terrain))
        rows.append(glance_row(facets.TERRAIN, names, wide=True))
    if h.get("permit"):
        rows.append(glance_row(PERMITS, common.sentence(h["permit"]), wide=True))
    country = " and ".join(words.COUNTRIES.get(c, c) for c in common.countries(rec))
    rows.append(glance_row(facets.WHERE, Markup(f'{region_names(rec)}, {esc(country)}'), wide=True))
    status = facets.gpx(rec)
    if facets.gpx_here(rec):
        text = facets.gpx_status_text(rec)
        value = Markup(f'<a href="#download">{esc(text)}</a>') if rec["derived"].get("downloads") else text
        note = common.partial_short_text(rec) if common.line_differs(rec) else ""
    else:
        value = Markup(f'<a href="#track">{esc(facets.gpx_status_text(rec))}</a>')
        note = ""
    rows.append(glance_row(facets.GPX, value, note, wide=True))
    halves = [i for i, r in enumerate(rows) if 'glance__wide' not in r.split(">", 1)[0]]
    if len(halves) % 2:  # an odd one out takes the full width rather than leave a gap beside it
        i = halves[-1]
        rows[i] = Markup(rows[i].replace("<div>", '<div class="glance__wide">', 1)
                         .replace('<div class="glance__length">', '<div class="glance__wide glance__length">', 1))
    caution = ""
    if h.get("caution"):
        caution = f'<p class="glance__warn"><strong>Know before you go.</strong> {common.rich(common.sentence(h["caution"]))}</p>'
    unfinished = ""
    if h.get("unfinished"):
        unfinished = f'<p class="glance__warn"><strong>Not finished.</strong> {common.rich(common.sentence(h["unfinished"]))}</p>'
    missing = [name for name, have in ((facets.TERRAIN, terrain),
                                       (facets.WALKING, facets.walking(rec)),
                                       (PERMITS, h.get("permit"))) if not have]
    pending = ""
    if missing:
        names = words.join_names([missing[0]] + [m.lower() for m in missing[1:]])
        verb = "is" if len(missing) == 1 and missing[0] != PERMITS else "are"
        pending = f'<p class="note">{esc(names)} {verb} not on file for this trail yet.</p>'
    elev_caveat = elevation.coverage_caveat(elev) if elev else ""
    elev_note = f'<p class="note">{esc(elev_caveat)}</p>' if elev_caveat else ""
    # On a narrow screen only the first facts show (length and time first) and a button opens the
    # rest (style.css, app.js); with no JavaScript every fact shows.
    return f"""<section class="glance detail__glance" aria-labelledby="glance-title">
  <h2 class="glance__title" id="glance-title">At a glance</h2>
  <dl class="glance__facts">{"".join(rows)}</dl>
  {unfinished}{caution}{elev_note}{pending}
  <button class="glance__toggle js-only" type="button" aria-expanded="false" data-glance-toggle>All the facts</button>
</section>"""


# Map or empty frame ---------------------------------------------------------

def sketch_of(box, features, route_main=False):
    """(data-frame attribute, the static sketch) of a map frame for the extent `box`: the ground the
    live map opens on, and the drawing of the track on it (olt/sketch.py). Both are "" without a box."""
    if not box:
        return "", ""
    fr = sketch.frame(box)
    return f' data-frame="{",".join(f"{v:g}" for v in fr)}"', sketch.svg(features, fr, route_main=route_main)


def map_figure(rec):
    src = rec["source"]
    has_alt = "alternates" in rec["derived"]["files"]
    route = common.is_route(rec)
    legend = f'<li>{common.SWATCH_ROUTE if route else common.SWATCH_LINE}Main track</li>'
    if has_alt:
        legend += f"<li>{common.SWATCH_ALT}Alternates and connectors</li>"
    bbox = rec["derived"].get("map_bbox") or rec["derived"].get("bbox")
    bbox_attr = f' data-bbox="{",".join(str(v) for v in bbox)}"' if bbox else ""
    frame_attr, drawing = sketch_of(bbox, sketch.trail_features(rec["id"]), route_main=route)
    credit = common.sentence(common.credit_text(src.get("attribution", "")))
    return f"""<figure class="mapfig mapfig--detail detail__map" data-map="trail" data-src="/trails/{esc(rec["id"])}/map.json" data-route="{"yes" if route else "no"}"{bbox_attr}{frame_attr} data-outdoor="{OUTDOOR_STYLE}">
  <div class="mapfig__frame">
    <span class="mapfig__corner mapfig__corner--nw" aria-hidden="true"></span>
    <div class="map" role="region" aria-label="Map of the {esc(rec["name"])}">
      <div class="map__fallback">{drawing}</div>
      <div class="map__canvas"></div>
      <p class="map__status" role="status">The map needs JavaScript. Download the GPX or GeoJSON file from this page.</p>
    </div>
    <span class="mapfig__corner mapfig__corner--se" aria-hidden="true"></span>
  </div>
  <figcaption class="mapfig__caption">
    <ul class="legend" aria-label="Legend">{legend}</ul>
    <p>Track: {esc(src.get("line_source", ""))}, read {esc(src.get("source_checked", ""))}, drawn simplified to 30&nbsp;m.</p>
  </figcaption>
</figure>"""


def map_credit(rec):
    """The credit of the map, beside it under the downloads: the track's source, the base map and the
    relief. "" for a trail with no map."""
    has_track = common.has_line(rec)
    if not has_track and not hike.sketch_points(rec):
        return ""
    track = ""
    if has_track:
        credit = common.sentence(common.credit_text(rec["source"].get("attribution", "")))
        track = f"<p>Track credit: {esc(credit)}</p>"
    return f"""<section class="map-credit" aria-labelledby="map-credit-title">
  <h2 class="map-credit__title" id="map-credit-title">Map credit</h2>
  {track}<p>{common.TRAIL_MAP_CREDIT}</p>
</section>"""


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


def purchase_guide(rec):
    """The first guide that is bought, for a route; None when there is none."""
    if common.is_route(rec):
        for g in rec.get("guide", []):
            if g.get("access") == "purchase" and g.get("title"):
                return g
    return None


def guide_sentence(g):
    """"The route is in <title> (<edition>), <where>." from what the guide says of itself."""
    edition = g.get("edition", "")
    title = g["title"] + (f" ({edition})" if edition and edition.lower() not in g["title"].lower() else "")
    where = str(g.get("where", "")).strip().rstrip(".")
    if where.lower().startswith("the whole guide"):
        return f"The whole of {title} is this route."
    return f"The route is in {title}" + (f", {where[:1].lower() + where[1:]}" if where else "") + "."


ROUTE_NO_GPX = {
    # GPX status -> (heading, what this site does about it); "" for nothing to add to the reason.
    "free": ("Get the GPX from its author",
             "A GPX is included here only where the author's terms allow passing it on, or where "
             "OpenStreetMap maps the route. Otherwise the author's own page is the place to get it."),
    "sold": ("The author sells the route as a guide", ""),
    "unpublished": ("The author does not publish a track",
                    "No GPX is included here from any source, OpenStreetMap included, so the author's choice is respected."),
    "elsewhere": ("No GPX here",
                  "No GPX is included here until it is clear that the author allows it."),
}
# A route whose author sells a GPX (common.sells_gpx).
ROUTE_SOLD_GPX = ("The author sells a GPX",
                  "A GPX that is sold is not passed on here, and OpenStreetMap's version is not used in its place.")


def _no_gpx_parts(rec):
    """(title, status, reason, rule, actions_html): why there is no GPX here
    and where to get one, for the empty frame and the sketch map alike."""
    src = rec["source"]
    reason = common.visitor_text(src.get("line_absent_reason", ""))
    actions = []
    status = facets.gpx(rec)
    if common.is_route(rec):
        title, rule = ROUTE_SOLD_GPX if status == "sold" and common.sells_gpx(rec) else ROUTE_NO_GPX.get(status, ROUTE_NO_GPX["elsewhere"])
        if status == "free" and free_guides(rec):
            g = free_guides(rec)[0]
            actions.append(f'<a class="button button--primary" href="{esc(g["url"])}">'
                           f'{esc(g["title"])} {common.ICON_EXTERNAL}</a>')
        bought = purchase_guide(rec)
        if bought:
            rule = f"{guide_sentence(bought)} {rule}".strip()
        if not actions:
            label = f"Where to get {bought['title']}" if bought else "See where to get the route"
            actions.append(f'<a class="button button--link" href="#guides-title">{esc(label)}</a>')
        elif len(rec.get("guide", [])) > 1:
            actions.append('<a class="button button--link" href="#guides-title">All guides</a>')
    else:
        title = "No GPX here"
        reason = common.absent_reason_short(rec)
        # "No track may be passed on" is for a trail whose track is held back, not one not added yet.
        rule = "" if common.not_added_yet(rec) else "A trail is listed without a GPX when no track for it may be passed on."
        official = official_link(rec)
        if official:
            actions.append(f'<a class="button button--link" href="{esc(official[0])}">'
                           f'{esc(official[1])} {common.ICON_EXTERNAL}</a>')
        places = [official[1][:1].lower() + official[1][1:] if official[1] == "Official site"
                  else official[1][:1].lower() + official[1][1:] if official[1].startswith("The ")
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
    rule_html = f'<p class="note">{esc(rule)}</p>' if rule else ""
    return f"""<figure class="mapfig mapfig--empty detail__map" id="track" aria-labelledby="noline-title">
  <div class="mapfig__frame">
    <span class="mapfig__corner mapfig__corner--nw" aria-hidden="true">No GPX here</span>
    <div class="map map--empty">
      <div class="map__message">
        <p class="kicker">GPX: {esc(facets.gpx_status_text(rec))}</p>
        <h2 id="noline-title">{esc(title)}</h2>
        <p class="map__reason">{reason if isinstance(reason, Markup) else common.rich(reason)}</p>
        {rule_html}
        {actions_html}
      </div>
    </div>
    <span class="mapfig__corner mapfig__corner--se" aria-hidden="true">Nothing drawn</span>
  </div>
  <figcaption class="mapfig__caption"><p>No map is drawn: there is no track for this trail here, and the site does not guess one.</p></figcaption>
</figure>"""


def sketch_figure(rec):
    """A real map for a trail with no track whose start and end are on file (or a loop's one place):
    the base map fitted to those points, with each one marked and named. No line joins them and
    nothing is drawn that could be read as the route. The notice about where to get a track sits
    beside the map, not over it."""
    points = hike.sketch_points(rec)
    box = hike.sketch_bbox(points, pad=True)
    bbox_attr = f' data-bbox="{",".join(str(v) for v in box)}"' if box else ""
    route = common.is_route(rec)
    marks = hike.termini(rec)
    items = "".join(
        f'<li class="terminus-item" data-lon="{m["lonlat"][0]}" data-lat="{m["lonlat"][1]}" '
        f'data-role="{m["role"]}" data-label="{esc(m["label"])}">'
        f'<strong>{"Start and end" if m["role"] == "both" else m["role"].capitalize()}</strong>'
        f'{" " + esc(m["place"]) if m["place"] else ""}</li>' for m in marks)
    if len(marks) == 1:
        caption = ("Only the place where it starts and ends is shown. There is no track for this trail here, "
                   "and the site does not guess one.")
    else:
        caption = ("Only the start and the end are shown. There is no track for this trail here, "
                   "and the site does not guess one.")
    title, status, reason, rule, actions_html = _no_gpx_parts(rec)
    rule_html = f'<p class="note">{esc(rule)}</p>' if rule else ""
    reason_html = reason if isinstance(reason, Markup) else common.rich(reason)
    frame_attr, drawing = sketch_of(box, sketch.trail_features(rec["id"]), route_main=route)
    rid = esc(rec["id"])
    return f"""<figure class="mapfig mapfig--detail mapfig--termini detail__map" id="track" data-map="sketch" data-src="/trails/{rid}/sketch.json" data-route="{"yes" if route else "no"}"{bbox_attr}{frame_attr} data-outdoor="{OUTDOOR_STYLE}">
  <div class="mapfig__frame">
    <span class="mapfig__corner mapfig__corner--nw" aria-hidden="true"></span>
    <div class="map" role="region" aria-label="Map of where the {esc(rec["name"])} starts and ends. No track is drawn." aria-describedby="termini-{rid}">
      <div class="map__fallback">{drawing}</div>
      <div class="map__canvas"></div>
      <div class="map__termini" aria-hidden="true"></div>
      <p class="map__status" role="status">The map needs JavaScript. The ends of the trail are named beside it.</p>
    </div>
    <span class="mapfig__corner mapfig__corner--se" aria-hidden="true"></span>
  </div>
  <div class="termini-notice">
    <div class="map__message">
      <p class="kicker">GPX: {esc(facets.gpx_status_text(rec))}</p>
      <h2 id="noline-title">{esc(title)}</h2>
      <p class="map__reason">{reason_html}</p>
      {rule_html}
      {actions_html}
    </div>
  </div>
  <figcaption class="mapfig__caption mapfig__caption--termini">
    <ul class="termini-list" id="termini-{rid}" aria-label="Marked on the map">{items}</ul>
    <p>{caption}</p>
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
    permission = permission_figure(src)
    licence_note = (f'<p class="note">{esc(words.LICENCE_NOTES[licence])}'
                    f'{" The statement is quoted below." if permission else ""}</p>'
                    if licence in words.LICENCE_NOTES else "")
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
      {osm_note}{licence_note}{permission}
    </div>
    {release}
  </div>
</section>"""


def guide_card(g, i):
    rows = [fact("Author", g.get("author", ""))]
    if g.get("edition"):
        rows.append(fact("Edition", g["edition"]))
    if g.get("where"):
        rows.append(fact("Where in it", g["where"]))
    if g.get("publisher"):
        rows.append(fact("Publisher", g["publisher"]))
    if g.get("isbn"):
        rows.append(Markup(f'<div><dt>ISBN</dt><dd><span class="nowrap">{esc(g["isbn"])}</span></dd></div>'))
    if g.get("format"):
        rows.append(fact("Form", g["format"]))
    if g.get("price"):
        rows.append(fact("Price", g["price"], f"As the page stated it on {g.get('price_checked', '')}"
                         if g.get("price_checked") else ""))
    access = g.get("access", "")
    return f"""<li class="guide">
  <p class="guide__tags"><span class="access access--{esc(access)}">{esc(words.ACCESS.get(access, access))}</span></p>
  <h3 id="guide-{i}">{esc(g.get("title", ""))}</h3>
  {facts(*rows)}
  <a class="button button--link" href="{esc(g.get("url", ""))}" aria-describedby="guide-{i}">{esc(guide_link_text(g))} {common.ICON_EXTERNAL}</a>
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
    if any(g.get("link_is") for g in guides):
        note = "Each link says what it goes to."
    else:
        note = f"Links go to the {'author&rsquo;s or publisher&rsquo;s' if common.is_route(rec) else 'holder&rsquo;s'} own page for each guide."
    return f"""<section class="panel" aria-labelledby="guides-title">
  <h2 class="panel__head" id="guides-title">{"Where to get the route" if common.is_route(rec) else "Maps and guides"}</h2>
  <div class="panel__body">
    <ul class="guides">{cards}</ul>
    <p class="note">{note}</p>
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


def route_block(rec, author_links=None):
    r = rec["route"]
    p = r.get("line_policy", "")
    rows = [
        fact("Author", credit_html(rec, r.get("creator", ""), author_links) if r.get("creator") else "", "Who worked the route out (route.creator)"),
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
    <p class="quote__who"><strong>{esc(by) if r.get("creator_words_by") else credit_html(rec, by, author_links)}</strong> {not_creator}</p>
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
    return meaning  # no note: say no more than the status (tools/validate.py check_held_note catches the gap in the data)


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
        fact("Common name", rec["common_name"], "The name hikers use, where it differs from the name above.")
        if rec.get("common_name") else "",
        fact("Designation", rec.get("designation", "")),
        fact("Tier", words.label(words.TIERS, tier), words.meaning(words.TIERS, tier)),
        fact("Listing", words.label(words.WAVES, wave), listing_note(rec)),
    ]
    if rec.get("inclusion"):
        inc = rec["inclusion"]
        rows.append(fact("Inclusion", words.label(words.INCLUSION, inc), words.meaning(words.INCLUSION, inc)))
    rows += [
        Markup(f'<div><dt>Where</dt><dd>{where}</dd></div>'),
        Markup(f'<div><dt>Length</dt><dd>{words.length(rec["length_km"], "inline", rec["derived"]["length_mi"])}'
               f'<small>{esc(common.sentence(rec.get("length_note", "")))} The published length of walking the whole '
               f'trail from end to end (for a loop reached by a stem, with the stem both ways), a check value, not measured from the track.</small></dd></div>'),
        fact("Built length", common.built_text(rec), "How much of the trail is built, as the holder states it.")
        if rec.get("built_km") else "",
        fact("Whole system", Markup(f'{words.length(rec["system_km"], "inline")}, counting '
                                    f'{esc(str(rec["system_note"]).strip().rstrip("."))}'),
             "The holder's larger figure, kept apart from the length.")
        if rec.get("system_km") else "",
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


def permission_figure(src):
    """The quoted words of a track shared by stated permission: the quotation, who said it and
    when, and the page it was read at. Empty for any other licence."""
    if src.get("licence") != "stated-permission" or not src.get("permission_quote"):
        return ""
    url = src.get("permission_url", "")
    return f"""<figure class="quote">
  <blockquote{f' cite="{esc(url)}"' if url else ""}><p>{esc(src["permission_quote"])}</p></blockquote>
  <figcaption>
    <p class="quote__who">Said by {esc(src.get("permission_by", ""))} on {esc(src.get("permission_date", ""))}.</p>
    {f'<p>Read at {ext_link(url)}.</p>' if url else ""}
  </figcaption>
</figure>"""


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
    permission = permission_figure(src)
    licence_note = (f'<p>{esc(words.LICENCE_NOTES[licence])}{" The statement is quoted below." if permission else ""}</p>'
                    if licence in words.LICENCE_NOTES else "")
    licence_text = (f'<h3 class="block__sub">What the source says</h3>{licence_note}{Markup(permission)}{record_text(src["licence_text"])}'
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
        # No logo file. The two states say different things: the trail has no emblem of its
        # own, or it has (or may have) one and no usable artwork of it was found.
        lead = {"no-logo-exists": "No emblem of its own",
                "logo-not-found": "Emblem not found"}.get(status, "No logo file")
        why = {"logo-not-found": " An emblem exists or may exist, but no usable artwork of it was found "
                                 "at a source the dataset allows."}.get(status, "")
        note = sh.get("note", "")
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
        record = esc(site.blob_url(f"{rec['id']}/trail.toml"))
        history = esc(site.history_url(rec["id"]))
        parts.append(f"""<p class="prose">This record is a text file anyone can correct. Please say where a correction can be checked: a source page, a map, or a measured track.</p>
<ul class="linklist">
  <li><a href="{report}">Report a correction</a><small>No git needed: a short form, with this record ({code(rec["id"])}) filled in</small></li>
  <li><a href="{record}">The record file</a><small>trail.toml on GitHub, to read it as it is written</small></li>
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
    basis = facets.season_basis_line(rec)
    basis = f'<p class="note">{esc(basis)}</p>' if basis else ""
    return block("hike-title", "Where the hiking facts come from", Markup(body + checked + basis))


def about_data(rec, site, author_links=None):
    """Everything about where the page's data comes from: collapsed, below the hiker's part."""
    blocks = ((route_block(rec, author_links) if common.is_route(rec) else "") + record_block(rec) + hike_sources_block(rec)
              + verification_block(rec) + elevation_block(rec) + source_block(rec) + osm_block(rec) + logo_block(rec)
              + links_block(rec) + correction_block(rec, site) + raw_record(rec))
    return f"""<details class="about-data" id="about-data">
  <summary><h2 id="about-data-title">About this data</h2>
  <span class="about-data__hint">Where the track and the facts come from, licence, checks, the logo, corrections, and every field of the record</span></summary>
  <div class="about-data__body detail__main">
    {blocks}
  </div>
</details>"""


HISTORY_LABELS = {"declined": "Request declined"}


def history_entry(e):
    """One entry of the record's [[history]], as a list item."""
    outcome = e.get("outcome", "")
    label = HISTORY_LABELS.get(outcome, "")
    url = e.get("basis_url", "")
    basis = esc(e.get("basis", ""))
    link = f' <a href="{esc(url)}">{esc(url)}</a>' if url else ""
    fields = "".join(f"<li><code>{esc(f)}</code></li>" for f in e.get("fields", []))
    date = esc(e.get("date", ""))
    return f"""<li class="history__entry history__entry--{esc(outcome)}">
  <p class="history__head"><time datetime="{date}">{date}</time>{f' <strong class="history__outcome">{esc(label)}</strong>' if label else ""}</p>
  <p class="history__change">{esc(e.get("change", ""))}</p>
  <p class="history__basis"><span class="history__label">Basis:</span> {basis}{link}</p>
  <p class="history__who"><span class="history__label">Asked by:</span> {esc(e.get("asked_by", ""))}</p>
  <ul class="history__fields" aria-label="Fields it concerns">{fields}</ul>
</li>"""


def history_section(rec):
    """Who asked for what on this record, on what evidence, and what was declined: collapsed,
    beside "About this data". Left out when the record has no history."""
    entries = [e for e in rec.get("history", []) if isinstance(e, dict)]
    if not entries:
        return ""
    count = len(entries)
    return f"""<details class="about-data about-data--history" id="record-history">
  <summary><h2 id="record-history-title">History of this record</h2>
  <span class="about-data__hint">What was changed or asked for, on what evidence, and who asked, oldest first ({count} entr{"y" if count == 1 else "ies"})</span></summary>
  <div class="about-data__body detail__main">
    <ol class="history">
    {"".join(history_entry(e) for e in entries)}
    </ol>
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
    rows = "".join(f'<div><dt><code>{esc(field)}</code></dt><dd>{esc(raw_value(value))}</dd></div>'
                   for field, value in flatten(fields))
    return Markup(f"""<details class="rawrecord">
  <summary>Every field of the record, with its exact value</summary>
  <p class="note">As stored in <a href="/trails/{esc(rec["id"])}/trail.toml">trail.toml</a>.
  The <a href="/data/schema/">record schema</a> says what each field means.</p>
  <dl class="rawrecord__fields">{rows}</dl>
</details>""")


# The page -------------------------------------------------------------------

def gpx_offered(rec):
    """True when the page offers a GPX download (the build lists its files in derived.downloads)."""
    downloads = rec["derived"].get("downloads")
    if downloads is None:
        return common.has_line(rec)
    return any(d.get("format") == "GPX" for d in downloads)


def page_title(rec, site):
    """The page's own title, before the site name is added: the name hikers use, the
    abbreviation where there is one, the length in miles, and what the page offers.
    Only what is true of the page: GPX only where it has a download, a map only
    where it has a track.

    The title alone stays within common.TITLE_LIMIT (the site name is added to <title> only
    where the whole is within it too, see common.title_tag). Pieces go in
    this order until it fits: the kilometres, the author of a route, the word
    "map", the abbreviation, then "GPX". A route says it is a route. Where even that is
    too long and the name alone fits, the title is the name; the name is never cut.
    """
    name = common.plain_name(rec)
    abbr = rec.get("short_name", "")
    named = f"{name} ({abbr})" if abbr and abbr.lower() != name.lower() else name
    mi = words.fmt_int(rec["derived"]["length_mi"])
    km = words.fmt_km(rec["length_km"])
    gpx = gpx_offered(rec)
    who = facets.author(rec)
    route = common.is_route(rec)

    def text(head, with_km, with_who, offer):
        if route:
            tail = f"{mi}-mile route" + (f" by {who}" if with_who and who else "")
        else:
            tail = f"{mi} miles" + (f" ({km} km)" if with_km else "")
        return f"{head}: {tail}" + {2: ", map and GPX", 1: ", GPX", 0: ""}[offer if gpx else 0]

    steps = ((named, True, True, 2), (named, False, False, 2), (named, False, False, 1),
             (name, False, False, 1), (name, False, False, 0))
    options = []
    for step in steps:
        option = text(*step)
        if option not in options:
            options.append(option)
    fitted = common.fit_title(options, site)
    if len(fitted) > common.title_room(site) >= len(name):
        return name  # only the name fits: the length goes before the name is cut
    return fitted


def places_short(rec):
    """Where it is, for a description: "in Oregon", "in Utah and Wyoming",
    "across 14 states", "across Canada"."""
    codes = rec.get("regions", [])
    if words.ALL_CANADA in codes:
        return "across Canada"
    countries = [words.COUNTRIES.get(c, c) for c in common.countries(rec)] or \
        [words.COUNTRIES.get(rec["country"], rec["country"])]
    if not codes:
        return f"in {words.join_names(countries)}"
    if len(codes) > 3:
        unit = {"United States": "states", "Canada": "provinces and territories"}.get(
            words.join_names(countries), "states and provinces")
        return f"across {len(codes)} {unit}"
    return f"in {words.join_names(words.region_name(c) for c in codes)}"


def description(rec):
    """The meta description, from the record's own fields and at most DESCRIPTION_LIMIT
    characters: what it is, how long, where, the usual time where a source states one,
    then the first sentence of the summary (or the designation where there is none).
    Always whole sentences, whatever fits of those."""
    mi = words.fmt_int(rec["derived"]["length_mi"])
    km = words.fmt_km(rec["length_km"])
    built = ""
    if rec.get("built_km"):
        built = f", {words.fmt_int(words.km_to_mi(rec['built_km']))} miles built,"
    lead = f"A {kind_word(rec)} of {mi} miles ({km} km){built} {places_short(rec)}"
    days = hike.days(rec)
    tail = hike.one_line(rec)
    if not tail and rec.get("designation"):
        tail = rec["designation"].strip()
        tail = tail[:1].upper() + tail[1:]
        if not tail.endswith("."):
            tail += "."
    # Whole sentences, the richest that fits first: the facts with the usual time and the summary's
    # first sentence, then without the time, then the facts alone; only a first sentence that is
    # itself too long is cut, at a word and with no ellipsis (common.cut_clean).
    sentences = [lead + (f", usually {days}" if days else "") + "."]
    if days:
        sentences.append(lead + ".")
    options = [f"{o} {tail}" for o in sentences] if tail else []
    options += sentences
    options = [re.sub(r"\s+", " ", o.replace("`", "")) for o in options]
    return next((o for o in options if len(o) <= common.DESCRIPTION_LIMIT),
                common.cut_clean(options[-1], common.DESCRIPTION_LIMIT))


# Ways onward ------------------------------------------------------------------

ONWARD_MAX = 6


def _onward_list(title, recs, more_href, more_text, heading_id, meta=None):
    """One list of ways onward: each trail's name and length, then meta(r) (HTML) where given."""
    items = "".join(
        f'<li><a href="{esc(common.trail_path(r))}">{common.name(r)}</a>'
        f'<span class="onward__len">{words.length(r["length_km"], "short", r["derived"]["length_mi"])}'
        f'{" · Route" if common.is_route(r) else ""}{meta(r) if meta else ""}</span></li>'
        for r in recs[:ONWARD_MAX])
    more = (f'<p class="onward__more"><a href="{esc(more_href)}">{esc(more_text)}</a></p>'
            if more_href else "")
    return (f'<section class="onward__part" aria-labelledby="{heading_id}">'
            f'<h3 id="{heading_id}">{esc(title)}</h3><ul class="onward__list">{items}</ul>{more}</section>')


def nearest_length(rec, other):
    """A sort key for the trails of a place on a trail's page: the closest in length first (by ratio, so
    300 and 600 miles are as far apart as 30 and 60), then by name."""
    return (abs(math.log(other["length_km"] / rec["length_km"])), facets.sort_name(other))


RELATED_WHY = {"name": "same name", "named": "named here", "names": "mentions this"}


def onward(rec, records):
    """Ways onward at the foot of the page, all worked out from the records (olt/related.py):
    trails tied to this one by name or by what the descriptions say; other trails in the
    same state or province (up to three of them), the closest in length first; trails like this one in length, terrain
    and shape; and for a route, other routes by the same author."""
    if not records:
        return ""
    others = [r for r in records if r["id"] != rec["id"]]
    parts = []
    tied = related.related_to(rec, records)
    if tied:
        why = {r["id"]: w for r, w in tied}
        parts.append(_onward_list("Related trails", [r for r, _ in tied], "", "", "onward-related",
                                  meta=lambda r: f" · {esc(RELATED_WHY[why[r['id']]])}"))
    for i, key in enumerate(k for k in facets.place_keys(rec) if k != facets.ACROSS_CANADA):
        if i >= 3:
            break
        here = sorted((r for r in others if key in facets.place_keys(r)), key=lambda r: nearest_length(rec, r))
        if not here:
            continue
        name = facets.place_name(key)
        more = (facets.place_path(key), f"All {len(here) + 1} trails in {name}") if len(here) > ONWARD_MAX else \
            (facets.place_path(key), f"{name} on the map")
        parts.append(_onward_list(f"More in {name}", here, more[0], more[1], f"onward-{key.lower()}"))
    like = related.similar_to(rec, records)
    if like:
        def alike(r):
            shared = related.shared_terrain(rec, r)
            return f" · {esc(', '.join(words.TERRAIN[t].lower() for t in shared))}" if shared else ""
        parts.append(_onward_list("Similar in length and terrain", like, "", "", "onward-similar", meta=alike))
    who = facets.author(rec)
    if who:
        same = sorted((r for r in others if facets.author(r) == who), key=lambda r: -r["length_km"])
        if same:
            parts.append(_onward_list(f"More routes by {who}", same, "/routes/", "Every route", "onward-author"))
    if not parts:
        return ""
    return (f'<nav class="onward" aria-labelledby="onward-title"><h2 id="onward-title">Where next</h2>'
            f'<div class="onward__grid">{"".join(parts)}</div></nav>')


def render(rec, site, records=None, author_links=None):
    """Return (title, description, body HTML, needs_map) for one trail.
    records: every trail, for the ways onward at the foot (left out when None)."""
    has_track = common.has_line(rec)
    sketch_points = hike.sketch_points(rec) if not has_track else []
    has_map = has_track or bool(sketch_points)
    aside = downloads_panel(rec) + guides_panel(rec)
    aside_html = (f'<aside class="detail__aside" aria-label="{"Downloads" if has_track else "Where to get the route"}">'
                  f'{aside}</aside>') if aside else ""
    profile = elevation_figure(rec)
    side = f'<div class="detail__side">{glance(rec, records)}{aside_html}{map_credit(rec)}</div>'
    body = f"""{page_head(rec, author_links)}
<div class="container detail{"" if aside else " detail--no-aside"}{"" if has_map else " detail--no-map"}{" detail--with-profile" if profile else ""}">
  {strip(rec)}
  {map_figure(rec) if has_track else sketch_figure(rec) if sketch_points else empty_frame(rec)}
  {side}
  <div class="detail__text">{trail_text(rec)}</div>
  {profile}
</div>
<div class="container trail-more">
  {onward(rec, records)}
  {page_foot(rec, site)}
  {about_data(rec, site, author_links)}
  {history_section(rec)}
</div>"""
    return page_title(rec, site), description(rec), body, has_map


def release_path(repo_root, rec):
    path = os.path.join(repo_root, rec["id"], "release.txt")
    return path if os.path.isfile(path) else ""
