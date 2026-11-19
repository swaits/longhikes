"""Places (/regions/, /regions/<state or province>/), lists (/lists/, /lists/<key>/) and
the Routes list (/routes/).

Every page lists trails with home.results(), the same rows the home page shows.
The section is called Places; its pages keep their /regions/ URLs.
"""
import collections

from . import bounds, browse, common, facets, home, summary, words
from .markup import Markup, esc


def collect_regions(records):
    """slug -> {key, code, country, name, group, records} for every state and province a
    trail names; plus the trails that name all of Canada, separately."""
    by_slug = {}
    across = []
    for r in records:
        for key in facets.place_keys(r):
            if key == facets.ACROSS_CANADA:
                across.append(r)
                continue
            slug = key.lower()
            country, code = key.split("-", 1)
            info = by_slug.setdefault(slug, {"key": key, "code": code, "country": country,
                                             "name": facets.place_name(key),
                                             "group": facets.GROUP_OF.get(key, ""), "records": []})
            if all(x["id"] != r["id"] for x in info["records"]):
                info["records"].append(r)
    for info in by_slug.values():
        info["records"].sort(key=home.sort_name)
    across.sort(key=home.sort_name)
    return by_slug, across


def group_box(g, by_slug):
    """The ground a group page opens on: the union of the boxes of its members that have trails,
    or None when one of them has no box (the map then opens on its trails)."""
    keys = next(k for x, _, k in facets.PLACE_GROUPS if x == g)
    return bounds.union([k for k in keys if k.lower() in by_slug])


def group_records(records, group):
    return [r for r in records if group in facets.place_groups(r)]


def _gpx_count(recs):
    return sum(1 for r in recs if facets.gpx_here(r))


def _plural(n, word="trail"):
    return f"{n} {word}{'' if n == 1 else 's'}"


def _with_gpx(n_gpx, total):
    """"3 with a GPX here", or "all with a GPX here" when every one has; "" when none has."""
    if not n_gpx:
        return ""
    return "all with a GPX here" if n_gpx == total else f"{n_gpx} with a GPX here"


def _miles(rec):
    return words.fmt_int(rec["derived"]["length_mi"])


def _fit(options, limit=common.DESCRIPTION_LIMIT):
    """The first of options (fullest first) that fits; else the last, cut at a word."""
    return common.cut_at_word(next((o for o in options if len(o) <= limit), options[-1]), limit)


def lists_here(recs, records):
    """The ready-made lists that hold some of these trails, as links with how many of them each
    holds. A list that holds all of them (and there are several) says nothing about the place."""
    ids = {r["id"] for r in recs}
    parts = []
    for lst, members in browse.shown(records):
        k = sum(1 for m in members if m["id"] in ids)
        if k and not (k == len(recs) > 1):
            parts.append(f'<a href="{esc(browse.path(lst))}">{esc(lst.title)}</a> ({k})')
    return parts


def regions_index_page(records, site):
    """(title, description, body) for /regions/: the Places hub."""
    by_slug, across = collect_regions(records)
    blocks = ""
    jump = []
    for g, name, keys in facets.PLACE_GROUPS:
        infos = sorted((by_slug[k.lower()] for k in keys if k.lower() in by_slug), key=lambda i: i["name"])
        if not infos:
            continue
        recs = group_records(records, g)
        jump.append(f'<li><a href="#{esc(g)}">{esc(name)}<span class="lists-row__n">{len(recs)}</span></a></li>')
        rows = "".join(
            f'<li><a href="{esc(facets.place_path(i["key"]))}">{esc(i["name"])}</a>'
            f'<span class="places__n">{_plural(len(i["records"]))}</span></li>'
            for i in infos)
        blocks += f"""<section class="places__group" aria-labelledby="{esc(g)}">
  <h2 id="{esc(g)}"><a href="{esc(group_path(g))}">{esc(name)}</a></h2>
  <p class="places__sum">{_plural(len(recs))}, {_gpx_count(recs)} with a GPX here.
  <a href="{esc(group_path(g))}">All {_plural(len(recs))} in {esc(name)}</a></p>
  <ul class="places__list">{rows}</ul>
</section>"""
    if across:
        links = ", ".join(f'<a href="{esc(common.trail_path(r))}">{common.name(r)}</a>' for r in across)
        jump.append(f'<li><a href="#across-canada">{facets.ACROSS_CANADA_NAME}<span class="lists-row__n">{len(across)}</span></a></li>')
        blocks += f"""<section class="places__group" aria-labelledby="across-canada">
  <h2 id="across-canada"><span id="canada-wide"></span>{facets.ACROSS_CANADA_NAME}</h2>
  <p class="places__sum">{_plural(len(across))} that {"crosses" if len(across) == 1 else "cross"} the whole country rather than one province: {links}.
  {"It is" if len(across) == 1 else "They are"} counted in every Canadian group, and on no single province&rsquo;s page.</p>
</section>"""
    n_us = sum(1 for r in records if "US" in common.countries(r))
    n_ca = sum(1 for r in records if "CA" in common.countries(r))
    body = f"""<div class="page-head"><div class="container"><header class="titleblock">
  <div class="titleblock__text"><h1>Places</h1>
  <p class="page-head__lede">The {len(records)} trails by state and province, grouped into parts of the
  United States ({n_us}) and Canada ({n_ca}). A trail that crosses several states is on each one&rsquo;s page.</p>
  </div></header>
  <nav class="lists-row" aria-label="Jump to a part of the country"><ul>{"".join(jump)}</ul></nav></div></div>
<div class="container section places">{blocks}</div>"""
    description = (f"Where the {len(records)} long trails and routes are: {n_us} in the United States and {n_ca} in Canada, "
                   f"by state and province, with the number in each.")
    return "Long Trails by State and Province: US and Canada", common.cut_at_word(description, common.DESCRIPTION_LIMIT), Markup(body)


def group_path(g):
    """The page of a part of the country: /regions/<group key>/ (state and province pages are
    /regions/<us-xx or ca-xx>/, so the two never meet)."""
    return f"/regions/{g}/"


def group_page(g, records, site):
    """(title, description, body, needs_map, recs) for /regions/<group>/: the trails in one part of
    the country (facets.PLACE_GROUPS), or None when no trail is there. A trail that crosses all of
    Canada is in every Canadian part, as the home page's Where filter counts it."""
    recs = sorted(group_records(records, g), key=home.sort_name)
    if not recs:
        return None
    name = facets.GROUP_NAME[g]
    by_slug, _ = collect_regions(records)
    keys = next(k for x, _, k in facets.PLACE_GROUPS if x == g)
    places = sorted((by_slug[k.lower()] for k in keys if k.lower() in by_slug), key=lambda i: i["name"])
    countries = {i["country"] for i in places}
    country = words.COUNTRIES[next(iter(countries))] if len(countries) == 1 else ""
    n_gpx = _gpx_count(recs)
    states = words.join_names(esc(i["name"]) for i in places)
    lede = f"{_plural(len(recs))} in {states}, {n_gpx} with a GPX here."
    nav = (f'<nav class="region-nav" aria-label="Places in {esc(name)}">Places in {esc(name)}, and how many there: '
           + " · ".join(f'<a href="{esc(facets.place_path(i["key"]))}">{esc(i["name"])}</a> ({len(i["records"])})'
                        for i in places) + "</nav>")
    others = [(x, n) for x, n, _ in facets.PLACE_GROUPS if x != g and group_records(records, x)]
    nav += (f'<nav class="region-nav" aria-label="Other parts">Other parts: '
            + " · ".join(f'<a href="{esc(group_path(x))}">{esc(n)}</a>' for x, n in others) + "</nav>")
    body = f"""<div class="page-head"><div class="container">
  <nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="/regions/">Places</a></li><li aria-current="page">{esc(name)}</li></ol></nav>
  <header class="titleblock"><div class="titleblock__text">
  <p class="kicker">{esc(country or "United States and Canada")}</p>
  <h1>{esc(name)}</h1>
  <p class="page-head__lede">{lede}</p>
  </div></header>
</div></div>
<div class="container section place">
  {home.browse_view(home.listing(recs, top=2, where="g:" + g), home.overview_map(recs, f"Map of the trails in {name}", place=group_box(g, by_slug)),
               about=f"{summary.facts(recs, records)}{summary.details(recs)}", about_title=f"About the trails in {name}")}
  {nav}
</div>"""
    title = common.fit_title([f"Long Trails in {name}: {_plural(len(recs), 'Trail')}", f"Long Trails in {name}"], site)
    by_length = sorted(recs, key=lambda r: (r["length_km"], r["id"]))
    first = (f"{_plural(len(recs))} in {name} ({words.join_names(i['name'] for i in places)}), from "
             f"{common.plain_name(by_length[0])}, {_miles(by_length[0])} miles, to {common.plain_name(by_length[-1])}, "
             f"{_miles(by_length[-1])} miles.")
    gpx = f" {_with_gpx(n_gpx, len(recs))[:1].upper()}{_with_gpx(n_gpx, len(recs))[1:]}." if n_gpx else ""
    desc = _fit([first + gpx, first, f"{_plural(len(recs))} in {name}.{gpx}"])
    return title, desc, Markup(body), home.has_overview_map(recs), recs


def region_page(slug, records, site, facet_pages=()):
    """(title, description, body, needs_map) for /regions/<slug>/: the trails in one state or province.

    facet_pages: [(label, path, how many)] for this place's pages of one kind of trail (olt/placefacets.py)."""
    by_slug, _ = collect_regions(records)
    info = by_slug[slug]
    recs = info["records"]
    key = info["key"]
    group = info["group"]
    group_name = facets.GROUP_NAME.get(group, "")
    country = words.COUNTRIES[info["country"]]
    n_gpx = _gpx_count(recs)
    crumbs = '<li><a href="/regions/">Places</a></li>'
    if group:
        crumbs += f'<li><a href="{esc(group_path(group))}">{esc(group_name)}</a></li>'
    siblings = []
    if group:
        _, _, keys = next(x for x in facets.PLACE_GROUPS if x[0] == group)
        for k in sorted(keys, key=facets.place_name):
            if k != key and k.lower() in by_slug:
                siblings.append(f'<a href="{esc(facets.place_path(k))}">{esc(facets.place_name(k))}</a>')
    nav = (f'<nav class="region-nav" aria-label="Elsewhere in {esc(group_name)}">Elsewhere in {esc(group_name)}: '
           f'{" · ".join(siblings)}</nav>') if siblings else ""
    held = lists_here(recs, records)
    nav += (f'<nav class="region-nav" aria-label="Lists with trails in {esc(info["name"])}">'
            f'Lists with trails in {esc(info["name"])}, and how many here: {" · ".join(held)}</nav>') if held else ""
    if facet_pages:
        nav += (f'<nav class="region-nav" aria-label="Kinds of trail in {esc(info["name"])}">'
                f'More in {esc(info["name"])}: '
                + " · ".join(f'<a href="{esc(path)}">{esc(label)}</a> ({n})' for label, path, n in facet_pages) + "</nav>")
    body = f"""<div class="page-head"><div class="container">
  <nav class="breadcrumb" aria-label="Breadcrumb"><ol>{crumbs}<li aria-current="page">{esc(info["name"])}</li></ol></nav>
  <header class="titleblock"><div class="titleblock__text">
  <p class="kicker">{esc(group_name + " · " if group_name else "")}{esc(country)}</p>
  <h1>{esc(info["name"])}</h1>
  <p class="page-head__lede">{_plural(len(recs))} in {esc(info["name"])}, {n_gpx} with a GPX here.</p>
  </div></header>
</div></div>
<div class="container section place">
  {home.browse_view(home.listing(recs, top=2, where=""), home.overview_map(recs, f"Map of the trails in {info['name']}", place=bounds.place_box(key)),
               about=f"{summary.facts(recs, records)}{summary.details(recs)}",
               about_title=f"About the trails in {info['name']}")}
  {nav}
</div>"""
    name = info["name"]
    routes = sum(1 for r in recs if common.is_route(r))
    mixed = 0 < routes < len(recs)
    options = []
    if mixed:
        options.append(f"Long Trails in {name}: {_plural(len(recs) - routes, 'Trail')} and {_plural(routes, 'Route')}")
        options.append(f"Long Trails in {name}: {len(recs)} Trails and Routes")
    else:
        options.append(f"Long Trails in {name}: {_plural(len(recs), 'Route' if routes else 'Trail')}")
    options.append(f"Long Trails in {name}")
    title = common.fit_title(options, site)
    by_length = sorted(recs, key=lambda r: (r["length_km"], r["id"]))
    shortest, longest = by_length[0], by_length[-1]
    what = _plural(len(recs), "trail") + (" and routes" if mixed else "")
    if routes == len(recs):
        what = _plural(len(recs), "route")
    gpx = f" {_with_gpx(n_gpx, len(recs))[:1].upper()}{_with_gpx(n_gpx, len(recs))[1:]}." if n_gpx else ""
    if len(recs) == 1:
        first = f"{common.plain_name(longest)}, {_miles(longest)} miles, is the one long trail listed in {name}, {country}."
    else:
        first = (f"{what[:1].upper() + what[1:]} in {name}, {country}, from {common.plain_name(shortest)}, {_miles(shortest)} miles, "
                 f"to {common.plain_name(longest)}, {_miles(longest)} miles.")
    desc = _fit([first + gpx, first, f"{what[:1].upper() + what[1:]} in {name}, {country}.{gpx}"])
    return title, desc, Markup(body), home.has_overview_map(recs)


def route_guides(rec):
    """A route's guides, compact, placed last in its row on /routes/."""
    items = ""
    for g in rec.get("guide", []):
        access = g.get("access", "")
        price = f' · {esc(g["price"])}' if g.get("price") else ""
        fmt = f' · {esc(g["format"])}' if g.get("format") else ""
        items += (f'<li><a href="{esc(g.get("url", ""))}">{esc(g.get("title", ""))}</a>'
                  f' <span class="access access--{esc(access)}">{esc(words.ACCESS.get(access, access))}</span>'
                  f'{fmt}{price}</li>')
    if not items:
        return ""
    return (f'\n  <div class="entry__guides"><p class="route-item__guides-label">Guides</p>'
            f'<ul class="route-guides">{items}</ul></div>')


def routes_page(records, site, repo_root=None, after="", author_pages=None, n_authors=None):
    """(title, description, body, needs_map) for /routes/: the Routes list."""
    routes = [r for r in records if facets.kind(r) == "route"]
    by_author = collections.defaultdict(list)
    for r in routes:
        by_author[facets.author(r) or "Author not named"].append(r)
    linked = author_pages is not None
    author_pages = author_pages or {}
    groups = [(f"By {author_pages[a]}" if a in author_pages else f"By {esc(a)}", sorted(by_author[a], key=home.sort_name), route_guides)
              for a in sorted(by_author, key=str.lower)]
    n_gpx = _gpx_count(routes)
    n_authors_said = n_authors or len(by_author)  # one figure for the intro, the head and the description
    intro = f"""<p>Every other trail on this site is an official trail. Being a route says who looks after it, not
  how rough it is: some routes are on maintained trail all the way, and some official trails have
  long road walks. The Walking line on each trail&rsquo;s page says what the walking is.</p>
  <p>{_plural(len(routes), "route")}, by {n_authors_said} authors. {n_gpx} {"has" if n_gpx == 1 else "have"} a GPX here; for the rest,
  each route&rsquo;s page says whether its author gives the track away, sells it, or does not publish it.</p>"""
    head_count = (f'\n  <p class="page-head__lede">{_plural(len(routes), "route")} by <a href="/authors/">{_plural(n_authors, "author")}</a></p>'
                  if n_authors else "")
    body = f"""<div class="page-head"><div class="container">
  <nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="/">Trails</a></li>
  <li><a href="/lists/">Lists</a></li><li aria-current="page">Routes</li></ol></nav>
  <header class="titleblock"><div class="titleblock__text"><p class="kicker">A list</p><h1>Routes</h1>
  <p class="page-head__lede" id="what-is-a-route">{esc(facets.ROUTE_DEFINITION)}</p>{head_count}
  </div></header></div></div>
<div class="container section place">
  {home.browse_view(home.listing(groups=groups, routes_list=True, top=2), home.overview_map(routes, "Map of the routes with a GPX here"),
               about=intro, about_title="About routes")}
  {after}
  <nav class="region-nav" aria-label="Other lists">{'<a href="/authors/">Route authors</a> · ' if linked else ""}<a href="/lists/">All lists</a> · <a href="/">Every trail</a></nav>
</div>"""
    description = (f"{_plural(len(routes), 'route')} in the United States and Canada by {n_authors_said} authors, "
                   f"with their guides{f' and {n_gpx} with a GPX here' if n_gpx else ''}.")
    return (browse.by_key("routes").search_title(len(routes)), common.cut_at_word(description, common.DESCRIPTION_LIMIT),
            Markup(body), home.has_overview_map(routes))


def list_page(lst, recs, total, site, *, records=None, before="", after="", lead=None):
    """(title, description, body, needs_map) for /lists/<key>/.

    records: every trail, for the summary and the note. before: HTML added to the text about the
    list, after the summary (what its figures mean); after: HTML placed under it (links to related
    lists, places and terms). lead: a figure to lead each row's line of facts (home.results)."""
    n_gpx = _gpx_count(recs)
    rule = (f"Lists are picked out by rule from each trail&rsquo;s facts, so they change as trails are added "
            f"or corrected. A list is shown when it has at least {browse.MIN_SIZE} trails and no more than "
            f"{round(browse.MAX_SHARE * 100)}% of the {total}.")
    note = lst.note(recs, records) if lst.note and records is not None else ""
    note = f" {esc(note)}" if note else ""
    about = summary.facts(recs, records) if records is not None else ""
    body = f"""<div class="page-head"><div class="container">
  <nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="/">Trails</a></li>
  <li><a href="/lists/">Lists</a></li><li aria-current="page">{esc(lst.title)}</li></ol></nav>
  <header class="titleblock"><div class="titleblock__text">
  <p class="kicker">A list</p>
  <h1>{esc(lst.title)}</h1>
  <p class="page-head__lede">{esc(lst.blurb)} {_plural(len(recs))}, {n_gpx} with a GPX here.</p>
  </div></header>
</div></div>
<div class="container section place">
  {home.browse_view(home.listing(recs, default_sort=lst.sort, top=2, lead=lead),
               home.overview_map(recs, f"Map of the trails in the list {lst.title}"),
               about=f"{about}{before}{f'<p>{esc(note.strip())}</p>' if note else ''}<p class=\"finder__foot\">{rule}</p>",
               about_title="About this list")}
  {after}
  <nav class="region-nav" aria-label="Other lists"><a href="/lists/">All lists</a> · <a href="/">Every trail</a></nav>
</div>"""
    by_length = sorted(recs, key=lambda r: (r["length_km"], r["id"]))
    stats = [f" {_plural(len(recs))}, from {common.plain_name(by_length[0])}, {_miles(by_length[0])} miles, "
             f"to {common.plain_name(by_length[-1])}, {_miles(by_length[-1])} miles; {_with_gpx(n_gpx, len(recs)) or 'none with a GPX here'}.",
             f" {_plural(len(recs))}, {_with_gpx(n_gpx, len(recs)) or 'none with a GPX here'}.", f" {_plural(len(recs))}."]
    desc = _fit([lst.blurb + s for s in stats] + [lst.blurb])
    return lst.search_title(len(recs)), desc, Markup(body), home.has_overview_map(recs)


def lists_index_page(records, site, extras=()):
    """(title, description, body) for /lists/: every list shown today, under its heading, and the
    other ways in (tables, authors, reference pages) that pages.py hands over as extras.

    extras: [(group key, title, blurb, path, how many)] for pages that are not lists."""
    shown = browse.shown(records)
    sections = ""
    for key, heading, intro in browse.GROUPS + EXTRA_GROUPS:
        items = [(lst.title, lst.blurb, browse.path(lst), len(recs)) for lst, recs in shown if lst.group == key]
        items += [(t, b, path, n) for g, t, b, path, n in extras if g == key]
        if not items:
            continue
        cards = "".join(f"""<li class="shelf">
        <h3 class="shelf__title"><a href="{esc(path)}">{esc(title)}</a>{f' <span class="shelf__count">{n}</span>' if n else ""}</h3>
        <p class="shelf__blurb">{esc(blurb)}</p>
      </li>""" for title, blurb, path, n in items)
        sections += f"""<section class="lists-group" aria-labelledby="group-{esc(key)}">
  <h2 id="group-{esc(key)}">{esc(heading)}</h2>
  <p class="places__sum">{esc(intro)}</p>
  <ul class="shelves">{cards}</ul>
</section>"""
    body = f"""<div class="page-head"><div class="container">
  <nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="/">Trails</a></li><li aria-current="page">Lists</li></ol></nav>
  <header class="titleblock"><div class="titleblock__text"><h1>Lists</h1>
  <p class="page-head__lede">Ready-made selections of the {len(records)} trails, and the tables and reference pages
  built from them. Each list is picked out by rule from what each trail&rsquo;s page says, so it grows as trails are added.</p>
  </div></header></div></div>
<div class="container section place">{sections}
<p class="finder__foot">A list is shown when it has at least {browse.MIN_SIZE} trails and no more than
{round(browse.MAX_SHARE * 100)}% of all of them. To combine conditions, use the filters on <a href="/">the home page</a>.</p></div>"""
    desc = (f"{len(shown)} ready-made lists of the {len(records)} long trails, each picked out by rule from the records: "
            f"by length, time to walk, month, terrain, who looks after it and type, with tables and a glossary.")
    return "Long Hiking Trail Lists: Length, Time and Terrain", common.cut_at_word(desc, common.DESCRIPTION_LIMIT), Markup(body)


# Headings for the pages that are not lists, after the lists' own (olt/browse.py GROUPS).
EXTRA_GROUPS = (
    ("tables", "Tables and rankings", "The trails laid side by side and ranked, with the caveats that go with each figure."),
    ("changes", "What is new", "The newest trails and the newest changes to them."),
    ("reference", "Reference", "What the words mean, and how the figures are measured."),
)
