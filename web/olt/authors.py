"""Route authors: /authors/ and a page for every author who has at least one route.

A route's author is the free text of its [route].creator. authors.toml names a person (or an
organisation) with each exact credit that names them, so one page can list every route credited
to them, in any form. A credit that names two or more people appears under each of them, so the
route is on each page, and each page says who else is credited. A credit that authors.toml does
not list stands alone as its own author, and is not typed as a person. Where a route is
published comes from its [[guide]] entries.

PROMINENT_MIN is the number of routes at which an author is shown at the top of /authors/,
in a block of their own, instead of in the alphabetical list below it. Change it here and the
page follows: an author who reaches it moves up with no other change.
"""
import re
import urllib.parse

from . import common, datafiles, facets, hike, home, pagekit, regions, seo, summary, trail, words
from .markup import Markup, esc

INDEX = "/authors/"
PROMINENT_MIN = 3
NOT_NAMED = "Author not named"
TITLE_LIMIT = 60  # the page's own title, before the site name


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def groups(records, repo_root):
    """[{name, slug, kind, credits, routes, others}] for every route author, sorted by name.
    kind: "person" or "organisation" as authors.toml says, "" for a credit it does not list.
    others: {route id: [the other authors the route's credit names]}."""
    entries = {a["name"]: a for a in datafiles.authors(repo_root)}
    named = {}  # credit -> [author names in authors.toml order]
    for a in datafiles.authors(repo_root):
        for c in a.get("credits", []):
            named.setdefault(c, []).append(a["name"])
    by_name = {}
    for r in (r for r in records if facets.kind(r) == "route"):
        credit = facets.author(r) or NOT_NAMED
        names = named.get(credit) or [credit]
        for name in names:
            g = by_name.setdefault(name, {"name": name, "slug": slug(name), "kind": entries.get(name, {}).get("kind", "person") if name in entries else "",
                                          "credits": set(), "routes": [], "others": {}})
            g["credits"].add(credit)
            g["routes"].append(r)
            g["others"][r["id"]] = [n for n in names if n != name]
    out = sorted(by_name.values(), key=lambda g: g["name"].lower())
    for g in out:
        g["routes"].sort(key=home.sort_name)
    return out


def author_pages(records, repo_root):
    """Every author with a route has a page; a route with no author named has none to give."""
    return [g for g in groups(records, repo_root) if g["name"] != NOT_NAMED]


def prominent(gs):
    """The authors at or above PROMINENT_MIN routes, most routes first, then by name."""
    return sorted((g for g in gs if len(g["routes"]) >= PROMINENT_MIN), key=lambda g: (-len(g["routes"]), g["name"].lower()))


def path(g):
    return f"{INDEX}{g['slug']}/"


def link_map(records, repo_root):
    """{credit: [(author name, page path)]} for each credit on a route, for the credit's own words on a route page."""
    out = {}
    for g in author_pages(records, repo_root):
        for c in g["credits"]:
            out.setdefault(c, []).append((g["name"], path(g)))
    return out


def credit_html(credit, links):
    """The credit as the record writes it, with each author's name in it a link to their page."""
    text = esc(credit)
    for name, href in links or []:
        n = esc(name)
        if n in text:
            text = text.replace(n, f'<a href="{esc(href)}">{n}</a>', 1)
    return Markup(text)


def guide_text(rec):
    """Where a route is published: its guides, each as a link with its format and whether it is free."""
    items = []
    for g in rec.get("guide", []):
        fmt = f", {esc(g['format'])}" if g.get("format") else ""
        access = words.ACCESS.get(g.get("access", ""), "").lower()
        items.append(f'<a href="{esc(g.get("url", ""))}">{esc(g.get("title", ""))}</a> ({access}{fmt})'.replace("( ", "("))
    return Markup("; ".join(items)) if items else "Not published as a guide"


def year_text(rec):
    y = rec.get("route", {}).get("year")
    return str(y) if y else "Not on file"


def _miles(rec):
    return f'{words.fmt_int(rec["derived"]["length_mi"])} miles ({words.fmt_km(rec["length_km"])} km)'


def _plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def own_sites(g):
    """[(host, url)] where the records give the author's own page: a guide they wrote and publish
    themselves (no other publisher), or the page their own words were read on."""
    found = {}
    for r in g["routes"]:
        for gd in r.get("guide", []):
            if gd.get("url") and not gd.get("publisher") and any(c.lower() in gd.get("author", "").lower() for c in (g["name"],)):
                found.setdefault(urllib.parse.urlparse(gd["url"]).hostname or gd["url"], gd["url"])
        route = r.get("route", {})
        if route.get("creator_words_url") and not route.get("creator_words_by") and g["name"] in route.get("creator", "") \
                and not g["others"].get(r["id"]):
            found.setdefault(urllib.parse.urlparse(route["creator_words_url"]).hostname or "", route["creator_words_url"])
    return sorted(found.items())


def _route_line(rec):
    return f'<a href="{esc(common.trail_path(rec))}">{esc(common.plain_name(rec))}</a> ({esc(words.fmt_int(rec["derived"]["length_mi"]))} miles)'


def _route_links(g):
    return ", ".join(_route_line(r) for r in g["routes"])


def _block(g):
    """A prominent author as a card, in the style of the lists index: name, route count, each
    route with its length (which follows the units switch), and a link to their page."""
    n = len(g["routes"])
    items = "".join(f'<li><a href="{esc(common.trail_path(r))}">{esc(common.plain_name(r))}</a>'
                    f'<span class="shelf__len">{words.length(r["length_km"], mi=r["derived"]["length_mi"])}</span></li>'
                    for r in g["routes"])
    return (f'<li class="shelf shelf--author">\n'
            f'  <h3 class="shelf__title"><a href="{esc(path(g))}">{esc(g["name"])}</a>'
            f' <span class="shelf__count" title="Routes on this site">{n}</span></h3>\n'
            f'  <ul class="shelf__items">{items}</ul>\n'
            f'  <p class="shelf__more"><a href="{esc(path(g))}">All {n} routes by {esc(g["name"])}</a></p>\n</li>')


def index_page(records, site, repo_root):
    """(title, description, body, routes) for /authors/."""
    gs = author_pages(records, repo_root)
    routes = [r for r in records if facets.kind(r) == "route"]
    top = prominent(gs)
    rest = [g for g in gs if g not in top]
    n_gpx = sum(1 for r in routes if facets.gpx_here(r))
    lede = (f"{len(routes)} long hiking routes, worked out by {len(gs)} authors. "
            f"Every author has a page of their own, with their routes and where each is published. "
            f"{n_gpx} of the routes {'has' if n_gpx == 1 else 'have'} a GPX here. {esc(facets.ROUTE_DEFINITION)}")
    sections = ""
    if top:
        blocks = "\n".join(_block(g) for g in top)
        sections += (f'<h2 id="most-routes">Authors with {PROMINENT_MIN} or more routes</h2>\n'
                     f'<p class="note">{_plural(len(top), "author")}, the most routes first.</p>\n'
                     f'<ul class="shelves shelves--wide">\n{blocks}\n</ul>\n')
    if rest:
        items = "\n".join(f'<li><a href="{esc(path(g))}">{esc(g["name"])}</a>, {_route_links(g)}</li>' for g in rest)
        heading = "Other authors" if top else "All authors"
        sections += f'<h2 id="other-authors">{heading}</h2>\n<ul class="author-list">\n{items}\n</ul>\n'
    rows = []
    for g in gs:
        first = True
        for r in g["routes"]:
            rows.append([Markup(f'<a href="{esc(path(g))}">{esc(g["name"])}</a>') if first else "", pagekit.trail_link(r), year_text(r),
                         words.length(r["length_km"], mi=r["derived"]["length_mi"]), facets.GPX_STATUS[facets.gpx(r)], guide_text(r)])
            first = False
    body = (pagekit.head("Route authors", lede, [("Trails", "/"), ("Lists", "/lists/"), ("Routes", "/routes/")])
            + f"""<div class="container section place">
  {sections}
  <h2 id="every-route">Every route, with its author</h2>
  {pagekit.table(["Author", "Route", "Year", "Length", "GPX", "Published in"], rows, caption="Routes by author")}
  <p class="finder__foot">A route credited to several people is listed under each of them. An author credited in more than one form is
  listed once, under the name authors.toml gives. Guides marked free are free; the rest are bought from the author or publisher.</p>
  <nav class="region-nav" aria-label="Related pages"><a href="/routes/">Routes with their guides</a> ·
  <a href="/glossary/#route">What a route is</a> · <a href="/lists/">All lists</a></nav>
</div>""")
    title = "Long Hiking Route Authors: Who Published Which Route"
    desc = common.cut_at_word(f"{len(routes)} long hiking routes by {len(gs)} authors. Who has published the most routes, "
                              "with each route's length and where it is published.", common.DESCRIPTION_LIMIT)
    return title, desc, Markup(body), routes


def author_page(g, records, site, all_pages):
    """(title, description, body, needs_map, routes, jsonld) for /authors/<slug>/."""
    routes = g["routes"]
    n = len(routes)
    credits = sorted(g["credits"], key=str.lower)
    lengths = [r["derived"]["length_mi"] for r in routes]
    if n == 1:
        lede = f"{esc(g['name'])} is credited with {esc(common.plain_name(routes[0]))}, {esc(_miles(routes[0]))}."
    else:
        lede = (f"{esc(g['name'])} is credited with {n} routes on this site, from {esc(words.fmt_int(min(lengths)))} "
                f"to {esc(words.fmt_int(max(lengths)))} miles.")
    forms = [c for c in credits if c != g["name"]]
    if forms:
        lede += " The records credit them as " + words.join_names(f"“{esc(c)}”" for c in forms) + "."
    sites = own_sites(g)
    if sites:
        lede += " Their own page: " + "; ".join(f'<a href="{esc(u)}">{esc(h)}</a>' for h, u in sites) + "."
    show_credit = any(r["route"].get("creator") != g["name"] for r in routes)
    rows = []
    for r in routes:
        cells = [pagekit.trail_link(r), words.length(r["length_km"], mi=r["derived"]["length_mi"]),
                 trail.place_text(r).removeprefix("in "), hike.days(r) or "Not on file", guide_text(r)]
        if show_credit:
            credit = r["route"].get("creator", "")
            cells.append(esc(credit) if credit != g["name"] else "")
        rows.append(cells)
    heads = ["Route", "Length", "Where it runs", "Usual time", "Published in"] + (["Credited as"] if show_credit else [])
    shared = [r for r in routes if g["others"].get(r["id"])]
    shared_note = ""
    if shared:
        by_name = {x["name"]: x for x in all_pages}
        lines = []
        for r in shared:
            people = [f'<a href="{esc(path(by_name[o]))}">{esc(o)}</a>' if o in by_name else esc(o) for o in g["others"][r["id"]]]
            lines.append(f'{esc(common.plain_name(r))}: also credited to {words.join_names(people)}.')
        shared_note = '<p class="note">' + " ".join(lines) + "</p>"
    briefs = "".join(f'<h3><a href="{esc(common.trail_path(r))}">{esc(common.plain_name(r))}</a></h3>\n{trail.brief(r)}\n' for r in routes)
    nav_items = [x for x in prominent(all_pages) if x is not g]
    nav = (f'<nav class="region-nav" aria-label="Authors with the most routes">Authors with the most routes: '
           + " · ".join(f'<a href="{esc(path(x))}">{esc(x["name"])}</a> ({len(x["routes"])})' for x in nav_items) + "</nav>") if nav_items else ""
    more = (f'<div class="prose place-summary">{summary.facts(routes, records)}</div>' if n >= 3 else "")
    body = (pagekit.head(f"Routes by {g['name']}", lede, [("Trails", "/"), ("Lists", "/lists/"), ("Authors", INDEX)])
            + f"""<div class="container section place">
  <h2 id="routes">{'The route' if n == 1 else 'The routes'}</h2>
  {pagekit.table(heads, rows, caption=f"Routes by {g['name']}")}
  {shared_note}
  <h2 id="in-brief">{'About the route' if n == 1 else 'About each route'}</h2>
  {briefs}
  {more}
  {home.overview_map(routes, f"Map of the routes by {g['name']}")}
  {nav}
  <nav class="region-nav" aria-label="Related pages"><a href="/routes/">All routes</a> · <a href="{INDEX}">All route authors</a></nav>
</div>""")
    name = g["name"]
    options = [f"Routes by {name}: {_plural(n, 'Long Hiking Route')}", f"Routes by {name}"]
    title = next((o for o in options if len(o) <= TITLE_LIMIT), common.cut_at_word(options[-1], TITLE_LIMIT))
    desc = regions._fit([f"{_plural(n, 'long hiking route')} by or with {name}, with length, where it runs, usual time and where it is published.",
                         f"{_plural(n, 'route')} by {name}."])
    return title, desc, Markup(body), home.has_overview_map(routes), routes, person_jsonld(g, site, sites)


def person_jsonld(g, site, sites):
    """The author as a Person, only where authors.toml says the credit is a person."""
    if g["kind"] != "person":
        return None
    node = {"@type": "Person", "@id": seo.url_of(site, path(g)) + "#author", "name": g["name"],
            "url": sites[0][1] if sites else None, "sameAs": [u for _, u in sites] or None}
    return seo._clean(node)
