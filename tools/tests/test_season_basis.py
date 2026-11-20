"""Tests for tools/season.py check_season.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import os
import sys
import unittest
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import season  # noqa: E402


def src(publisher, facts=("season", "months"), url="https://example.org/trail"):
    return {"url": url, "publisher": publisher, "facts": list(facts)}


def check(**fields):
    hike = {
        "season": "June to September",
        "months": [6, 7, 8, 9],
        "season_basis": "primary",
        "source": [src("Park Service")],
    }
    for k, v in fields.items():
        if v is None:
            hike.pop(k, None)
        else:
            hike[k] = v
    errors = []
    season.check_season("t", hike, errors)
    return errors


class SeasonBasisTest(unittest.TestCase):
    def test_primary_with_one_naming_source_passes(self):
        self.assertEqual(check(), [])

    def test_season_without_basis_is_an_error(self):
        errors = check(season_basis=None)
        self.assertTrue(any("season_basis" in e for e in errors), errors)

    def test_basis_without_season_is_an_error(self):
        errors = check(season=None, months=None)
        self.assertTrue(any("season_basis" in e for e in errors), errors)

    def test_unknown_basis_is_an_error(self):
        errors = check(season_basis="guessed")
        self.assertTrue(any("season_basis" in e for e in errors), errors)

    def test_months_without_season_is_an_error(self):
        errors = check(season=None, season_basis=None)
        self.assertTrue(errors)

    def test_season_without_months_is_an_error(self):
        errors = check(months=None)
        self.assertTrue(errors)

    def test_sources_needs_two_publishers(self):
        same = [src("Guide A", url="https://a.example/1"), src("guide a", url="https://a.example/2")]
        errors = check(season_basis="sources", source=same)
        self.assertEqual(len(errors), 1, errors)
        diff = [src("Guide A", url="https://a.example/1"), src("Guide B", url="https://b.example/1")]
        self.assertEqual(check(season_basis="sources", source=diff), [])

    def test_source_basis_needs_a_naming_source(self):
        self.assertEqual(check(season_basis="source"), [])
        errors = check(season_basis="source", source=[src("Guide A", facts=("days",))])
        self.assertTrue(errors)

    def test_primary_needs_a_naming_source(self):
        errors = check(source=[src("Park Service", facts=("days",))])
        self.assertTrue(errors)

    def test_estimate_needs_a_method_and_refuses_one_otherwise(self):
        self.assertTrue(check(season_basis="estimate"))
        self.assertEqual(
            check(season_basis="estimate", season_method="Estimated from climate normals."), [])
        self.assertTrue(check(season_basis="estimate", season_method=""))
        self.assertTrue(check(season_basis="estimate", season_method="x" * 401))
        self.assertTrue(check(season_method="Estimated from climate normals."))

    def test_estimate_with_two_naming_sources_is_an_error(self):
        two = [src("Climate", url="https://c.example/1"), src("Other", url="https://o.example/1")]
        errors = check(season_basis="estimate", season_method="Estimated from climate.", source=two)
        self.assertTrue(errors)

    def test_estimate_with_no_naming_source_is_an_error(self):
        errors = check(season_basis="estimate", season_method="Estimated from climate.",
                       source=[src("Climate", facts=("days",))])
        self.assertTrue(errors)

    def test_a_hike_without_season_passes_until_required(self):
        self.assertEqual(check(season=None, months=None, season_basis=None, source=None), [])

    def test_required_flag_makes_it_an_error(self):
        with mock.patch.object(season, "SEASON_REQUIRED", True):
            errors = check(season=None, months=None, season_basis=None, source=None)
            self.assertTrue(any("season" in e for e in errors), errors)

    def test_method_without_season_is_an_error(self):
        errors = check(season=None, months=None, season_basis=None, season_method="Some method.")
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
