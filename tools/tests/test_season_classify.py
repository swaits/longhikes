"""Tests for tools/season_classify.py.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import csv
import os
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import refresh  # noqa: E402
import season  # noqa: E402
import season_classify as C  # noqa: E402
import validate as V  # noqa: E402
import test_refresh as TR  # noqa: E402


def rec(**kw):
    base = {
        "hike": {
            "season": "June to September",
            "months": [6, 7, 8, 9],
            "source": [{"url": "https://www.example.org/trail",
                        "publisher": "Example Publisher",
                        "facts": ["season", "months"]}],
        }
    }
    base.update(kw)
    return base


class SuggestBasisTest(unittest.TestCase):
    def test_official_site_host_is_primary(self):
        r = rec()
        r["hike"]["official_url"] = "https://example.org/trail-page"
        basis, reason = C.suggest_basis(r)
        self.assertEqual(basis, "primary")
        self.assertIn("official_url", reason)

    def test_source_publisher_host_is_primary(self):
        r = rec(source={"publisher": "X", "publisher_url": "https://www.example.org/"})
        basis, reason = C.suggest_basis(r)
        self.assertEqual(basis, "primary")
        self.assertIn("publisher_url", reason)

    def test_route_author_page_is_primary(self):
        r = rec(kind="route", route={"creator": "A Hiker"},
                guide=[{"title": "G", "url": "https://example.org/guide", "link_is": "author"}])
        basis, reason = C.suggest_basis(r)
        self.assertEqual(basis, "primary")
        self.assertIn("route author", reason)

    def test_route_creator_words_host_is_primary(self):
        r = rec(kind="route", route={"creator": "A Hiker",
                                     "creator_words_url": "https://example.org/words"})
        basis, _ = C.suggest_basis(r)
        self.assertEqual(basis, "primary")

    def test_two_unrelated_publishers_are_sources(self):
        r = rec()
        r["hike"]["source"] = [
            {"url": "https://a.example/t", "publisher": "Guide A", "facts": ["season"]},
            {"url": "https://b.example/t", "publisher": "Guide B", "facts": ["season", "months"]},
        ]
        basis, reason = C.suggest_basis(r)
        self.assertEqual(basis, "sources")
        self.assertTrue(reason)

    def test_one_unrelated_page_is_source(self):
        basis, reason = C.suggest_basis(rec())
        self.assertEqual(basis, "source")
        self.assertTrue(reason)

    def test_www_and_bare_host_are_the_same_host(self):
        r = rec()
        r["hike"]["official_url"] = "https://example.org/x"
        r["hike"]["source"][0]["url"] = "https://www.example.org/y"
        self.assertEqual(C.suggest_basis(r)[0], "primary")

    def test_non_route_guide_host_is_not_primary(self):
        r = rec(guide=[{"title": "G", "url": "https://example.org/guide", "link_is": "author"}])
        self.assertEqual(C.suggest_basis(r)[0], "source")


class TableTest(unittest.TestCase):
    def test_table_covers_every_record_with_a_season(self):
        rows = C.table(V.ROOT)
        expected = 0
        for tid in refresh.trail_ids(V.ROOT):
            r = refresh.load_toml(os.path.join(V.ROOT, tid, "trail.toml"))
            if (r.get("hike") or {}).get("season"):
                expected += 1
        self.assertEqual(expected, 109)
        self.assertEqual(len(rows), expected)
        for row in rows:
            self.assertIn(row["suggested"], season.BASES)

    def test_table_has_a_reason_for_every_row(self):
        for row in C.table(V.ROOT):
            self.assertTrue(row["reason"], row["id"])
            self.assertTrue(row["season"], row["id"])


class ProposalsTest(unittest.TestCase):
    def test_a_proposal_collects_cleanly_and_applies(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = TR.make_repo(tmp)
        path = os.path.join(root, "aaa", "trail.toml")
        text = TR.read(root, "aaa/trail.toml")
        text = text.replace('official_url = "https://example.org/aaa/"\n',
                            'official_url = "https://example.org/aaa/"\n'
                            'season = "June to September"\nmonths = [6, 7, 8, 9]\n', 1)
        text += ('\n[[hike.source]]\nurl = "https://example.org/aaa/season"\n'
                 'publisher = "Example Club"\nfacts = ["season", "months"]\n')
        TR.write(path, text)
        d = os.path.join(tmp, "stage")
        os.makedirs(os.path.join(d, "season"))
        reviewed = os.path.join(d, "season", "classification.reviewed.csv")
        with open(reviewed, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "basis", "note"])
            w.writerow(["aaa", "primary", ""])
        self.assertEqual(C.proposals(root, reviewed, d), 1)
        code, out = TR.main(root, "--dir", d, "collect")
        self.assertEqual(code, 0, out)
        coll = refresh.load_toml(os.path.join(d, "collected.toml"))
        props = coll["proposal"]
        self.assertEqual(len(props), 1)
        self.assertEqual(props[0]["status"], "proposed", out)
        with open(os.path.join(d, "owner.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["pid", "digest", "decision", "note"])
            w.writerow([props[0]["pid"], props[0]["digest"], "accept", ""])
        code, out = TR.main(root, "--dir", d, "collect")
        self.assertEqual(code, 0, out)
        code, out = TR.main(root, "--dir", d, "apply")
        self.assertEqual(code, 0, out)
        rec_after = refresh.load_toml(path)
        self.assertEqual(rec_after["hike"]["season_basis"], "primary")
        last = rec_after["history"][-1]
        self.assertEqual(last["fields"], ["hike.season_basis"])

    def test_reviewed_rows_must_name_a_known_basis(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        reviewed = os.path.join(tmp, "r.csv")
        with open(reviewed, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "basis"])
            w.writerow(["aaa", "estimate"])
        with self.assertRaises(ValueError):
            C.read_reviewed(reviewed)


if __name__ == "__main__":
    unittest.main()
