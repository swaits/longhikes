"""Tests for the [[link]] checks in tools/validate.py: no network, no numpy.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import validate as V  # noqa: E402

WIKI = {"title": "Appalachian Trail", "publisher": "LongTrailsWiki",
        "url": "https://www.longtrailswiki.net/wiki/Appalachian_Trail"}


def check(rec):
    errors = []
    V.check_links("t", rec, errors)
    return errors


class LinkTest(unittest.TestCase):
    def test_no_link_is_valid(self):
        self.assertEqual(check({}), [])

    def test_good_links_are_valid(self):
        other = {"title": "Appalachian Trail", "publisher": "Wikipedia",
                 "url": "https://en.wikipedia.org/wiki/Appalachian_Trail", "note": "A short history."}
        self.assertEqual(check({"link": [WIKI, other]}), [])

    def test_each_required_field(self):
        for field in ("title", "publisher", "url"):
            link = {k: v for k, v in WIKI.items() if k != field}
            self.assertTrue(any(f"missing {field}" in e for e in check({"link": [link]})), field)
            self.assertTrue(check({"link": [dict(WIKI, **{field: "  "})]}), field)

    def test_url_must_be_http(self):
        errors = check({"link": [dict(WIKI, url="ftp://example.org/a")]})
        self.assertTrue(any("http(s)" in e for e in errors))

    def test_unknown_key(self):
        self.assertTrue(any("unknown field rank" in e for e in check({"link": [dict(WIKI, rank=1)]})))

    def test_duplicate_url(self):
        twin = dict(WIKI, title="Again", url="http://www.longtrailswiki.net/wiki/Appalachian_Trail/")
        self.assertTrue(any("repeats" in e for e in check({"link": [WIKI, twin]})))

    def test_official_url_and_publisher_url_are_not_links(self):
        rec = {"hike": {"official_url": "https://www.nps.gov/appa/index.htm"},
               "source": {"publisher_url": "https://example.org/trail"}}
        for url in ("https://www.nps.gov/appa/index.htm/", "http://example.org/trail"):
            errors = check(dict(rec, link=[dict(WIKI, url=url)]))
            self.assertTrue(any("official site" in e for e in errors), url)

    def test_single_table_is_not_an_array(self):
        self.assertTrue(any("array of tables" in e for e in check({"link": dict(WIKI)})))


if __name__ == "__main__":
    unittest.main()
