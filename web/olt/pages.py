"""Render the site's HTML pages. Called by web/build.py after the data files are written.

    render_site(records, out_dir, repo_root)

writes:
    /assets/...                 web/assets/ copied as it is (icons, social card, base-map style), less the
                                files below that are fingerprinted
    /immutable/...              the stylesheet, scripts, fonts and map libraries, each named for a hash of
                                its content; written by web/build.py through olt/fingerprint.py once the
                                pages are, which also removes their copies from /assets/
    /index.html                 home: overview map and the trail finder with every record
    /trails/<id>/index.html     one page per record
    /trails/<id>/trail.toml     the raw record; release.txt beside it where the trail has one
    /trails/<id>/shield-thumb.png  the 256 px copy of a PNG logo; shield-list.png the list-size copy (olt/thumbs.py)
    /trails/<id>/card.png       the trail's social card, from web/cards/ (olt/cards.py)
    /regions/, /regions/<slug>/ Places: the hub and one page per state or province
    /lists/, /lists/<key>/      the lists shown today (olt/browse.py); /routes/ is the Routes list
    /about/ and the pages under it: /data/, /data/schema/, /data/changelog/, /sources/, /logos/, /left-out/
    /saved/                     the visitor's saved trails (olt/saved.py; not indexed)
    /404.html                   not found (not indexed)
    /sitemap.xml, /robots.txt   with a <lastmod> from the data (olt/seo.py)
    /feed.xml                   the changelog as an Atom feed (olt/feed.py)
    /llms.txt                   the bulk files, per-trail files and licences, as plain links

Adding a page elsewhere (regions, sources, ...): build its body as HTML,
wrap it with olt.layout.layout() and write it with olt.layout.write_page().
See the docstring of olt/layout.py.
"""
import json
import os
import shutil

from .markup import esc
from . import authors, browse, cards, datafiles, docs, facets, feed, home, layout, leftout, pagekit, placefacets, placepages, places, reference, regions, saved, searchtext, seo, site as site_settings, sketch, standing, thumbs, trail, views

WEB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(WEB_DIR, "assets")

# Builders of further place pages, run after the state and group pages. Each takes
# (records, site, repo_root) and returns pages as (path, title, description, body,
# needs_map, recs); each page is added like a state page and reaches the sitemap
# through region_paths.
EXTRA_PAGE_BUILDERS = (placepages.build,)


def copy_assets(out_dir, assets_dir=ASSETS_DIR):
    """Copy web/assets/ to <out>/assets/, replacing what was there. The fingerprinted files
    (olt/fingerprint.py) are copied too and taken out again by fingerprint.publish()."""
    dest = os.path.join(out_dir, "assets")
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    shutil.copytree(assets_dir, dest, ignore=shutil.ignore_patterns("README.md", ".*"))


def copy_record_files(rec, out_dir, repo_root):
    """Copy trail.toml (and release.txt where present) next to the trail page.

    Also notes on the record what the page needs to know about those files and
    the map geometry: derived.release and derived.map_bbox.
    """
    tdir = os.path.join(out_dir, "trails", rec["id"])
    os.makedirs(tdir, exist_ok=True)
    shutil.copyfile(os.path.join(repo_root, rec["id"], "trail.toml"), os.path.join(tdir, "trail.toml"))
    release = trail.release_path(repo_root, rec)
    rec["derived"]["release"] = bool(release)
    if release:
        shutil.copyfile(release, os.path.join(tdir, "release.txt"))
    map_json = os.path.join(tdir, "map.json")
    if os.path.isfile(map_json):
        with open(map_json, encoding="utf-8") as f:
            box = json.load(f).get("bbox")
        if box:
            rec["derived"]["map_bbox"] = box


def not_found_page(site):
    """The 404 page. It is not for search results: noindex, and no canonical address."""
    body = layout.page_head("Page not found", kicker="404",
                            lede="There is no page at this address. Search the trails by name instead.")
    body += """<div class="container section">
  <form class="notfound-search" action="/" method="get" role="search">
    <label class="field__label" for="notfound-q">Search the trails</label>
    <input class="input" id="notfound-q" name="q" type="search" placeholder="Name, abbreviation or author of a route" autocomplete="off" spellcheck="false">
    <button class="button button--primary" type="submit">Search</button>
  </form>
  <p class="prose"><a href="/">Find a trail</a> on the home page, or browse by <a href="/regions/">place</a>.</p>
</div>"""
    return layout.layout("Page not found", body, path="/404.html", site=site, noindex=True)


def render_site(records, out_dir, repo_root, site=None):
    """Write every HTML page for the given records. Returns the number of pages written."""
    with browse.remembering_shown():
        return _render_site(records, out_dir, repo_root, site)


def _render_site(records, out_dir, repo_root, site=None):
    site = site or site_settings.load()
    copy_assets(out_dir)
    sketch.use(out_dir)  # the maps' static drawings are read from the track files written here
    layout.UNDER_LISTS.clear()
    pages = 0
    dates = {}  # page path -> its own date (YYYY-MM-DD), for the sitemap
    everything = seo.newest(records)
    author_links = authors.link_map(records, repo_root)
    home.use_authors(author_links)
    # The parks, ranges and wilderness areas (olt/places.py): which have a page, for
    # the links on trail and state pages and the hub, and every trail's place names
    # for search, a page or not.
    registry = places.load(repo_root)
    place_infos = places.collect(records, registry)
    search_names = {}
    for key, recs in places.membership(records, registry).items():
        for r in recs:
            search_names.setdefault(r["id"], []).append(registry[key].get("name", ""))
    searchtext.use_place_names(search_names)
    for rec in records:
        # Read by common.name() wherever a page shows the record's name as text.
        rec["derived"]["name_lang"] = site.name_lang.get(rec["id"], "")
    for rec in records:
        copy_record_files(rec, out_dir, repo_root)
        thumbs.prepare(rec, out_dir, repo_root)
        title, description, body, needs_map = trail.render(
            rec, site, records, author_links=author_links, place_infos=place_infos)
        path = f"/trails/{rec['id']}/"
        card, card_alt = cards.prepare(rec, out_dir)
        layout.write_page(out_dir, path, layout.layout(
            title, body, path=path, description=description, maps=needs_map, outdoor=needs_map, site=site,
            jsonld=seo.trail_jsonld(rec, site, title=title, description=description),
            image=card, image_alt=card_alt))
        dates[path] = seo.modified(rec)
        pages += 1
    body = home.render(records, site, repo_root, place_kinds={i["kind"] for i in place_infos.values()})
    layout.write_page(out_dir, "/", layout.layout("", body, path="/", maps=True, site=site,
                                                  description=home.description(records),
                                                  jsonld=seo.home_jsonld(site)))
    dates["/"] = everything
    layout.write_page(out_dir, "/404.html", not_found_page(site))
    pages += 2

    def add(path, title, description, body_html, *, maps=False, jsonld=None, recs=None, date="", alternates=(), about=None):
        """Write a page. recs: the trails it lists, which give its date and its ItemList.
        about: a node the page is about (an author's Person), added to its graph."""
        nonlocal pages
        if recs is not None:
            jsonld = seo.collection_jsonld(path, site, title=title, description=description, recs=recs)
            if about:
                jsonld[0]["about"] = {"@id": about["@id"]}
                jsonld.append(about)
        layout.write_page(out_dir, path, layout.layout(
            title, body_html, path=path, description=description, maps=maps, site=site, jsonld=jsonld,
            alternates=alternates))
        dates[path] = date or (seo.newest(recs) if recs is not None else everything)
        pages += 1

    shown = browse.shown(records)
    facet_plan = placefacets.plan(records) + placefacets.plan_places(place_infos, records)
    facets_of_place = placefacets.pages_by_place(facet_plan)
    t, d, b = regions.regions_index_page(records, site, infos=place_infos)
    add("/regions/", t, d, b)  # every trail is on it: the newest of them
    by_slug, _ = regions.collect_regions(records)
    region_paths = []
    for slug in sorted(by_slug):
        here = [(p["lst"].title, p["path"], len(p["recs"])) for p in facets_of_place.get(slug, [])]
        t, d, b, needs_map = regions.region_page(
            slug, records, site, facet_pages=here,
            place_links=regions.place_links_for(by_slug[slug]["key"], place_infos))
        path = f"/regions/{slug}/"
        region_paths.append(path)
        add(path, t, d, b, maps=needs_map, recs=by_slug[slug]["records"])
    # A place the site holds a box for and no trail is in: a page that says so, and what was left out there.
    left_out = leftout.load_entries(repo_root)
    for key in regions.empty_places(records):
        t, d, b = regions.empty_place_page(key, records, site, left_out)
        path = facets.place_path(key)
        region_paths.append(path)
        add(path, t, d, b)
    # The parts of the country (facets.PLACE_GROUPS), each a page of its own.
    for g, _, _ in facets.PLACE_GROUPS:
        built = regions.group_page(g, records, site)
        if built:
            t, d, b, needs_map, recs = built
            path = regions.group_path(g)
            region_paths.append(path)
            add(path, t, d, b, maps=needs_map, recs=recs)
    # Further place pages (parks, ranges and wilderness areas, olt/placepages.py).
    for builder in EXTRA_PAGE_BUILDERS:
        for built in builder(records, site, repo_root, facet_pages=facets_of_place):
            region_paths.append(built.path)
            add(built.path, built.title, built.description, built.body,
                maps=built.needs_map, recs=built.recs)
    # Pages for one kind of trail in one place (olt/placefacets.py).
    for p in facet_plan:
        t, d, b, needs_map = placefacets.page(p, records, site, facet_plan)
        region_paths.append(p["path"])
        add(p["path"], t, d, b, maps=needs_map, recs=p["recs"])
    # The view pages: each is built only when the records give it at least MIN_SIZE trails.
    view_paths = []
    labels = {"/": "Every trail", "/lists/": "All lists", "/regions/": "Places", "/data/schema/": "Record schema"}
    extras = []      # (group, title, blurb, path, how many) for /lists/
    for lst, _ in shown:
        labels[browse.path(lst)] = lst.title

    pending = []     # (path, title, description, body, add() options): written once every view is known

    def view(path, group, link_label, blurb, built, count=None):
        """Hold a view page built as (title, description, body, recs...) and note it for /lists/.
        count: what the page's tile counts, when that is not the trails it lists (the authors page lists routes)."""
        t, d, b = built[:3]
        recs = built[3] if len(built) > 3 and isinstance(built[3], list) else None
        pending.append((path, t, d, b, {"recs": recs, "maps": 'data-map="overview"' in str(b)}))
        view_paths.append(path)
        layout.UNDER_LISTS.add(path)  # its header item is Lists
        labels[path] = link_label
        if group:
            extras.append((group, link_label, blurb, path, count if count is not None else len(recs) if recs else 0))

    for c in datafiles.collections(repo_root):
        built = standing.collection_page(c, records, site)
        if built:
            view(standing.collection_path(c), "tables", f"{c['name']} trails compared",
                 f"The {c['name']} trails with their map: length, time, high point, climb and the year each was named.", built)
    ranked = []
    for spec in standing.RANKINGS:
        built = standing.ranking_page(spec, records, site)
        if built:
            path = f"{standing.NUMBERS}{spec[0]}/"
            ranked.append((path, spec[1], len(built[3])))
            view(path, "tables", spec[1], f"{len(built[3])} trails with the figure, ranked, with the caveats.", built)
    if ranked:
        view(standing.NUMBERS, "tables", "Long trails by the numbers",
             "The longest and shortest, trails by state and province, and links to the rankings.",
             standing.numbers_page(records, site, ranked))
    author_groups = authors.author_pages(records, repo_root)
    authors_built = any(facets.kind(r) == "route" for r in records)
    if authors_built:
        t, d, b, routes = authors.index_page(records, site, repo_root)
        view(authors.INDEX, "standing", "Route authors", f"The {len(routes)} routes by who published them, and where.",
             (t, d, b, routes), count=len(author_groups))
        for g in author_groups:
            t, d, b, needs_map, routes, person = authors.author_page(g, records, site, author_groups)
            path = authors.path(g)
            pending.append((path, t, d, b, {"maps": needs_map, "recs": routes, "about": person}))
            view_paths.append(path)
            labels[path] = f"Routes by {g['name']}"
    built = views.recent_page(records, site)
    if built:
        view(views.RECENT, "changes", "Recently added and changed",
             "The newest additions and the newest changes to what each trail says.", built)
    built = views.connected_page(records, site)
    if built:
        view(views.CONNECTED, "changes", "Linked long trails", "Trails whose own descriptions name another trail.", built)
    t, d, b = reference.method_page(records, site, repo_root)
    pending.append((reference.METHOD, t, d, b, {"jsonld": seo.article_jsonld(reference.METHOD, site, title=t, description=d,
                                                                              date=everything)}))
    view_paths.append(reference.METHOD)
    labels[reference.METHOD] = "Method"
    extras.append(("reference", "How the figures are measured", "What each figure means and how far to trust it.", reference.METHOD, 0))
    glossary = reference.glossary_page(repo_root, labels, site)
    if glossary:
        t, d, b, terms = glossary
        pending.append((reference.GLOSSARY, t, d, b, {"jsonld": seo.glossary_jsonld(
            reference.GLOSSARY, site, title=t, description=d, terms=terms, date=everything)}))
        view_paths.append(reference.GLOSSARY)
        extras.append(("reference", "Glossary", f"{len(terms)} trail terms as this site uses them.", reference.GLOSSARY, len(terms)))
    for path, t, d, b, options in pending:
        b = pagekit.append_nav(b, pagekit.more_nav(path, extras) + reference.terms_nav(path, repo_root))
        add(path, t, d, b, **options)
    # Lists, each with its figures, related lists and terms.
    list_paths = []
    for lst, recs in shown:
        if lst.key == "routes":
            continue  # /routes/ below, built whether or not the list is shown
        path = browse.path(lst)
        same = [(o, len(r)) for o, r in shown if o.group == lst.group and o.key != lst.key]
        after = ""
        if same:
            heading = next(h for k, h, _ in browse.GROUPS if k == lst.group)
            after += (f'<nav class="region-nav" aria-label="{esc(heading)}">{esc(heading)}: ' + " · ".join(
                f'<a href="{esc(browse.path(o))}">{esc(o.title)}</a> ({n})' for o, n in same) + "</nav>")
        after += placefacets.places_nav(lst, facet_plan)
        after += reference.terms_nav(path, repo_root)
        t, d, b, needs_map = regions.list_page(lst, recs, len(records), site, records=records, after=after)
        list_paths.append(path)
        add(path, t, d, b, maps=needs_map, recs=recs)
    t, d, b = regions.lists_index_page(records, site, extras)
    add("/lists/", t, d, b)
    t, d, b, needs_map = regions.routes_page(records, site, repo_root, after=reference.terms_nav("/routes/", repo_root),
                                             n_authors=len(author_groups) if authors_built else None,
                                             author_pages=({c: authors.credit_html(c, links) for c, links in author_links.items()}
                                                       if authors_built else None))
    add("/routes/", t, d, b, maps=needs_map, recs=[r for r in records if facets.kind(r) == "route"])
    t, d, b = docs.sources_page(records, site, repo_root)
    add("/sources/", t, d, b)
    t, d, b = docs.logos_page(records, site, repo_root)
    add("/logos/", t, d, b)
    t, d, b = docs.about_page(records, site, repo_root)
    add("/about/", t, d, b)
    changelog = feed.newest_date(docs.read_doc(repo_root, "CHANGELOG.md"))
    t, d, b = docs.data_page(records, site, repo_root, out_dir)
    add("/data/", t, d, b, jsonld=seo.dataset_jsonld(records, site, version=changelog),
        alternates=[(f"/data/{name}", kind, f"{site.name}: {name}") for name, kind, _ in seo.distribution()[:2]])
    t, d, b = docs.schema_page(site, repo_root)
    add("/data/schema/", t, d, b, date=changelog)
    t, d, b = docs.changelog_page(site, repo_root)
    add("/data/changelog/", t, d, b, date=changelog)
    entries = leftout.load_entries(repo_root)
    t, d, b = leftout.left_out_page(entries, site, repo_root)
    add(leftout.PATH, t, d, b, date=max((str(e.get("decided", "")) for e in entries), default=""))
    # The visitor's own list: not indexed, and left out of the sitemap below.
    t, d, b = saved.saved_page(records, site)
    layout.write_page(out_dir, saved.PATH, layout.layout(
        t, b, path=saved.PATH, description=d, maps=True, site=site, noindex=True))
    pages += 1
    docs.copy_licences(out_dir, repo_root)
    feed.write_feed(out_dir, site, repo_root)
    if site.base_url:  # its links are absolute
        with open(os.path.join(out_dir, "llms.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write(seo.llms_txt(records, site, changelog))
    seo.write_seo_files(out_dir, seo.all_paths(records, region_paths + ["/lists/"] + list_paths, view_paths), site, dates)
    print(f"pages written {pages}: {len(records)} trail pages, home, 404, places, lists, about")
    return pages
