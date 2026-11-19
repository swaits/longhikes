"""Tests for the held-needs-a-note rule in tools/validate.py.

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
    V.check_held_note("t", rec, errors)
    return errors


class HeldNoteTests(unittest.TestCase):
    def test_held_without_a_note_fails(self):
        self.assertEqual(len(check({"wave": "held"})), 1)
        self.assertEqual(len(check({"wave": "held", "wave_note": "  "})), 1)

    def test_held_with_a_note_passes(self):
        self.assertEqual(check({"wave": "held", "wave_note": "No whole track exists."}), [])

    def test_other_waves_need_no_note(self):
        self.assertEqual(check({"wave": 1}), [])
        self.assertEqual(check({}), [])


if __name__ == "__main__":
    unittest.main()
