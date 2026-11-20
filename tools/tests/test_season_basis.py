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
import validate as V  # noqa: E402
import refresh  # noqa: E402


def src(publisher, facts=("season", "months"), url="https://example.org/trail"):
    return {"url": url, "publisher": publisher, "facts": list(facts)}


CLIMATE_URL = "https://www.chelsa-climate.org/datasets/chelsa_climatologies"
CLIMATE = "WSL (CHELSA) and NOAA NCEI (ETOPO)"
METHOD = "Snow clears from the high ground in June. Confidence: medium."


def climate_src(**kw):
    return src(CLIMATE, url=CLIMATE_URL, **kw)


def estimate(**fields):
    fields.setdefault("season_basis", "estimate")
    fields.setdefault("season_method", METHOD)
    fields.setdefault("source", [climate_src()])
    return check(**fields)


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

    def test_source_basis_needs_exactly_one_publisher(self):
        two = [src("Park Service"), src("Blog", url="https://example.org/b")]
        errors = check(season_basis="source", source=two)
        self.assertTrue(any("exactly one publisher" in e for e in errors), errors)
        same = [src("Park Service"), src("Park Service", url="https://example.org/b")]
        self.assertEqual(check(season_basis="source", source=same), [])

    def test_method_is_allowed_with_sources_only_besides_estimate(self):
        two = [src("Park Service"), src("Blog", url="https://example.org/b")]
        ok = check(season_basis="sources", source=two,
                   season_method="The pages differ; set from both and the climate estimate.")
        self.assertEqual(ok, [])
        self.assertEqual(check(season_basis="sources", source=two), [])
        for basis in ("primary", "source"):
            errors = check(season_basis=basis, season_method="Some sentence.")
            self.assertTrue(any("season_method" in e for e in errors), (basis, errors))
        long = check(season_basis="sources", source=two, season_method="x" * 401)
        self.assertTrue(any("400" in e for e in long), long)
        blank = check(season_basis="sources", source=two, season_method=" ")
        self.assertTrue(any("season_method" in e for e in blank), blank)

    def test_primary_needs_a_naming_source(self):
        errors = check(source=[src("Park Service", facts=("days",))])
        self.assertTrue(errors)

    def test_an_estimate_with_a_method_and_a_climate_source_passes(self):
        self.assertEqual(estimate(), [])

    def test_an_estimate_needs_a_method(self):
        errors = estimate(season_method=None)
        self.assertTrue(any("season_method" in e for e in errors), errors)
        self.assertTrue(estimate(season_method=""))
        self.assertTrue(estimate(season_method="x" * 401))

    def test_an_estimate_method_ends_with_its_confidence(self):
        for word in ("high", "medium", "low"):
            self.assertEqual(estimate(season_method=f"Set by snow. Confidence: {word}."), [])
        errors = estimate(season_method="Set by snow.")
        self.assertTrue(any("Confidence" in e for e in errors), errors)
        self.assertTrue(estimate(season_method="Set by snow. Confidence: certain."))

    def test_a_method_without_an_estimate_is_still_an_error_on_a_primary(self):
        self.assertTrue(check(season_method=METHOD))

    def test_an_estimate_refuses_an_ordinary_page_naming_the_season(self):
        two = [climate_src(), src("Park Service", url="https://example.org/p")]
        errors = estimate(source=two)
        self.assertTrue(errors)
        only = [src("Park Service", url="https://example.org/p")]
        errors = estimate(source=only)
        self.assertTrue(any("climate" in e for e in errors), errors)

    def test_an_estimate_with_no_naming_source_is_an_error(self):
        self.assertTrue(estimate(source=[climate_src(facts=("days",))]))

    def test_an_estimate_source_names_both_season_and_months(self):
        errors = estimate(source=[climate_src(facts=("season",))])
        self.assertTrue(any("months" in e for e in errors), errors)

    def test_a_sourced_season_may_not_cite_the_climate_data(self):
        errors = check(source=[climate_src()])
        self.assertTrue(any("climate" in e for e in errors), errors)

    def test_the_climate_host_is_the_one_the_estimator_reads(self):
        import urllib.parse
        import season_climate
        self.assertEqual(
            season.CLIMATE_HOSTS,
            frozenset({urllib.parse.urlparse(season_climate.SOURCE["url"]).hostname}))

    def test_sources_judged_from_pages_that_differ_may_share_a_publisher(self):
        two = [src("The Trek", url="https://t.example/1"), src("The Trek", url="https://t.example/2")]
        errors = check(season_basis="sources", source=two)
        self.assertTrue(errors)
        self.assertEqual(
            check(season_basis="sources", source=two,
                  season_method="The pages differ. Confidence: low."), [])

    def test_judged_from_pages_that_differ_needs_a_page(self):
        errors = check(season_basis="sources", source=[src("The Trek", facts=("days",))],
                       season_method="The pages differ. Confidence: low.")
        self.assertTrue(errors)

    def test_a_season_read_from_a_page_has_no_method_and_no_estimate_basis(self):
        self.assertTrue(season.read_from_a_page({"season": "x", "season_basis": "primary"}))
        self.assertFalse(season.read_from_a_page({"season": "x", "season_basis": "estimate"}))
        self.assertFalse(season.read_from_a_page(
            {"season": "x", "season_basis": "sources", "season_method": "Judged."}))
        self.assertFalse(season.read_from_a_page({"season_basis": "primary"}))

    def test_the_confidence_is_read_from_the_method(self):
        self.assertEqual(season.confidence_of("Set by snow. Confidence: low."), "low")
        self.assertEqual(season.confidence_of("Set by snow."), "")

    def test_a_hike_without_season_is_an_error(self):
        errors = check(season=None, months=None, season_basis=None, source=None)
        self.assertTrue(any("season" in e for e in errors), errors)

    def test_a_record_with_no_hike_is_an_error(self):
        errors = []
        season.check_present("t", {}, errors)
        self.assertTrue(errors)
        errors = []
        season.check_present("t", {"hike": {"season": "x"}}, errors)
        self.assertEqual(errors, [])

    def test_method_without_season_is_an_error(self):
        errors = check(season=None, months=None, season_basis=None, season_method="Some method.")
        self.assertTrue(errors)

    def test_every_record_passes_the_validator(self):
        errors = []
        for tid in refresh.trail_ids(V.ROOT):
            rec = refresh.load_toml(os.path.join(V.ROOT, tid, "trail.toml"))
            V.check_hike(tid, rec, errors)
            season.check_present(tid, rec, errors)
        self.assertEqual(errors, [])

    def test_provenance_keys_need_no_source_fact(self):
        hike = {"season": "June to September", "months": [6, 7, 8, 9], "season_basis": "primary",
                "source": [src("Park Service", facts=("season", "months"))]}
        errors = []
        V.check_hike("t", {"hike": hike}, errors)
        self.assertFalse([e for e in errors if "not named in the facts" in e], errors)
        self.assertFalse([e for e in errors if "not a known field" in e], errors)


if __name__ == "__main__":
    unittest.main()
