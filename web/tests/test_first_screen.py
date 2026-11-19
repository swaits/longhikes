"""The first screen: what the top of the trail page and the home page hold, the home page's lists
(read from data), the header's Lists item, the shared layout of every page that shows a set of
trails, the rows that take the place of tables, and the maps' static drawings (olt/sketch.py) with
the script's handover from them.

Pages are rendered one at a time; the site is not built. The sketch reads the track files of a
site directory, so those are written to a temporary one here. The behaviour of the script in a
browser was checked by driving the pages (see the changelog); these pin what its source promises.
"""
import json
import os
import re
import sys
import tempfile
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from olt import browse, common, datafiles, facets, home, layout, pagekit, records, site, sketch, trail  # noqa: E402

SITE = site.load()


def read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def load(tid):
    return records.load_record(ROOT, tid)


class HomePageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recs = records.load_records(ROOT)
        cls.body = home.render(cls.recs, SITE, ROOT)

    def test_the_hero_no_longer_repeats_the_site_mark_or_the_strip_of_words(self):
        hero = self.body[:self.body.index('class="container home"')]
        self.assertNotIn("lockup", hero)
        self.assertNotIn("hero__tags", hero)
        self.assertNotIn("<img", hero)
        self.assertIn("<h1", hero)
        self.assertIn(SITE.tagline.rstrip("."), hero)

    def test_the_header_shows_the_name_on_the_home_page(self):
        css = read(WEB, "assets", "style.css")
        self.assertNotIn(".hero--home) .site-header .wordmark", css)

    def test_the_lists_row_is_read_from_the_data_file_in_its_order(self):
        entries = datafiles.lists(ROOT)
        keys = home.home_picks(entries)
        self.assertEqual(keys, ["national-scenic-trails", "routes", "high-routes", "loops", "under-100-miles",
                                "a-week-or-less", "one-to-two-weeks", "a-month-or-more", "with-gpx", "canada"])
        row = home.lists_row(self.recs, keys)
        titles = re.findall(r'<li><a href="[^"]+">(.*?)<span class="lists-row__n">', row)
        # the file's lists in its order, with the trip-length band it leaves out added where it belongs
        keys = keys[:7] + ["two-to-four-weeks"] + keys[7:]
        self.assertEqual(titles, [browse.by_key(k).title for k in keys])
        self.assertTrue(row.rstrip().endswith("</nav>"))
        self.assertIn('<li class="lists-row__all"><a href="/lists/">All lists</a></li></ul>', row)
        self.assertNotIn("Hiking in", row)
        self.assertNotIn("chips", row)  # one quiet line of links, not pills
        # a different file gives a different row: the set is not a constant of the generator
        other = home.home_picks([{"key": "loops", "home": 2}, {"key": "routes", "home": 1}, {"key": "canada"}])
        self.assertEqual(other, ["routes", "loops"])
        self.assertEqual(re.findall(r'<li><a href="[^"]+">(.*?)<span', home.lists_row(self.recs, other)), ["Routes", "Loops"])

    def test_the_row_offers_every_trip_length_band_the_time_filter_does(self):
        row = home.lists_row(self.recs, home.home_picks(datafiles.lists(ROOT)))
        linked = [browse.by_key(k) for k in re.findall(r'href="/lists/([^/"]+)/"', row)]
        for band, label, _ in facets.TIME_BANDS:
            members = [r for r in self.recs if facets.time_band(r) == band]
            self.assertTrue(members, band)
            self.assertTrue(any(all(lst.test(r) for r in members) for lst in linked if lst.group == "time"),
                            f"no chip for {label}")
        self.assertIn("Two weeks to a month", row)
        self.assertNotIn("weekend", row.lower())
        # a row the data file gives with no trip length is not given one
        self.assertNotIn("weeks", home.lists_row(self.recs, ["loops", "routes"]))

    def test_a_row_that_scrolls_sideways_fades_at_its_edge(self):
        css = read(WEB, "assets", "style.css")
        phone = css[css.index(".lists-row ul {\n    flex-wrap: nowrap"):]
        phone = phone[:phone.index("}")]
        self.assertIn("mask-image: linear-gradient(to right", phone)

    def test_the_introduction_is_the_headline_its_sentence_and_the_lists(self):
        intro = self.body[:self.body.index('class="container home"')]
        self.assertIn('<section class="intro"', intro)
        h1, lede, lists = intro.index("<h1"), intro.index('class="intro__lede"'), intro.index('class="lists-row"')
        self.assertLess(h1, lede)
        self.assertLess(lede, lists)

    def test_search_and_filters_are_one_bar_with_a_clear_control_that_starts_hidden(self):
        bar = self.body[self.body.index('class="filters__bar"'):self.body.index('id="filters-panels"')]
        self.assertIn('id="q"', bar)
        self.assertIn('aria-controls="filters-panels"', bar)
        self.assertRegex(bar, r'class="button button--quiet filters__clear" type="reset" hidden')
        self.assertIn('id="filters-panels"', self.body)
        self.assertIn('class="filters__panel"', self.body)
        self.assertIn('class="filters__more"', self.body)

    def test_the_trails_and_the_map_are_the_shared_browsing_layout_with_the_search_bar_over_the_rows(self):
        grid = self.body[self.body.index('<div class="browse">'):]
        self.assertLess(grid.index('class="browse__map" id="map"'), grid.index('class="browse__list"'))
        self.assertLess(grid.index('class="browse__list"'), grid.index('id="finder-form"'))
        self.assertLess(grid.index('id="finder-form"'), grid.index('id="entries"'))
        self.assertNotIn("filters__maplink", self.body)

    def test_the_open_filters_sit_between_the_bar_and_the_rows_and_can_be_closed(self):
        css = read(WEB, "assets", "style.css")
        self.assertNotRegex(css, r"\.filters__panels \{[^}]*position: absolute;")
        self.assertIn('class="button filters__done"', self.body)
        js = read(WEB, "assets", "app.js")
        self.assertIn("e.key === 'Escape'", js)


class ListEntriesCheckTest(unittest.TestCase):
    def check(self, entries, keys=("a", "b", "c")):
        import check_datafiles
        errors = []
        check_datafiles.check_list_entries(entries, set(keys), errors)
        return errors

    def test_the_real_entries_pass(self):
        import check_datafiles
        errors = []
        import tomllib
        with open(os.path.join(ROOT, "collections.toml"), "rb") as f:
            doc = tomllib.load(f)
        check_datafiles.check_list_entries(doc["list"], check_datafiles.built_in_list_keys(), errors)
        self.assertEqual(errors, [])

    def test_unknown_keys_repeats_and_bad_positions_are_reported(self):
        self.assertEqual(self.check([{"key": "a", "home": 1}, {"key": "b", "home": 2}]), [])
        self.assertTrue(any("not the key of a list" in e for e in self.check([{"key": "zzz", "home": 1}])))
        self.assertTrue(any("appears twice" in e for e in self.check([{"key": "a", "home": 1}, {"key": "a", "home": 2}])))
        self.assertTrue(any("also the place of" in e for e in self.check([{"key": "a", "home": 1}, {"key": "b", "home": 1}])))
        self.assertTrue(any("whole number" in e for e in self.check([{"key": "a", "home": 0}])))
        self.assertTrue(any("whole number" in e for e in self.check([{"key": "a", "home": "1"}])))
        self.assertTrue(any("unknown field" in e for e in self.check([{"key": "a", "shown": 1}])))


class HeaderTest(unittest.TestCase):
    def nav(self, path):
        html = str(layout.header(path, SITE))
        return {m.group(2): m.group(1) for m in re.finditer(r'<a href="(/[^"]*)"(?: aria-current="[a-z]+")?>', html)}, html

    def current(self, path):
        html = str(layout.header(path, SITE))
        return re.findall(r'<a href="([^"]+)" aria-current="(?:page|true)"', html)

    def test_the_items_are_trails_places_lists_about_saved(self):
        html = str(layout.header("/", SITE))
        names = re.findall(r"<li[^>]*><a [^>]*>(?:<svg.*?</svg>)?([A-Za-z]+)", html)
        self.assertEqual(names[:5], ["Trails", "Places", "Lists", "About", "Saved"])
        self.assertIn('<a href="/lists/">Lists</a>', html)

    def test_lists_is_current_on_the_index_lists_tables_and_views(self):
        for path in ("/lists/", "/lists/loops/", "/routes/", "/numbers/", "/numbers/highest-points/", "/authors/",
                     "/authors/andrew-skurka/", "/recent/", "/connected/"):
            self.assertEqual(self.current(path), ["/lists/"], path)
        layout.UNDER_LISTS.add("/triple-crown/")
        try:
            self.assertEqual(self.current("/triple-crown/"), ["/lists/"])
        finally:
            layout.UNDER_LISTS.discard("/triple-crown/")

    def test_the_other_items_keep_their_pages(self):
        self.assertEqual(self.current("/"), ["/"])
        self.assertEqual(self.current("/trails/tonto-trail/"), ["/"])
        self.assertEqual(self.current("/regions/us-co/"), ["/regions/"])
        self.assertEqual(self.current("/regions/us-co/loops/"), ["/regions/"])
        self.assertEqual(self.current("/about/"), ["/about/"])
        self.assertEqual(self.current("/sources/"), ["/about/"])
        self.assertEqual(self.current("/glossary/"), ["/about/"])

    def test_the_triple_crown_page_is_listed_under_lists_by_the_page_builder(self):
        self.assertIn("layout.UNDER_LISTS.add(path)", read(WEB, "olt", "pages.py"))


class NoTablesTest(unittest.TestCase):
    """The site sets no tables. A set of trails is the site's trail rows; a set of other things is
    rows in the same language (pagekit.rows_list); a table written in Markdown is set the same way."""

    def test_a_set_of_things_is_rows_with_a_name_a_sentence_and_a_line_of_facts(self):
        t = str(pagekit.table(["File", "What it holds", "Size"],
                              [["a.json", "Every trail with all its fields, written out for the programs that read it", "3 MB"]],
                              caption="c"))
        self.assertNotIn("<table", t)
        self.assertIn('<ol class="entries entries--plain" aria-label="c">', t)
        self.assertLess(t.index('class="entry__name">a.json'), t.index('class="entry__desc">Every trail'))
        self.assertIn('<p class="entry__meta"><span><span class="entry__label">Size</span> 3 MB</span></p>', t)

    def test_a_table_written_in_markdown_or_by_hand_is_set_as_rows(self):
        html = ('<p>x</p><div class="table-wrap"><table><thead><tr><th scope="col">Tier</th><th>Records</th></tr></thead>'
                '<tbody><tr><td>Measured</td><td>12</td></tr><tr><td>Stated</td><td>3</td></tr></tbody></table></div><p>y</p>')
        out = pagekit.untable(html)
        self.assertNotIn("<table", out)
        self.assertNotIn("table-wrap", out)
        self.assertEqual(re.findall(r'class="entry__name">(\w+)<', out), ["Measured", "Stated"])
        self.assertTrue(out.startswith("<p>x</p>") and out.endswith("<p>y</p>"))

    def test_the_triple_crown_is_three_trail_rows_with_their_map_and_the_compared_figures_in_each_row(self):
        from olt import standing
        recs = records.load_records(ROOT)
        c = datafiles.collections(ROOT)[0]
        title, desc, body, members = standing.collection_page(c, recs, SITE)
        body = str(body)
        self.assertNotIn("<table", body)
        self.assertEqual(body.count('<li class="entry"'), len(members))
        self.assertIn('class="browse__map"', body)
        self.assertIn("<dt>High point</dt>", body)
        self.assertIn("<dt>Designated</dt>", body)

    def test_a_ranking_is_the_trail_rows_in_rank_order_led_by_the_rank_and_the_figure(self):
        from olt import standing
        recs = records.load_records(ROOT)
        title, desc, body, have = standing.ranking_page(standing.RANKINGS[0], recs, SITE)
        body = str(body)
        self.assertNotIn("<table", body)
        ranks = [int(n) for n in re.findall(r'data-rank="(\d+)"', body)]
        self.assertEqual(ranks, list(range(1, len(have) + 1)))
        first = body[body.index('data-rank="1"'):]
        self.assertLess(first.index('class="entry__lead"'), first.index('class="entry__length"'))
        self.assertIn('<span class="entry__rank">No. 1</span>', first)
        self.assertIn('<option value="rank" selected>', body)

    def test_the_left_out_entries_are_rows_in_the_trail_row_language(self):
        src = read(WEB, "olt", "leftout.py")
        self.assertNotIn("<table", src)
        self.assertIn("pagekit.plain_entry(", src)


class SketchTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        os.makedirs(os.path.join(self.dir.name, "trails", "x"))
        coords = [[-112.0 + i * 0.001, 36.0 + (i % 7) * 0.0004 + i * 0.0005] for i in range(400)]
        fc = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {"role": "main"}, "geometry": {"type": "MultiLineString", "coordinates": [coords]}}]}
        with open(os.path.join(self.dir.name, "trails", "x", "map.json"), "w") as f:
            json.dump(fc, f)
        sketch.use(self.dir.name)
        self.box = [-112.0, 36.0, -111.6, 36.2]

    def tearDown(self):
        sketch.use("")
        self.dir.cleanup()

    def test_the_drawing_is_light_and_in_the_site_s_track_classes(self):
        fr = sketch.frame(self.box)
        svg = str(sketch.svg(sketch.trail_features("x"), fr))
        self.assertLess(len(svg), 4000)
        self.assertIn('class="map__sketch"', svg)
        self.assertIn('class="fallback__casing"', svg)
        self.assertIn('class="fallback__line"', svg)
        self.assertIn('preserveAspectRatio="xMidYMid meet"', svg)
        self.assertNotRegex(svg, r"\d\.\d{3,}")  # whole numbers, relative steps
        self.assertRegex(svg, r'd="M\d+ \d+l')

    def test_the_frame_is_the_extent_widened_on_every_side(self):
        w, s, e, n = sketch.frame(self.box)
        self.assertLess(w, self.box[0])
        self.assertLess(s, self.box[1])
        self.assertGreater(e, self.box[2])
        self.assertGreater(n, self.box[3])

    def test_the_viewbox_has_the_frames_proportions_so_both_fit_a_container_the_same_way(self):
        import math
        fr = sketch.frame(self.box)
        svg = str(sketch.svg(sketch.trail_features("x"), fr))
        vw, vh = map(float, re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg).groups())
        merc = lambda lat: math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
        want = (math.radians(fr[2] - fr[0])) / (merc(fr[3]) - merc(fr[1]))
        self.assertAlmostEqual(vw / vh, want, places=3)

    def test_a_trail_page_carries_the_frame_and_the_drawing(self):
        rec = load("tonto-trail")
        rec["id"] = "x"
        rec["derived"]["bbox"] = self.box
        rec["derived"]["files"] = {"line": "x.gpx"}
        fig = trail.map_figure(rec)
        self.assertRegex(fig, r'data-frame="-?[\d.]+,-?[\d.]+,-?[\d.]+,-?[\d.]+"')
        self.assertIn('<div class="map__fallback"><svg class="map__sketch"', fig)
        self.assertIn('class="map__status"', fig)  # the no-script text stays

    def test_no_data_no_drawing_and_no_empty_placeholder_text_for_scripts(self):
        sketch.use("")
        rec = load("tonto-trail")
        rec["derived"]["bbox"] = self.box
        self.assertIn('<div class="map__fallback"></div>', trail.map_figure(rec))


class HandoverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = read(WEB, "assets", "app.js")
        cls.css = read(WEB, "assets", "style.css")

    def test_the_live_map_opens_on_the_drawings_ground_with_no_padding(self):
        self.assertIn("var frame = (fig.dataset.frame || '').split(',').map(Number);", self.js)
        self.assertIn("options.bounds = [[frame[0], frame[1]], [frame[2], frame[3]]];", self.js)
        self.assertIn("options.fitBoundsOptions = { padding: 0 };", self.js)

    def test_nothing_is_drawn_over_the_page_s_own_drawing_and_no_placeholder_text_is_written(self):
        self.assertIn("if (hasSketch()) { sketchCorners(); return; }", self.js)
        self.assertNotIn("The map loads when you scroll to it.", self.js)
        self.assertNotIn("Loading the track", self.js)
        self.assertNotIn("Loading the base map", self.js)
        self.assertIn("html.js .map__status:not([data-say]) { display: none; }", self.css)

    def test_the_drawing_gives_way_after_the_first_frame_with_the_tracks_and_a_fade(self):
        self.assertIn("map.once('render', reveal);", self.js)
        self.assertIn("map.isSourceLoaded('olt')", self.js)
        self.assertIn(".map[data-state=\"ready\"] .map__fallback { visibility: hidden; transition: visibility 0s 0.4s; }", self.css)
        self.assertIn(".map__canvas { opacity: 0; transition: opacity 0.4s ease; }", self.css)

    def test_every_frame_starts_when_the_page_is_idle_whatever_its_place(self):
        self.assertIn("requestIdleCallback(begin, { timeout: 500 })", self.js)
        self.assertNotIn("IntersectionObserver", self.js)
        self.assertNotIn("MAP_AHEAD", self.js)

    def test_the_first_view_of_an_overview_needs_no_move(self):
        self.assertIn("if (entry.frame && same) { target = entry.frame; padding = 0; }", self.js)


class PageTopsTest(unittest.TestCase):
    def test_a_browsing_page_is_the_map_and_the_rows_then_the_text_about_the_set(self):
        grid = str(home.browse_view("LIST", '<figure class="mapfig">MAP</figure>', about="<p>TEXT</p>", about_title="About X"))
        self.assertLess(grid.index("MAP"), grid.index("LIST"))     # the map is a band above the rows when narrow
        self.assertLess(grid.index("LIST"), grid.index("TEXT"))    # the text about the set follows the rows
        self.assertIn('<h2 id="about-these">About X</h2>', grid)
        css = read(WEB, "assets", "style.css")
        self.assertIn('grid-template-areas: "list map";', css)
        self.assertRegex(css, r"\.browse__map \{ grid-area: map; position: sticky;")

    def test_a_set_too_small_to_map_is_the_rows_with_the_note_under_them(self):
        grid = str(home.browse_view("LIST", '<p class="note">NOTE</p>'))
        self.assertIn('class="browse browse--no-map"', grid)
        self.assertLess(grid.index("LIST"), grid.index("NOTE"))

    def test_a_place_page_has_its_rows_before_its_summary(self):
        from olt import regions
        recs = records.load_records(ROOT)
        _, _, body, _ = regions.region_page("us-co", recs, SITE)
        body = str(body)
        self.assertLess(body.index('class="browse__list"'), body.index('class="browse-about"'))
        self.assertNotIn("percent", body)

    def test_every_page_head_is_compact(self):
        css = read(WEB, "assets", "style.css")
        self.assertRegex(css, r"\.page-head \.titleblock h1 \{ font-size: var\(--step-3\)")


if __name__ == "__main__":
    unittest.main()
