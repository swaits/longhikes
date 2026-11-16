"""[[guide]] on a trail that is not a route: its holder's own guide or map set."""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import validate as V  # noqa: E402

GOOD = {"title": "Guide and Map Set", "author": "An Association", "access": "free",
        "url": "https://example.org/mapset.pdf", "format": "PDF"}


def check(guides):
    errors = []
    V.check_guides("t", guides, errors)
    return errors


class GuideTest(unittest.TestCase):
    def test_no_guide_is_fine(self):
        self.assertEqual(check(None), [])

    def test_a_complete_guide_passes(self):
        self.assertEqual(check([dict(GOOD)]), [])

    def test_each_required_field(self):
        for field in ("title", "author", "access", "url"):
            errors = check([{k: v for k, v in GOOD.items() if k != field}])
            self.assertTrue(errors, field)

    def test_access_and_url_are_checked(self):
        self.assertTrue(check([dict(GOOD, access="gift")]))
        self.assertTrue(check([dict(GOOD, url="ftp://example.org/x")]))

    def test_price_needs_its_date(self):
        self.assertTrue(check([dict(GOOD, price="$5")]))
        self.assertEqual(check([dict(GOOD, price="$5", price_checked="2026-11-16")]), [])


if __name__ == "__main__":
    unittest.main()
