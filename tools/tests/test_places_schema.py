"""Tests for the place schema: the record's [[place]] table, places_checked and
places_track, and their place in the history rules (tools/trail_history.py, docs/schema.md).

Run from the repository root:
    python3 -m unittest discover tools/tests -p "test_places_schema.py"
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import trail_history as H  # noqa: E402


class PlaceSchemaTest(unittest.TestCase):
    def test_place_fields_are_schema_fields(self):
        self.assertIn("place", H.SCHEMA_FIELDS)
        self.assertIn("place.km", H.SCHEMA_FIELDS)
        self.assertIn("places_checked", H.SCHEMA_FIELDS)
        self.assertIn("places_track", H.SCHEMA_FIELDS)

    def test_km_and_stamps_are_not_facts(self):
        self.assertFalse(H.is_fact("place.km"))
        self.assertFalse(H.is_fact("places_checked"))
        self.assertFalse(H.is_fact("places_track"))
        self.assertTrue(H.is_fact("place.slug"))
        self.assertTrue(H.is_fact("place.basis"))
        self.assertTrue(H.is_fact("place.kind"))
        self.assertTrue(H.is_fact("place.source"))

    def test_a_km_only_change_needs_no_history(self):
        old = {"id": "x", "place": [{"kind": "range", "slug": "a", "basis": "track", "km": 10.0}]}
        new = {"id": "x", "place": [{"kind": "range", "slug": "a", "basis": "track", "km": 11.5}]}
        changed = H.changed_paths(old, new)
        self.assertEqual(changed, ["place.km"])
        self.assertEqual([p for p in changed if H.is_fact(p)], [])

    def test_schema_documents_every_place_field(self):
        with open(os.path.join(ROOT, "docs", "schema.md"), encoding="utf-8") as f:
            text = f.read()
        for name in H._TABLES["place"]:
            self.assertIn(f"`{name}`", text, name)
        for name in ("places_checked", "places_track"):
            self.assertIn(f"`{name}`", text, name)

    def test_facts_text_names_place(self):
        self.assertIn("place", H.FACTS_TEXT)
        self.assertIn("place.km", H.NOT_FACTS_TEXT)


if __name__ == "__main__":
    unittest.main()
