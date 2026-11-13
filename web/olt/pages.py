"""Render the site's HTML pages. Called by web/build.py after the data files are written.

    render_site(records, out_dir, repo_root)

writes:
    /assets/...                 web/assets/ copied verbatim (style.css, app.js, fonts, vendor)
    /index.html                 home: overview map and the trail finder with every record
    /trails/<id>/index.html     one page per record
    /trails/<id>/trail.toml     the raw record; release.txt beside it where the trail has one
    /trails/<id>/shield-thumb.png  the list-size copy of a PNG logo (olt/thumbs.py)
    /404.html                   not found

Adding a page elsewhere (regions, sources, ...): build its body as HTML,
wrap it with olt.layout.layout() and write it with olt.layout.write_page().
See the docstring of olt/layout.py.
"""
import json
import os
import shutil

from . import docs, home, layout, regions, seo, site as site_settings, thumbs, trail

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
    body = layout.page_head("Page not found", kicker="404",
                            lede="There is no page at this address. Search the trails and routes by name instead.")
    body += """<div class="container section">
  <form class="notfound-search" action="/" method="get" role="search">
    <label class="field__label" for="notfound-q">Search the trails and routes</label>
    <input class="input" id="notfound-q" name="q" type="search" placeholder="Name, abbreviation or creator" autocomplete="off" spellcheck="false">
    <button class="button button--primary" type="submit">Search</button>
  </form>
  <p class="prose"><a href="/">Find a trail</a> on the home page, or browse <a href="/regions/">by region</a>.</p>
</div>"""
    return layout.layout("Page not found", body, path="/404.html", site=site)


def render_site(records, out_dir, repo_root, site=None):
    """Write every HTML page for the given records. Returns the number of pages written."""
    site = site or site_settings.load()
    copy_assets(out_dir)
    pages = 0
    for rec in records:
        # Read by common.name() wherever a page shows the record's name as text.
        rec["derived"]["name_lang"] = site.name_lang.get(rec["id"], "")
    for rec in records:
        copy_record_files(rec, out_dir, repo_root)
        thumbs.prepare(rec, out_dir, repo_root)
        title, description, body, needs_map = trail.render(rec, site)
        path = f"/trails/{rec['id']}/"
        layout.write_page(out_dir, path, layout.layout(title, body, path=path, description=description,
                                                      maps=needs_map, site=site))
        pages += 1
    dataset = seo.dataset_jsonld(records, site)
    body = home.render(records, site)
    layout.write_page(out_dir, "/", layout.layout("", body, path="/", maps=True, site=site, jsonld=dataset))
    layout.write_page(out_dir, "/404.html", not_found_page(site))
    pages += 2

    def add(path, title, description, body_html, *, maps=False, jsonld=None):
        nonlocal pages
        layout.write_page(out_dir, path, layout.layout(
            title, body_html, path=path, description=description, maps=maps, site=site, jsonld=jsonld))
        pages += 1

    t, d, b = regions.regions_index_page(records, site)
    add("/regions/", t, d, b)
    by_slug, _ = regions.collect_regions(records)
    region_paths = []
    for slug in sorted(by_slug):
        t, d, b, needs_map = regions.region_page(slug, records, site)
        path = f"/regions/{slug}/"
        region_paths.append(path)
        add(path, t, d, b, maps=needs_map)
    t, d, b = regions.routes_page(records, site, repo_root)
    add("/routes/", t, d, b)
    t, d, b = docs.sources_page(records, site, repo_root)
    add("/sources/", t, d, b)
    t, d, b = docs.logos_page(records, site, repo_root)
    add("/logos/", t, d, b)
    t, d, b = docs.about_page(records, site, repo_root)
    add("/about/", t, d, b)
    t, d, b = docs.data_page(records, site, repo_root, out_dir)
    add("/data/", t, d, b, jsonld=dataset)
    t, d, b = docs.schema_page(site, repo_root)
    add("/data/schema/", t, d, b)
    t, d, b = docs.changelog_page(site, repo_root)
    add("/data/changelog/", t, d, b)
    docs.copy_licences(out_dir, repo_root)
    seo.write_seo_files(out_dir, seo.all_paths(records, region_paths), site)
    print(f"pages written {pages}: {len(records)} trail pages, home, 404, regions, routes, docs")
    return pages
