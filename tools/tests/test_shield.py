"""Tests for the [shield] checks in tools/validate.py: no network.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import validate as V  # noqa: E402

WITH_FILE = {"status": "use-real-logo", "logo_source": "https://example.org/logo.png", "contact": "Club",
             "note": "The club's crest.", "logo_file": "shield.png", "logo_owner": "Club"}
NO_EMBLEM = {"status": "no-logo-exists", "logo_source": "", "contact": "", "note": "Looked at https://example.org/; no crest.",
             "logo_file": "", "logo_owner": ""}
NOT_FOUND = dict(NO_EMBLEM, status="logo-not-found", note="A sign shows one; no artwork found at https://example.org/.")


def check(shield, files=()):
    with tempfile.TemporaryDirectory() as d:
        for f in files:
            open(os.path.join(d, f), "wb").write(b"x")
        errors = []
        V.check_shield("t", shield, d, errors)
        return errors


class ShieldStatusTest(unittest.TestCase):
    def test_the_three_states_pass(self):
        self.assertEqual(check(WITH_FILE, ["shield.png"]), [])
        self.assertEqual(check(NO_EMBLEM), [])
        self.assertEqual(check(NOT_FOUND), [])

    def test_status_is_required(self):
        errors = check({k: v for k, v in NO_EMBLEM.items() if k != "status"})
        self.assertEqual(len(errors), 1)
        self.assertIn("shield.status", errors[0])

    def test_status_must_be_one_of_the_three(self):
        for bad in ("no-logo", "logo not found", "use-logo", "none"):
            errors = check(dict(NO_EMBLEM, status=bad))
            self.assertTrue(any("not one of" in e for e in errors), bad)

    def test_use_real_logo_needs_a_file(self):
        errors = check(dict(WITH_FILE, logo_file=""))
        self.assertTrue(any("use-real-logo" in e and "names no file" in e for e in errors), errors)

    def test_use_real_logo_needs_the_file_on_disk(self):
        errors = check(WITH_FILE)
        self.assertTrue(any("does not exist" in e for e in errors), errors)

    def test_logo_file_name_is_limited(self):
        errors = check(dict(WITH_FILE, logo_file="crest.jpg"), ["crest.jpg"])
        self.assertTrue(any("shield.svg or shield.png" in e for e in errors), errors)

    def test_a_file_on_disk_means_use_real_logo(self):
        for status in ("no-logo-exists", "logo-not-found"):
            errors = check(dict(NO_EMBLEM, status=status), ["shield.svg"])
            self.assertTrue(any("is use-real-logo" in e for e in errors), (status, errors))
            errors = check(dict(NO_EMBLEM, status=status, logo_file="shield.png"), ["shield.png"])
            self.assertTrue(any("is use-real-logo" in e for e in errors), (status, errors))

    def test_a_trail_without_a_file_says_where_it_looked(self):
        for base in (NO_EMBLEM, NOT_FOUND):
            errors = check(dict(base, note="  "))
            self.assertEqual(len(errors), 1, base["status"])
            self.assertIn("shield.note", errors[0])

    def test_logo_owner_is_still_required_with_a_file(self):
        errors = check(dict(WITH_FILE, logo_owner=""), ["shield.png"])
        self.assertTrue(any("logo_owner" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
