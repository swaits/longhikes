"""Tests for the shared season helpers in tools/season.py.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import season  # noqa: E402


class SpanTest(unittest.TestCase):
    def test_span_wraps_the_year(self):
        self.assertEqual(season.span([11, 12, 1, 2, 3]), (11, 3))

    def test_span_of_two_windows_covers_both(self):
        self.assertEqual(season.span([4, 5, 9, 10]), (4, 10))

    def test_span_of_one_month(self):
        self.assertEqual(season.span([7]), (7, 7))

    def test_span_of_all_year(self):
        self.assertEqual(season.span(list(range(1, 13))), (1, 12))

    def test_span_is_order_independent(self):
        self.assertEqual(season.span([3, 1, 12, 2, 11]), (11, 3))


class GradeTest(unittest.TestCase):
    def test_grade_exact(self):
        self.assertEqual(season.grade([6, 7, 8, 9], [6, 7, 8, 9]), "exact")
        self.assertEqual(season.grade([11, 12, 1, 2], [11, 12, 1, 2]), "exact")

    def test_grade_within_one_at_each_end(self):
        self.assertEqual(season.grade([5, 6, 7, 8, 9], [6, 7, 8]), "within1")

    def test_grade_worse(self):
        self.assertEqual(season.grade([6, 7], [9, 10]), "worse")

    def test_grade_across_the_year_end(self):
        self.assertEqual(season.grade([12, 1, 2], [1, 2, 3]), "within1")

    def test_grade_two_months_off_at_one_end_is_worse(self):
        self.assertEqual(season.grade([4, 5, 6, 7, 8], [6, 7, 8]), "worse")


class PhraseTest(unittest.TestCase):
    def test_phrase_runs(self):
        self.assertEqual(season.phrase_for([6, 7, 8, 9]), "June to September")
        self.assertEqual(season.phrase_for([11, 12, 1, 2, 3]), "November to March")
        self.assertEqual(season.phrase_for([4, 5, 9, 10]),
                         "April to May and September to October")
        self.assertEqual(season.phrase_for([7]), "July")
        self.assertEqual(season.phrase_for(list(range(1, 13))), "All year")

    def test_phrase_two_month_run(self):
        self.assertEqual(season.phrase_for([7, 8]), "July to August")
        self.assertEqual(season.phrase_for([12, 1]), "December to January")


class MethodSentenceTest(unittest.TestCase):
    def test_method_sentence_names_dataset_period_and_points(self):
        text = season.method_sentence("ERA5-Land via Open-Meteo", "2011-2020", 5, "track", 1)
        self.assertIn("ERA5-Land via Open-Meteo", text)
        self.assertIn("2011-2020", text)
        self.assertIn("5", text)
        self.assertTrue(text.endswith("."))
        self.assertLess(len(text), 400)

    def test_method_sentence_for_each_kind(self):
        for kind in ("track", "ends", "place"):
            text = season.method_sentence("Dataset", "2011-2020", 1, kind, 1)
            self.assertIn("Dataset", text)


if __name__ == "__main__":
    unittest.main()
