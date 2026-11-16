"""Tests for the added pages: regions, routes, sources, logos, about, data, SEO files,
the bulk archives and the response headers."""
import html
import json
import os
import re
import subprocess
import sys
import unittest
import zipfile

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)

import serve  # noqa: E402
from olt import common, docs, facets, home, records, regions as regions_mod, seo, site, words  # noqa: E402

OUT = os.path.join(WEB, ".cache", "test-site")


def setUpModule():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    subprocess.run([sys.executable, os.path.join(WEB, "build.py"), "--out", OUT],
                   check=True, stdout=subprocess.DEVNULL)


def read_out(relpath):
    with open(os.path.join(OUT, *relpath.split("/")), encoding="utf-8") as f:
        return f.read()


def entry_ids(doc):
    return re.findall(r'<li class="entry" data-id="([^"]+)"', doc)


class ExtraPagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = records.load_records(ROOT)

    def test_every_region_code_has_a_page(self):
        codes = {c for r in self.records for c in r.get("regions", [])
                 if c != words.ALL_CANADA}
        for code in codes:
            slug = words.region_key(code, "US").lower()
            path = os.path.join(OUT, "regions", slug, "index.html")
            self.assertTrue(os.path.isfile(path), f"{code} -> {slug}")
        self.assertTrue(os.path.isfile(os.path.join(OUT, "regions", "index.html")))

    def test_each_record_on_each_region_page(self):
        for rec in self.records:
            for code in rec.get("regions", []):
                if code == words.ALL_CANADA:
                    page = read_out("regions/index.html")
                else:
                    slug = words.region_key(code, rec["country"]).lower()
                    page = read_out(f"regions/{slug}/index.html")
                self.assertIn(f'href="/trails/{rec["id"]}/"', page, f'{rec["id"]} in {code}')

    def test_all_routes_on_routes_page(self):
        routes = [r for r in self.records if r["derived"]["kind"] == "route"]
        self.assertEqual(len(routes), 57)
        page = read_out("routes/index.html")
        import html as _html
        text = _html.unescape(re.sub(r"<[^>]+>", "", page))  # a credit naming two authors links each name
        for r in routes:
            self.assertIn(f'href="/trails/{r["id"]}/"', page, r["id"])
            self.assertIn(r["route"]["creator"], text, r["id"])

    def test_every_logo_on_logos_page(self):
        page = read_out("logos/index.html")
        for r in self.records:
            if "shield" in r["derived"]["files"]:
                self.assertIn(f'href="/trails/{r["id"]}/"', page, r["id"])
        self.assertIn("no-logo-exists", page)
        self.assertIn("logo-not-found", page)

    def test_added_pages_exist(self):
        for rel in ("sources/index.html", "about/index.html", "data/index.html",
                    "data/schema/index.html", "data/changelog/index.html",
                    "licences/LICENSE", "licences/MIT.txt", "robots.txt"):
            self.assertTrue(os.path.isfile(os.path.join(OUT, *rel.split("/"))), rel)

    def test_no_dead_internal_links_in_added_pages(self):
        import re
        for rel in ("regions/index.html", "routes/index.html", "lists/index.html", "sources/index.html",
                    "logos/index.html", "about/index.html", "data/index.html",
                    "data/schema/index.html", "data/changelog/index.html"):
            html = read_out(rel)
            for url in re.findall(r'(?:href|src)="(/[^"]*)"', html):
                path = url.split("#", 1)[0].split("?", 1)[0]
                if not path:
                    continue
                if path.endswith("/"):
                    path += "index.html"
                target = os.path.join(OUT, *path.lstrip("/").split("/"))
                self.assertTrue(os.path.isfile(target), f"{rel} -> {url}")

    def test_region_map_limited_to_region_ids(self):
        page = read_out("regions/us-vt/index.html")
        self.assertIn('data-map="overview"', page)
        self.assertIn("data-ids=", page)
        self.assertIn("long-trail", page)

    def test_home_region_links_point_to_region_pages(self):
        page = read_out("index.html")
        self.assertIn('href="/regions/us-vt/"', page)


    def test_where_counts_match_the_place_pages(self):
        home_doc = read_out("index.html")
        by_slug, across = regions_mod.collect_regions(self.records)
        # each state or province option's count is the number of trails on its place page
        found = re.findall(r'<option value="((?:US|CA)-[A-Z]{2})">[^<(]+\((\d+)\)</option>', home_doc)
        self.assertEqual({v for v, _ in found}, {i["key"] for i in by_slug.values()})
        for value, n in found:
            page = read_out(f"regions/{value.lower()}/index.html")
            self.assertEqual(int(n), len(entry_ids(page)), value)
            # and the rows that say they are there
            self.assertEqual(int(n), len(re.findall(rf'data-where="[^"]*\b{value}\b', home_doc)), value)
        for country, label in (("US", "United States"), ("CA", "Canada")):
            n = int(re.search(rf'<option value="{country}">{label} \((\d+)\)</option>', home_doc).group(1))
            self.assertEqual(n, sum(1 for r in self.records if country in common.countries(r)), country)
        for g, name, _ in facets.PLACE_GROUPS:
            m = re.search(rf'<option value="g:{g}">All of {re.escape(name)} \((\d+)\)</option>', home_doc)
            n = sum(1 for r in self.records if g in facets.place_groups(r))
            self.assertEqual(int(m.group(1)) if m else 0, n, g)
        # No trail spans a whole country now that the Trans Canada Trail is gone;
        # the "across" section appears only when one does.
        self.assertEqual('id="across-canada"' in read_out("regions/index.html"), bool(across))
        self.assertEqual('id="canada-wide"' in read_out("regions/index.html"), bool(across))  # the old anchor

    def test_list_pages_share_the_home_list(self):
        for rel in ("index.html", "regions/us-co/index.html", "routes/index.html",
                    "lists/national-scenic-trails/index.html"):
            doc = read_out(rel)
            results = doc[doc.index('<div class="results"'):]
            for part in ('<div class="list-head" aria-hidden="true">', '<ol class="entries"',
                         '<ul class="key"', "Sort by", 'data-sort-select'):
                self.assertIn(part, results, f"{rel}: {part}")
            self.assertNotIn('name="units-list"', doc, rel)  # the header's switch is the only one
            scale = re.search(r'<div class="list-head".*?</div>', results, re.S).group(0)
            self.assertEqual(scale.count('class="len__km"'), 3, rel)
            self.assertEqual(scale.count('class="len__mi"'), 3, rel)
            # round in each unit, miles first
            self.assertIn('<span class="len__mi">100</span><span class="len__km">100</span>', scale)
            self.assertIn('<span class="len__mi">10,000 mi</span><span class="len__km">10,000 km</span>', scale)
            for name in ("Length", "Time", "GPX", "Climb"):
                self.assertIn(name, scale, rel)
            for col in ("name", "length", "time", "climb"):
                self.assertIn(f'data-sort-col="{col}"', scale, rel)
        self.assertNotIn('class="route-item"', read_out("routes/index.html"))

    def test_routes_page_rows_carry_their_guides(self):
        doc = read_out("routes/index.html")
        routes = [r for r in self.records if r["derived"]["kind"] == "route"]
        self.assertEqual(sorted(entry_ids(doc)), sorted(r["id"] for r in routes))
        for r in routes:
            row = re.search(rf'<li class="entry" data-id="{r["id"]}".*?\n</li>', doc, re.S).group(0)
            for g in r["guide"]:
                self.assertIn(f'href="{html.escape(g["url"], quote=True)}"', row, r["id"])
        # says what a route is, in the one definition, and no longer explains track policies
        self.assertIn(html.escape(facets.ROUTE_DEFINITION, quote=True), doc)
        self.assertNotIn("track policies", doc.lower())
        self.assertNotIn("policy-scale", doc)

    def test_home_finder_layout(self):
        doc = read_out("index.html")
        form = doc[doc.index('<form class="filters"'):doc.index("</form>")]
        self.assertIn('<details class="filters__more">', form)
        self.assertNotIn("filters__more\" open", form)
        self.assertIn("No trails match these filters.", doc)
        more = form[form.index('<details class="filters__more">'):]
        first = form[:form.index('<details class="filters__more">')]
        # the first-rank filters in view, Walking, Shape and GPX behind "More"
        for name in ("q", "where", "min", "max", "time", "kind"):
            self.assertIn(f'name="{name}"', first, name)
        for name in ("gpx",):
            self.assertIn(f'name="{name}"', more, name)
        for name, key in (("month", "season"), ("terrain", "terrain")):
            self.assertEqual(f'name="{name}"' in first, facets.offered(self.records, key), name)
        for name, key in (("walking", "walking"), ("shape", "shape")):
            self.assertEqual(f'name="{name}"' in more, facets.offered(self.records, key), name)
        # no dataset filters
        for name in ("tier", "policy", "designated", "line", "country", "region"):
            self.assertNotIn(f'name="{name}"', form, name)
        # the map is in the tool, beside the list it filters
        main = doc[doc.index('<div class="finder__main">'):]
        self.assertLess(main.index('data-map="overview"'), main.index('<ol class="entries" id="entries"'))
        longest_km = max(r["length_km"] for r in self.records)
        maxsel = form[form.index('id="max"'):form.index("</select>", form.index('id="max"'))]
        minsel = form[form.index('id="min"'):form.index("</select>", form.index('id="min"'))]
        # the steps are round miles, miles first; the top step reaches the longest trail
        steps = [int(v) for v in re.findall(r'<option value="(\d+)mi">', maxsel)]
        self.assertGreaterEqual(steps[-1] * words.KM_PER_MI, longest_km)
        self.assertEqual(steps, home.length_steps(self.records)[1:])
        self.assertIn("100 mi &middot; 161 km", minsel)
        self.assertEqual(home.length_steps(self.records)[:11], list(home.LENGTH_STEPS_MI))
        # a reader who chose kilometres gets round kilometre steps (app.js builds them from data-steps-km)
        km_steps = home.length_steps(self.records, "km")
        self.assertEqual(km_steps[:11], list(home.LENGTH_STEPS_KM))
        self.assertGreaterEqual(km_steps[-1], longest_km)
        self.assertIn('data-steps-km="' + ",".join(map(str, km_steps)) + '"', form)
        for n in home.LENGTH_STEPS_MI + home.LENGTH_STEPS_KM:
            self.assertEqual(n % 5, 0, n)

    def test_logos_page_shows_exactly_the_logo_files(self):
        page = read_out("logos/index.html")
        files = sorted(d for d in os.listdir(ROOT)
                       if any(os.path.isfile(os.path.join(ROOT, d, n)) for n in records.SHIELD_NAMES))
        cards = re.findall(r'<li class="logo-card">.*?<h3><a href="/trails/([^/]+)/">', page, re.S)
        self.assertEqual(sorted(cards), files)
        for img in re.findall(r'<li class="logo-card">\s*<div class="plate[^"]*">(.*?)</div>', page, re.S):
            self.assertIn('alt=""', img)
            self.assertIn('class="vh"', img)  # the link around the image still has a name

    def test_sources_page_counts_measured_lines(self):
        page = read_out("sources/index.html")
        measured = sum(1 for r in self.records if r.get("verification", {}).get("verified"))
        self.assertIn(f"<dt>Track measured</dt><dd>{measured}<", page)
        self.assertIn("<dt>Source status: OpenStreetMap only</dt>", page)
        # a record's "none (no line included)" is shown in words, not as the raw value
        self.assertIn("<td>None (no track included)</td>", page)
        self.assertNotIn("none (no line included)", page)
        self.assertEqual(page.count('<th scope="col">Trails</th>'), 2)
        self.assertNotRegex(page, r'<td><a href="/trails/[^"]+/">[^<]*</a>, <a')

    def test_data_page_licences_from_the_records(self):
        page = read_out("data/index.html")
        self.assertNotIn("Pacific Crest line (PCTA)", page)
        lines = [r for r in self.records if r["derived"]["has_line"]]
        for lic in {r["source"]["licence"] for r in lines}:
            n = sum(1 for r in lines if r["source"]["licence"] == lic)
            label = html.escape(words.label(words.LICENCES, lic), quote=True)
            what = (f"Tracks shared with permission: {n} record" if lic == "stated-permission"
                    else f"Tracks licensed {label}: {n} record")
            self.assertIn(what, page, lic)
        for name in ("trails.json", "overview.geojson"):
            self.assertRegex(page, rf'<a href="/data/{re.escape(name)}">')
        for name in ("all-gpx.zip", "all-geojson.zip"):
            size = words.fmt_bytes(os.path.getsize(os.path.join(OUT, "data", name)))
            self.assertRegex(page, rf'/data/{re.escape(name)}</a></td><td>[^<]*</td><td class="num">{re.escape(size)}<')
            self.assertIn(f'"contentUrl":"{site.load().base_url}/data/{name}"', page)

    def test_archives_hold_every_line(self):
        lines = [r for r in self.records if r["derived"]["has_line"]]
        for name, ext in (("all-gpx.zip", ".gpx"), ("all-geojson.zip", ".geojson")):
            with zipfile.ZipFile(os.path.join(OUT, "data", name)) as zf:
                names = set(zf.namelist())
                for doc in ("README.txt", "trails.csv", "SOURCES.md"):
                    self.assertIn(doc, names, name)
                for r in lines:
                    self.assertIn(f'{r["id"]}/{r["id"]}{ext}', names, name)
                    self.assertIn(f'{r["id"]}/release.txt', names, name)
                    if "alternates" in r["derived"]["files"]:
                        self.assertIn(f'{r["id"]}/{r["id"]}-alternates{ext}', names, name)
                self.assertTrue(all(n.endswith((ext, "release.txt")) or "/" not in n for n in names), name)
                readme = zf.read("README.txt").decode("utf-8")
                self.assertIn("release.txt", readme)
                self.assertIn("trails.csv", readme)
                self.assertIn("5 m", readme)
                if ext == ".gpx":
                    self.assertIsNone(zf.testzip())
                    info = zf.getinfo(f"{lines[0]['id']}/{lines[0]['id']}.gpx")
                    self.assertEqual(info.compress_type, zipfile.ZIP_DEFLATED)

    def test_document_requests_link_only_when_configured(self):
        text = ("<p>Open an issue, or send a patch.</p><p>Ask by opening an issue in this repository, "
                "or by writing to the repository maintainers through the contact.</p>")
        self.assertEqual(docs.link_requests(text, site.Site("N", "T")), text)
        out = docs.link_requests(text, site.Site("N", "T", repo_url="https://example.org/r"))
        self.assertIn('<a href="https://example.org/r/issues">Open an issue</a>', out)
        self.assertIn('<a href="https://example.org/r/issues">opening an issue</a>', out)
        self.assertIn('<a href="https://example.org/r">writing to the repository maintainers</a>', out)
        out = docs.link_requests(text, site.Site("N", "T", contact_url="mailto:a@example.org"))
        self.assertIn('<a href="mailto:a@example.org">writing to the repository maintainers</a>', out)
        self.assertIn('<a href="mailto:a@example.org">Open an issue</a>', out)
        configured = site.load()
        if not (configured.repo_url or configured.contact_url):  # left as the documents have it
            self.assertIn("<p>Open an issue, or send a patch", read_out("about/index.html"))
            self.assertIn(" by opening an issue in this repository, or by writing to the repository maintainers ",
                          read_out("logos/index.html"))


class HeadersTest(unittest.TestCase):
    """The built _headers, read the way serve.py applies it, over every file in the built site."""
    NETLIFY_DEFAULT_CACHE = "public, max-age=0, must-revalidate"  # when no rule sets Cache-Control

    @classmethod
    def setUpClass(cls):
        cls.rules = serve.parse_headers(os.path.join(OUT, "_headers"))
        cls.paths = []
        for base, _, names in os.walk(OUT):
            for n in names:
                cls.paths.append("/" + os.path.relpath(os.path.join(base, n), OUT).replace(os.sep, "/"))

    def headers(self, path):
        """{lower name: value}, failing when two matching rules set the same header."""
        out = {}
        for pattern, headers in self.rules:
            if pattern.match(path):
                for name, value in headers:
                    self.assertNotIn(name.lower(), out, f"{path}: {name} set by two rules")
                    out[name.lower()] = value
        return out

    def test_pages_revalidate(self):
        pages = [p for p in self.paths if p.endswith(".html")]
        self.assertGreater(len(pages), 200)
        clean = [p[:-len("index.html")] for p in pages if p.endswith("/index.html")]
        for path in pages + clean:
            cache = self.headers(path).get("cache-control", self.NETLIFY_DEFAULT_CACHE)
            self.assertIn("max-age=0", cache, path)
        for path in ("/data/", "/data/index.html", "/data/schema/", "/data/changelog/"):
            self.assertIn("max-age=0", self.headers(path).get("cache-control", self.NETLIFY_DEFAULT_CACHE), path)

    def test_line_files_and_licences_get_their_types(self):
        seen = {".gpx": 0, ".geojson": 0}
        for path in self.paths:
            h = self.headers(path)
            if path.startswith("/trails/") and path.endswith(".gpx"):
                seen[".gpx"] += 1
                self.assertEqual(h.get("content-type"), "application/gpx+xml", path)
            elif path.startswith("/trails/") and path.endswith(".geojson"):
                seen[".geojson"] += 1
                self.assertEqual(h.get("content-type"), "application/geo+json", path)
            elif path.startswith("/data/") and path.endswith(".zip"):
                self.assertEqual(h.get("content-type"), "application/zip", path)
        self.assertGreater(seen[".gpx"], 85)
        self.assertGreater(seen[".geojson"], 85)
        self.assertEqual(self.headers("/licences/LICENSE").get("content-type"), "text/plain; charset=utf-8")
        self.assertIn("/licences/LICENSE", self.paths)

    def test_fonts_are_same_origin(self):
        csp = self.headers("/").get("content-security-policy", "")
        font_src = re.search(r"font-src ([^;]*)", csp).group(1)
        self.assertEqual(font_src.strip(), "'self'")
        self.assertIn("https://tiles.openfreemap.org", re.search(r"connect-src ([^;]*)", csp).group(1))

    def test_elevation_tiles_allowed_by_their_path_only(self):
        """The outdoor map fetches Terrain Tiles (fetch() in the page or the
        contour add-on's blob: worker): connect-src names that one path."""
        csp = self.headers("/trails/john-muir/").get("content-security-policy", "")
        self.assertEqual(csp, self.headers("/").get("content-security-policy", ""))
        connect = re.search(r"connect-src ([^;]*)", csp).group(1).split()
        self.assertEqual(connect, ["'self'", "https://tiles.openfreemap.org",
                                   "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/"])
        self.assertIn("worker-src 'self' blob:", csp)
        self.assertIn("img-src 'self' data: blob:;", csp)
        with open(os.path.join(WEB, "assets", "map", "outdoor.json"), encoding="utf-8") as f:
            dem = json.load(f)["sources"]["olt-dem"]["tiles"][0]
        self.assertTrue(dem.startswith(connect[2]), dem)


class SeoTest(unittest.TestCase):
    def test_sitemap_absent_without_base_url(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            seo.write_seo_files(tmp, ["/"], site.Site("N", "T"))
            self.assertFalse(os.path.exists(os.path.join(tmp, "sitemap.xml")))
            with open(os.path.join(tmp, "robots.txt"), encoding="utf-8") as f:
                self.assertNotIn("Sitemap:", f.read())

    def test_sitemap_complete_with_base_url(self):
        import tempfile
        recs = records.load_records(ROOT)
        by_slug, _ = regions_mod.collect_regions(recs)
        region_paths = [f"/regions/{s}/" for s in sorted(by_slug)]
        paths = seo.all_paths(recs, region_paths)
        s = site.Site("N", "T", base_url="https://example.org")
        with tempfile.TemporaryDirectory() as tmp:
            seo.write_seo_files(tmp, paths, s)
            with open(os.path.join(tmp, "sitemap.xml"), encoding="utf-8") as f:
                xml = f.read()
            for p in paths:
                self.assertIn(f"<loc>https://example.org{p}</loc>", xml, p)
            with open(os.path.join(tmp, "robots.txt"), encoding="utf-8") as f:
                self.assertIn("Sitemap: https://example.org/sitemap.xml", f.read())


if __name__ == "__main__":
    unittest.main()
