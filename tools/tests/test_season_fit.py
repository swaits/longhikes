"""Tests for the committed fit figure in tools/season_fit.json.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import json
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import estimate_season as E  # noqa: E402
import refresh  # noqa: E402
import validate as V  # noqa: E402

FIT_PATH = os.path.join(V.ROOT, "tools", "season_fit.json")


def load_fit():
    with open(FIT_PATH, encoding="utf-8") as f:
        return json.load(f)


class SeasonFitFileTest(unittest.TestCase):
    def test_the_committed_fit_has_the_fields_the_site_reads(self):
        fit = load_fit()
        for key in ("computed", "rule_version", "dataset", "period",
                    "params", "loo", "bar", "passes", "confidence"):
            self.assertIn(key, fit)
        self.assertEqual(sorted(fit["params"]), sorted(E.Params(0, 0).as_dict()))
        for part in ("loo",):
            for key in ("n", "within1", "worse", "no_data", "classified",
                        "jaccard", "by_group", "by_kind"):
                self.assertIn(key, fit[part], part)
            rep = fit[part]
            self.assertEqual(rep["within1"] + rep["worse"] + rep["no_data"],
                             rep["n"], part)
        self.assertEqual(fit["bar"], E.BAR)
        self.assertEqual(fit["rule_version"], E.RULE_VERSION)
        self.assertEqual(fit["passes"], E.passes_bar(fit["loo"], fit["bar"]))

    def test_estimates_only_over_the_bar_by_the_blind_test(self):
        """The machine estimate on its own is under the bar and is never
        written to a record. Estimated seasons are judged, and the judged
        method must pass the bar in its blind test."""
        estimated = []
        for tid in refresh.trail_ids(V.ROOT):
            rec = refresh.load_toml(os.path.join(V.ROOT, tid, "trail.toml"))
            if (rec.get("hike") or {}).get("season_basis") == "estimate":
                estimated.append(tid)
        if not estimated:
            self.skipTest("no estimated seasons on file yet")
        import season_judge
        blind = season_judge.load_blind_test()
        self.assertEqual(season_judge.check_blind_test(blind), [])
        self.assertGreaterEqual(blind["share"], E.BAR["within1_min"])

if __name__ == "__main__":
    unittest.main()
