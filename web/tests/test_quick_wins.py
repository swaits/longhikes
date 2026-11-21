"""Small site-wide improvements that change nothing on screen: map click tolerance, cross-origin data
files, description endings, guessable-address redirects, the print rules, the extra skip links and the
list-size logo thumbnails."""
import os
import re
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)

import serve  # noqa: E402
from olt import common, records, redirects, thumbs  # noqa: E402

import builtsite  # noqa: E402

OUT = builtsite.OUT


def setUpModule():
    builtsite.ensure()


def read(relpath):
    with open(os.path.join(OUT, *relpath.split("/")), encoding="utf-8") as f:
        return f.read()


def asset(name):
    with open(os.path.join(WEB, "assets", name), encoding="utf-8") as f:
        return f.read()


class MapClickToleranceTest(unittest.TestCase):
    """The click handler itself needs a browser; these check the logic it is built on is in place."""

    @classmethod
    def setUpClass(cls):
        js = asset("app.js")
        cls.src = js[js.index("function wireOverview"):js.index("function fitToVisible")]

    def test_clicks_and_hovers_look_in_a_box_round_the_pointer_not_at_one_pixel(self):
        self.assertIn("queryRenderedFeatures([[x - pad, y - pad], [x + pad, y + pad]]", self.src)
        self.assertNotIn("map.on('click', def.id", self.src)
        self.assertNotIn("map.on('mousemove', def.id", self.src)
        self.assertIn("map.on('click', function (e)", self.src)

    def test_a_finger_gets_a_wider_box_than_a_mouse(self):
        match = re.search(r"var pad = coarse \? (\d+) : (\d+);", self.src)
        self.assertTrue(match)
        self.assertGreater(int(match.group(1)), int(match.group(2)))
        self.assertGreaterEqual(int(match.group(2)), 4)

    def test_the_nearest_feature_wins_and_a_miss_does_nothing(self):
        self.assertIn("d < bestD", self.src)
        self.assertIn("bestD <= pad * pad", self.src)
        self.assertIn("if (!hit) return;", self.src)

    def test_the_tracks_are_drawn_as_before(self):
        js = asset("app.js")
        self.assertIn("{ id: 'olt-line', color: '--trail', width: [3, 1.6, 9, 4]", js)
        self.assertNotIn("olt-hit", js)  # no extra hit layer: nothing new is drawn


class CrossOriginDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = serve.parse_headers(os.path.join(OUT, "_headers"))

    def headers(self, path):
        out = {}
        for pattern, headers in self.rules:
            if pattern.match(path):
                for name, value in headers:
                    self.assertNotIn(name.lower(), out, f"{path}: {name} set by two rules")
                    out[name.lower()] = value
        return out

    def test_the_public_data_files_allow_any_site_to_fetch_them(self):
        for path in ("/data/trails.json", "/data/overview.geojson", "/data/index.geojson", "/data/trails.csv",
                     "/data/all-gpx.zip", "/trails/appalachian/appalachian.gpx",
                     "/trails/appalachian/appalachian.geojson"):
            self.assertEqual(self.headers(path).get("access-control-allow-origin"), "*", path)

    def test_no_page_and_no_other_file_carries_it(self):
        for path in ("/", "/index.html", "/data/", "/data/schema/", "/data/changelog/", "/trails/appalachian/",
                     "/trails/appalachian/index.html", "/404.html", "/feed.xml", "/llms.txt",
                     "/trails/appalachian/trail.toml", "/trails/appalachian/release.txt", "/assets/og.png"):
            self.assertNotIn("access-control-allow-origin", self.headers(path), path)

    def test_every_built_data_file_and_trail_download_is_covered(self):
        for base, _, names in os.walk(os.path.join(OUT, "data")):
            for n in names:
                if n.endswith((".json", ".geojson", ".csv", ".zip")):
                    path = "/" + os.path.relpath(os.path.join(base, n), OUT).replace(os.sep, "/")
                    self.assertEqual(self.headers(path).get("access-control-allow-origin"), "*", path)

    def test_the_security_headers_are_still_on_everything(self):
        for path in ("/", "/trails/appalachian/", "/data/trails.json", "/trails/appalachian/appalachian.gpx"):
            h = self.headers(path)
            self.assertEqual(h.get("x-content-type-options"), "nosniff", path)
            self.assertEqual(h.get("referrer-policy"), "strict-origin-when-cross-origin", path)
            self.assertIn("frame-ancestors 'none'", h.get("content-security-policy", ""), path)


class DescriptionEndingTest(unittest.TestCase):
    def test_cut_clean_ends_at_a_word_with_a_full_stop_and_no_ellipsis(self):
        text = "The walk goes " + "on and on and on " * 20 + "to the end."
        cut = common.cut_clean(text, 100)
        self.assertLessEqual(len(cut), 100)
        self.assertTrue(cut.endswith("."))
        self.assertNotIn("…", cut)
        self.assertEqual(common.cut_clean("Short.", 100), "Short.")

    def test_cut_clean_never_ends_on_a_joining_word(self):
        cut = common.cut_clean("A long trail through the mountains and valleys of the northern part of the state", 52)
        self.assertNotRegex(cut, r"\b(and|of|the|through)\.$")

    def test_the_share_description_is_a_whole_sentence_where_one_fits(self):
        text = ("A trail of 70 miles (113 km) in Maine, usually 5 days. "
                "It follows the ridge and crosses several summits before it drops to the lake shore and the road.")
        self.assertEqual(common.share_description(text), "A trail of 70 miles (113 km) in Maine, usually 5 days.")

    def test_the_share_description_from_one_long_sentence_ends_at_a_word(self):
        got = common.share_description("A trail of " + "many long miles and more " * 12 + "end.")
        self.assertLessEqual(len(got), common.SHARE_DESCRIPTION_LIMIT)
        self.assertTrue(got.endswith("."))
        self.assertNotIn("…", got)

    def test_every_built_trail_page_describes_itself_in_whole_sentences(self):
        trails = os.path.join(OUT, "trails")
        pages = 0
        for tid in sorted(os.listdir(trails)):
            path = os.path.join(trails, tid, "index.html")
            if not os.path.isfile(path):
                continue
            doc = read(f"trails/{tid}/index.html")
            desc = re.search(r'<meta name="description" content="([^"]*)"', doc).group(1)
            og = re.search(r'<meta property="og:description" content="([^"]*)"', doc).group(1)
            tw = re.search(r'<meta name="twitter:description" content="([^"]*)"', doc).group(1)
            pages += 1
            for text in (desc, og, tw):
                self.assertNotIn("…", text, tid)
                self.assertTrue(text.endswith("."), f"{tid}: {text}")
            self.assertEqual(og, tw, tid)
            self.assertTrue(desc.startswith(og), tid)  # the share text is cut from the same text
        self.assertGreater(pages, 200)


class GuessableAddressTest(unittest.TestCase):
    @staticmethod
    def rec(tid, name, common_name="", kind="trail"):
        r = {"id": tid, "name": name, "kind": kind}
        if common_name:
            r["common_name"] = common_name
        return r

    def test_the_full_name_the_common_name_and_the_name_plus_trail_redirect(self):
        recs = [self.rec("pacific-crest", "Pacific Crest National Scenic Trail", "Pacific Crest Trail"),
                self.rec("wonderland", "Wonderland"),
                self.rec("high-line", "High Line Route", kind="route")]
        got = dict(redirects.trail_redirects(recs))
        self.assertEqual(got["pacific-crest-trail"], "pacific-crest")
        self.assertEqual(got["pacific-crest-national-scenic-trail"], "pacific-crest")
        self.assertEqual(got["wonderland-trail"], "wonderland")
        self.assertEqual(got["high-line-route"], "high-line")
        self.assertNotIn("high-line-route-trail", got)

    def test_a_real_page_is_never_shadowed_and_an_ambiguous_slug_is_dropped(self):
        recs = [self.rec("avon-trail", "Avon Trail"), self.rec("avon", "Avon"),
                self.rec("a", "Same Name Trail"), self.rec("b", "Same Name Trail")]
        got = dict(redirects.trail_redirects(recs, taken=["taken-trail"]))
        self.assertNotIn("avon-trail", got)       # the real page of the first record
        self.assertNotIn("same-name-trail", got)  # two records give it
        self.assertEqual(redirects.trail_redirects([self.rec("x", "Taken Trail")], taken=["taken-trail"]), [])

    def test_the_built_redirects_shadow_no_page_and_none_is_ambiguous(self):
        recs = records.load_records(ROOT)
        ids = {r["id"] for r in recs}
        text = read("_redirects")
        rules = [line.split() for line in text.splitlines() if line.strip() and not line.startswith("#")]
        sources = [r[0] for r in rules]
        self.assertEqual(len(sources), len(set(sources)), "a source is listed twice")
        trail_rules = [r for r in rules if r[0].startswith("/trails/")]
        self.assertGreater(len(trail_rules), 100)
        for source, dest, status in trail_rules:
            slug = source[len("/trails/"):].strip("/")
            self.assertNotIn(slug, ids, f"{source} shadows a trail page")
            self.assertFalse(os.path.exists(os.path.join(OUT, "trails", slug)), f"{source} shadows a built path")
            self.assertEqual(status, "301")
            if dest.startswith("/left-out/"):  # the hand-written lines for trails moved to the left-out list
                self.assertIn(slug, ("kekekabic", "pukaskwa-coastal"), source)
                continue
            self.assertRegex(dest, r"^/trails/[^/]+/$")
            self.assertIn(dest.split("/")[2], ids, dest)
            self.assertTrue(os.path.isfile(os.path.join(OUT, *dest.strip("/").split("/"), "index.html")), dest)
        # the one address a hiker types for a trail named differently from its id
        self.assertIn(["/trails/pacific-crest-trail/", "/trails/pacific-crest/", "301"], rules)
        for gone in ("kekekabic", "pukaskwa-coastal"):  # the removed trails keep their hand-written lines
            self.assertIn([f"/trails/{gone}/", "/left-out/#left-out-below-floor", "301"], rules)
        # one destination per slug: no slug is given by two records
        by_slug = {}
        for source, dest, _ in trail_rules:
            by_slug.setdefault(source.rstrip("/"), set()).add(dest)
        self.assertTrue(all(len(d) == 1 for d in by_slug.values()))
        for old in ("/lists/under-100-km/", "/lists/under-100-km"):  # the fixed ones are kept
            self.assertIn(old, sources)


class PrintRulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = asset("style.css")
        cls.start = cls.css.index("@media print {")
        cls.block = cls.css[cls.start:]

    def test_the_print_rules_are_one_block_at_the_end_and_nothing_follows_it(self):
        self.assertEqual(self.css.count("@media print {"), 1)
        self.assertEqual(self.block.count("{"), self.block.count("}"))
        depth, closed_at = 0, None
        for i, ch in enumerate(self.block):
            depth += (ch == "{") - (ch == "}")
            if depth == 0 and ch == "}":
                closed_at = i
                break
        self.assertEqual(self.block[closed_at + 1:].strip(), "")

    def test_the_chrome_is_left_off_and_the_text_is_black_on_white(self):
        for needle in (".site-header", ".breadcrumb", ".filters", ".button", ".maplibregl-ctrl", ".map__canvas",
                       ".skip-link", "display: none !important", "background: #fff", "color: #000",
                       'a[href^="http"]::after', "attr(href)"):
            self.assertIn(needle, self.block)

    def test_the_title_facts_sources_and_drawings_are_not_hidden(self):
        hidden = re.search(r"([^{}]*)\{ display: none !important; \}", self.block).group(1)
        for kept in (".titleblock", ".facts", ".trail-text", ".elev", ".map__fallback", ".mapfig", ".block"):
            self.assertNotIn(kept + ",", hidden + ",")
            self.assertNotIn(kept + " ", hidden + " ")


class SkipLinkTest(unittest.TestCase):
    def test_the_home_page_can_skip_the_map_and_go_to_the_list(self):
        doc = read("index.html")
        self.assertIn('<a class="skip-link" href="#main">Skip to content</a>', doc)
        self.assertIn('<a class="skip-link" href="#browse-list">Skip the map</a>', doc)
        self.assertIn('<a class="skip-link" href="#entries">Skip to the list of trails</a>', doc)
        for target in ("browse-list", "entries"):
            self.assertEqual(doc.count(f'id="{target}"'), 1, target)

    def test_a_page_without_those_targets_gets_only_the_one_skip_link(self):
        doc = read("trails/appalachian/index.html")
        self.assertEqual(doc.count('class="skip-link"'), 1)

    def test_every_skip_link_has_a_target_on_its_page(self):
        for page in ("index.html", "regions/index.html", "trails/appalachian/index.html", "lists/index.html"):
            doc = read(page)
            for target in re.findall(r'class="skip-link" href="#([^"]+)"', doc):
                self.assertEqual(doc.count(f'id="{target}"'), 1, f"{page}: #{target}")


class ListThumbnailTest(unittest.TestCase):
    def test_a_list_thumbnail_is_at_most_twice_the_largest_box_a_list_draws(self):
        for name in os.listdir(thumbs.LIST_THUMB_DIR):
            w, h = thumbs.png_size(os.path.join(thumbs.LIST_THUMB_DIR, name))
            self.assertLessEqual(w, 200, name)
            self.assertLessEqual(h, 124, name)
            self.assertTrue(os.path.isfile(os.path.join(thumbs.THUMB_DIR, name)), f"{name}: no full thumbnail")

    def test_the_list_shows_the_small_copy_with_its_own_size_and_the_header_the_larger(self):
        home_doc = read("index.html")
        m = re.search(r'<img src="(/trails/([^/]+)/shield-list\.png)" alt="" width="(\d+)" height="(\d+)"', home_doc)
        self.assertTrue(m)
        w, h = thumbs.png_size(os.path.join(OUT, *m.group(1).strip("/").split("/")))
        self.assertEqual((int(m.group(3)), int(m.group(4))), (w, h))
        page = read(f"trails/{m.group(2)}/index.html")
        self.assertIn(f'src="/trails/{m.group(2)}/shield-thumb.png"', page)
        self.assertNotIn("shield-list.png", page)

    def test_the_small_copies_are_much_smaller_in_all(self):
        small = big = 0
        for name in os.listdir(thumbs.LIST_THUMB_DIR):
            small += os.path.getsize(os.path.join(thumbs.LIST_THUMB_DIR, name))
            big += os.path.getsize(os.path.join(thumbs.THUMB_DIR, name))
        self.assertLess(small, big * 0.6)


if __name__ == "__main__":
    unittest.main()
