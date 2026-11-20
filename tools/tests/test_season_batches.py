"""Tests for tools/season_batches.py and the researchers' brief.

Run from the repository root:
    python3 -m unittest discover tools/tests -p "test_season_batches.py"
"""
import math
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import refresh  # noqa: E402
import season_batches as B  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def write(root, tid, regions, season=None):
    os.makedirs(os.path.join(root, tid))
    hike = '[hike]\nshape = "loop"\n' + (f'season = "{season}"\nmonths = [6, 7]\n' if season else "")
    with open(os.path.join(root, tid, "trail.toml"), "w", encoding="utf-8") as f:
        f.write(f'name = "{tid}"\ncountry = "US"\nregions = {regions!r}\n\n'.replace("'", '"') + hike)


class BatchesTest(unittest.TestCase):
    def test_missing_ids_are_the_records_without_a_season(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "b-trail", ["CA"], season="June to July")
            write(root, "c-trail", ["CA"])
            write(root, "a-trail", ["WY"])
            self.assertEqual(B.missing_ids(root), ["a-trail", "c-trail"])

    def test_batches_are_at_most_the_size_and_cover_every_id_once(self):
        with tempfile.TemporaryDirectory() as root:
            for i in range(23):
                write(root, f"ca-{i:02d}", ["CA"])
            for i in range(7):
                write(root, f"pa-{i:02d}", ["PA"])
            got = B.batches(root, 10)
            flat = [x for b in got for x in b]
            self.assertEqual(sorted(flat), B.missing_ids(root))
            self.assertEqual(len(flat), len(set(flat)))
            self.assertTrue(all(0 < len(b) <= 10 for b in got))

    def test_a_batch_stays_in_one_region_group_unless_joined(self):
        with tempfile.TemporaryDirectory() as root:
            for i in range(23):
                write(root, f"ca-{i:02d}", ["CA"])
            for i in range(3):
                write(root, f"pa-{i:02d}", ["PA"])
            got = B.batches(root, 10)
            west = [b for b in got if all(x.startswith("ca-") for x in b)]
            self.assertEqual([len(b) for b in west], [10, 10])
            # the leftover 3 and the 3 Pennsylvania trails are each fewer than 5, so they share a batch
            mixed = [b for b in got if b not in west]
            self.assertEqual([len(b) for b in mixed], [6])

    def test_a_small_leftover_joins_a_neighbour_with_room(self):
        with tempfile.TemporaryDirectory() as root:
            for i in range(12):
                write(root, f"ca-{i:02d}", ["CA"])  # 10 and 2
            for i in range(4):
                write(root, f"or-{i:02d}", ["OR"])  # same group as CA
            got = B.batches(root, 10)
            self.assertEqual(sorted(len(b) for b in got), [6, 10])

    def test_real_count(self):
        n = len(B.missing_ids(ROOT))
        recs = [t for t in refresh.trail_ids(ROOT)
                if not (refresh.load_toml(os.path.join(ROOT, t, "trail.toml")).get("hike") or {}).get("season")]
        self.assertEqual(n, len(recs))
        got = B.batches(ROOT)
        # each region group can leave one part-full batch
        self.assertGreaterEqual(len(got), math.ceil(n / 10))
        self.assertLessEqual(len(got), math.ceil(n / 10) + len(B.REGION_GROUPS))
        self.assertEqual(sorted(x for b in got for x in b), B.missing_ids(ROOT))

    def test_every_region_code_in_the_records_has_a_group(self):
        for tid in refresh.trail_ids(ROOT):
            rec = refresh.load_toml(os.path.join(ROOT, tid, "trail.toml"))
            self.assertNotEqual(B.group_of(rec), B.OTHER, tid)

    def test_the_brief_names_what_a_researcher_records(self):
        text = open(os.path.join(ROOT, "docs", "season-research.md"), encoding="utf-8").read()
        for want in ("hike.season_basis", "hike.months", "quote", "not-found", "publisher"):
            self.assertIn(want, text)


if __name__ == "__main__":
    unittest.main()
