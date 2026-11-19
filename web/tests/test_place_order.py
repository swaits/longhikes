"""Place and region pages open with the trails wholly in the place first (regions.wholly_in)."""
import copy
import os
import re
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)

from olt import facets, home, records, regions, site  # noqa: E402


def row_ids(html):
    return re.findall(r'<li class="entry"[^>]*data-id="([^"]+)"', str(html))


class PlaceOrderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = copy.deepcopy(records.load_records(ROOT))
        cls.site = site.load()
        cls.by_slug, _ = regions.collect_regions(cls.records)

    def test_utah_leads_with_trails_wholly_in_utah(self):
        ids = row_ids(regions.region_page("us-ut", self.records, self.site)[2])
        by_id = {r["id"]: r for r in self.records}
        wholly = [i for i in ids if set(facets.place_keys(by_id[i])) == {"US-UT"}]
        self.assertTrue(wholly and len(wholly) < len(ids))
        self.assertEqual(ids[:len(wholly)], wholly)
        self.assertEqual(wholly, sorted(wholly, key=lambda i: facets.sort_name(by_id[i])))
        rest = ids[len(wholly):]
        self.assertIn("american-discovery-trail", rest)
        self.assertEqual(rest, sorted(rest, key=lambda i: facets.sort_name(by_id[i])))

    def test_rows_carry_the_tier_and_the_select_opens_on_it(self):
        html = str(regions.region_page("us-ut", self.records, self.site)[2])
        self.assertIn('data-default-sort="here"', html)
        self.assertIn('<option value="here" selected>', html)
        # plain A to Z is still an option
        self.assertIn('<option value="name">Name, A to Z</option>', html)
        tiers = re.findall(r'data-id="([^"]+)"[^>]* data-here="(\d)"', html)
        self.assertEqual({t for _, t in tiers}, {"0", "1"})
        self.assertEqual([t for _, t in tiers], sorted(t for _, t in tiers))

    def test_region_pages_use_their_own_places(self):
        g = "mountain-west"
        html = regions.group_page(g, self.records, self.site)[2]
        ids = row_ids(html)
        keys = set(next(k for x, _, k in facets.PLACE_GROUPS if x == g))
        by_id = {r["id"]: r for r in self.records}
        tier = [0 if set(facets.place_keys(by_id[i])) <= keys else 1 for i in ids]
        self.assertEqual(tier, sorted(tier))
        self.assertIn(1, tier)

    def test_a_page_whose_trails_are_all_of_one_kind_keeps_plain_order(self):
        recs = [r for r in self.records if facets.place_keys(r) == ["US-UT"]]
        self.assertIsNone(regions.wholly_in(recs, ["US-UT"]))
        self.assertNotIn("data-here", str(home.results(recs)))

    def test_the_home_page_and_other_lists_are_unchanged(self):
        html = str(home.results(self.records, every=True))
        self.assertNotIn("data-here", html)
        self.assertIn('data-default-sort="name"', html)

    def test_across_canada_is_not_wholly_in_one_province(self):
        test = regions.wholly_in(self.records, ["CA-ON"])
        self.assertIsNotNone(test)
        for r in self.records:
            if "CA-*" in facets.place_keys(r):
                self.assertFalse(test(r))

    def test_the_script_orders_here_before_name(self):
        js = open(os.path.join(WEB, "assets", "app.js"), encoding="utf-8").read()
        self.assertIn("SORT_KEYS.here = 1", js)
        self.assertIn("if (key === 'here') return cmpNum(Number(a.dataset.here || 0)", js)


if __name__ == "__main__":
    unittest.main()
