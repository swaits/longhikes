"""A state or province with no listed trail has a page that says so (regions.empty_place_page)."""
import os
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)

from olt import bounds, facets, home, leftout, records, regions, seo, site  # noqa: E402


class EmptyPlaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = records.load_records(ROOT)
        cls.site = site.load()
        cls.entries = leftout.load_entries(ROOT)
        cls.by_slug, _ = regions.collect_regions(cls.records)

    def test_every_place_with_a_box_and_no_trail_is_listed(self):
        keys = regions.empty_places(self.records)
        self.assertTrue(keys)
        for k in keys:
            self.assertIn(k, bounds.boxes())
            self.assertNotIn(k.lower(), self.by_slug)
        for k in bounds.boxes():
            self.assertEqual(k in keys, k.lower() not in self.by_slug)
        self.assertEqual(keys, sorted(keys, key=facets.place_name))

    def test_a_place_with_left_out_entries_lists_them_with_their_reasons(self):
        fake = [{"id": "x-trail", "name": "X Trail", "country": "CA", "regions": ["MB"], "reason": "rail-trail-or-towpath",
                 "note": "A rail trail.", "decided": "2026-11-01"}]
        title, desc, body = regions.empty_place_page("CA-MB", self.records, self.site, fake)
        body = str(body)
        self.assertEqual(title, "No Long Trails Listed in Manitoba")
        self.assertIn("No trail of 50 miles or more is listed in Manitoba.", body)
        self.assertIn("1 trail considered here was left out", body)
        self.assertIn("X Trail", body)
        self.assertIn("Rail trails and canal towpaths", body)
        self.assertIn('href="/left-out/"', body)
        self.assertIn('href="/about/#how-trails-are-chosen"', body)
        self.assertNotIn('data-map', body)
        self.assertIn("Manitoba, Canada", desc)
        self.assertIn("1 trail considered there was left out", desc)

    def test_a_place_with_none_says_so(self):
        _, desc, body = regions.empty_place_page("US-HI", self.records, self.site, [])
        self.assertIn("Nothing in Hawaii is on the left-out list either.", str(body))
        self.assertIn("none considered there was left out", desc)

    def test_the_real_entries_reach_their_place(self):
        for key in regions.empty_places(self.records):
            here = leftout.entries_for_place(self.entries, key)
            _, _, body = regions.empty_place_page(key, self.records, self.site, self.entries)
            for e in here:
                self.assertIn(e["name"], str(body))

    def test_the_places_index_links_them_in_one_line(self):
        _, _, body = regions.regions_index_page(self.records, self.site)
        body = str(body)
        self.assertIn("Places with no listed trail: ", body)
        line = body[body.index("Places with no listed trail:"):]
        line = line[:line.index("</p>")]
        for key in regions.empty_places(self.records):
            self.assertIn(f'<a href="{facets.place_path(key)}">{facets.place_name(key)}</a>', line)

    def test_they_are_in_no_filter_and_no_count(self):
        recs = self.records
        counts = home.counts(recs)
        for key in regions.empty_places(recs):
            self.assertFalse(counts.get("where:" + key))
            self.assertNotIn(f'value="{key}"', str(home.finder_form(recs, counts)))
        index = str(regions.regions_index_page(recs, self.site)[2])
        self.assertIn(f"The {len(recs)} trails by state and province", index)

    def test_the_sitemap_names_them(self):
        paths = [facets.place_path(k) for k in regions.empty_places(self.records)]
        self.assertIn("/regions/us-hi/", paths)
        for p in paths:
            self.assertIn(p, seo.all_paths(self.records, paths))


if __name__ == "__main__":
    unittest.main()
