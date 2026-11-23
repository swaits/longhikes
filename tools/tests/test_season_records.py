"""Tests over the real records: every trail has a season, with its provenance.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import refresh  # noqa: E402
import season  # noqa: E402
import validate as V  # noqa: E402

RECORDS = {tid: refresh.load_toml(os.path.join(V.ROOT, tid, "trail.toml"))
           for tid in refresh.trail_ids(V.ROOT)}


def hikes():
    for tid, rec in RECORDS.items():
        yield tid, rec.get("hike") or {}


class EveryTrailHasASeasonTest(unittest.TestCase):
    def test_every_record_has_season_months_and_a_basis(self):
        for tid, hike in hikes():
            self.assertTrue(hike.get("season"), tid)
            self.assertTrue(hike.get("months"), tid)
            self.assertIn(hike.get("season_basis"), season.BASES, tid)

    def test_the_basis_fits_the_sources(self):
        for tid, hike in hikes():
            errors = []
            season.check_season(tid, hike, errors)
            self.assertEqual(errors, [], tid)

    def test_every_estimate_has_a_method_with_its_confidence_and_a_climate_source(self):
        found = 0
        for tid, hike in hikes():
            if hike.get("season_basis") != "estimate":
                continue
            found += 1
            self.assertIn(season.confidence_of(hike.get("season_method")), season.CONFIDENCES, tid)
            naming = [s for s in hike["source"] if "season" in s["facts"]]
            self.assertEqual(len(naming), 1, tid)
            self.assertEqual(naming[0]["facts"], ["season", "months"], tid)
            self.assertIn("chelsa-climate.org", naming[0]["url"], tid)
        self.assertGreater(found, 0)

    def test_no_season_from_a_page_cites_climate_data(self):
        for tid, hike in hikes():
            if hike.get("season_basis") == "estimate":
                continue
            for source in hike.get("source") or []:
                if "season" in source["facts"]:
                    self.assertNotIn("chelsa", source["url"], tid)

    def test_no_record_says_a_season_is_missing(self):
        for tid, hike in hikes():
            for field in ("summary", "caution"):
                text = str(hike.get(field) or "").lower()
                self.assertNotIn("no season", text, tid)
                self.assertNotIn("season on file", text, tid)

    def test_the_estimated_phrase_is_built_from_its_months(self):
        for tid, hike in hikes():
            if hike.get("season_basis") == "estimate":
                self.assertEqual(hike["season"], season.phrase_for(hike["months"]), tid)

    def test_a_season_with_a_method_has_its_confidence_in_the_method(self):
        judged = [t for t, h in hikes() if h.get("season_method")]
        self.assertGreater(len(judged), 0)
        for tid in judged:
            self.assertTrue(season.confidence_of(RECORDS[tid]["hike"]["season_method"]), tid)

    def test_a_judged_season_changed_its_record_history(self):
        for tid, hike in hikes():
            if hike.get("season_method"):
                changed = [e for e in RECORDS[tid]["history"]
                           if "hike.season_method" in (e.get("fields") or [])]
                # at least one: a later correction to the method's wording is a second entry
                self.assertGreaterEqual(len(changed), 1, tid)


if __name__ == "__main__":
    unittest.main()
