"""A trail with an abbreviation shows it, shared or not; a trail without one shows the site's mark.

Fixtures only; no real trail's abbreviation is pinned.
"""
import copy
import os
import re
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from olt import common, home, site, trail  # noqa: E402
from test_pages import sample_record  # noqa: E402


def rec(tid, abbr="PCT", *, tier="regional", kind="designated", km=100, name=None):
    r = copy.deepcopy(sample_record(name or tid))
    r.update(id=tid, tier=tier, length_km=km)
    r["derived"]["kind"] = kind
    r["derived"]["length_mi"] = round(km / 1.609344)
    if abbr is None:
        del r["short_name"]
    else:
        r["short_name"] = abbr
        r["short_name_url"] = f"https://www.example.org/{tid}"
    return r


class PageTest(unittest.TestCase):
    def setUp(self):
        self.a = rec("a", name="Big Trail")
        self.b = rec("b", name="Small Trail")  # shares the abbreviation: both show it
        self.none = rec("none", None, name="Plain Trail")
        self.site = site.Site("N", "T")

    def page(self, r):
        return trail.render(r, self.site)[2]

    def test_trail_page_shows_it_for_every_trail_that_has_it(self):
        for r in (self.a, self.b):
            self.assertRegex(self.page(r), r'<h1>.*<span class="titleblock__abbr">PCT</span>')
        self.assertNotIn("titleblock__abbr", self.page(self.none))

    def test_list_row_shows_it_for_every_trail_that_has_it(self):
        for r in (self.a, self.b):
            self.assertIn('<span class="entry__abbr vh">PCT</span>', home.entry(r))
        self.assertNotIn("entry__abbr", home.entry(self.none))

    def test_row_search_text_carries_the_abbreviation(self):
        search = lambda r: re.search(r'data-search="([^"]*)"', home.entry(r)).group(1)
        self.assertIn("pct", search(self.a))
        self.assertIn("pct", search(self.b))
        self.assertNotIn("pct", search(self.none))

    def test_plate_letters_or_the_mark(self):
        self.assertIn("<span>PCT</span>", common.plate(self.a))
        plate = common.plate(self.none)
        self.assertIn('class="plate plate--none" aria-hidden="true"', plate)
        self.assertIn('class="plate__mark"', plate)
        self.assertNotIn("<text", plate)

    def test_about_data_lists_it_with_the_page_it_was_seen_on(self):
        body = self.page(self.a)
        self.assertIn("<dt>Abbreviation</dt>", body)
        self.assertIn('Seen in use at <a href="https://www.example.org/a">example.org</a>', body)
        self.assertNotIn("shown with it", body)

    def test_about_data_has_no_abbreviation_row_without_one(self):
        self.assertNotIn("<dt>Abbreviation</dt>", self.page(self.none))


if __name__ == "__main__":
    unittest.main()
