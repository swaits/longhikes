"""Tests for the stated-permission licence in tools/validate.py.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import validate as V  # noqa: E402

GOOD = {
    "licence": "stated-permission",
    "licence_text": "The association's president answered the form on the issue tracker.",
    "permission_quote": "It's completely public and free to share.",
    "permission_by": "the association's president",
    "permission_date": "2026-11-16",
    "permission_url": "https://github.com/example/repo/issues/2",
}


def check(src):
    errors = []
    V.check_stated_permission("t", src, errors)
    return errors


def without(field, **more):
    src = {k: v for k, v in GOOD.items() if k != field}
    src.update(more)
    return src


class StatedPermissionTest(unittest.TestCase):
    def test_value_is_allowed_and_carries_a_track(self):
        self.assertIn("stated-permission", V.ALLOWED_LICENCES)
        self.assertIn("stated-permission", V.DATA_LICENCES)

    def test_complete_statement_passes(self):
        self.assertEqual(check(dict(GOOD)), [])

    def test_each_of_the_four_fields_is_required(self):
        for field in V.PERMISSION_FIELDS:
            errors = check(without(field))
            self.assertEqual(len(errors), 1, field)
            self.assertIn(field, errors[0])

    def test_empty_quote_or_role_fails(self):
        self.assertEqual(len(check(without("permission_quote", permission_quote="  "))), 1)
        self.assertEqual(len(check(without("permission_by", permission_by=""))), 1)

    def test_date_must_be_a_real_iso_date(self):
        for bad in ("16 November 2026", "2026-11-1", "2026-13-40", 20261116):
            self.assertEqual(len(check(without("permission_date", permission_date=bad))), 1, bad)

    def test_address_must_be_http_or_https(self):
        for bad in ("github.com/example/repo/issues/2", "ftp://example.org/x", "https://", "see the issue"):
            self.assertEqual(len(check(without("permission_url", permission_url=bad))), 1, bad)
        self.assertEqual(check(without("permission_url", permission_url="http://example.org/x")), [])

    def test_missing_licence_text_fails(self):
        self.assertEqual(len(check(without("licence_text"))), 1)

    def test_other_licences_may_not_carry_the_fields(self):
        errors = check({"licence": "ODbL-1.0", "licence_text": "ODbL",
                        "permission_quote": "Yes", "permission_by": "x"})
        self.assertEqual(len(errors), 2)
        self.assertIn("stated-permission licence only", errors[0])

    def test_other_licences_without_the_fields_pass(self):
        self.assertEqual(check({"licence": "ODbL-1.0", "licence_text": "no address"}), [])

    def test_the_hoosier_record_passes(self):
        import tomllib
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                            "hoosier-heritage-trail", "trail.toml")
        with open(path, "rb") as f:
            src = tomllib.load(f)["source"]
        self.assertEqual(src["licence"], "stated-permission")
        self.assertEqual(check(src), [])


class LonlatWithoutPlaceNameTest(unittest.TestCase):
    def run_check(self, line_file):
        errors = []
        rec = {"length_km": 259, "source": {"line_file": line_file},
               "hike": {"summary": "S.", "official_url": "https://x.example/",
                        "start_lonlat": [-85.863, 38.462], "end_lonlat": [-86.477, 39.323],
                        "checked": "2026-11-16"}}
        V.check_hike("t", rec, errors)
        return [e for e in errors if "lonlat" in e]

    def test_track_ends_need_no_place_name(self):
        self.assertEqual(self.run_check("line.geojson"), [])

    def test_record_without_track_still_needs_the_place_name(self):
        errors = self.run_check("")
        self.assertEqual(len(errors), 2)
        self.assertIn("hike.start is not", errors[0])


if __name__ == "__main__":
    unittest.main()
