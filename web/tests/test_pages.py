"""Tests for the generated HTML pages (web/olt/pages.py and friends).

The first run builds the whole site into web/.cache/test-site (about a minute:
every line is simplified); later runs are incremental and take seconds.
"""
import html
import os
import re
import subprocess
import sys
import tempfile
import tomllib
import unittest
from html.parser import HTMLParser

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)

from olt import home, layout, pages, records, regions, site, trail, words  # noqa: E402

OUT = os.path.join(WEB, ".cache", "test-site")

# Linked from the shared navigation and footer; written by other page modules.
# Remove a path from this set once its page exists.
PENDING_PAGES = set()


class Tags(HTMLParser):
    """Collect every start tag with its attributes, and <script> contents."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.scripts = []
        self._in_script = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a))
        if tag == "script":
            self._in_script = [a, ""]

    def handle_data(self, data):
        if self._in_script is not None:
            self._in_script[1] += data

    def handle_endtag(self, tag):
        if tag == "script" and self._in_script is not None:
            self.scripts.append(tuple(self._in_script))
            self._in_script = None


def parse(path):
    p = Tags()
    with open(path, encoding="utf-8") as f:
        p.feed(f.read())
    return p


def html_files(out):
    for base, _, names in os.walk(out):
        for n in names:
            if n.endswith(".html"):
                yield os.path.join(base, n)


def resolve(out, url):
    """File for a root-relative URL, or None when the URL is not a local path."""
    if not url.startswith("/") or url.startswith("//"):
        return None
    path = url.split("#", 1)[0].split("?", 1)[0]
    if path.endswith("/"):
        path += "index.html"
    return os.path.join(out, *path.lstrip("/").split("/"))


class BuiltSiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        subprocess.run([sys.executable, os.path.join(WEB, "build.py"), "--out", OUT],
                       check=True, stdout=subprocess.DEVNULL)
        cls.records = records.load_records(ROOT)
        cls.pages = {}
        for rec in cls.records:
            with open(os.path.join(OUT, "trails", rec["id"], "index.html"), encoding="utf-8") as f:
                cls.pages[rec["id"]] = f.read()

    def test_one_detail_page_per_record(self):
        found = [d for d in os.listdir(os.path.join(OUT, "trails"))
                 if os.path.isfile(os.path.join(OUT, "trails", d, "index.html"))]
        self.assertEqual(len(self.records), 223)
        self.assertEqual(sorted(found), sorted(r["id"] for r in self.records))
        self.assertTrue(os.path.isfile(os.path.join(OUT, "index.html")))

    def test_record_files_copied(self):
        for rec in self.records:
            tdir = os.path.join(OUT, "trails", rec["id"])
            self.assertTrue(os.path.isfile(os.path.join(tdir, "trail.toml")), rec["id"])
            has_release = os.path.isfile(os.path.join(ROOT, rec["id"], "release.txt"))
            self.assertEqual(os.path.isfile(os.path.join(tdir, "release.txt")), has_release, rec["id"])

    def test_internal_links_resolve(self):
        missing = set()
        for path in html_files(OUT):
            for tag, a in parse(path).tags:
                for key in ("href", "src"):
                    url = a.get(key)
                    if not url or url.split("?")[0].split("#")[0] in PENDING_PAGES:
                        continue
                    target = resolve(OUT, url)
                    if target and not os.path.isfile(target):
                        missing.add((os.path.relpath(path, OUT), url))
                    self.assertFalse(url.startswith(("http://", "https://")) and tag in ("script", "link")
                                     and a.get("rel") != "canonical", f"external asset {url} in {path}")
        self.assertEqual(sorted(missing)[:20], [])

    def test_no_inline_scripts(self):
        for path in html_files(OUT):
            for a, body in parse(path).scripts:
                if a.get("type") in ("application/json", "application/ld+json"):
                    continue
                self.assertTrue(a.get("src"), f"inline script in {path}")
                self.assertEqual(body.strip(), "", f"script with src and a body in {path}")

    def test_style_attributes_only_carry_custom_properties(self):
        # The CSP allows style="" (style-src-attr) only for data passed to CSS.
        for path in html_files(OUT):
            for tag, a in parse(path).tags:
                if "style" in a:
                    self.assertRegex(a["style"], r"^\s*--[a-z-]+:\s*[-0-9.%]+;?\s*$", f"{tag} in {path}")

    def test_record_only_pages_have_no_line_downloads(self):
        for rec in self.records:
            if rec["derived"]["has_line"]:
                continue
            for tag, a in parse(os.path.join(OUT, "trails", rec["id"], "index.html")).tags:
                href = a.get("href", "")
                line_file = href.startswith("/trails/") and href.endswith((".gpx", ".geojson"))
                self.assertFalse(line_file or "download" in a, f"{rec['id']} links {href}")

    def test_line_pages_offer_every_download(self):
        for rec in self.records:
            if not rec["derived"]["has_line"]:
                continue
            page = self.pages[rec["id"]]
            names = trail_downloads(rec["id"])
            self.assertTrue(names, rec["id"])
            for name in names:
                self.assertIn(f'href="/trails/{rec["id"]}/{name}"', page, rec["id"])
            self.assertIn("simplified to 5 m", html.unescape(page), rec["id"])

    def test_every_field_appears(self):
        """Each field the record carries is on its page (text or number, in some written form)."""
        for rec in self.records:
            with open(os.path.join(ROOT, rec["id"], "trail.toml"), "rb") as f:
                raw = tomllib.load(f)
            text = page_text(self.pages[rec["id"]])
            for field, value in leaves(raw):
                if field.endswith(("line_file", "logo_file")) and value == "":
                    continue  # shown as "None included"
                for form in written_forms(value):
                    if form.lower() in text.lower():
                        break
                else:
                    self.fail(f"{rec['id']}: {field} = {value!r} not on the page")

    def test_partial_line_notice_and_row_note_for_exactly_the_partial_records(self):
        """Decided from the TOML alone: a track, measured, more than 15% from the published length."""
        expected = set()
        for rec in self.records:
            with open(os.path.join(ROOT, rec["id"], "trail.toml"), "rb") as f:
                raw = tomllib.load(f)
            v = raw.get("verification", {})
            if raw["source"].get("line_file") and v.get("verified") and abs(v.get("difference_percent", 0)) > 15:
                expected.add(rec["id"])
        self.assertEqual(len(expected), 14)
        self.assertIn("knobstone", expected)
        for rec in self.records:
            page = self.pages[rec["id"]]
            has_notice = 'class="notice notice--partial"' in page
            self.assertEqual(has_notice, rec["id"] in expected, rec["id"])
            if has_notice:  # the notice is inside the download panel, above the buttons
                panel = page[page.index('<section class="panel" id="download"'):]
                self.assertLess(panel.index("notice--partial"), panel.index('<ul class="downloads">'), rec["id"])
                v = rec["verification"]
                text = page_text(panel[:panel.index('<ul class="downloads">')])
                self.assertIn(f"{v['measured_km']:,.1f} km against a published", text)
                self.assertIn(f"{rec['length_km']:,} km ({words.fmt_percent(v['difference_percent'])})", text)
                self.assertIn(re.sub(r"\s+", " ", rec["source"]["length_gap_note"]), text, rec["id"])
            short = rec["id"] in expected and rec["verification"]["difference_percent"] < 0
            glance = page[page.index('<section class="glance'):page.index("</section>", page.index('<section class="glance'))]
            self.assertEqual("Partial GPX to download here" in glance, short, rec["id"])
            if rec["derived"]["has_line"]:
                self.assertRegex(glance, r'<dt>GPX</dt><dd><a href="#download">(Partial )?GPX to download here</a>', rec["id"])
                # the partial warning is in view, outside "About this data"
                if rec["id"] in expected:
                    self.assertLess(page.index("notice--partial"), page.index('<details class="about-data"'), rec["id"])
        rows_seen = set()
        for path in html_files(OUT):
            with open(path, encoding="utf-8") as f:
                doc = f.read()
            rel = os.path.relpath(path, OUT)
            for m in re.finditer(r'<li class="entry" data-id="([^"]+)"([^>]*)>(.*?)\n</li>', doc, re.S):
                tid, attrs, row = m.groups()
                self.assertEqual('data-partial="yes"' in attrs, tid in expected, f"{rel}: {tid}")
                self.assertEqual(row.count('class="entry__partial"'), 1 if tid in expected else 0, f"{rel}: {tid}")
                if tid in expected:
                    rows_seen.add(tid)
                    self.assertRegex(page_text(row), r"Track measures [\d,.]+ mi [\d,.]+ km (of|against) [\d,]+ mi [\d,.]+ km published")
            entries = len(re.findall(r'<li class="entry" ', doc))
            partial_rows = len(re.findall(r'<li class="entry" [^>]*data-partial="yes"', doc))
            self.assertEqual(doc.count('class="entry__partial"'), partial_rows, rel)
            if not entries:
                self.assertNotIn("entry__partial", doc, rel)
            if not rel.startswith("trails" + os.sep):
                self.assertNotIn("notice--partial", doc, rel)
        self.assertEqual(rows_seen, expected)

    def test_gpx_first_and_primary_in_every_download_group(self):
        groups = 0
        for rec in self.records:
            for group in re.findall(r'<li class="download">(.*?)</li>', self.pages[rec["id"]], re.S):
                groups += 1
                label = html.unescape(re.search(r'<strong id="[^"]+">(.*?)</strong>', group).group(1))
                links = re.findall(r'<a class="([^"]*)" href="[^"]+\.(gpx|geojson)"[^>]*>(.*?)</a>', group, re.S)
                kinds = [k for _, k, _ in links]
                self.assertTrue(kinds, rec["id"])
                if "gpx" in kinds:
                    self.assertEqual(kinds[0], "gpx", f"{rec['id']}: {label}")
                    self.assertIn("button--primary", links[0][0], rec["id"])
                self.assertEqual(sorted(kinds, key=lambda k: k != "gpx"), kinds, rec["id"])
                for cls, kind, inner in links:
                    # the accessible name: the link's text, visually hidden parts included
                    name = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", inner))).strip()
                    fmt = "GPX" if kind == "gpx" else "GeoJSON"
                    self.assertRegex(name, rf"^{re.escape(label)}: {fmt}, [\d.,]+ [KM]?B$", rec["id"])
                    self.assertEqual("button--primary" in cls, kind == "gpx", rec["id"])
                if label.startswith("Extract"):
                    self.assertNotIn("swatch", group, rec["id"])
        self.assertGreater(groups, 85)

    def test_no_page_in_the_build_sets_a_table(self):
        """The site sets no tables: sets of trails are the trail rows, other sets are rows in the
        same language, and a record's raw fields are a definition list."""
        pages = 0
        for path in html_files(OUT):
            with open(path, encoding="utf-8") as f:
                doc = f.read()
            pages += 1
            self.assertNotIn("<table", doc, os.path.relpath(path, OUT))
        self.assertGreater(pages, 20)

    def test_raw_record_listing_holds_every_field(self):
        for rec in self.records:
            with open(os.path.join(ROOT, rec["id"], "trail.toml"), "rb") as f:
                raw = tomllib.load(f)
            page = self.pages[rec["id"]]
            self.assertIn('<details class="rawrecord">', page, rec["id"])
            # the last block of the page's main column
            tail = page[page.index('<details class="rawrecord">'):]
            self.assertNotIn('<section class="block"', tail, rec["id"])
            listing = re.search(r'<dl class="rawrecord__fields">(.*?)</dl>', tail, re.S).group(1)
            rows = {html.unescape(f): re.sub(r"\s+", " ", html.unescape(v)).strip()
                    for f, v in re.findall(r'<div><dt><code>(.*?)</code></dt><dd>(.*?)</dd></div>', listing, re.S)}
            fields = dict(leaves(raw))
            self.assertEqual(set(rows), set(fields), rec["id"])
            for field, value in fields.items():
                self.assertEqual(rows[field], re.sub(r"\s+", " ", trail.raw_value(value)).strip(), f"{rec['id']}: {field}")

    def test_no_raw_tokens_in_the_main_flow(self):
        for rec in self.records:
            page = self.pages[rec["id"]]
            top = page[page.index('<main id="main">'):page.index('<details class="about-data"')]
            self.assertNotIn('<code class="raw">', top, rec["id"])
            main = page[page.index('<div class="about-data__body'):page.index('<details class="rawrecord">')]
            codes = set(html.unescape(c) for c in re.findall(r'<code class="raw">(.*?)</code>', main))
            self.assertLessEqual(codes, {rec["id"]}, rec["id"])
            # "About this data" sections are not landmarks; the glance and the aside panels are
            self.assertNotIn('<section class="block" aria-labelledby', page, rec["id"])
            self.assertIn('<section class="glance detail__glance" aria-labelledby="glance-title">', page, rec["id"])
            self.assertIn('<h2 id="links-title">Links</h2>', main, rec["id"])

    def test_record_without_a_line_says_so_once(self):
        for rec in self.records:
            page = self.pages[rec["id"]]
            main = page_text(page[page.index('<div class="about-data__body'):page.index('<details class="rawrecord">')])
            helper = "Where to ask for the track: a layer or relation page"
            if rec["derived"]["has_line"]:
                self.assertEqual(helper in main, bool(rec["source"].get("url")), rec["id"])
                continue
            self.assertNotIn(helper, main, rec["id"])
            for gone in ("none (no line included)", "None (no line included)", "No line to measure", "None recorded",
                         "none (no track included)", "None (no track included)", "No track to measure"):
                self.assertNotIn(gone, main, rec["id"])
            for row in ("Coordinates", "May be passed on", "OpenStreetMap only", "Line source", "Track source",
                        "Line in this dataset", "Track in this dataset", "Why there is no line", "Why there is no track"):
                self.assertNotIn(f"<dt>{row}</dt>", page, rec["id"])
            if not rec["derived"]["files"].get("shield"):
                logo = re.search(r'<h2 id="logo-title">Logo</h2>(.*?)</section>', page, re.S).group(1)
                self.assertEqual(logo.count("<p"), 1, rec["id"])
                self.assertNotIn("<dl", logo, rec["id"])

    def test_all_guides_button_only_with_more_than_one_guide(self):
        for rec in self.records:
            page = self.pages[rec["id"]]
            if rec["derived"]["has_line"] or rec["derived"]["kind"] != "route":
                continue
            # The hatched frame, or the map of a trail drawn from its start and end.
            start = re.search(r'<figure class="mapfig (?:mapfig--empty|[^"]*"[^>]* data-map="sketch")', page).start()
            frame = page[start:page.index("</figure>", start)]
            self.assertEqual(">All guides<" in frame, len(rec.get("guide", [])) > 1
                             and rec["route"]["line_policy"] == "open"
                             and any(g.get("access") == "free" for g in rec["guide"]), rec["id"])

    def test_names_marked_with_their_language(self):
        langs = site.load().name_lang
        self.assertEqual(langs, {"traversee-charlevoix": "fr", "sentier-international-appalaches": "fr"})
        with open(os.path.join(OUT, "index.html"), encoding="utf-8") as f:
            home = f.read()
        by_id = {r["id"]: r for r in self.records}
        for tid, lang in langs.items():
            marked = f'<span lang="{lang}">{html.escape(by_id[tid]["name"], quote=True)}</span>'
            self.assertIn(f'<a href="/trails/{tid}/">{marked}</a>', home, tid)
            page = self.pages[tid]
            self.assertIn(f"<h1>{marked}", page, tid)
            self.assertIn(f'<li aria-current="page">{marked}</li>', page, tid)
        for path in html_files(OUT):
            with open(path, encoding="utf-8") as f:
                for m in re.finditer(r'<span lang="([^"]+)">([^<]*)</span>', f.read()):
                    names = {html.escape(by_id[t]["name"], quote=True) for t in langs}
                    self.assertIn(m.group(2), names, path)

    def test_every_table_head_cell_has_col_scope(self):
        for path in html_files(OUT):
            with open(path, encoding="utf-8") as f:
                doc = f.read()
            for head in re.findall(r"<thead>(.*?)</thead>", doc, re.S):
                for th in re.findall(r"<th\b[^>]*>", head):
                    self.assertIn('scope="col"', th, path)

    def test_maplibre_is_not_loaded_with_the_page(self):
        # app.js loads MapLibre a moment after the page has loaded, from the
        # addresses on its own tag (layout.py); the page itself names no MapLibre file.
        with open(os.path.join(OUT, "index.html"), encoding="utf-8") as f:
            doc = f.read()
        tag = re.search(r'<script src="/immutable/app\.[0-9a-f]{10}\.js" defer ([^>]*)></script>', doc)
        self.assertIsNotNone(tag)
        self.assertRegex(tag.group(1), r'data-maplibre-js="/immutable/maplibre-gl\.[0-9a-f]{10}\.js"')
        self.assertRegex(tag.group(1), r'data-maplibre-css="/immutable/maplibre-gl\.[0-9a-f]{10}\.css"')
        self.assertNotRegex(doc, r'<link[^>]*maplibre')
        self.assertNotRegex(doc, r'<script src="[^"]*maplibre')
        self.assertNotIn("data-contour-js", tag.group(1))

    def test_not_found_page_has_a_search_form(self):
        with open(os.path.join(OUT, "404.html"), encoding="utf-8") as f:
            doc = f.read()
        form = re.search(r'<form class="notfound-search" action="/" method="get"[^>]*>(.*?)</form>', doc, re.S)
        self.assertIsNotNone(form)
        field = re.search(r'<input class="input" id="([^"]+)" name="q"', form.group(1))
        self.assertIsNotNone(field)
        self.assertIn(f'<label class="field__label" for="{field.group(1)}">', form.group(1))
        self.assertIn('type="submit"', form.group(1))
        self.assertNotIn("&lt;id&gt;", doc)

    def test_titles_and_descriptions(self):
        name = site.load().name
        for path in html_files(OUT):
            p = parse(path)
            metas = [a for t, a in p.tags if t == "meta" and a.get("name") == "description"]
            self.assertEqual(len(metas), 1, path)
            self.assertTrue(metas[0].get("content"), path)
            with open(path, encoding="utf-8") as f:
                doc = f.read()
            self.assertRegex(doc, r"<title>[^<]+</title>", path)
            self.assertIn(html.escape(name), doc, path)


def trail_downloads(tid):
    tdir = os.path.join(OUT, "trails", tid)
    return [n for n in os.listdir(tdir) if n.endswith((".gpx", ".geojson"))]


def page_text(doc):
    """Visible text and attribute values of a page, unescaped, with whitespace collapsed."""
    doc = re.sub(r"<[^>]+?(?:href|title|cite)=\"([^\"]*)\"[^>]*>", lambda m: " " + m.group(1) + " " + m.group(0), doc)
    text = html.unescape(re.sub(r"<[^>]+>", " ", doc))
    return re.sub(r"\s+", " ", text)


def leaves(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from leaves(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from leaves(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def written_forms(value):
    """The ways a value may be written on a page."""
    if isinstance(value, bool):
        return [str(value).lower()]
    if isinstance(value, (int, float)):
        forms = [str(value), words.fmt_km(value), words.fmt_percent(value), f"{abs(value):.1f}"]
        return forms
    text = re.sub(r"\s+", " ", str(value)).strip()
    return [text, text.replace("`", "")]


class RenderUnitTest(unittest.TestCase):
    def test_links_listed_in_order_with_publisher(self):
        rec = sample_record("L Trail")
        rec["link"] = [
            {"title": "First", "publisher": "Pub One", "url": "https://one.example/a?x=1&y=2", "note": "Maps."},
            {"title": "Second", "publisher": "Pub Two", "url": "https://two.example/b"}]
        rec.setdefault("hike", {})["official_url"] = "https://trail.example/"
        body = trail.render(rec, site.Site("N", "T"))[2]
        self.assertIn("More about this trail", body)
        self.assertLess(body.index("First"), body.index("Second"))
        self.assertIn('href="https://one.example/a?x=1&amp;y=2"', body)
        self.assertIn("Pub One", body)
        self.assertIn("<small>Maps.</small>", body)
        self.assertEqual(body.count("<small>Maps.</small>"), 1)

    def test_stand_in_link_is_not_repeated_in_the_list(self):
        rec = sample_record("L Trail")
        rec["link"] = [{"title": "First", "publisher": "Pub One", "url": "https://one.example/a"},
                       {"title": "Second", "publisher": "Pub Two", "url": "https://two.example/b"}]
        body = trail.render(rec, site.Site("N", "T"))[2]
        self.assertEqual(body.count('href="https://one.example/a"'), 1)
        self.assertIn('href="https://two.example/b"', body)
        self.assertNotIn("Official site", body)
        rec["link"] = rec["link"][:1]
        self.assertNotIn("More about this trail", trail.render(rec, site.Site("N", "T"))[2])

    def test_no_links_shows_nothing(self):
        body = trail.render(sample_record("L Trail"), site.Site("N", "T"))[2]
        self.assertNotIn("More about this trail", body)
        self.assertNotIn("morelinks", body)

    def test_link_title_and_note_are_escaped(self):
        rec = sample_record("L Trail")
        rec["link"] = [{"title": "<script>alert(1)</script>", "publisher": "<b>P</b>",
                        "url": "https://one.example/", "note": "<img src=x onerror=1>"}]
        body = trail.render(rec, site.Site("N", "T"))[2]
        self.assertNotIn("<script>alert(1)", body)
        self.assertNotIn("<b>P</b>", body)
        self.assertNotIn("<img src=x", body)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", body)

    def test_links_with_an_official_site_keep_that_button(self):
        rec = sample_record("L Trail")
        rec["hike"] = {"official_url": "https://official.example/"}
        rec["link"] = [{"title": "T", "publisher": "Wiki", "url": "https://wiki.example/t"}]
        buttons = re.search(r'<p class="trail-actions">.*?</p>', trail.action_buttons(rec), re.S).group(0)
        self.assertIn("Official site", buttons)
        self.assertNotIn("wiki.example", buttons)

    def test_no_official_site_first_link_stands_in_named_by_publisher(self):
        rec = sample_record("L Trail")
        rec["link"] = [{"title": "T", "publisher": "Wiki Pub", "url": "https://wiki.example/t"},
                       {"title": "U", "publisher": "Other", "url": "https://other.example/u"}]
        buttons = re.search(r'<p class="trail-actions">.*?</p>', trail.action_buttons(rec), re.S).group(0)
        self.assertIn('href="https://wiki.example/t"', buttons)
        self.assertIn("Wiki Pub", buttons)
        self.assertNotIn("other.example", buttons)
        self.assertNotIn("Official site", buttons)

    def test_names_are_escaped(self):
        rec = sample_record(name='Trail & "Quotes" <b>bold</b>')
        _, description, body, _ = trail.render(rec, site.Site("Site & Co", "Tag"))
        doc = layout.layout(rec["name"], body, path="/trails/x/", description=description,
                            site=site.Site("Site & Co", "Tag"))
        self.assertIn("Trail &amp; &quot;Quotes&quot; &lt;b&gt;bold&lt;/b&gt;", doc)
        self.assertNotIn("<b>bold</b>", doc)
        self.assertNotIn("<script>alert", doc)
        self.assertIn("Site &amp; Co", doc)
        self.assertIn('href="https://example.org/?a=1&amp;b=2"', doc)

    def test_canonical_only_with_base_url(self):
        doc = layout.layout("T", "", path="/trails/x/", site=site.Site("N", "T"))
        self.assertNotIn('rel="canonical"', doc)
        doc = layout.layout("T", "", path="/trails/x/", site=site.Site("N", "T", base_url="https://example.org/"))
        self.assertIn('<link rel="canonical" href="https://example.org/trails/x/">', doc)

    def test_site_name_comes_from_settings(self):
        doc = layout.layout("", "", path="/", site=site.Site("Another Name", "A tagline"))
        self.assertIn("<title>Another Name: A tagline</title>", doc)
        self.assertNotIn("Long Hikes", doc)

    def test_report_links_need_repo_url(self):
        self.assertNotIn("/issues", layout.footer(site.Site("N", "T")))
        self.assertIn("https://example.org/repo/issues", layout.footer(site.Site("N", "T", repo_url="https://example.org/repo")))

    def test_trail_correction_links_github(self):
        gh = site.Site("N", "T", repo_url="https://github.com/swaits/longhikes")
        _, _, body, _ = trail.render(sample_record("A & B Trail"), gh)
        plain = html.unescape(body)
        self.assertIn("Report a correction", plain)
        self.assertIn("https://github.com/swaits/longhikes/issues/new?"
                      "template=correction.yml&title=Correction%3A+A+%26+B+Trail+%28x%29&trail=x", plain)
        # the raw editor, which a web contributor cannot finish a change in, is no longer offered
        self.assertNotIn("Edit this record", plain)
        self.assertNotIn("/edit/", plain)
        self.assertIn("The record file", plain)
        self.assertIn("https://github.com/swaits/longhikes/blob/main/x/trail.toml", plain)
        self.assertIn("History", plain)
        self.assertIn("https://github.com/swaits/longhikes/commits/main/x", plain)

    def test_logo_source_without_a_logo_file_is_not_called_taken_from(self):
        # A record can name where its logo is held without including the logo.
        rec = sample_record("X Trail")
        rec["shield"] = {"status": "logo-not-found", "logo_source": "https://holder.example/", "contact": "Holder",
                         "note": "No policy found.", "logo_file": "", "logo_owner": "Holder & Co"}
        _, _, body, _ = trail.render(rec, site.Site("N", "T"))
        self.assertIn('href="https://holder.example/"', body)
        self.assertNotIn("logo was taken from", body)
        self.assertIn("the logo is not included here", body)
        self.assertIn("Emblem not found.", body)
        self.assertIn("An emblem exists or may exist, but no usable artwork of it was found at a source the dataset allows.", body)

    def test_trail_correction_links_github_branch(self):
        gh = site.Site("N", "T", repo_url="https://github.com/o/r/", repo_branch="dev")
        block = html.unescape(trail.correction_block(sample_record("X Trail"), gh))
        self.assertIn("https://github.com/o/r/blob/dev/x/trail.toml", block)
        self.assertIn("https://github.com/o/r/commits/dev/x", block)

    def test_trail_correction_links_non_github_fall_back_to_repo(self):
        other = site.Site("N", "T", repo_url="https://example.org/repo")
        block = html.unescape(trail.correction_block(sample_record("X Trail"), other))
        self.assertIn('href="https://example.org/repo"', block)
        self.assertNotIn("template=correction.yml", block)
        self.assertNotIn("/edit/", block)
        self.assertNotIn("/blob/", block)
        self.assertNotIn("/commits/", block)
        self.assertNotIn("Edit this record", block)

    def test_trail_correction_links_empty_repo_url(self):
        block = trail.correction_block(sample_record("X Trail"), site.Site("N", "T"))
        self.assertEqual(block, "")
        self.assertNotIn("github.com", layout.footer(site.Site("N", "T")))
        self.assertNotIn("Suggest a trail", layout.footer(site.Site("N", "T")))

    def test_footer_and_home_contribute_links_github(self):
        gh = site.Site("N", "T", repo_url="https://github.com/swaits/longhikes")
        footer = html.unescape(layout.footer(gh))
        self.assertIn("Fix or add a trail", footer)
        self.assertIn('href="https://github.com/swaits/longhikes"', footer)
        self.assertIn("Suggest a trail", footer)
        self.assertIn("https://github.com/swaits/longhikes/issues/new?template=new-trail.yml", footer)
        body = html.unescape(home.render([sample_record("X Trail")], gh))
        self.assertIn("https://github.com/swaits/longhikes/issues/new?template=new-trail.yml", body)

    def test_footer_contribute_links_non_github_have_no_github_forms(self):
        other = site.Site("N", "T", repo_url="https://example.org/repo")
        footer = html.unescape(layout.footer(other))
        self.assertIn('href="https://example.org/repo"', footer)
        self.assertNotIn("template=", footer)
        self.assertNotIn("github.com", footer)

    def test_render_site_on_a_synthetic_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, out = os.path.join(tmp, "repo"), os.path.join(tmp, "out")
            os.makedirs(os.path.join(repo, "x"))
            with open(os.path.join(repo, "x", "trail.toml"), "w", encoding="utf-8") as f:
                f.write('id = "x"\n')
            rec = sample_record(name="A & B")
            n = pages.render_site([rec], out, repo, site=site.Site("N", "T"))
            # trail page + home + 404 + places hub + 1 place + its part of the country + lists hub + routes,
            # sources, logos, about, data, schema, changelog, left out, saved (no list holds MIN_SIZE trails),
            # and the two reference pages, the glossary and the method (the tables, authors, recent and
            # linked-trails pages need at least MIN_SIZE trails and are not built for one)
            # and a page for each state and province with no listed trail (regions.empty_places)
            self.assertEqual(n, 18 + len(regions.empty_places([rec])))
            with open(os.path.join(out, "trails", "x", "index.html"), encoding="utf-8") as f:
                self.assertIn("A &amp; B", f.read())
            with open(os.path.join(out, "index.html"), encoding="utf-8") as f:
                self.assertIn('href="/trails/x/"', f.read())


def sample_record(name):
    return {
        "id": "x", "name": name, "short_name": "X", "country": "US", "regions": ["AZ"],
        "length_km": 100, "length_note": "about 62 mi", "tier": "regional", "designation": "A & B Association",
        "wave": 1,
        "source": {"status": "none", "publisher": "P", "url": "https://example.org/?a=1&b=2", "format": "None",
                   "crs": "EPSG:4326", "licence": "none-stated", "licence_text": "None.", "attribution": "none",
                   "osm_only": False, "mainline": "None", "source_checked": "2026-11-10", "redistributable": True,
                   "line_source": "none (no line included)", "line_file": "",
                   "line_absent_reason": "No line is included. <script>alert(1)</script>"},
        "osm": {"relation": 0, "note": "None"},
        "shield": {"status": "no-logo-exists", "logo_source": "", "contact": "P", "note": "None",
                   "logo_file": "", "logo_owner": "P"},
        "verification": {"verified": False, "note": "No line to measure."},
        "derived": {"kind": "designated", "has_line": False, "length_mi": 62, "files": {},
                    "status": "record-only", "downloads": []},
    }


if __name__ == "__main__":
    unittest.main()
