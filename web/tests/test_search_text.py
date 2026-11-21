"""Tests for the words a search result shows (titles and descriptions), the heading order of
the place and list pages, and the links between trails (olt/trail.py, olt/regions.py,
olt/browse.py, olt/related.py, olt/leftout.py).

They render fixtures; they do not need the built site.
"""
import copy
import os
import re
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from olt import browse, common, home, layout, leftout, regions, related, site, trail  # noqa: E402
from test_hike import FULL_HIKE, fake  # noqa: E402

S = site.Site("Long Hikes", "A tagline", home_title="Long-Distance Hiking Trails of the US and Canada")
ROOM = common.title_room(S)


def gpx(rec):
    """Give a fixture the downloads a built record has."""
    rec["derived"]["has_line"] = True
    rec["derived"]["downloads"] = [
        {"file": "t.geojson", "format": "GeoJSON", "role": "main", "bytes": 1000, "note": "Full"},
        {"file": "t.gpx", "format": "GPX", "role": "main", "bytes": 500, "note": "Simplified"}]
    return rec


def at():
    rec = gpx(fake(1, km=3537, regions=["GA", "NC", "TN", "VA", "WV", "MD", "PA", "NJ", "NY", "CT", "MA", "VT", "NH", "ME"],
                   hike=dict(FULL_HIKE, days=[150, 210])))
    rec["name"] = "Appalachian National Scenic Trail"
    rec["common_name"] = "Appalachian Trail"
    rec["short_name"] = "AT"
    rec["derived"]["length_mi"] = 2198
    return rec


def levels(html_text):
    return [int(m) for m in re.findall(r"<h([1-6])[ >]", html_text)]


class TrailTitleTest(unittest.TestCase):
    def test_common_name_abbreviation_miles_and_what_the_page_offers(self):
        self.assertEqual(trail.page_title(at(), S), "Appalachian Trail (AT): 2,198 miles (3,537 km), map and GPX")

    def test_the_record_name_is_used_where_there_is_no_common_name(self):
        rec = gpx(fake(1, km=160))
        rec["name"] = "Hoosier Heritage Trail"
        del rec["short_name"]
        rec["derived"]["length_mi"] = 99
        self.assertEqual(trail.page_title(rec, S), "Hoosier Heritage Trail: 99 miles (160 km), map and GPX")

    def test_gpx_and_map_only_where_the_page_has_them(self):
        rec = at()
        rec["derived"]["has_line"] = False
        rec["derived"]["downloads"] = []
        title = trail.page_title(rec, S)
        self.assertNotIn("GPX", title)
        self.assertNotIn("map", title)
        self.assertIn("2,198 miles", title)

    def test_a_route_says_it_is_a_route(self):
        rec = fake(1, km=314)
        rec["name"], rec["short_name"] = "Sierra High Route", "SHR"
        rec["derived"]["kind"], rec["derived"]["length_mi"] = "route", 195
        rec["kind"] = "route"
        rec["route"] = {"creator": "Steve Roper", "line_policy": "sold"}
        title = trail.page_title(rec, S)
        self.assertEqual(title, "Sierra High Route (SHR): 195-mile route by Steve Roper")
        self.assertNotIn("GPX", title)
        rec["name"], rec["short_name"] = "A Route With A Rather Long Name", "RWLN"
        self.assertEqual(trail.page_title(rec, S), "A Route With A Rather Long Name (RWLN): 195-mile route")

    def test_pieces_go_in_a_stated_order_and_the_length_stays(self):
        rec = at()
        rec["common_name"] = "Appalachian Long Distance Footpath"
        rec["short_name"] = "ALDF"
        rec["derived"]["length_mi"] = 2198
        title = trail.page_title(rec, S)
        self.assertLessEqual(len(title), ROOM)
        self.assertIn("2,198 miles", title)
        rec["common_name"] = "A Very Long Name For A Trail That Goes On"
        title = trail.page_title(rec, S)
        self.assertEqual(title, "A Very Long Name For A Trail That Goes On: 2,198 miles, GPX")

    def test_kilometres_follow_only_where_there_is_room(self):
        rec = gpx(fake(1, km=80))
        rec["name"], rec["short_name"] = "Short Path", "SP"
        rec["derived"]["length_mi"] = 50
        self.assertEqual(trail.page_title(rec, S), "Short Path (SP): 50 miles (80 km), map and GPX")

    def test_the_page_carries_the_title_and_the_common_name_in_its_heading(self):
        rec = at()
        title, description, body, _ = trail.render(rec, S)
        self.assertEqual(title, "Appalachian Trail (AT): 2,198 miles (3,537 km), map and GPX")
        self.assertIn('<h1>Appalachian Trail <span class="titleblock__abbr">AT</span></h1>', body)
        self.assertIn("Full name: Appalachian National Scenic Trail", body)
        self.assertIn("Common name", body)

    def test_a_record_without_a_common_name_shows_no_full_name(self):
        body = trail.render(gpx(fake(1)), S)[2]
        self.assertNotIn("Full name", body)


class TrailDescriptionTest(unittest.TestCase):
    def test_it_leads_with_the_facts_of_the_record(self):
        text = trail.description(at())
        self.assertTrue(text.startswith("A trail of 2,198 miles (3,537 km) across 14 states, usually 5 to 7 months."), text)
        self.assertIn("A long walk along the crest of the Example Range", text)

    def test_at_most_155_characters_in_whole_sentences(self):
        rec = at()
        rec["hike"]["summary"] = "The walk goes " + "on and on and on " * 20 + "to the end."
        text = trail.description(rec)
        self.assertLessEqual(len(text), common.DESCRIPTION_LIMIT)
        self.assertEqual(text, "A trail of 2,198 miles (3,537 km) across 14 states, usually 5 to 7 months.")
        self.assertNotIn("\u2026", text)

    def test_a_first_sentence_too_long_is_cut_at_a_word_with_no_ellipsis(self):
        rec = at()
        rec["common_name"] = rec["name"] = "N" * 58
        rec["regions"] = ["GA", "NC", "TN", "VA", "WV", "MD", "PA", "NJ", "NY", "CT", "MA", "VT", "NH", "ME"]
        text = trail.description(rec)
        self.assertLessEqual(len(text), common.DESCRIPTION_LIMIT)
        self.assertTrue(text.endswith("."))
        self.assertNotIn("\u2026", text)

    def test_the_summary_sentence_follows_when_it_fits(self):
        rec = at()
        rec["hike"]["summary"] = "A short walk."
        self.assertEqual(trail.description(rec),
                         "A trail of 2,198 miles (3,537 km) across 14 states, usually 5 to 7 months. A short walk.")

    def test_no_stock_sentence(self):
        for rec in (at(), fake(1), fake(2, hike={})):
            text = trail.description(rec)
            self.assertNotIn("GPX", text)

    def test_a_record_with_no_summary_uses_its_designation(self):
        rec = fake(1, km=160)
        rec["derived"]["length_mi"] = 99
        rec["regions"] = ["IN"]
        self.assertEqual(trail.description(rec), "A trail of 99 miles (160 km) in Arizona. A & B Association.".replace("Arizona", "Indiana"))

    def test_a_route_is_a_route_and_stated_time_only(self):
        rec = fake(1, km=300, hike={"summary": "Steve Roper's route.", "checked": "2026-11-13"})
        rec["derived"]["kind"], rec["kind"] = "route", "route"
        self.assertTrue(trail.description(rec).startswith("A route of "), trail.description(rec))
        self.assertNotIn("usually", trail.description(rec))


class PlaceAndListTitleTest(unittest.TestCase):
    def setUp(self):
        self.recs = [fake(i, km=100 + 90 * i, regions=["CO"], hike=dict(FULL_HIKE)) for i in range(1, 7)]
        for i, r in enumerate(self.recs):
            r["id"], r["name"] = f"t{i}", f"Trail {i}"
            r["derived"]["length_mi"] = round(r["length_km"] / 1.609344)
        self.recs[0]["derived"]["kind"] = self.recs[0]["kind"] = "route"

    def test_place_title_counts_trails_and_routes(self):
        title, desc, body, _ = regions.region_page("us-co", self.recs, S)
        self.assertEqual(title, "Long Trails in Colorado: 5 Trails and 1 Route")
        self.assertLessEqual(len(desc), common.DESCRIPTION_LIMIT)
        self.assertIn("from Trail 0, 118 miles, to Trail 5, 398 miles.", desc)
        self.assertNotIn(title, desc)

    def test_a_long_place_name_drops_the_counts_to_fit(self):
        recs = [fake(i, regions=["NL"], country="CA") for i in range(1, 4)]
        for i, r in enumerate(recs):
            r["id"], r["name"] = f"n{i}", f"Trail {i}"
        recs[0]["derived"]["kind"] = recs[0]["kind"] = "route"
        title = regions.region_page("ca-nl", recs, S)[0]
        self.assertLessEqual(len(title), common.TITLE_LIMIT)
        self.assertTrue(title.startswith("Long Trails in Newfoundland and Labrador"))

    def test_a_place_with_one_trail(self):
        title, desc = regions.region_page("us-co", self.recs[1:2], S)[:2]
        self.assertEqual(title, "Long Trails in Colorado: 1 Trail")
        self.assertIn("is the one long trail listed in Colorado", desc)

    def test_every_list_has_a_search_title_that_fits(self):
        for lst in browse.LISTS:
            title = lst.search_title(999)
            self.assertLessEqual(len(title), ROOM, title)
            self.assertIn("999", title)
        self.assertEqual(browse.by_key("loops").search_title(32), "Backpacking Loops: 32 Long Trail Loops")

    def test_list_description_adds_to_the_title(self):
        lst = browse.by_key("under-100-miles")
        members = browse.members(lst, [fake(i, km=100) for i in range(1, 5)])
        title, desc = regions.list_page(lst, members, 20, S)[:2]
        self.assertTrue(title.startswith("Short Thru-Hikes and Loops Under 100 Miles: 4"))
        self.assertLessEqual(len(desc), common.DESCRIPTION_LIMIT)
        self.assertTrue(desc.startswith(lst.blurb))
        self.assertIn("4 trails", desc)

    def test_the_home_page_has_its_own_title_and_description(self):
        page = layout.layout("", "<h1>x</h1>", path="/", site=S, description=home.description(self.recs))
        # 48 + " · Long Hikes" is 61 characters: the site name is dropped from <title>, and the
        # share titles never carry it.
        self.assertIn("<title>Long-Distance Hiking Trails of the US and Canada</title>", page)
        self.assertIn('<meta property="og:title" content="Long-Distance Hiking Trails of the US and Canada">', page)
        self.assertIn('<meta name="twitter:title" content="Long-Distance Hiking Trails of the US and Canada">', page)
        self.assertNotIn("A tagline", page.split("</head>")[0].split('name="description"')[1].split(">")[0])
        self.assertLessEqual(len(home.description(self.recs)), common.DESCRIPTION_LIMIT)
        self.assertIn("6 long-distance hiking trails and routes", home.description(self.recs))
        bare = layout.layout("", "x", path="/", site=site.Site("N", "Tag"))
        self.assertIn("<title>N: Tag</title>", bare)


class TitleAndShareTextTest(unittest.TestCase):
    def head(self, title, description="Short."):
        return layout.layout(title, "<h1>x</h1>", path="/x/", site=S, description=description).split("</head>")[0]

    def test_the_site_name_is_kept_in_title_only_where_the_whole_is_60_or_fewer(self):
        fits = "T" * (60 - len(" · Long Hikes"))
        head = self.head(fits)
        self.assertIn(f"<title>{fits} · Long Hikes</title>", head)
        over = "T" * (60 - len(" · Long Hikes") + 1)
        self.assertIn(f"<title>{over}</title>", self.head(over))

    def test_share_titles_never_carry_the_site_name(self):
        for title in ("Short", "T" * 47, "T" * 70):
            head = self.head(title)
            self.assertIn(f'<meta property="og:title" content="{title}">', head)
            self.assertIn(f'<meta name="twitter:title" content="{title}">', head)

    def test_a_title_that_only_its_name_makes_long_is_not_cut(self):
        rec = at()
        rec["common_name"] = rec["name"] = "N" * 58
        rec["short_name"] = ""
        self.assertEqual(trail.page_title(rec, S), "N" * 58)  # the name fits, the length does not
        rec["common_name"] = rec["name"] = "N" * 70
        self.assertEqual(trail.page_title(rec, S), "N" * 70 + f": {rec['derived']['length_mi']:,} miles")

    def test_share_description_is_at_most_125_and_cut_at_a_sentence_or_word(self):
        self.assertEqual(common.share_description("A short one."), "A short one.")
        text = ("A trail of 2,198 miles (3,537 km) across 14 states, usually 5 to 7 months. "
                "It follows the crest of the Appalachian Mountains from Georgia to Maine and is the longest.")
        got = common.share_description(text)
        self.assertEqual(got, "A trail of 2,198 miles (3,537 km) across 14 states, usually 5 to 7 months.")
        words = ("A trail of 2,198 miles (3,537 km) across 14 states, usually 5 to 7 months and "
                 "following the crest of the Appalachian Mountains from Georgia to Maine, and more")
        got = common.share_description(words)
        self.assertLessEqual(len(got), 125)
        self.assertTrue(got.endswith("."))
        self.assertNotIn("\u2026", got)
        self.assertTrue(words.startswith(got[:-1]))
        self.assertIsNone(re.search(r"(,|\b(and|or|but|with|to|of|the|in))\.$", got), got)
        for limit in range(40, 125):
            cut = common.share_description(words, limit)
            self.assertLessEqual(len(cut), limit)
            self.assertIsNone(re.search(r"([,;:]|\b(and|or|but|with|to|of|the|a|in|by|from))\.?$", cut), cut)

    def test_the_search_description_is_unchanged_and_the_share_one_is_cut_from_it(self):
        desc = ("A trail of 2,198 miles (3,537 km) across 14 states, usually 5 to 7 months. "
                "It follows the crest of the Appalachian Mountains from Georgia to Maine, the longest in the country.")
        head = self.head("T", desc)
        self.assertIn(f'<meta name="description" content="{desc}">', head)
        self.assertIn('<meta property="og:description" content="A trail of 2,198 miles (3,537 km) across 14 states, usually 5 to 7 months.">', head)
        self.assertIn('<meta name="twitter:description" content="A trail of 2,198 miles (3,537 km) across 14 states, usually 5 to 7 months.">', head)

    def test_the_footer_links_the_glossary_the_method_and_the_authors(self):
        foot = layout.footer(S)
        for href in ("/glossary/", "/method/", "/authors/"):
            self.assertEqual(foot.count(f'href="{href}"'), 1, href)


class HeadingOrderTest(unittest.TestCase):
    def setUp(self):
        self.recs = [fake(i, km=100 + 50 * i, regions=["CO"]) for i in range(1, 6)]
        for i, r in enumerate(self.recs):
            r["id"] = f"t{i}"

    def check(self, body):
        found = levels(str(body))
        for before, after in zip(found, found[1:]):
            self.assertLessEqual(after, before + 1, found)
        return found

    def test_place_page(self):
        found = self.check(regions.region_page("us-co", self.recs, S)[2])
        self.assertEqual(found[0], 1)
        self.assertEqual(found[1], 2)

    def test_list_page(self):
        lst = browse.by_key("under-100-miles")
        self.check(regions.list_page(lst, self.recs, 10, S)[2])

    def test_routes_page_keeps_groups_above_their_trails(self):
        for r in self.recs:
            r["kind"] = r["derived"]["kind"] = "route"
            r["route"] = {"creator": "A. Author", "line_policy": "sold"}
        found = self.check(regions.routes_page(self.recs, S)[2])
        self.assertIn(3, found)

    def test_the_home_page_list_is_unchanged(self):
        self.assertIn('<h3 class="entry__name">', str(home.results(self.recs)))
        self.assertIn('<h2 class="entry__name">', str(home.results(self.recs, top=2)))


class LeftOutLayoutTest(unittest.TestCase):
    def test_the_intro_and_the_groups_are_spaced_like_the_other_list_pages(self):
        entries = [{"id": "a", "name": "A", "country": "US", "regions": ["AZ"], "reason": "below-floor",
                    "note": "Short.", "decided": "2026-11-14", "source_url": "https://e.org/"}]
        body = str(leftout.left_out_page(entries, S, "")[2])
        # .place spaces its children apart (the intro from the first heading); each reason is a
        # section of rows in the language of a trail's row.
        opening = '<div class="container section place left-out">'
        self.assertIn(opening, body)
        main = body[body.index(opening):]
        self.assertLess(main.index('<p class="prose">'), main.index("<section"))


class LinksTest(unittest.TestCase):
    def setUp(self):
        self.recs = []
        for i in range(1, 13):
            r = fake(i, km=100 + 25 * i, hike={"summary": f"Walk number {i}.", "checked": "2026-11-13",
                                               "terrain": ["desert"] if i % 2 else ["forest"], "shape": "loop" if i < 7 else "point-to-point"})
            r["id"], r["name"] = f"t{i}", f"Trail {i}"
            r["derived"]["length_mi"] = round(r["length_km"] / 1.609344)
            self.recs.append(r)

    def test_every_trail_is_listed_by_three_others(self):
        counts = {r["id"]: 0 for r in self.recs}
        for r in self.recs:
            like = related.similar_to(r, self.recs)
            self.assertTrue(4 <= len(like) <= related.SIMILAR_MAX)
            self.assertNotIn(r["id"], [x["id"] for x in like])
            for x in like:
                counts[x["id"]] += 1
        self.assertGreaterEqual(min(counts.values()), related.MIN_INBOUND)

    def test_similar_trails_are_close_in_length(self):
        rec = self.recs[5]
        like = related.similar_to(rec, self.recs)
        self.assertTrue(any(abs(x["length_km"] - rec["length_km"]) <= 50 for x in like))

    def test_shared_terrain(self):
        self.assertEqual(related.shared_terrain(self.recs[0], self.recs[2]), ["desert"])
        self.assertEqual(related.shared_terrain(self.recs[0], self.recs[1]), [])

    def test_trails_that_share_a_name_or_name_each_other_are_related(self):
        a, b, c = fake(1), fake(2), fake(3)
        a["name"], b["name"], c["name"] = "Teton Crest Trail", "Teton Crest Route", "Lone Peak Trail"
        c["hike"] = {"summary": "It meets the Teton Crest Route at its north end.", "checked": "2026-11-13"}
        recs = [a, b, c]
        for r, i in zip(recs, "abc"):
            r["id"] = i
        self.assertEqual([(r["id"], why) for r, why in related.related_to(c, recs)], [("b", "named")])
        self.assertEqual([(r["id"], why) for r, why in related.related_to(b, recs)], [("c", "names")])
        self.assertEqual(related.related_to(a, recs), [])
        b["name"] = "Teton Crest Trail (Route)"
        related._CACHE.clear()
        self.assertIn(("b", "name"), [(r["id"], why) for r, why in related.related_to(a, recs)])

    def test_a_one_word_name_is_not_matched(self):
        a, b = fake(1), fake(2)
        a["name"], b["name"] = "Wonderland", "Wonderland Loop"
        a["id"], b["id"] = "a", "b"
        b["hike"] = {"summary": "Not the Wonderland.", "checked": "2026-11-13"}
        self.assertEqual(related.related_to(b, [a, b]), [])

    def test_the_page_links_terrain_shape_time_and_length_to_their_lists(self):
        recs = [copy.deepcopy(r) for r in self.recs]
        rec = recs[0]
        page = str(trail.glance(rec, recs))
        shown = {lst.key for lst, _ in browse.shown(recs)}
        for key in ("terrain-desert", "loops"):
            if key in shown:
                self.assertIn(f'href="{browse.path(browse.by_key(key))}"', page, key)
        bare = str(trail.glance(rec))
        self.assertNotIn("/lists/", bare)

    def test_a_list_that_is_not_shown_is_not_linked(self):
        recs = self.recs[:2]
        self.assertIsNone(related.list_link(recs, "loops"))
        self.assertIsNone(related.list_link(None, "loops"))

    def test_the_foot_of_the_page_offers_similar_and_related_trails(self):
        body = str(trail.onward(self.recs[0], self.recs))
        self.assertIn('id="onward-similar"', body)
        self.assertIn("Similar in length and terrain", body)


if __name__ == "__main__":
    unittest.main()
