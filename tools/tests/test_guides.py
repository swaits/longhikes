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

    def test_new_fields_are_checked(self):
        self.assertEqual(check([dict(GOOD, edition="9th edition, 2021", where="Trip 25, page 149", link_is="author")]), [])
        self.assertTrue(check([dict(GOOD, edition=" ")]))
        self.assertTrue(check([dict(GOOD, where=3)]))
        self.assertTrue(check([dict(GOOD, link_is="shop")]))
        for kind in ("publisher", "author", "library", "seller"):
            self.assertEqual(check([dict(GOOD, link_is=kind)]), [])

    def test_a_purchase_must_say_what_it_is(self):
        bought = dict(GOOD, access="purchase")
        self.assertTrue(check([bought]))
        for field, value in (("isbn", "978-0-89997-884-0"), ("edition", "2nd edition"), ("link_is", "seller")):
            self.assertEqual(check([dict(bought, **{field: value})]), [], field)
        self.assertEqual(check([dict(GOOD)]), [])  # a free guide needs none


if __name__ == "__main__":
    unittest.main()
