"""Tests for tools/season_classify.py.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import refresh  # noqa: E402
import season  # noqa: E402
import season_classify as C  # noqa: E402
import validate as V  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
