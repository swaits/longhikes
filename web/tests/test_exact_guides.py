"""A route's guide card and notice say exactly what to get, and a bookshop is not an "official site"."""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from olt import site, trail  # noqa: E402
from test_pages import sample_record  # noqa: E402

BOOK = {"title": "Sierra South: Backcountry Trips in California's Sierra Nevada", "author": "Elizabeth Wenk",
        "access": "purchase", "url": "https://shop.example/sierra-south/", "format": "book",
        "publisher": "Wilderness Press", "isbn": "978-0-89997-884-0", "edition": "9th edition, 2021",
        "where": "Trip 25, page 149", "link_is": "publisher"}


def route(guide=None, **extra):
    rec = sample_record("R Route")
    rec["derived"]["kind"] = "route"
    rec["kind"] = "route"
    rec["route"] = {"creator": "A", "line_policy": "sold"}
    rec["guide"] = [dict(BOOK, **(guide or {}))]
    rec.update(extra)
    return rec


def body(rec):
    return trail.render(rec, site.Site("N", "T"))[2]


class ExactGuideTest(unittest.TestCase):
    def test_card_lines_in_order_and_only_when_present(self):
        card = trail.guide_card(BOOK, 1)
        order = ["Author", "Edition", "Where in it", "Publisher", "ISBN", "Form"]
        at = [card.index(f"<dt>{label}</dt>") for label in order]
        self.assertEqual(at, sorted(at))
        self.assertIn("9th edition, 2021", card)
        bare = trail.guide_card({"title": "T", "author": "A", "access": "free", "url": "https://x.example/"}, 1)
        for label in ("Edition", "Where in it", "Publisher", "ISBN", "Form", "Price"):
            self.assertNotIn(f"<dt>{label}</dt>", bare)

    def test_link_words_come_from_link_is(self):
        words = {"publisher": "The publisher's page for this book", "author": "The author's page for this guide",
                 "library": "Library record (out of print)", "seller": "Bookseller's page"}
        for kind, text in words.items():
            card = trail.guide_card(dict(BOOK, link_is=kind), 1)
            self.assertTrue(text in card or text.replace("'", "&#x27;") in card, kind)
        old = {k: v for k, v in BOOK.items() if k != "link_is"}
        self.assertIn("Guide page on shop.example", trail.guide_card(old, 1))

    def test_notice_names_the_guide(self):
        page = body(route())
        self.assertIn("The route is in Sierra South: Backcountry Trips in California", page)
        self.assertIn("(9th edition, 2021), trip 25, page 149.", page)
        self.assertIn("Where to get Sierra South", page)
        self.assertNotIn("See where to get the route", page)

    def test_notice_without_where_or_edition(self):
        self.assertEqual(trail.guide_sentence({"title": "T"}), "The route is in T.")
        self.assertEqual(trail.guide_sentence({"title": "T", "edition": "2004"}), "The route is in T (2004).")
        self.assertEqual(trail.guide_sentence({"title": "T, 2nd Edition", "edition": "2nd edition", "where": "Chapter 8"}),
                         "The route is in T, 2nd Edition, chapter 8.")
        self.assertEqual(trail.guide_sentence({"title": "T", "where": "The whole guide is this route"}),
                         "The whole of T is this route.")

    def test_official_site_that_is_the_guides_shop_is_not_official(self):
        rec = route(hike={"official_url": "https://shop.example/sierra-south"})
        self.assertEqual(trail.official_link(rec), ("https://shop.example/sierra-south",
                                                    "The publisher's page for this book"))

    def test_a_publishers_host_is_not_official_either(self):
        rec = route(guide={"link_is": "library", "url": "https://lib.example/b"},
                    hike={"official_url": "https://shop.example/sierra-south/"})
        rec["guide"].append(dict(BOOK, edition="10th edition"))
        self.assertEqual(trail.official_link(rec)[1], "The publisher's page for this book")
        rec = route(hike={"official_url": "https://shop.example/wilderness-press/"})
        self.assertEqual(trail.official_link(rec)[1], "The publisher's page for this book")

    def test_the_authors_own_route_page_stays_official(self):
        rec = route(hike={"official_url": "https://author.example/route"})
        self.assertEqual(trail.official_link(rec), ("https://author.example/route", "Official site"))
        rec["guide"] = [dict(BOOK, access="free", url="https://author.example/route", link_is="author")]
        self.assertEqual(trail.official_link(rec)[1], "Official site")


if __name__ == "__main__":
    unittest.main()
