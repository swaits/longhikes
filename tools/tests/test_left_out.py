"""Tests for the left-out.toml checks in tools/validate.py: no network.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import validate as V  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GOOD = {
    "id": "example-trail",
    "name": "Example Trail",
    "country": "US",
    "regions": ["PA"],
    "length_mi": 42.0,
    "length_km": 68,
    "reason": "below-floor",
    "note": "The holder gives it as 42 miles, below the 50 mile floor.",
    "source_url": "https://example.org/example-trail",
    "decided": "2026-11-14",
    "was_listed": False,
}
WAITING = dict(
    GOOD,
    id="waiting-trail",
    name="Waiting Trail",
    reason="waiting",
    waiting_for="The holder builds enough of it to walk through.",
)
TRAILS = [{"id": "long-trail", "name": "Long Trail (Vermont)"}]


def check(entries, trails=TRAILS):
    errors = []
    V.check_left_out_entries(entries, trails, errors)
    return errors


class LeftOutTest(unittest.TestCase):
    def test_good_entries_are_valid(self):
        self.assertEqual(check([GOOD, WAITING]), [])

    def test_every_required_field(self):
        for field in ("id", "name", "country", "regions", "reason", "note",
                      "decided", "was_listed"):
            entry = {k: v for k, v in GOOD.items() if k != field}
            self.assertTrue(check([entry]), field)
            self.assertTrue(check([dict(GOOD, **{field: ""})]), field)
            self.assertTrue(check([dict(GOOD, **{field: "  "})]), field)

    def test_unknown_key(self):
        self.assertTrue(any("unknown field rank" in e
                            for e in check([dict(GOOD, rank=1)])))

    def test_unknown_reason(self):
        errors = check([dict(GOOD, reason="too-short")])
        self.assertTrue(any("reason" in e for e in errors))

    def test_outside_us_canada(self):
        ok = dict(GOOD, reason="outside-us-canada", country="DM", regions=["Dominica"])
        self.assertEqual(check([ok]), [])
        self.assertTrue(any("country" in e for e in check([dict(ok, country="US")])))
        self.assertTrue(any("country" in e for e in check([dict(ok, country="Dominica")])))

    def test_bad_country_and_region(self):
        self.assertTrue(any("country" in e for e in check([dict(GOOD, country="MX")])))
        self.assertTrue(any("region" in e for e in check([dict(GOOD, regions=["XX"])])))
        self.assertTrue(any("regions" in e for e in check([dict(GOOD, regions="PA")])))

    def test_bad_date(self):
        for bad in ("2026-11-31", "November 2026", "2026/11/14"):
            self.assertTrue(any("decided" in e
                                for e in check([dict(GOOD, decided=bad)])), bad)

    def test_source_url_must_be_http(self):
        self.assertTrue(any("http(s)" in e
                            for e in check([dict(GOOD, source_url="ftp://example.org/a")])))

    def test_source_url_may_be_missing_only_when_the_note_says_why(self):
        entry = {k: v for k, v in GOOD.items() if k != "source_url"}
        self.assertTrue(check([entry]))
        said = dict(entry, note="No page publishes it as one trail, so there is no source page to give.")
        self.assertEqual(check([said]), [])

    def test_waiting_needs_waiting_for_and_others_must_not_have_it(self):
        entry = {k: v for k, v in WAITING.items() if k != "waiting_for"}
        self.assertTrue(any("waiting_for" in e for e in check([entry])))
        self.assertTrue(any("waiting_for" in e
                            for e in check([dict(GOOD, waiting_for="Something changes.")])))

    def test_was_listed_must_be_a_boolean(self):
        self.assertTrue(any("was_listed" in e
                            for e in check([dict(GOOD, was_listed="yes")])))

    def test_lengths_must_agree_and_be_positive(self):
        self.assertTrue(check([dict(GOOD, length_mi=42.0, length_km=420)]))
        self.assertTrue(check([dict(GOOD, length_mi=-1)]))
        no_length = {k: v for k, v in GOOD.items() if not k.startswith("length_")}
        self.assertEqual(check([no_length]), [])

    def test_entries_must_be_sorted_by_name(self):
        errors = check([WAITING, GOOD])
        self.assertTrue(any("sorted" in e for e in errors))

    def test_no_duplicate_id_or_name(self):
        self.assertTrue(any("duplicate" in e for e in check([GOOD, dict(GOOD)])))

    def test_no_entry_matches_a_listed_trail(self):
        by_id = dict(GOOD, id="long-trail")
        self.assertTrue(any("listed" in e for e in check([by_id])))
        by_name = dict(GOOD, name="Long Trail (Vermont)")
        self.assertTrue(any("listed" in e for e in check([by_name])))

    def test_the_real_file_passes(self):
        errors = []
        trails = []
        import tomllib
        for name in sorted(os.listdir(ROOT)):
            path = os.path.join(ROOT, name, "trail.toml")
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    rec = tomllib.load(f)
                trails.append({"id": rec.get("id", name), "name": rec.get("name", "")})
        V.check_left_out(ROOT, trails, errors)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
