"""Tests for system_km, system_note and built_km in tools/validate.py.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import trail_history as H  # noqa: E402
import validate as V  # noqa: E402


def check(**fields):
    rec = {"length_km": 1818, "hike": {"unfinished": "About 290 miles are built."}}
    rec.update(fields)
    errors = []
    V.check_length_facts("t", rec, errors)
    return errors


class SystemFigureTest(unittest.TestCase):
    def test_a_larger_figure_with_its_note_passes(self):
        self.assertEqual(check(system_km=2549, system_note="both corridors and the connectors"), [])

    def test_a_record_without_them_passes(self):
        self.assertEqual(check(), [])

    def test_the_figure_must_be_larger_than_the_length(self):
        for km in (1818, 1000):
            errors = check(system_km=km, system_note="the whole system")
            self.assertEqual(len(errors), 1, km)
            self.assertIn("greater than length_km", errors[0])

    def test_the_figure_needs_its_note(self):
        for note in (None, "", "  "):
            fields = {"system_km": 2549}
            if note is not None:
                fields["system_note"] = note
            errors = check(**fields)
            self.assertEqual(len(errors), 1, repr(note))
            self.assertIn("system_note", errors[0])

    def test_a_note_alone_is_refused(self):
        errors = check(system_note="the whole system")
        self.assertEqual(len(errors), 1)
        self.assertIn("system_km is not", errors[0])

    def test_the_note_does_not_repeat_the_word_the_page_adds(self):
        errors = check(system_km=2549, system_note="Counting both corridors")
        self.assertEqual(len(errors), 1)
        self.assertIn("counting", errors[0])

    def test_the_figure_is_a_whole_number_of_kilometres(self):
        for bad in (2549.5, "2549", True, 0, -5):
            errors = check(system_km=bad, system_note="the whole system")
            self.assertEqual(len(errors), 1, repr(bad))
            self.assertIn("whole number", errors[0])


class BuiltFigureTest(unittest.TestCase):
    def test_a_built_length_on_an_unfinished_trail_passes(self):
        self.assertEqual(check(built_km=467), [])

    def test_it_cannot_exceed_the_length(self):
        errors = check(built_km=1819)
        self.assertEqual(len(errors), 1)
        self.assertIn("cannot exceed length_km", errors[0])
        self.assertEqual(check(built_km=1818), [])

    def test_it_belongs_only_on_an_unfinished_trail(self):
        for hike in ({}, {"unfinished": " "}):
            errors = check(built_km=467, hike=hike)
            self.assertEqual(len(errors), 1)
            self.assertIn("hike.unfinished", errors[0])
        rec = {"length_km": 500, "built_km": 400}
        errors = []
        V.check_length_facts("t", rec, errors)
        self.assertEqual(len(errors), 1)

    def test_it_is_a_whole_number_of_kilometres(self):
        for bad in (290.5, "290", False, 0):
            errors = check(built_km=bad)
            self.assertEqual(len(errors), 1, repr(bad))
            self.assertIn("whole number", errors[0])


class HistoryFieldsTest(unittest.TestCase):
    def test_the_new_fields_are_known_to_the_history_and_are_facts(self):
        for name in ("system_km", "system_note", "built_km"):
            self.assertIn(name, H.SCHEMA_FIELDS)
            self.assertTrue(H.is_fact(name), name)
            self.assertIn(name, H.FACTS_TEXT)


if __name__ == "__main__":
    unittest.main()
