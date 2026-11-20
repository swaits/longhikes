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
                    "params", "all", "held_out", "bar", "passes"):
            self.assertIn(key, fit)
        for key in ("snow_cm_max", "cold_c_min", "heat_c_max"):
            self.assertIn(key, fit["params"])
        for part in ("all", "held_out"):
            for key in ("n", "exact", "within1", "worse", "no_data", "by_group"):
                self.assertIn(key, fit[part], part)
            rep = fit[part]
            self.assertEqual(rep["within1"] + rep["worse"] + rep["no_data"],
                             rep["n"], part)
        self.assertEqual(fit["bar"], E.BAR)
        self.assertEqual(fit["rule_version"], E.RULE_VERSION)
        self.assertEqual(fit["passes"], E.passes_bar(fit["held_out"], fit["bar"]))

    def test_estimates_only_with_a_passing_fit(self):
        estimated = []
        for tid in refresh.trail_ids(V.ROOT):
            rec = refresh.load_toml(os.path.join(V.ROOT, tid, "trail.toml"))
            if (rec.get("hike") or {}).get("season_basis") == "estimate":
                estimated.append(tid)
        if not estimated:
            self.skipTest("no estimated seasons on file yet")
        fit = load_fit()
        self.assertTrue(fit["passes"], fit)
        held = fit["held_out"]
        self.assertGreaterEqual(held["within1"] / held["n"],
                                E.BAR["within1_min"])


if __name__ == "__main__":
    unittest.main()
