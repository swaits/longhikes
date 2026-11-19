"""Tests for trail-numbers.txt: the validator's check, build_index's append, and the append-only
check in tools/check_history.py. No network. Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import os
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)

import check_history as C  # noqa: E402
import trail_numbers as N  # noqa: E402

HEAD = "# a comment\n# another\n"


class ParseTest(unittest.TestCase):
    def test_numbers_are_line_indexes_among_the_id_lines(self):
        ids, problems = N.parse(HEAD + "a\nb-c\nd2\n")
        self.assertEqual((ids, problems), (["a", "b-c", "d2"], []))

    def test_malformed_lines_are_problems(self):
        for text in (HEAD + "a\n\nb\n",            # a blank line
                     HEAD + "a\nB\n",              # upper case
                     HEAD + "a\n b\n",             # leading space
                     HEAD + "a\nb \n",             # trailing space
                     HEAD + "a\nb--c\n",           # double hyphen
                     HEAD + "a\n-b\n",
                     HEAD + "a\nb c\n",
                     HEAD + "a\n# late comment\nb\n",
                     HEAD + "a\nb"):               # no newline at the end
            self.assertTrue(N.parse(text)[1], repr(text))

    def test_an_id_twice_is_a_problem(self):
        ids, problems = N.parse("a\nb\na\n")
        self.assertEqual(ids, ["a", "b"])
        self.assertEqual(len(problems), 1)
        self.assertIn("already on line 1", problems[0])


class Root:
    def __init__(self, test, text=None):
        self.dir = tempfile.TemporaryDirectory()
        test.addCleanup(self.dir.cleanup)
        self.root = self.dir.name
        if text is not None:
            self.write(text)

    def write(self, text):
        with open(os.path.join(self.root, N.FILE), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    def read(self):
        with open(os.path.join(self.root, N.FILE), encoding="utf-8") as f:
            return f.read()


class ValidatorTest(unittest.TestCase):
    def errors(self, text, ids):
        errors = []
        N.check(Root(self, text).root, ids, errors)
        return errors

    def test_complete_passes(self):
        self.assertEqual(self.errors(HEAD + "a\nb\n", ["a", "b"]), [])

    def test_a_record_with_no_line_fails(self):
        errors = self.errors(HEAD + "a\n", ["a", "b"])
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("b: has no line"))

    def test_a_retired_number_is_not_an_error(self):
        self.assertEqual(self.errors(HEAD + "a\ngone\nb\n", ["a", "b"]), [])

    def test_a_duplicate_and_a_malformed_line_fail(self):
        self.assertTrue(self.errors(HEAD + "a\na\n", ["a"]))
        self.assertTrue(self.errors(HEAD + "a\nNot An Id\n", ["a"]))

    def test_a_missing_file_fails(self):
        errors = []
        N.check(Root(self).root, ["a"], errors)
        self.assertTrue(errors)


class AppendTest(unittest.TestCase):
    def test_creates_a_seeded_file_in_alphabetical_order(self):
        r = Root(self)
        self.assertEqual(N.append(r.root, ["c", "a", "b"]), ["a", "b", "c"])
        self.assertEqual(N.parse(r.read()), (["a", "b", "c"], []))
        self.assertTrue(r.read().startswith("# "))

    def test_appends_only_the_missing_in_sorted_order_and_leaves_lines_alone(self):
        text = HEAD + "m\ngone\na\n"
        r = Root(self, text)
        self.assertEqual(N.append(r.root, ["m", "a", "z", "d"]), ["d", "z"])
        self.assertEqual(r.read(), text + "d\nz\n")

    def test_second_run_changes_nothing(self):
        r = Root(self, HEAD + "a\n")
        N.append(r.root, ["a", "b"])
        before = r.read()
        self.assertEqual(N.append(r.root, ["a", "b"]), [])
        self.assertEqual(r.read(), before)

    def test_a_retired_trail_keeps_its_line(self):
        r = Root(self, HEAD + "a\nb\nc\n")
        N.append(r.root, ["a", "c", "d"])
        self.assertEqual(N.parse(r.read())[0], ["a", "b", "c", "d"])


class OnlyAppendedTest(unittest.TestCase):
    OLD = HEAD + "a\nb\nc\n"

    def test_appending_is_allowed(self):
        self.assertEqual(N.only_appended(self.OLD, self.OLD + "d\ne\n"), [])

    def test_the_header_is_free(self):
        self.assertEqual(N.only_appended(self.OLD, "# new words\na\nb\nc\nd\n"), [])

    def test_changed_removed_and_reordered_fail(self):
        self.assertTrue(N.only_appended(self.OLD, HEAD + "a\nx\nc\n"))        # changed
        self.assertTrue(N.only_appended(self.OLD, HEAD + "a\nc\n"))           # removed in the middle
        self.assertTrue(N.only_appended(self.OLD, HEAD + "a\nb\n"))           # removed at the end
        self.assertTrue(N.only_appended(self.OLD, HEAD + "a\nc\nb\n"))        # reordered
        self.assertTrue(N.only_appended(self.OLD, HEAD + "z\na\nb\nc\n"))     # inserted at the front
        self.assertTrue(N.only_appended(self.OLD, ""))                        # emptied


class GitCheckTest(unittest.TestCase):
    """C.check_numbers against a scratch repository."""

    def repo(self, text):
        r = Root(self, text)
        self.git(r.root, "init", "-q")
        self.git(r.root, "add", "-A")
        self.git(r.root, "commit", "-q", "-m", "base")
        mb = self.git(r.root, "rev-parse", "HEAD").strip()
        return r, mb

    @staticmethod
    def git(root, *args):
        done = subprocess.run(["git", "-C", root, "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                              capture_output=True, text=True, check=True)
        return done.stdout

    def test_append_passes_and_edits_fail(self):
        r, mb = self.repo(HEAD + "a\nb\n")
        self.assertEqual(C.check_numbers(r.root, mb), [])
        r.write(HEAD + "a\nb\nc\n")
        self.assertEqual(C.check_numbers(r.root, mb), [])
        r.write(HEAD + "b\na\n")
        self.assertTrue(C.check_numbers(r.root, mb))
        r.write(HEAD + "a\n")
        self.assertTrue(C.check_numbers(r.root, mb))
        os.unlink(os.path.join(r.root, N.FILE))
        self.assertTrue(C.check_numbers(r.root, mb))

    def test_a_base_without_the_registry_allows_introducing_it(self):
        r, mb = self.repo(HEAD + "a\n")
        self.git(r.root, "rm", "-q", "--cached", N.FILE)
        self.git(r.root, "commit", "-q", "-m", "without")
        mb = self.git(r.root, "rev-parse", "HEAD").strip()
        self.assertEqual(C.check_numbers(r.root, mb), [])


class RepositoryTest(unittest.TestCase):
    def test_this_repository_has_a_number_for_every_record(self):
        import build_index
        root = os.path.dirname(TOOLS)
        errors = []
        N.check(root, build_index.trail_dirs(root), errors)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
