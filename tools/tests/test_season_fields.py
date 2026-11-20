"""Tests that season_basis and season_method are known fields and documented.

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


class SeasonFieldsTest(unittest.TestCase):
    def test_the_new_fields_are_known_to_the_history_tool(self):
        for f in ("hike.season_basis", "hike.season_method"):
            self.assertIn(f, H.SCHEMA_FIELDS)
            self.assertTrue(H.is_fact(f))

    def test_the_facts_text_names_them(self):
        self.assertIn("season_basis", H.FACTS_TEXT)

    def test_the_schema_documents_them_and_the_estimate_exception(self):
        text = open(os.path.join(V.ROOT, "docs", "schema.md"), encoding="utf-8").read()
        for needle in ("`season_basis`", "`season_method`", "except season, which may be estimated"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
