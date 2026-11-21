"""The wording of the ready-made lists (olt/browse.py): titles in the words people search with.
Addresses and rules do not change; only title, blurb, page_title, noun and lede."""
import os
import re
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from olt import browse, common, records  # noqa: E402
from test_facets import BANNED  # noqa: E402

KEYS = ['national-scenic-trails', 'national-recreation-trails', 'routes', 'high-routes', 'longest', '500-to-1000-miles', '200-to-500-miles', '100-to-200-miles', 'under-100-miles', 'under-200-miles', 'weekend', 'a-week-or-less', 'one-to-two-weeks', 'two-to-four-weeks', 'a-month-or-more', 'loops', 'off-trail', 'mostly-cross-country', 'unfinished', 'parks-canada', 'forest-service', 'state-and-provincial-parks', 'clubs-and-associations', 'with-gpx', 'canada', 'united-states', 'terrain-alpine', 'terrain-forest', 'terrain-desert', 'terrain-coast', 'terrain-prairie', 'terrain-canyon', 'terrain-tundra', 'terrain-lakes', 'terrain-farmland', 'hike-in-january', 'hike-in-february', 'hike-in-march', 'hike-in-april', 'hike-in-may', 'hike-in-june', 'hike-in-july', 'hike-in-august', 'hike-in-september', 'hike-in-october', 'hike-in-november', 'hike-in-december']


class ListWordingTest(unittest.TestCase):
    def test_list_urls_and_keys_are_unchanged(self):
        self.assertEqual([lst.key for lst in browse.LISTS], KEYS)
        self.assertEqual(browse.path(browse.by_key("loops")), "/lists/loops/")
        self.assertEqual(browse.path(browse.by_key("routes")), "/routes/")

    def test_the_reworded_lists_have_the_new_page_titles(self):
        want = {
            "longest": "Longest Hiking Trails in the US and Canada: 7 Trails",
            "under-100-miles": "Short Thru-Hikes and Loops Under 100 Miles: 7 Trails",
            "under-200-miles": "Thru-Hikes and Loops Under 200 Miles: 7 Trails",
            "a-week-or-less": "Backpacking Trips of a Week or Less: 7 Long Trails",
            "weekend": "Long-Weekend Backpacking Trips: 7 Long Trails",
            "off-trail": "Long Trails with Cross-Country Stretches: 7 Trails",
            "loops": "Backpacking Loops: 7 Long Trail Loops",
        }
        for key, title in want.items():
            self.assertEqual(browse.by_key(key).search_title(7), title)

    def test_a_loop_is_never_called_a_thru_hike_alone(self):
        # the length bands hold loops too, so their titles say so
        for key in ("under-100-miles", "under-200-miles"):
            self.assertIn("Loops", browse.by_key(key).page_title)
        self.assertNotIn("thru", browse.by_key("loops").page_title.lower())

    def test_the_week_band_has_a_noun_and_loops_say_backpacking(self):
        self.assertEqual(browse.by_key("a-week-or-less").noun, "Backpacking Trips of a Week or Less")
        self.assertEqual(browse.by_key("loops").noun, "Backpacking Loops")

    def test_no_banned_word_and_no_best_in_any_list_wording(self):
        for lst in browse.LISTS:
            for text in (lst.title, lst.blurb, lst.search_title(9), lst.noun, lst.short):
                for pattern in BANNED:
                    self.assertIsNone(re.search(pattern, text, re.I), (lst.key, text))
                self.assertIsNone(re.search(r"\bbest\b", text, re.I), (lst.key, text))

    def test_every_search_title_is_unique_and_fits(self):
        titles = [lst.search_title(99) for lst in browse.LISTS]
        self.assertEqual(len(titles), len(set(titles)))
        for t in titles:
            self.assertLessEqual(len(t), common.TITLE_LIMIT, t)

    def test_the_longest_list_names_the_longest_trail_and_its_length_first(self):
        recs = records.load_records(records.ROOT)
        lst = browse.by_key("longest")
        top = max(browse.members(lst, recs), key=lambda r: (r["length_km"], r["id"]))
        first = lst.lede(browse.members(lst, recs))
        self.assertTrue(first.startswith("The longest hiking trail"), first)
        self.assertIn(common.plain_name(top), first)
        self.assertIn(f"{top['derived']['length_mi']:,.0f} miles", first)


if __name__ == "__main__":
    unittest.main()
