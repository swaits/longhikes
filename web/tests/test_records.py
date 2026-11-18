import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from olt import records  # noqa: E402


class RecordsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recs = records.load_records()

    def test_counts(self):
        self.assertEqual(len(self.recs), 200)
        self.assertEqual(sum(r["derived"]["kind"] == "route" for r in self.recs), 58)
        self.assertEqual(sum(r["derived"]["kind"] == "designated" for r in self.recs), 142)
        self.assertEqual(sum(r["derived"]["has_line"] for r in self.recs), 122)

    def test_sorted_by_id(self):
        ids = [r["id"] for r in self.recs]
        self.assertEqual(ids, sorted(ids))

    def test_derived_fields(self):
        by_id = {r["id"]: r for r in self.recs}
        ct = by_id["colorado-trail"]
        self.assertEqual(ct["derived"]["status"], "included")
        self.assertEqual(ct["derived"]["length_mi"], 486)
        self.assertEqual(sorted(ct["derived"]["files"]["extracts"]), ["osm", "usfs"])
        self.assertEqual(ct["derived"]["files"]["line"], "colorado-trail/line.geojson")
        self.assertEqual(ct["name"], "Colorado Trail")  # TOML fields unchanged

    def test_status_matches_csv(self):
        import csv
        path = os.path.join(records.ROOT, "trails.csv")
        with open(path, encoding="utf-8", newline="") as f:
            status = {row["id"]: row["status"] for row in csv.DictReader(f)}
        for r in self.recs:
            self.assertEqual(r["derived"]["status"], status[r["id"]])

    def test_line_file_exists_when_has_line(self):
        for r in self.recs:
            self.assertEqual(r["derived"]["has_line"], "line" in r["derived"]["files"])


if __name__ == "__main__":
    unittest.main()
