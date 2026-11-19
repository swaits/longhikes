"""A place page's map opens on the place, not on the extent of its trails (olt/bounds.py)."""
import copy
import os
import re
import sys
import unittest
from unittest import mock

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)

from olt import bounds, facets, home, placefacets, records, regions, site, sketch  # noqa: E402


def attr(html, name):
    m = re.search(rf'\bdata-{name}="([^"]*)"', html)
    return [float(v) for v in m.group(1).split(",")] if m else None


def figure(html):
    return re.search(r'<figure class="mapfig[^>]*>', str(html)).group(0)


def rounded(box):
    return [round(v, 4) for v in box]


class PlaceViewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The tracks' extents are worked out by the build; here each trail is given one: a small box
        # at the middle of its first place, and the American Discovery Trail's, from coast to coast.
        cls.records = copy.deepcopy(records.load_records(ROOT))
        for r in cls.records:
            key = facets.place_keys(r)[0] if facets.place_keys(r) else None
            box = bounds.place_box(key) if key else None
            cx, cy = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2) if box else (-100.0, 40.0)
            r["derived"]["bbox"] = [-123.0, 33.0, -75.0, 40.0] if r["id"] == "american-discovery-trail" \
                else [cx - 0.3, cy - 0.2, cx + 0.3, cy + 0.2]
            r["derived"]["files"] = dict(r["derived"].get("files", {}), line="x.gpx")
        cls.site = site.load()
        cls.by_slug, _ = regions.collect_regions(cls.records)

    def region_figure(self, slug):
        return figure(regions.region_page(slug, self.records, self.site)[2])

    def test_every_place_the_site_has_a_page_for_has_a_box(self):
        for _, _, keys in facets.PLACE_GROUPS:
            for key in keys:
                box = bounds.place_box(key)
                self.assertIsNotNone(box, key)
                w, s, e, n = box
                self.assertTrue(-180 <= w < e <= 180 and -90 <= s < n <= 90, key)  # none wraps the antimeridian

    def test_utah_opens_on_utah_and_not_on_its_trails(self):
        fig = self.region_figure("us-ut")
        self.assertEqual(attr(fig, "bbox"), [-114.04, 37.0, -109.05, 42.0])
        self.assertEqual(attr(fig, "frame"), [float(f"{v:g}") for v in sketch.frame(bounds.place_box("US-UT"))])
        trails = home.overview_box(self.by_slug["us-ut"]["records"])
        self.assertLess(trails[0], -114.04 - 5)   # the American Discovery Trail runs far past the state
        self.assertIn("american-discovery-trail", re.search(r'data-ids="([^"]*)"', fig).group(1))

    def test_a_group_opens_on_the_union_of_its_members_with_trails(self):
        g = "mountain-west"
        html = regions.group_page(g, self.records, self.site)[2]
        keys = next(k for x, _, k in facets.PLACE_GROUPS if x == g)
        boxes = [bounds.place_box(k) for k in keys if k.lower() in self.by_slug]
        want = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
        self.assertEqual(attr(figure(html), "bbox"), rounded(want))

    def test_a_member_with_no_trails_is_left_out_of_the_union(self):
        by_slug = {"us-id": {}, "us-mt": {}}
        self.assertEqual(regions.group_box("mountain-west", by_slug), [-117.22, 42.0, -104.04, 48.99])

    def test_a_place_with_no_bounds_keeps_the_extent_of_its_trails(self):
        with mock.patch.object(bounds, "_boxes", {}):
            fig = self.region_figure("us-ut")
            self.assertIsNone(bounds.union(["US-UT", "US-CO"]))
        want = home.overview_box(self.by_slug["us-ut"]["records"])
        self.assertEqual(attr(fig, "bbox"), rounded(want))

    def test_one_missing_member_box_leaves_the_group_on_its_trails(self):
        boxes = {k: v for k, v in bounds.boxes().items() if k != "US-WY"}
        with mock.patch.object(bounds, "_boxes", boxes):
            html = regions.group_page("mountain-west", self.records, self.site)[2]
        recs = regions.group_records(self.records, "mountain-west")
        self.assertEqual(attr(figure(html), "bbox"), rounded(home.overview_box(recs)))

    def test_a_place_and_kind_page_opens_on_its_place(self):
        pages = [p for p in placefacets.plan(self.records) if p["slug"] == "us-ut"]
        if not pages:
            self.skipTest("no Utah page of one kind of trail")
        fig = figure(placefacets.page(pages[0], self.records, self.site, pages)[2])
        self.assertEqual(attr(fig, "bbox"), [-114.04, 37.0, -109.05, 42.0])

    def test_the_home_and_list_maps_open_on_their_trails(self):
        sample = self.records[:12]
        box = home.overview_box(sample)
        fig = figure(home.overview_map(sample, "Map"))
        self.assertEqual(attr(fig, "bbox"), rounded(box))
        self.assertEqual(attr(fig, "frame"), [float(f"{v:g}") for v in sketch.frame(box)])
        whole = figure(home.overview_map(self.records, "Map", scope="all"))
        self.assertEqual(attr(whole, "bbox"), rounded(home.overview_box(self.records)))

    def test_a_place_page_declares_its_place_and_no_other_page_does(self):
        self.assertIn(" data-place", self.region_figure("us-ut"))
        self.assertIn(" data-place", figure(regions.group_page("mountain-west", self.records, self.site)[2]))
        self.assertNotIn("data-place", figure(home.overview_map(self.records[:12], "Map")))
        self.assertNotIn("data-place", figure(home.overview_map(self.records, "Map", scope="all")))
        with mock.patch.object(bounds, "_boxes", {}):
            self.assertNotIn("data-place", self.region_figure("us-ut"))

    def test_the_script_keeps_a_place_page_on_its_place_when_the_list_holds_trails_it_cannot_draw(self):
        # The list of a place page holds every trail there, drawn or not; the filters hand fitToVisible
        # that list. Comparing it with the drawn trails (data-ids) alone sent Utah and Mountain West to
        # the extent of the American Discovery Trail. Only trails with geometry count.
        with open(os.path.join(WEB, "assets", "app.js"), encoding="utf-8") as f:
            js = f.read()
        fit = re.search(r"function fitToVisible\(.*?\n  \}\n", js, re.S).group(0)
        self.assertIn("entry.place", fit)
        self.assertIn("entry.boundsById[id]", fit)
        self.assertIn("if (entry.frame && same) { target = entry.frame; padding = 0; }", fit)
        self.assertIn("entry.place = fig.hasAttribute('data-place');", js)


if __name__ == "__main__":
    unittest.main()
