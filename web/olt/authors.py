"""Route authors: /authors/ and a page for every author who has at least one route.

A route's author is the free text of its [route].creator. authors.toml names a person (or an
organisation) with each exact credit that names them, so one page can list every route credited
to them, in any form. A credit that names two or more people appears under each of them, so the
route is on each page, and that route's row says who else is credited. A credit that authors.toml
does not list stands alone as its own author, and is not typed as a person. Where a route is
published comes from its [[guide]] entries.

The words about an author (summary, bio, url, and the sources they were read on) are for people
only (kind "person", or "people" for a pair or a person known by a blog's name): an organisation's
page lists its routes and nothing more.

PROMINENT_MIN is the number of routes at which a person is shown at the top of /authors/, under
their own heading with their routes as rows, instead of in the alphabetical list below it. Change
it here and the page follows: a person who reaches it moves up with no other change.
"""
import datetime
import re
import urllib.parse

from . import common, datafiles, facets, hike, home, pagekit, regions, seo, summary, trail, words
from .markup import Markup, esc

INDEX = "/authors/"
PROMINENT_MIN = 3
NOT_NAMED = "Author not named"
TITLE_LIMIT = 60  # the page's own title, before the site name
HUMAN = ("person", "people")  # the kinds that are people, and may carry a summary and a bio


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def groups(records, repo_root):
    """[{name, slug, kind, entry, credits, routes, others}] for every route author, sorted by name.
    kind: "person", "people" or "organisation" as authors.toml says, "" for a credit it does not
    list. entry: the authors.toml entry ({} for none). others: {route id: [the other authors the
    route's credit names]}."""
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
            entry = entries.get(name, {})
            g = by_name.setdefault(name, {"name": name, "slug": slug(name), "kind": entry.get("kind", "person") if entry else "",
                                          "entry": entry, "credits": set(), "routes": [], "others": {}})
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


def is_human(g):
    """A person or people, as authors.toml says: not an organisation, and not a credit it does not list."""
    return g["kind"] in HUMAN


def about(g):
    """The words about a person from authors.toml: {summary, bio, url, checked, sources}. Empty for
    an organisation or a credit with no entry, whatever the file says (the checker refuses it too)."""
    e = g.get("entry") or {}
    if not is_human(g):
        return {}
    return {"summary": e.get("summary", ""), "bio": e.get("bio", ""), "url": e.get("url", ""),
            "checked": e.get("checked"), "sources": e.get("source", [])}


def prominent(gs):
    """The people at or above PROMINENT_MIN routes, most routes first, then by name. Only people
    lead: an organisation, or a credit with no entry, is never here however many routes it has."""
    return sorted((g for g in gs if is_human(g) and len(g["routes"]) >= PROMINENT_MIN),
                  key=lambda g: (-len(g["routes"]), g["name"].lower()))


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


def _host(url):
    host = urllib.parse.urlparse(url).hostname or url
    return host[4:] if host.startswith("www.") else host


def own_site(g):
    """(text, url) of the author's own site: the entry's url, else the one the records give; None."""
    url = about(g).get("url")
    if url:
        return _host(url), url
    sites = own_sites(g)
    return (_host(sites[0][1]), sites[0][1]) if sites else None


def range_text(g):
    """"5 routes" and "77 to 6,875 miles", or for one route "1 route" and "77 miles" (miles first)."""
    lengths = [r["derived"]["length_mi"] for r in g["routes"]]
    lo, hi = words.fmt_int(min(lengths)), words.fmt_int(max(lengths))
    return _plural(len(lengths), "route"), (f"{hi} miles" if lo == hi else f"{lo} to {hi} miles")


def fact_lede(g):
    """The plain sentence of fact an author's page opens with where there is no summary. It names
    the author and never stands in for them with a pronoun."""
    routes = g["routes"]
    if len(routes) == 1:
        return f"{g['name']} is credited with one route on this site, {common.plain_name(routes[0])}, {_miles(routes[0])}."
    count, span = range_text(g)
    return f"{g['name']} is credited with {count} on this site, from {span}."


def with_html(g, rec, by_name):
    """A row's author line on an author's page: who else the route is credited to ("With Ryan
    Jordan", each linked to their page), or "" where the route is this author's alone. The rest of
    a credit that names no one else in full ("and collaborators") is given as written."""
    others = g["others"].get(rec["id"], [])
    if others:
        names = [f'<a href="{esc(path(by_name[o]))}">{esc(o)}</a>' if o in by_name else esc(o) for o in others]
        return Markup("With " + words.join_names(names))
    credit = facets.author(rec) or ""
    rest = credit.replace(g["name"], "", 1) if g["name"] in credit else ""
    if " and " in rest:
        return Markup("With " + esc(rest.split(" and ", 1)[1].strip()))
    return ""


def _route_line(rec):
    return f'<a href="{esc(common.trail_path(rec))}">{esc(common.plain_name(rec))}</a> ({esc(words.fmt_int(rec["derived"]["length_mi"]))} miles)'


def _route_links(g):
    return ", ".join(_route_line(r) for r in g["routes"])


def _index_item(g):
    """An author in the list under the leading ones: the name, the summary where there is one, the routes."""
    summary = about(g).get("summary")
    line = f'<p class="author-list__summary">{esc(summary)}</p>' if summary else ""
    return (f'<li><a class="author-list__name" href="{esc(path(g))}">{esc(g["name"])}</a>{line}'
            f'<p class="author-list__routes">{_route_links(g)}</p></li>')


def index_page(records, site, repo_root):
    """(title, description, body, routes) for /authors/."""
    gs = author_pages(records, repo_root)
    routes = [r for r in records if facets.kind(r) == "route"]
    top = prominent(gs)
    # The others, alphabetically; organisations last, as plainly as the rest.
    rest = sorted((g for g in gs if g not in top), key=lambda g: (g["kind"] == "organisation", g["name"].lower()))
    n_gpx = sum(1 for r in routes if facets.gpx_here(r))
    lede = f"{len(routes)} long hiking routes, worked out by {len(gs)} authors, each with a page of their own."
    lede_more = (f"<p>Every author has a page with their routes and where each is published. "
                 f"{n_gpx} of the routes {'has' if n_gpx == 1 else 'have'} a GPX here. {esc(facets.ROUTE_DEFINITION)}</p>")
    # The people with the most routes lead the page: each under their own name, with the sentence
    # that says who they are, their routes as the site's rows, and every route on the map beside them.
    groups = [((f'<a href="{esc(path(g))}">{esc(g["name"])}</a> <span class="results__n">{_plural(len(g["routes"]), "route")}</span>',
                esc(about(g).get("summary", ""))), g["routes"], regions.route_guides) for g in top]
    rest_html = ""
    if rest:
        items = "\n".join(_index_item(g) for g in rest)
        heading = "Other authors" if top else "All authors"
        rest_html = f'<ul class="author-list" aria-label="{heading}">\n{items}\n</ul>\n'
    listing = home.results(groups=groups, routes_list=True, top=2) if top else ""
    about_text = (f"<p>{_plural(len(top), 'author')} with {PROMINENT_MIN} or more routes are above, the most routes first. "
                  "A route credited to several people is listed under each of them. An author credited in more than one form is "
                  "listed once, under the name authors.toml gives. Guides marked free are free; the rest are bought from the "
                  "author or publisher.</p>")
    body = (pagekit.head("Route authors", lede, [("Trails", "/"), ("Lists", "/lists/"), ("Routes", "/routes/")])
            + f"""<div class="container section place">
  <h2 class="vh" id="most-routes">Authors with {PROMINENT_MIN} or more routes</h2>
  {home.browse_view(listing, home.overview_map(routes, "Map of every route"), about=rest_html + about_text + lede_more, about_title="Other authors") if top else rest_html}
  <nav class="region-nav" aria-label="Related pages"><a href="/routes/">Routes with their guides</a> ·
  <a href="/glossary/#route">What a route is</a> · <a href="/lists/">All lists</a></nav>
</div>""")
    title = "Long Hiking Route Authors: Who Published Which Route"
    desc = common.cut_at_word(f"{len(routes)} long hiking routes by {len(gs)} authors. Who has published the most routes, "
                              "with each route's length and where it is published.", common.DESCRIPTION_LIMIT)
    return title, desc, Markup(body), routes


def _date_text(value):
    return value.isoformat() if isinstance(value, datetime.date) else str(value or "")


def source_links(sources):
    """Each publisher once, in order of first appearance: one page is a link on the name; more are the
    name then numbered links, "The Trek (1, 2)"."""
    pages = {}
    for x in sources:
        pages.setdefault(x.get("publisher", ""), []).append(x.get("url", ""))
    out = []
    for pub, urls in pages.items():
        if len(urls) == 1:
            out.append(f'<a href="{esc(urls[0])}">{esc(pub)}</a>')
        else:
            nums = ", ".join(f'<a href="{esc(u)}">{i}</a>' for i, u in enumerate(urls, 1))
            out.append(f"{esc(pub)} ({nums})")
    return out


def about_html(g):
    """The bio paragraph and, in small print, the pages it was read on and the date it was checked;
    "" where there is no bio (every organisation)."""
    a = about(g)
    if not a.get("bio"):
        return ""
    sources = source_links(a["sources"])
    checked = _date_text(a.get("checked"))
    small = []
    if sources:
        small.append("Read on " + words.join_names(sources) + ".")
    if checked:
        small.append(f'Checked <time datetime="{esc(checked)}">{esc(checked)}</time>.')
    note = f'\n<p class="author-about__sources">{" ".join(small)}</p>' if small else ""
    return f'<p class="author-about__bio">{esc(a["bio"])}</p>{note}'


def author_page(g, records, site, all_pages):
    """(title, description, body, needs_map, routes, jsonld) for /authors/<slug>/.

    The head is the author's name, the summary sentence that says who they are (or, with none, a
    plain sentence of fact), and one quiet line: the routes, their range, and the author's own
    site. The routes follow as the site's rows beside the map; a route credited to others too says
    so in its own row, and nowhere else. After the rows: the bio, then each route in brief."""
    routes = g["routes"]
    n = len(routes)
    name = g["name"]
    a = about(g)
    by_name = {x["name"]: x for x in all_pages}
    site_link = own_site(g)
    count, span = range_text(g)
    if a.get("summary"):
        lede = esc(a["summary"])
        facts = [esc(count), esc(span)]
    else:
        lede = esc(fact_lede(g))
        facts = []
    if site_link:
        facts.append(f'<a href="{esc(site_link[1])}">{esc(site_link[0])}</a>')
    nav_items = [x for x in prominent(all_pages) if x is not g]
    nav = (f'<nav class="region-nav" aria-label="Authors with the most routes">Authors with the most routes: '
           + " · ".join(f'<a href="{esc(path(x))}">{esc(x["name"])}</a> ({len(x["routes"])})' for x in nav_items) + "</nav>") if nav_items else ""
    more = str(summary.facts(routes, records, by_authors=False)) if n >= 3 else ""
    briefs = "".join(f'<h3><a href="{esc(common.trail_path(r))}">{esc(common.plain_name(r))}</a></h3>\n{trail.brief(r)}\n' for r in routes)
    listing = home.results(groups=[(None, routes, regions.route_guides)], routes_list=True, top=2,
                           by=lambda r: with_html(g, r, by_name))
    route_title = "About the route" if n == 1 else "About each route"
    bio = about_html(g)
    if bio:
        view = home.browse_view(listing, home.overview_map(routes, f"Map of the routes by {name}"),
                                about=bio, about_title=f"About {name}", about_id="about-author")
        view += home.about_section(f"{more}{briefs}", route_title, "in-brief")
    else:
        view = home.browse_view(listing, home.overview_map(routes, f"Map of the routes by {name}"),
                                about=f"{more}{briefs}", about_title=route_title, about_id="in-brief")
    kicker = "Route authors" if g["kind"] == "people" and " and " in name else "Route author"
    body = (pagekit.head(name, lede, [("Trails", "/"), ("Lists", "/lists/"), ("Authors", INDEX)], kicker=kicker, facts=facts)
            + f"""<div class="container section place">
  <h2 class="vh" id="routes">{'The route' if n == 1 else 'The routes'}</h2>
  {view}
  {nav}
  <nav class="region-nav" aria-label="Related pages"><a href="/routes/">All routes</a> · <a href="{INDEX}">All route authors</a></nav>
</div>""")
    options = ([f"{name}: {common.plain_name(routes[0])}"] if n == 1 else [f"{name}: {_plural(n, 'Long Hiking Route')}"]) \
        + [f"{name}, Route Author", name]
    title = next((o for o in options if len(o) <= TITLE_LIMIT), common.cut_at_word(options[-1], TITLE_LIMIT))
    facts_text = f"{count} on this site, {span}."
    if a.get("summary"):
        desc = regions._fit([f"{a['summary']} {facts_text}", a["summary"]])
    else:
        desc = regions._fit([f"{fact_lede(g)} With length, where each runs, usual time and where it is published.",
                             fact_lede(g), f"{_plural(n, 'route')} by {name}."])
    return title, desc, Markup(body), home.has_overview_map(routes), routes, person_jsonld(g, site, site_link)


def person_jsonld(g, site, site_link=None):
    """The author as a Person, only where authors.toml says the entry is one person (not "people",
    not an organisation, not a credit it does not list): with the summary as its description and
    the author's own site as its url and sameAs."""
    if g["kind"] != "person":
        return None
    a = about(g)
    url = site_link[1] if site_link else None
    node = {"@type": "Person", "@id": seo.url_of(site, path(g)) + "#author", "name": g["name"],
            "description": a.get("summary") or None, "url": url, "sameAs": [url] if url else None}
    return seo._clean(node)
