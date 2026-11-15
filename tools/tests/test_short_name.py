"""Tests for the short_name and short_name_url checks in tools/validate.py: no network, no numpy.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import validate as V  # noqa: E402

URL = "https://www.pcta.org/"


def check(rec):
    errors = []
    V.check_short_name("t", rec, errors)
    return errors


class ShortNameTest(unittest.TestCase):
    def test_none_is_valid(self):
        self.assertEqual(check({}), [])

    def test_abbreviation_with_page_is_valid(self):
        self.assertEqual(check({"short_name": "PCT", "short_name_url": URL}), [])
        self.assertEqual(check({"short_name": "PCT", "short_name_url": "http://example.org/a"}), [])

    def test_abbreviation_needs_a_page(self):
        errors = check({"short_name": "PCT"})
        self.assertEqual(len(errors), 1)
        self.assertIn("needs short_name_url", errors[0])

    def test_page_needs_an_abbreviation(self):
        errors = check({"short_name_url": URL})
        self.assertEqual(len(errors), 1)
        self.assertIn("without short_name", errors[0])

    def test_page_must_be_http(self):
        for bad in ("www.pcta.org", "ftp://example.org/", "", 5):
            self.assertTrue(any("http(s)" in e for e in check({"short_name": "PCT", "short_name_url": bad})), bad)

    def test_no_full_stops(self):
        errors = check({"short_name": "A.T.", "short_name_url": URL})
        self.assertEqual(len(errors), 1)
        self.assertIn("full stops", errors[0])
        self.assertEqual(check({"short_name": "M-DT", "short_name_url": URL}), [])
        self.assertEqual(check({"short_name": "L2H", "short_name_url": URL}), [])

    def test_abbreviation_must_be_a_clean_string(self):
        for bad in ("", "  ", " PCT", "PCT ", 7, ["PCT"]):
            self.assertTrue(check({"short_name": bad, "short_name_url": URL}), repr(bad))


if __name__ == "__main__":
    unittest.main()
