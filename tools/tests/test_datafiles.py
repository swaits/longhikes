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

    def test_kind_is_a_person_people_or_an_organisation(self):
        self.assertEqual(run(C.check_author_entries, [dict(AUTHOR, kind="organisation")], self.ROUTES), [])
        self.assertEqual(run(C.check_author_entries, [dict(AUTHOR, kind="people")], self.ROUTES), [])
        self.assertTrue(any("kind" in e for e in run(C.check_author_entries, [dict(AUTHOR, kind="other")], self.ROUTES)))
        self.assertTrue(any("kind" in e for e in run(C.check_author_entries, [dict(AUTHOR, kind="band")], self.ROUTES)))


BIO = " ".join(["Jo Walker worked out a long route across the hills and wrote a guide to it."] * 4)
ABOUT = dict(AUTHOR, url="https://jowalker.example/", summary="Jo Walker is a hiker who works out long routes.",
             bio=BIO, checked="2026-11-17", source=[{"url": "https://jowalker.example/about/", "publisher": "Jo Walker"}])


class AuthorAboutTest(unittest.TestCase):
    ROUTES = AuthorTest.ROUTES

    def errs(self, **changes):
        entry = dict(ABOUT, **changes)
        for k in [k for k, v in changes.items() if v is None]:
            del entry[k]
        return run(C.check_author_entries, [entry], self.ROUTES)

    def has(self, text, **changes):
        errs = self.errs(**changes)
        self.assertTrue(any(text in e for e in errs), errs)

    def test_a_full_entry_passes_and_the_fields_are_optional(self):
        self.assertEqual(self.errs(), [])
        self.assertEqual(run(C.check_author_entries, [AUTHOR], self.ROUTES), [])
        self.assertEqual(self.errs(bio=None), [])  # a summary alone, with its source and date
        self.assertEqual(self.errs(summary=None), [])  # a bio alone
        self.assertEqual(self.errs(checked=__import__("datetime").date(2026, 11, 17)), [])  # a TOML date

    def test_summary_length_and_name(self):
        self.has("at most 160", summary="Jo Walker " + "walks far. " * 20)
        self.assertEqual(self.errs(summary="Jo Walker " + "x" * (160 - len("Jo Walker ") - 1) + "."), [])
        self.has("must begin with the name", summary="A hiker, Jo Walker, works out routes.")
        self.has("one sentence", summary="Jo Walker works out routes")
        self.has("dash", summary="Jo Walker — a hiker.")

    def test_bio_length(self):
        self.has("words", bio="Jo Walker hikes.")
        self.has("words", bio=" ".join(["word"] * 131) + ".")
        self.assertEqual(self.errs(bio=" ".join(["word"] * 130) + "."), [])
        self.assertEqual(self.errs(bio=" ".join(["word"] * 40) + "."), [])
        self.has("one paragraph", bio=BIO + "\n\n" + BIO[:40] + ".")

    def test_sources_and_date_are_required_with_words(self):
        self.has("no [[author.source]]", source=None)
        self.has("source must be", source=[])
        self.has("no checked date", checked=None)
        self.has("must be a date", checked="17 November 2026")
        self.has("not a real date", checked="2026-02-30")
        self.has("in the future", checked="2999-01-01")
        self.has("source 1 is missing required field publisher", source=[{"url": "https://x.example/"}])
        self.has("http", source=[{"url": "x.example", "publisher": "X"}])
        self.has("source twice", source=ABOUT["source"] * 2)
        self.has("but no summary or bio", summary=None, bio=None)

    def test_a_pair_of_people_may_carry_the_words(self):
        pair = dict(ABOUT, name="Jo and Sam", credits=["Jo and Sam"], kind="people",
                    summary="Jo and Sam are a couple who hike long routes together.")
        self.assertEqual(run(C.check_author_entries, [pair], [("r3", "Jo and Sam")]), [])

    def test_nothing_biographical_on_an_organisation(self):
        org = dict(ABOUT, kind="organisation")
        errs = run(C.check_author_entries, [org], self.ROUTES)
        for k in ("summary", "bio", "checked", "source"):
            self.assertTrue(any(f"organisation: {k} is for people only" in e for e in errs), (k, errs))
        self.assertEqual(run(C.check_author_entries, [dict(AUTHOR, kind="organisation", url="https://club.example/")], self.ROUTES), [])
        self.assertTrue(run(C.check_author_entries, [dict(AUTHOR, kind="organisation", url="club.example")], self.ROUTES))
        self.assertTrue(run(C.check_author_entries, [dict(AUTHOR, kind="organisation", motto="x")], self.ROUTES))

    def test_urls_and_unknown_keys(self):
        self.has("url must be an http(s) address", url="jowalker.example")
        self.has("unknown field", nickname="Jo")
        self.has("unknown field", source=[{"url": "https://x.example/", "publisher": "X", "note": "n"}])


class RealFilesTest(unittest.TestCase):
    def test_the_repository_files_pass(self):
        import validate as V
        trails = [V.load_toml(os.path.join(ROOT, d, "trail.toml")) for d in V.build_index.trail_dirs(ROOT)]
        errors = []
        C.check_datafiles(ROOT, trails, errors)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
