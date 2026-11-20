"""Fingerprinted assets: the names, the files the build writes, every reference to them in
the built pages, and the response headers that make them cacheable for a year."""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)

from olt import fingerprint, layout  # noqa: E402
import serve  # noqa: E402

OUT = os.path.join(WEB, ".cache", "test-site")
NAME = re.compile(r"^/immutable/[a-z0-9.-]+\.[0-9a-f]{10}\.[a-z0-9]+$")


class NamesTest(unittest.TestCase):
    def test_a_fingerprinted_address_names_the_hash_of_the_content(self):
        for path in fingerprint.FILES:
            address = fingerprint.url(path)
            self.assertRegex(address, NAME, path)
            digest = hashlib.sha256(fingerprint._content(path)).hexdigest()[:10]
            stem, ext = os.path.splitext(os.path.basename(path))
            self.assertEqual(address, f"/immutable/{stem}.{digest}{ext}")

    def test_other_assets_keep_their_address(self):
        for path in ("/assets/og.png", "/assets/favicon.svg", "/assets/map/outdoor.json",
                     "/assets/vendor/maplibre-gl/LICENSE.txt"):
            self.assertEqual(fingerprint.url(path), path)

    def test_every_file_exists_and_names_are_unique(self):
        names = [fingerprint.url(p) for p in fingerprint.FILES]
        self.assertEqual(len(set(names)), len(names))
        for path in fingerprint.FILES:
            self.assertTrue(os.path.isfile(os.path.join(WEB, *path.lstrip("/").split("/"))), path)

    def test_the_stylesheet_names_its_fonts_and_picture_by_their_hashed_names(self):
        css = fingerprint._content(fingerprint.STYLESHEET).decode("utf-8")
        for target in re.findall(r'url\("([^"]+)"\)', css):
            self.assertRegex(target, r"\.[0-9a-f]{10}\.(woff2|svg)$", target)
        for path in fingerprint.FILES:
            if path.endswith((".woff2", "contours.svg")):
                self.assertIn(fingerprint.url(path).rsplit("/", 1)[1], css, path)
        self.assertNotIn('url("fonts/', css)

    def test_a_changed_file_gets_a_new_name_and_so_does_what_names_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            for rel in ("fonts", ):
                os.makedirs(os.path.join(tmp, rel))
            files = {"style.css": 'a{background:url("contours.svg")}', "contours.svg": "<svg/>", "app.js": "1;"}
            for rel, text in files.items():
                with open(os.path.join(tmp, rel), "w", encoding="utf-8") as f:
                    f.write(text)
            saved = fingerprint.ASSETS_DIR, fingerprint.FILES
            try:
                fingerprint.ASSETS_DIR, fingerprint.FILES = tmp, ("/assets/style.css", "/assets/contours.svg", "/assets/app.js")
                fingerprint._cache.clear()
                first = {p: fingerprint.url(p) for p in fingerprint.FILES}
                with open(os.path.join(tmp, "contours.svg"), "w", encoding="utf-8") as f:
                    f.write("<svg><path/></svg>")
                os.utime(os.path.join(tmp, "contours.svg"), (1, 2))
                second = {p: fingerprint.url(p) for p in fingerprint.FILES}
            finally:
                fingerprint.ASSETS_DIR, fingerprint.FILES = saved
                fingerprint._cache.clear()
        self.assertNotEqual(first["/assets/contours.svg"], second["/assets/contours.svg"])
        self.assertNotEqual(first["/assets/style.css"], second["/assets/style.css"])  # it names the picture
        self.assertEqual(first["/assets/app.js"], second["/assets/app.js"])


class PublishTest(unittest.TestCase):
    def test_publish_writes_the_files_and_takes_the_originals_out_of_assets(self):
        with tempfile.TemporaryDirectory() as out:
            shutil.copytree(fingerprint.ASSETS_DIR, os.path.join(out, "assets"))
            self.assertEqual(fingerprint.publish(out), len(fingerprint.FILES))
            written = sorted(os.listdir(os.path.join(out, "immutable")))
            self.assertEqual(written, sorted(fingerprint.url(p).rsplit("/", 1)[1] for p in fingerprint.FILES))
            for path in fingerprint.FILES:
                self.assertFalse(os.path.exists(os.path.join(out, *path.lstrip("/").split("/"))), path)
            # what is not fingerprinted stays
            self.assertTrue(os.path.isfile(os.path.join(out, "assets", "og.png")))
            self.assertTrue(os.path.isfile(os.path.join(out, "assets", "map", "outdoor.json")))
            # the file is its hash: a second publish writes the same names
            fingerprint.publish(out)
            self.assertEqual(sorted(os.listdir(os.path.join(out, "immutable"))), written)


class LayoutTest(unittest.TestCase):
    def doc(self, **kw):
        from olt import site
        return layout.layout("T", "<p>x</p>", path="/x/", site=site.Site("N", "T"), **kw)

    def test_the_head_names_hashed_files_and_a_map_page_gives_the_script_the_libraries(self):
        plain = self.doc()
        for path in ("/assets/style.css", "/assets/prefs.js", "/assets/app.js"):
            self.assertIn(fingerprint.url(path), plain)
            self.assertNotIn(path, plain)
        self.assertNotIn("maplibre", plain)
        mapped = self.doc(maps=True, outdoor=True)
        self.assertNotIn('<link rel="stylesheet" href="/immutable/maplibre', mapped)  # nothing is loaded with the page
        self.assertNotRegex(mapped, r'<script src="/immutable/maplibre[^>]*>')
        tag = re.search(r'<script src="(/immutable/app\.[0-9a-f]{10}\.js)" defer([^>]*)></script>', mapped)
        self.assertIsNotNone(tag)
        self.assertIn(f'data-maplibre-js="{fingerprint.url(layout.MAPLIBRE_JS)}"', tag.group(2))
        self.assertIn(f'data-maplibre-css="{fingerprint.url(layout.MAPLIBRE_CSS)}"', tag.group(2))
        self.assertIn(f'data-contour-js="{fingerprint.url(layout.CONTOUR_JS)}"', tag.group(2))
        overview = self.doc(maps=True)
        self.assertNotIn("data-contour-js", overview)

    def test_the_preloaded_fonts_are_the_hashed_ones(self):
        doc = self.doc()
        for font in layout.FONT_PRELOADS:
            self.assertIn(f'<link rel="preload" href="{fingerprint.url(font)}" as="font"', doc)


class Refs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.urls = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ("src", "href", "data-maplibre-js", "data-maplibre-css", "data-contour-js"):
            if a.get(key, "").startswith("/"):
                self.urls.append((key, a[key]))


class BuiltSiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        subprocess.run([sys.executable, os.path.join(WEB, "build.py"), "--out", OUT],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.pages = []
        for base, _, names in os.walk(OUT):
            for n in names:
                if n.endswith(".html"):
                    cls.pages.append(os.path.join(base, n))
        cls.rules = serve.parse_headers(os.path.join(OUT, "_headers"))

    def test_no_page_names_an_original_of_a_fingerprinted_file(self):
        originals = set(fingerprint.FILES)
        used = 0
        for page in self.pages:
            refs = Refs()
            with open(page, encoding="utf-8") as f:
                refs.feed(f.read())
            for key, url in refs.urls:
                self.assertNotIn(url, originals, f"{page}: {url}")
                if url.startswith("/immutable/"):
                    used += 1
                    self.assertRegex(url, NAME, page)
                    self.assertTrue(os.path.isfile(os.path.join(OUT, *url.lstrip("/").split("/"))), f"{page}: {url}")
        self.assertGreater(used, len(self.pages))  # at least the stylesheet and a script on every page

    def test_every_page_loads_the_stylesheet_and_scripts_by_hashed_address(self):
        for page in self.pages:
            with open(page, encoding="utf-8") as f:
                doc = f.read()
            for path in ("/assets/style.css", "/assets/prefs.js", "/assets/app.js"):
                self.assertIn(fingerprint.url(path), doc, f"{page} lacks {path}")

    def test_the_originals_are_not_in_the_build_and_the_hashed_files_are(self):
        for path in fingerprint.FILES:
            self.assertFalse(os.path.exists(os.path.join(OUT, *path.lstrip("/").split("/"))), path)
            self.assertTrue(os.path.isfile(os.path.join(OUT, *fingerprint.url(path).lstrip("/").split("/"))), path)

    def test_the_stylesheets_urls_resolve(self):
        css_path = os.path.join(OUT, *fingerprint.url(fingerprint.STYLESHEET).lstrip("/").split("/"))
        with open(css_path, encoding="utf-8") as f:
            css = f.read()
        found = re.findall(r'url\("([^"]+)"\)', css)
        self.assertGreaterEqual(len(found), 6)
        for target in found:
            self.assertTrue(os.path.isfile(os.path.join(os.path.dirname(css_path), target)), target)

    def headers_for(self, path):
        """Every header a rule gives the path, as (name, rule pattern) pairs: a name twice is a header set twice."""
        found = []
        for pattern, headers in self.rules:
            if pattern.match(path):
                found += [(name.lower(), pattern.pattern) for name, _ in headers]
        return found

    def value(self, path, header):
        out = None
        for pattern, headers in self.rules:
            if pattern.match(path):
                for name, value in headers:
                    if name.lower() == header.lower():
                        out = value
        return out

    def test_the_fingerprinted_files_are_cached_for_a_year_and_never_revalidated(self):
        for path in fingerprint.FILES:
            address = fingerprint.url(path)
            self.assertEqual(self.value(address, "Cache-Control"), "public, max-age=31536000, immutable", address)

    def test_what_is_not_fingerprinted_still_revalidates_and_html_is_never_immutable(self):
        for path in ("/assets/og.png", "/assets/map/outdoor.json", "/", "/index.html", "/trails/appalachian/"):
            value = self.value(path, "Cache-Control")
            self.assertNotIn("immutable", value or "", path)
        self.assertIn("must-revalidate", self.value("/assets/og.png", "Cache-Control"))
        self.assertIn("max-age=0", self.value("/index.html", "Cache-Control"))

    def test_no_header_is_set_twice_for_one_path(self):
        paths = [fingerprint.url(p) for p in fingerprint.FILES] + [
            "/assets/og.png", "/assets/map/outdoor.json", "/", "/index.html", "/404.html",
            "/data/overview.geojson", "/data/trails.json", "/data/trails.csv", "/data/all-gpx.zip",
            "/trails/appalachian/", "/trails/appalachian/map.json", "/trails/appalachian/appalachian.gpx",
            "/trails/appalachian/appalachian.geojson", "/trails/appalachian/trail.toml", "/feed.xml", "/llms.txt"]
        for path in paths:
            names = [n for n, _ in self.headers_for(path)]
            self.assertEqual(len(names), len(set(names)), f"{path}: {self.headers_for(path)}")

    def test_the_content_security_policy_stays_strict(self):
        csp = self.value("/index.html", "Content-Security-Policy")
        self.assertIn("default-src 'self'", csp)
        self.assertIn("script-src 'self' https://www.googletagmanager.com 'sha256-", csp)
        self.assertIn("style-src 'self';", csp)
        self.assertNotIn("unsafe-eval", csp)
        self.assertNotIn("script-src 'self' 'unsafe-inline'", csp)
        # the one policy covers the hashed files too
        self.assertEqual(self.value("/immutable/app.0123456789.js", "Content-Security-Policy"), csp)


if __name__ == "__main__":
    unittest.main()
