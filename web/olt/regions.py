"""Places (/regions/, /regions/<state or province>/), lists (/lists/, /lists/<key>/) and
the Routes list (/routes/).

Every page lists trails with home.results(), the same rows the home page shows.
The section is called Places; its pages keep their /regions/ URLs.
"""
import collections

from . import browse, common, facets, home, words
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
        jump.append(f'<li><a href="#{esc(g)}">{esc(name)} <span class="chips__n">{len(recs)}</span></a></li>')
        rows = "".join(
            f'<li><a href="{esc(facets.place_path(i["key"]))}">{esc(i["name"])}</a>'
            f'<span class="places__n">{_plural(len(i["records"]))}</span></li>'
            for i in infos)
        blocks += f"""<section class="places__group" aria-labelledby="{esc(g)}">
  <h2 id="{esc(g)}">{esc(name)}</h2>
  <p class="places__sum">{_plural(len(recs))}, {_gpx_count(recs)} with a GPX here.
  <a href="/?where=g:{esc(g)}">See them with the filters</a></p>
  <ul class="places__list">{rows}</ul>
</section>"""
    if across:
        links = ", ".join(f'<a href="{esc(common.trail_path(r))}">{common.name(r)}</a>' for r in across)
        jump.append(f'<li><a href="#across-canada">{facets.ACROSS_CANADA_NAME} <span class="chips__n">{len(across)}</span></a></li>')
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
  <ul class="chips" aria-label="Jump to a part of the country">{"".join(jump)}</ul></div></div>
<div class="container section places">{blocks}</div>"""
    description = (f"Where the {len(records)} long trails and routes are: {n_us} in the United States and {n_ca} in Canada, "
                   f"by state and province, with the number in each.")
    return "Long Trails by State and Province: US and Canada", common.cut_at_word(description, common.DESCRIPTION_LIMIT), Markup(body)


def region_page(slug, records, site):
    """(title, description, body, needs_map) for /regions/<slug>/: the trails in one state or province."""
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
        crumbs += f'<li><a href="/regions/#{esc(group)}">{esc(group_name)}</a></li>'
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
    body = f"""<div class="page-head"><div class="container">
  <nav class="breadcrumb" aria-label="Breadcrumb"><ol>{crumbs}<li aria-current="page">{esc(info["name"])}</li></ol></nav>
  <header class="titleblock"><div class="titleblock__text">
  <p class="kicker">{esc(group_name + " · " if group_name else "")}{esc(country)}</p>
  <h1>{esc(info["name"])}</h1>
  <p class="page-head__lede">{_plural(len(recs))} in {esc(info["name"])}, {n_gpx} with a GPX here.
  <a href="/?where={esc(key)}">Narrow them with the filters</a>.</p>
  </div></header>
</div></div>
<div class="container section place">
  {home.overview_map(recs, f"Map of the trails in {info['name']}")}
  {home.results(recs, top=2)}
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


def routes_page(records, site, repo_root=None):
    """(title, description, body, needs_map) for /routes/: the Routes list."""
    routes = [r for r in records if facets.kind(r) == "route"]
    by_author = collections.defaultdict(list)
    for r in routes:
        by_author[facets.author(r) or "Author not named"].append(r)
    groups = [(f"By {esc(a)}", sorted(by_author[a], key=home.sort_name), route_guides)
              for a in sorted(by_author, key=str.lower)]
    n_gpx = _gpx_count(routes)
    body = f"""<div class="page-head"><div class="container">
  <nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="/">Trails</a></li>
  <li><a href="/lists/">Lists</a></li><li aria-current="page">Routes</li></ol></nav>
  <header class="titleblock"><div class="titleblock__text"><p class="kicker">A list</p><h1>Routes</h1>
  <p class="page-head__lede" id="what-is-a-route">{esc(facets.ROUTE_DEFINITION)}</p>
  </div></header></div></div>
<div class="container section">
  <div class="prose">
  <p>Every other trail on this site is an official trail. Being a route says who looks after it, not
  how rough it is: some routes are on maintained trail all the way, and some official trails have
  long road walks. The Walking line on each trail&rsquo;s page says what the walking is.</p>
  <p>{_plural(len(routes), "route")}, by {len(by_author)} authors. {n_gpx} {"has" if n_gpx == 1 else "have"} a GPX here; for the rest,
  each route&rsquo;s page says whether its author gives the track away, sells it, or does not publish it.
  <a href="/?kind=route">Narrow them with the filters</a>.</p>
  </div>
</div>
<div class="container section">
  {home.overview_map(routes, "Map of the routes with a GPX here")}
  {home.results(groups=groups, routes_list=True, top=2)}
  <nav class="region-nav" aria-label="Other lists"><a href="/lists/">All lists</a> · <a href="/">Every trail</a></nav>
</div>"""
    description = (f"{_plural(len(routes), 'route')} in the United States and Canada by {len(by_author)} authors, "
                   f"with their guides{f' and {n_gpx} with a GPX here' if n_gpx else ''}.")
    return (browse.by_key("routes").search_title(len(routes)), common.cut_at_word(description, common.DESCRIPTION_LIMIT),
            Markup(body), home.has_overview_map(routes))


def list_page(lst, recs, total, site):
    """(title, description, body, needs_map) for /lists/<key>/."""
    n_gpx = _gpx_count(recs)
    rule = (f"Lists are picked out by rule from each trail&rsquo;s facts, so they change as trails are added "
            f"or corrected. A list is shown when it has at least {browse.MIN_SIZE} trails and no more than "
            f"{round(browse.MAX_SHARE * 100)}% of the {total}.")
    body = f"""<div class="page-head"><div class="container">
  <nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="/">Trails</a></li>
  <li><a href="/lists/">Lists</a></li><li aria-current="page">{esc(lst.title)}</li></ol></nav>
  <header class="titleblock"><div class="titleblock__text">
  <p class="kicker">A list</p>
  <h1>{esc(lst.title)}</h1>
  <p class="page-head__lede">{esc(lst.blurb)} {_plural(len(recs))}, {n_gpx} with a GPX here.</p>
  </div></header>
</div></div>
<div class="container section">
  {home.overview_map(recs, f"Map of the trails in the list {lst.title}")}
  {home.results(recs, default_sort=lst.sort, top=2)}
  <p class="finder__foot">{rule}</p>
  <nav class="region-nav" aria-label="Other lists"><a href="/lists/">All lists</a> · <a href="/">Every trail</a></nav>
</div>"""
    by_length = sorted(recs, key=lambda r: (r["length_km"], r["id"]))
    stats = [f" {_plural(len(recs))}, from {common.plain_name(by_length[0])}, {_miles(by_length[0])} miles, "
             f"to {common.plain_name(by_length[-1])}, {_miles(by_length[-1])} miles; {_with_gpx(n_gpx, len(recs)) or 'none with a GPX here'}.",
             f" {_plural(len(recs))}, {_with_gpx(n_gpx, len(recs)) or 'none with a GPX here'}.", f" {_plural(len(recs))}."]
    desc = _fit([lst.blurb + s for s in stats] + [lst.blurb])
    return lst.search_title(len(recs)), desc, Markup(body), home.has_overview_map(recs)


def lists_index_page(records, site):
    """(title, description, body) for /lists/: every list shown today, with a few of its trails."""
    cards = []
    for lst, recs in browse.shown(records):
        sample = "".join(
            f'<li><a href="{esc(common.trail_path(r))}">{common.name(r)}</a> '
            f'<span class="shelf__len">{words.length(r["length_km"], "short", r["derived"]["length_mi"])}</span></li>'
            for r in recs[:4])
        cards.append(f"""<li class="shelf">
        <h2 class="shelf__title"><a href="{esc(browse.path(lst))}">{esc(lst.title)}</a> <span class="shelf__count">{len(recs)}</span></h2>
        <p class="shelf__blurb">{esc(lst.blurb)}</p>
        <ul class="shelf__items">{sample}</ul>
        <p class="shelf__more"><a href="{esc(browse.path(lst))}">See all {len(recs)}<span class="vh">: {esc(lst.title)}</span></a></p>
      </li>""")
    body = f"""<div class="page-head"><div class="container">
  <nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="/">Trails</a></li><li aria-current="page">Lists</li></ol></nav>
  <header class="titleblock"><div class="titleblock__text"><h1>Lists</h1>
  <p class="page-head__lede">Ready-made selections of the {len(records)} trails, a way to start. Each is
  picked out by rule from what each trail&rsquo;s page says, so a list grows as trails are added.</p>
  </div></header></div></div>
<div class="container section"><ul class="shelves">{"".join(cards)}</ul>
<p class="finder__foot">A list is shown when it has at least {browse.MIN_SIZE} trails and no more than
{round(browse.MAX_SHARE * 100)}% of all of them. To combine conditions, use the filters on <a href="/">the home page</a>.</p></div>"""
    shown = browse.shown(records)
    desc = (f"{len(shown)} ready-made lists of the {len(records)} long trails, each picked out by rule from the records: "
            f"by length, time, terrain, type and country.")
    return "Long Hiking Trail Lists: Length, Terrain and Type", common.cut_at_word(desc, common.DESCRIPTION_LIMIT), Markup(body)
