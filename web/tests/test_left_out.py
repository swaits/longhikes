"""Tests for the Considered and left out page (web/olt/leftout.py).

Run from the repository root:
    python3 -m unittest discover -s web/tests
"""
import os
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)

from olt import leftout, seo, site  # noqa: E402

ENTRIES = [
    {
        "id": "waiting-trail",
        "name": "Waiting Trail",
        "country": "US",
        "regions": ["KY"],
        "length_mi": 120,
        "length_km": 193,
        "length_note": "120 miles planned",
        "reason": "waiting",
        "note": "Only part of it is built.",
        "source_url": "https://example.org/waiting",
        "decided": "2026-11-16",
        "was_listed": False,
        "waiting_for": "Enough of it is built to walk through.",
    },
    {
        "id": "example-trail",
        "name": "Example & Trail",
        "country": "US",
        "regions": ["PA", "MD"],
        "length_mi": 42.0,
        "length_km": 68,
        "reason": "below-floor",
        "note": "The holder gives it as 42 miles.",
        "source_url": "https://example.org/example?a=1&b=2",
        "decided": "2026-11-14",
        "was_listed": True,
    },
]


class PageTest(unittest.TestCase):
    def setUp(self):
        self.site = site.Site(name="Long Hikes", tagline="Tagline",
                              base_url="https://example.org",
                              repo_url="https://github.com/swaits/longhikes")
        self.title, self.description, self.body = leftout.left_out_page(
            ENTRIES, self.site, ROOT)
        self.text = str(self.body)

    def test_title(self):
        self.assertEqual(self.title, "Considered and left out")

    def test_opening_is_generated_from_the_entries(self):
        self.assertIn("lists 2 trails and routes", self.text)
        self.assertIn("1 of them was listed here once", self.text)
        self.assertIn("open an issue", self.text)

    def test_grouped_by_reason_in_order(self):
        self.assertLess(self.text.index("Below the 50 mile floor"),
                        self.text.index("Waiting"))

    def test_entry_facts_and_escaping(self):
        self.assertIn("Example &amp; Trail", self.text)
        self.assertIn("Pennsylvania", self.text)
        self.assertIn("Maryland", self.text)
        self.assertIn("42 mi", self.text)
        self.assertIn("68 km", self.text)
        self.assertIn("The holder gives it as 42 miles.", self.text)
        self.assertIn('datetime="2026-11-14"', self.text)
        self.assertIn('href="https://example.org/example?a=1&amp;b=2"', self.text)

    def test_once_listed_mark(self):
        self.assertIn("Once listed here", self.text)
        self.assertEqual(self.text.count("Once listed here"), 1)

    def test_waiting_shows_what_would_change_it(self):
        self.assertIn("Enough of it is built to walk through.", self.text)
        self.assertIn("120 miles planned", self.text)

    def test_no_length_shows_nothing_made_up(self):
        entries = [dict(ENTRIES[1])]
        del entries[0]["length_mi"], entries[0]["length_km"]
        _, _, body = leftout.left_out_page(entries, self.site, ROOT)
        self.assertNotIn("len__mi", str(body))

    def test_sitemap_includes_the_page(self):
        self.assertIn("/left-out/", seo.all_paths([], []))

    def test_the_real_file_loads_sorted(self):
        entries = leftout.load_entries(ROOT)
        self.assertGreaterEqual(len(entries), 30)
        names = [e["name"].lower() for e in entries]
        self.assertEqual(names, sorted(names))
        reasons = {e["reason"] for e in entries}
        self.assertTrue(reasons <= set(leftout.REASON_ORDER))


if __name__ == "__main__":
    unittest.main()
