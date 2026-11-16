"""Render the site's HTML pages. Called by web/build.py after the data files are written.

    render_site(records, out_dir, repo_root)

writes:
    /assets/...                 web/assets/ copied verbatim (style.css, app.js, fonts, vendor)
    /index.html                 home: overview map and the trail finder with every record
    /trails/<id>/index.html     one page per record
    /trails/<id>/trail.toml     the raw record; release.txt beside it where the trail has one
    /trails/<id>/shield-thumb.png  the list-size copy of a PNG logo (olt/thumbs.py)
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

from . import browse, cards, docs, facets, feed, home, layout, leftout, regions, saved, seo, site as site_settings, thumbs, trail

WEB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(WEB_DIR, "assets")


def copy_assets(out_dir, assets_dir=ASSETS_DIR):
    """Copy web/assets/ to <out>/assets/, replacing what was there."""
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
    site = site or site_settings.load()
    copy_assets(out_dir)
    pages = 0
    dates = {}  # page path -> its own date (YYYY-MM-DD), for the sitemap
    everything = seo.newest(records)
    for rec in records:
        # Read by common.name() wherever a page shows the record's name as text.
        rec["derived"]["name_lang"] = site.name_lang.get(rec["id"], "")
    for rec in records:
        copy_record_files(rec, out_dir, repo_root)
        thumbs.prepare(rec, out_dir, repo_root)
        title, description, body, needs_map = trail.render(rec, site, records)
        path = f"/trails/{rec['id']}/"
        card, card_alt = cards.prepare(rec, out_dir)
        layout.write_page(out_dir, path, layout.layout(
            title, body, path=path, description=description, maps=needs_map, outdoor=needs_map, site=site,
            jsonld=seo.trail_jsonld(rec, site, title=title, description=description),
            image=card, image_alt=card_alt))
        dates[path] = seo.modified(rec)
        pages += 1
    body = home.render(records, site)
    layout.write_page(out_dir, "/", layout.layout("", body, path="/", maps=True, site=site,
                                                  description=home.description(records),
                                                  jsonld=seo.home_jsonld(site)))
    dates["/"] = everything
    layout.write_page(out_dir, "/404.html", not_found_page(site))
    pages += 2

    def add(path, title, description, body_html, *, maps=False, jsonld=None, recs=None, date="", alternates=()):
        """Write a page. recs: the trails it lists, which give its date and its ItemList."""
        nonlocal pages
        if recs is not None:
            jsonld = seo.collection_jsonld(path, site, title=title, description=description, recs=recs)
        layout.write_page(out_dir, path, layout.layout(
            title, body_html, path=path, description=description, maps=maps, site=site, jsonld=jsonld,
            alternates=alternates))
        dates[path] = date or (seo.newest(recs) if recs is not None else everything)
        pages += 1

    t, d, b = regions.regions_index_page(records, site)
    add("/regions/", t, d, b)  # every trail is on it: the newest of them
    by_slug, _ = regions.collect_regions(records)
    region_paths = []
    for slug in sorted(by_slug):
        t, d, b, needs_map = regions.region_page(slug, records, site)
        path = f"/regions/{slug}/"
        region_paths.append(path)
        add(path, t, d, b, maps=needs_map, recs=by_slug[slug]["records"])
    list_paths = []
    shown = browse.shown(records)
    for lst, recs in shown:
        if lst.key == "routes":
            continue  # /routes/ below, built whether or not the list is shown
        t, d, b, needs_map = regions.list_page(lst, recs, len(records), site)
        path = browse.path(lst)
        list_paths.append(path)
        add(path, t, d, b, maps=needs_map, recs=recs)
    t, d, b = regions.lists_index_page(records, site)
    add("/lists/", t, d, b)
    t, d, b, needs_map = regions.routes_page(records, site, repo_root)
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
    seo.write_seo_files(out_dir, seo.all_paths(records, region_paths + ["/lists/"] + list_paths), site, dates)
    print(f"pages written {pages}: {len(records)} trail pages, home, 404, places, lists, about")
    return pages
