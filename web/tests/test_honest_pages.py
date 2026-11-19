"""Pages say only what is so: a place's figures are the place's, and a no-track notice says one thing.

    python3 -m unittest discover -s web/tests
"""
import os
import re
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)

from olt import common, facets, hike, records, regions, summary, trail, words  # noqa: E402
from olt.markup import Markup  # noqa: E402


def text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(html))).strip()


class PlaceFiguresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = records.load_records(ROOT)
        cls.by_slug, _ = regions.collect_regions(cls.records)

    def facts(self, slug):
        info = self.by_slug[slug]
        return text(summary.facts(info["records"], self.records, place=(info["name"], [info["key"]])))

    def test_iowa_does_not_get_the_high_point_of_the_discovery_trail(self):
        said = self.facts("us-ia")
        self.assertNotIn("13,209", said)
        self.assertEqual(said, "American Discovery Trail passes through Iowa and is 5,008 miles (8,060 km) long in all.")
        self.assertIn("in all", said)
        self.assertNotIn("highest point", said)

    def test_a_high_point_is_only_taken_from_trails_wholly_in_the_place(self):
        checked = 0
        for slug, info in self.by_slug.items():
            keys = [info["key"]]
            inside = [r for r in info["records"] if summary.wholly_in(r, keys)]
            said = text(summary.facts(info["records"], self.records, place=(info["name"], keys)))
            marks = [hike.table(r).get("high_point_m") for r in inside]
            marks = [m for m in marks if isinstance(m, (int, float)) and not isinstance(m, bool)]
            if marks:
                self.assertIn(text(words.elevation(max(marks))), said, slug)
                checked += 1
            else:
                self.assertNotIn("highest point", said, slug)
            if len(inside) < len(info["records"]):
                self.assertNotIn("The longest is", said, slug)
                self.assertIn("passes through", said, slug)
        self.assertGreater(checked, 10)

    def test_a_place_wholly_holding_its_trail_keeps_the_plain_sentences(self):
        rec = next(r for r in self.records if len(facets.place_keys(r)) == 1)
        said = text(summary.facts([rec], self.records, place=("There", facets.place_keys(rec))))
        self.assertNotIn("passes through", said)
        self.assertNotIn("in all", said)
        self.assertIn(" long.", said)

    def test_a_description_marks_a_whole_trail_length_that_is_not_the_places(self):
        adt = next(r for r in self.records if r["id"] == "american-discovery-trail")
        self.assertTrue(regions.trail_miles(adt, ["US-IA"]).endswith("miles in all"))
        own = next(r for r in self.records if len(facets.place_keys(r)) == 1)
        self.assertTrue(regions.trail_miles(own, facets.place_keys(own)).endswith(" miles"))


class NoTrackNoticeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = [r for r in records.load_records(ROOT) if not common.has_line(r)]

    def notice(self, rec):
        title, status, reason, rule, actions = trail._no_gpx_parts(rec)
        reason = reason if isinstance(reason, Markup) else common.rich(reason)
        return text(f"GPX: {facets.gpx_status_text(rec)}. {title}. {reason} {rule}"), text(trail.brief(rec))

    def test_none_contradicts_itself(self):
        for rec in self.records:
            notice, brief = self.notice(rec)
            both = notice + " " + brief
            self.assertFalse("may be passed on" in notice and re.search(r"added (here )?yet|not been added", notice), rec["id"])
            self.assertFalse("no track from its author was found" in notice and "sells a GPX" in both, rec["id"])
            self.assertFalse(re.search(r"Overpass|Nominatim|Held\.", both), rec["id"])
            if "sells a GPX" in both or "Sold by its author" in both:
                self.assertTrue(common.sells_gpx(rec), rec["id"])

    def test_not_added_yet_says_only_that(self):
        found = [r for r in self.records if common.not_added_yet(r) and not common.is_route(r)]
        self.assertTrue(found)
        for rec in found:
            notice, _ = self.notice(rec)
            self.assertIn("added", notice)
            self.assertNotIn("may be passed on", notice)
            self.assertEqual(trail._no_gpx_parts(rec)[3], "")

    def test_a_route_sold_only_as_a_book_is_not_said_to_sell_a_gpx(self):
        rec = next(r for r in self.records if r["id"] == "grand-teton-loop")
        notice, brief = self.notice(rec)
        self.assertNotIn("sells a GPX", brief)
        self.assertIn("sells it as a guide", brief)
        self.assertNotIn("Sold by its author", notice)

    def test_a_route_that_sells_a_gpx_says_so(self):
        rec = next(r for r in self.records if r["id"] == "beartooth-high-route")
        notice, brief = self.notice(rec)
        self.assertIn("sells a GPX", brief)
        self.assertIn("The author sells a GPX", notice)

    def test_search_services_are_not_named_to_visitors(self):
        self.assertEqual(common.visitor_text("No track is included. A search on Overpass and Nominatim found none. Ask the holder."),
                         "No track is included. Ask the holder.")
        rec = next(r for r in self.records if r["id"] == "bayou-state-trail")
        notice, _ = self.notice(rec)
        self.assertNotIn("Overpass", notice)


class HeldNoteTest(unittest.TestCase):
    def test_a_held_record_without_a_note_prints_no_sentence_about_it(self):
        said = text(trail.listing_note({"wave": "held"}))
        self.assertNotIn("no note", said)
        self.assertEqual(said, words.meaning(words.WAVES, "held"))
        self.assertIn("because", text(trail.listing_note({"wave": "held", "wave_note": "because"})))


class ListTileCountTest(unittest.TestCase):
    def test_the_authors_tile_counts_authors_not_routes(self):
        with open(os.path.join(WEB, "olt", "pages.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("count=len(author_groups)", src)


if __name__ == "__main__":
    unittest.main()
