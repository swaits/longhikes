"""Tests for the common_name check in tools/validate.py: no network, no numpy.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import validate as V  # noqa: E402
import trail_history as H  # noqa: E402


def check(rec):
    errors = []
    V.check_common_name("t", rec, errors)
    return errors


class CommonNameTest(unittest.TestCase):
    def test_none_is_valid(self):
        self.assertEqual(check({"name": "Appalachian National Scenic Trail"}), [])

    def test_a_different_name_is_valid(self):
        self.assertEqual(check({"name": "Appalachian National Scenic Trail", "common_name": "Appalachian Trail"}), [])

    def test_must_be_a_clean_string(self):
        for bad in ("", "  ", " Appalachian Trail", "Appalachian Trail ", 7, ["AT"]):
            self.assertTrue(check({"name": "x", "common_name": bad}), repr(bad))

    def test_must_differ_from_name(self):
        errors = check({"name": "Long Trail", "common_name": "Long Trail"})
        self.assertEqual(len(errors), 1)
        self.assertIn("repeats name", errors[0])

    def test_is_a_field_that_needs_history(self):
        self.assertIn("common_name", H.SCHEMA_FIELDS)
        self.assertNotIn("common_name", H.NOT_FACTS)


if __name__ == "__main__":
    unittest.main()
