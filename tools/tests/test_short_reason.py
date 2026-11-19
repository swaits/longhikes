"""Tests for the short_reason rule in tools/validate.py.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import validate as V  # noqa: E402


def check(rec):
    errors = []
    V.check_short_reason("t", rec, errors)
    return errors


class ShortReasonTests(unittest.TestCase):
    def test_under_the_floor_needs_a_reason(self):
        self.assertEqual(len(check({"length_km": 67})), 1)
        self.assertEqual(len(check({"length_km": 67, "short_reason": "  "})), 1)

    def test_under_the_floor_with_a_reason_passes(self):
        self.assertEqual(check({"length_km": 67, "short_reason": "It takes five days."}), [])

    def test_at_or_over_the_floor_refuses_a_reason(self):
        self.assertEqual(len(check({"length_km": 80, "short_reason": "It takes five days."})), 1)
        self.assertEqual(len(check({"length_km": 300, "short_reason": "x"})), 1)

    def test_at_or_over_the_floor_needs_nothing(self):
        self.assertEqual(check({"length_km": 80}), [])
        self.assertEqual(check({"length_km": 1931}), [])

    def test_the_old_placeholder_sentence_is_refused(self):
        old = "Listed before the test was written; under review."
        self.assertEqual(len(check({"length_km": 64, "short_reason": old})), 1)


if __name__ == "__main__":
    unittest.main()
