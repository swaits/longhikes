"""Tests for the checks on glossary.toml, collections.toml and authors.toml (tools/check_datafiles.py).

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import check_datafiles as C  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TERM = {"id": "loop", "term": "Loop", "definition": "A trail that finishes where it starts.", "see": ["/lists/loops/"]}
COLLECTION = {"id": "set", "name": "Set", "members": ["a", "b"], "definition": "Two trails.",
              "source_url": "https://example.org/", "source_publisher": "Someone"}
AUTHOR = {"name": "Jo Walker", "credits": ["Jo Walker", "Jo Walker and Sam"]}


def run(fn, *args, **kw):
    errors = []
    fn(*args, errors, **kw)
    return errors


class GlossaryTest(unittest.TestCase):
    def test_a_good_entry_passes(self):
        self.assertEqual(run(C.check_glossary_entries, [TERM]), [])

    def test_duplicates_and_missing_fields(self):
        errs = run(C.check_glossary_entries, [TERM, dict(TERM, term="Other")])
        self.assertTrue(any("duplicate id" in e for e in errs))
        errs = run(C.check_glossary_entries, [{"id": "x", "term": "X"}])
        self.assertTrue(any("missing required field definition" in e for e in errs))

    def test_dashes_full_stop_and_paths(self):
        self.assertTrue(any("dash" in e for e in run(C.check_glossary_entries, [dict(TERM, definition="A trail — a loop.")])))
        self.assertTrue(any("full stop" in e for e in run(C.check_glossary_entries, [dict(TERM, definition="A loop")])))
        self.assertTrue(any("site paths" in e for e in run(C.check_glossary_entries, [dict(TERM, see=["lists/loops"])])))
        self.assertTrue(any("http" in e for e in run(C.check_glossary_entries, [dict(TERM, source_url="ftp://x")])))

    def test_unknown_field(self):
        self.assertTrue(any("unknown field" in e for e in run(C.check_glossary_entries, [dict(TERM, extra="x")])))


class CollectionTest(unittest.TestCase):
    def test_good(self):
        self.assertEqual(run(C.check_collection_entries, [COLLECTION], {"a", "b"}), [])

    def test_members_must_be_records(self):
        errs = run(C.check_collection_entries, [COLLECTION], {"a"})
        self.assertTrue(any("member b is not a trail" in e for e in errs))

    def test_two_members_at_least_and_no_repeat(self):
        self.assertTrue(run(C.check_collection_entries, [dict(COLLECTION, members=["a"])], {"a"}))
        self.assertTrue(any("repeats" in e for e in run(C.check_collection_entries, [dict(COLLECTION, members=["a", "a"])], {"a"})))

    def test_source_is_required(self):
        bad = dict(COLLECTION)
        del bad["source_url"]
        self.assertTrue(any("source_url" in e for e in run(C.check_collection_entries, [bad], {"a", "b"})))


class AuthorTest(unittest.TestCase):
    ROUTES = [("r1", "Jo Walker"), ("r2", "Jo Walker and Sam")]

    def test_good(self):
        self.assertEqual(run(C.check_author_entries, [AUTHOR], self.ROUTES), [])

    def test_a_credit_must_be_on_a_route(self):
        errs = run(C.check_author_entries, [AUTHOR], self.ROUTES[:1])
        self.assertTrue(any("not the route.creator of any route" in e for e in errs))

    def test_a_credit_may_name_two_authors(self):
        sam = {"name": "Sam", "credits": ["Jo Walker and Sam"]}
        self.assertEqual(run(C.check_author_entries, [AUTHOR, sam], self.ROUTES), [])

    def test_a_credit_twice_for_one_author_and_a_name_not_in_it(self):
        errs = run(C.check_author_entries, [dict(AUTHOR, credits=["Jo Walker", "Jo Walker"])], self.ROUTES)
        self.assertTrue(any("given twice" in e for e in errs))
        errs = run(C.check_author_entries, [dict(AUTHOR, name="Someone Else")], self.ROUTES)
        self.assertTrue(any("does not contain the name" in e for e in errs))

    def test_one_credit_is_enough_and_none_is_not(self):
        self.assertEqual(run(C.check_author_entries, [dict(AUTHOR, credits=["Jo Walker"])], self.ROUTES), [])
        self.assertTrue(run(C.check_author_entries, [dict(AUTHOR, credits=[])], self.ROUTES))

    def test_kind_is_a_person_or_an_organisation(self):
        self.assertEqual(run(C.check_author_entries, [dict(AUTHOR, kind="organisation")], self.ROUTES), [])
        self.assertTrue(any("kind" in e for e in run(C.check_author_entries, [dict(AUTHOR, kind="band")], self.ROUTES)))


class RealFilesTest(unittest.TestCase):
    def test_the_repository_files_pass(self):
        import validate as V
        trails = [V.load_toml(os.path.join(ROOT, d, "trail.toml")) for d in V.build_index.trail_dirs(ROOT)]
        errors = []
        C.check_datafiles(ROOT, trails, errors)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
