"""Links to the park, range and wilderness pages: the Places hub sections, the block
on a state page, the links on a trail page, and place names in search
(regions.regions_index_page, regions.place_links_for, trail.place_links,
searchtext.place_names). Fixtures only."""
import hashlib
import json
import os
import re
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from olt import home, placefacets, places, regions, searchtext, site, trail  # noqa: E402
from test_place_page import REGISTRY, rec, wind_records, yosemite_records  # noqa: E402
from test_state_pages_unchanged import GOLDEN, fixtures, normalise  # noqa: E402

S = site.Site("Long Hikes", "T", repo_url="https://github.com/o/r")


def registry(entries=REGISTRY):
    return {(e["kind"], e["slug"]): e for e in entries}


def infos(records):
    return places.collect(records, registry())


class HomeWayInTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = wind_records(4) + yosemite_records(3)

    def test_below_the_rows_a_line_links_each_kind_that_has_pages(self):
        body = str(home.render(self.records, S, ROOT, place_kinds=["park", "range", "wilderness"]))
        line = re.search(r'<p class="finder__foot finder__places">(.*?)</p>', body, re.S).group(1)
        self.assertEqual(
            re.sub(r"<[^>]+>", "", line),
            "Browse by park, by mountain range or by wilderness area.")
        for frag in ('href="/regions/#parks">park', 'href="/regions/#ranges">mountain range',
                     'href="/regions/#wilderness">wilderness area'):
            self.assertIn(frag, line)
        # after the rows and the map, in the notes at the foot, never in the intro
        self.assertGreater(body.index("finder__places"), body.rindex('<li class="entry"'))
        self.assertGreater(body.index("finder__places"), body.index('id="browse-list"'))
        self.assertLess(body.index("</section>"), body.index("finder__places"))

    def test_only_the_kinds_with_pages_and_none_when_there_are_none(self):
        line = re.search(r'finder__places">(.*?)</p>', str(home.render(self.records, S, ROOT, place_kinds=["range"])), re.S).group(1)
        self.assertEqual(re.sub(r"<[^>]+>", "", line), "Browse by mountain range.")
        self.assertNotIn("finder__places", str(home.render(self.records, S, ROOT)))


class HubTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = wind_records(4) + yosemite_records(3)
        cls.infos = infos(cls.records)

    def test_the_hub_lists_each_kind_with_exact_counts_and_hides_empty_kinds(self):
        _, _, body = regions.regions_index_page(self.records, S, infos=self.infos)
        body = str(body)
        self.assertIn(">Parks</h2>", body)
        self.assertIn(">Mountain ranges</h2>", body)
        self.assertNotIn(">Wilderness areas</h2>", body)
        self.assertIn('<a href="/ranges/wind-river-range/">Wind River Range</a>'
                      '<span class="places__n">4 trails</span>', body)
        self.assertIn('<a href="/parks/yosemite/">Yosemite National Park</a>'
                      '<span class="places__n">3 trails</span>', body)
        self.assertIn("Parks, mountain ranges and wilderness areas with three or more "
                      "trails have pages too.", re.sub(r"\s+", " ", body))

    def test_a_jump_row_tops_the_hub_with_exact_counts_of_pages(self):
        _, _, body = regions.regions_index_page(self.records, S, infos=self.infos)
        body = str(body)
        by_slug, _ = regions.collect_regions(self.records)
        row = body[body.index('<nav class="places-jump"'):]
        row = row[:row.index("</nav>")]
        self.assertLess(body.index('<nav class="places-jump"'), body.index("<h1>"))
        self.assertIn(f'<a href="#states-and-provinces">States and provinces <span class="places-jump__n">{len(by_slug)}</span></a>', row)
        self.assertIn('<a href="#parks">Parks <span class="places-jump__n">1</span></a>', row)
        self.assertIn('<a href="#ranges">Mountain ranges <span class="places-jump__n">1</span></a>', row)
        self.assertNotIn("#wilderness", row)  # no wilderness page here: no link
        self.assertLess(row.index("#states-and-provinces"), row.index("#parks"))
        self.assertIn('id="states-and-provinces"', body)
        # the kinds are in the one row, not also in the strip of regional groups
        strip = body[body.index('<nav class="lists-row"'):]
        self.assertNotIn("#parks", strip[:strip.index("</nav>")])
        _, _, plain = regions.regions_index_page(self.records, S)
        self.assertNotIn('class="places-jump"', str(plain))

    def test_the_hub_still_lists_every_state_group_as_before(self):
        _, _, plain = regions.regions_index_page(self.records, S)
        _, _, with_places = regions.regions_index_page(self.records, S, infos=self.infos)
        stripped = re.sub(r'<section class="places__group" aria-labelledby="(?:parks|ranges|wilderness)">.*?</section>',
                          "", str(with_places), flags=re.S)
        stripped = stripped.replace(" or a kind of place", "")
        stripped = re.sub(r'<nav class="places-jump".*?</nav>\s*', "", stripped, flags=re.S)
        stripped = stripped.replace(
            " Parks, mountain ranges and wilderness areas with three or more trails have pages too.", "")
        self.assertEqual(stripped, str(plain))


class StateLinkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = fixtures()
        # three Colorado fixtures in one range whose `where` is Colorado
        cls.reg = {("range", "front-range"): {
            "kind": "range", "slug": "front-range", "name": "Front Range", "where": ["CO"],
            "source": "gmba-v2", "source_id": "1", "source_version": "2026-11-20",
            "box": [-106.0, 38.0, -105.0, 41.0]}}
        co = [r for r in cls.records if "CO" in r.get("regions", [])][:3]
        for r in co:
            r["place"] = [{"kind": "range", "slug": "front-range", "basis": "track", "km": 42.0}]
        cls.infos = places.collect(cls.records, cls.reg)

    def test_a_state_page_links_to_the_places_in_the_state_with_exact_counts_and_nothing_else_changes(self):
        block = regions.place_links_for("US-CO", self.infos)
        self.assertIn('aria-label="Parks, ranges and wilderness in Colorado"', str(block))
        self.assertIn('<a href="/ranges/front-range/">Front Range</a> (3)', str(block))
        plan = placefacets.plan(self.records)
        facet_pages = [(placefacets.label(p["lst"]), p["path"], len(p["recs"]))
                       for p in placefacets.pages_by_place(plan).get("us-co", [])]
        built = regions.region_page("us-co", self.records, S, facet_pages, place_links=block)
        page = "\n".join(str(p) for p in built if isinstance(p, str) or hasattr(p, "__html__"))
        self.assertIn("/ranges/front-range/", page)
        with open(GOLDEN, encoding="utf-8") as f:
            want = json.load(f)["/regions/us-co/"]
        self.assertEqual(hashlib.sha256(normalise(page).encode()).hexdigest(), want)

    def test_a_state_with_no_place_has_no_block(self):
        self.assertEqual(str(regions.place_links_for("US-UT", self.infos)), "")
        _, _, body, _ = regions.region_page(
            "us-ut", self.records, S, place_links=regions.place_links_for("US-UT", self.infos))
        self.assertNotIn("Parks, ranges and wilderness in Utah", str(body))


class TrailLinkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        small = [rec(301, "Small One", [("range", "wind-river-range"), ("park", "small")]),
                 rec(302, "Small Two", [("park", "small")])]
        cls.records = wind_records(3) + small
        cls.infos = infos(cls.records)
        cls.rec = small[0]

    def test_a_trail_page_links_to_each_of_its_places_that_has_a_page_and_not_to_a_place_below_three(self):
        links = str(trail.place_links(self.rec, self.infos))
        self.assertIn('<a href="/ranges/wind-river-range/">Wind River Range</a>', links)
        self.assertNotIn("small", links)
        body = str(trail.render(self.rec, S, self.records, place_infos=self.infos)[2])
        glance = body[body.index('class="glance'):body.index("All the facts")]
        self.assertIn('<a href="/ranges/wind-river-range/">Wind River Range</a>', glance)
        self.assertNotIn("/parks/small/", body)
        self.assertIn("More in the Wind River Range", body)  # the ways onward

    def test_the_place_links_are_also_on_the_page_for_a_phone_outside_the_glance(self):
        body = str(trail.render(self.rec, S, self.records, place_infos=self.infos)[2])
        foot = body[body.index('class="container trail-more"'):]
        self.assertIn('<nav class="region-nav trail-places"', foot)
        self.assertIn('<a href="/ranges/wind-river-range/">Wind River Range</a>',
                      foot[:foot.index("</nav>")])
        self.assertLess(foot.index("trail-places"), foot.index('class="onward"'))
        css = open(os.path.join(WEB, "assets", "style.css"), encoding="utf-8").read()
        narrow = css[css.index("@media (max-width: 63.99rem)", css.index(".trail-places")):]
        self.assertIn("html.js .trail-places { display: block; }", narrow[:200])
        plain = str(trail.render(self.rec, S, self.records)[2])
        self.assertNotIn("trail-places", plain)

    def test_a_trail_with_no_place_page_is_unchanged(self):
        plain = str(trail.render(self.rec, S, self.records)[2])
        self.assertNotIn("/ranges/wind-river-range/", plain)


class LosingATrailTest(unittest.TestCase):
    def test_losing_a_trail_removes_the_page_and_every_link(self):
        three = wind_records(3)
        got = infos(three)
        self.assertIn(("range", "wind-river-range"), got)
        two = three[:2]
        gone = infos(two)
        self.assertEqual(gone, {})
        _, _, hub = regions.regions_index_page(two, S, infos=gone)
        self.assertNotIn("/ranges/wind-river-range/", str(hub))
        self.assertEqual(str(regions.place_links_for("US-WY", gone)), "")
        self.assertEqual(str(trail.place_links(two[0], gone)), "")


class SearchTextTest(unittest.TestCase):
    def tearDown(self):
        searchtext.use_place_names({})

    def test_search_text_holds_the_place_names(self):
        # names with none of the place's words: a word already in the name tier
        # is not repeated in the places tier (searchtext.tiers)
        records = [rec(401, "Alpha Trail", [("range", "wind-river-range")]),
                   rec(402, "Bravo Trail", [("range", "wind-river-range")]),
                   rec(403, "Charlie Trail", [("range", "wind-river-range")])]
        got = infos(records)
        attr = searchtext.attribute(records[0], got)
        self.assertIn("wind river range", attr)
        # through a row, once the build has named each trail's places
        searchtext.use_place_names({records[0]["id"]: ["Wind River Range"]})
        row = home.entry(records[0])
        self.assertIn("wind river range", row)
        names = searchtext.place_names(records[0], got)
        self.assertIn("Wind River Range", names)

    def test_search_text_without_places_is_as_before(self):
        r = rec(9, "Plain Trail", [])
        self.assertNotIn("wind river", searchtext.attribute(r))


class SourcesTest(unittest.TestCase):
    def test_sources_names_the_four_outline_publishers(self):
        with open(os.path.join(ROOT, "SOURCES.md"), encoding="utf-8") as f:
            text = f.read()
        for want in ("National Park Service", "Wilderness Connect", "CPCAD",
                     "GMBA Mountain Inventory", "Open Government Licence", "CC BY 4.0",
                     "public domain"):
            self.assertTrue(want in text, want)


if __name__ == "__main__":
    unittest.main()
