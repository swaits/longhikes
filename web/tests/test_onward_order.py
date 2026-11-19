"""On a trail page, the other trails of the same state come closest in length first."""
import math
import os
import re
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)

from olt import facets, records, trail  # noqa: E402


class OnwardOrderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recs = records.load_records(ROOT)
        cls.by_id = {r["id"]: r for r in cls.recs}

    def part(self, rec, key):
        html = str(trail.onward(rec, self.recs))
        start = html.index(f'id="onward-{key.lower()}"')
        return html[start:html.index("</section>", start)]

    def test_the_sierra_high_route_leads_with_trails_near_its_length(self):
        rec = self.by_id["sierra-high-route"]
        ids = re.findall(r'href="/trails/([^/"]+)/"', self.part(rec, "US-CA"))
        self.assertEqual(len(ids), trail.ONWARD_MAX)
        gaps = [abs(math.log(self.by_id[i]["length_km"] / rec["length_km"])) for i in ids]
        self.assertEqual(gaps, sorted(gaps))
        self.assertNotIn("great-western-loop", ids)  # the 6,875 mile loop is no longer first
        everyone = sorted((r for r in self.recs if r["id"] != rec["id"] and "US-CA" in facets.place_keys(r)),
                          key=lambda r: trail.nearest_length(rec, r))
        self.assertEqual(ids, [r["id"] for r in everyone[:trail.ONWARD_MAX]])

    def test_how_many_are_shown_is_unchanged(self):
        for rec in self.recs[:40]:
            html = str(trail.onward(rec, self.recs))
            for ul in re.findall(r'<ul class="onward__list">(.*?)</ul>', html):
                self.assertLessEqual(ul.count("<li>"), trail.ONWARD_MAX)


if __name__ == "__main__":
    unittest.main()
