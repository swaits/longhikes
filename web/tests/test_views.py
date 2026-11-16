"""Tests for the views built from the records: the extra lists, the place-by-list pages, tables, rankings,
authors, recent changes, linked trails, the glossary and the method page.

Each view's selection rule is tested on small fixtures; the data files are checked against the real records.
These do not need the built site.

    python3 -m unittest discover -s web/tests
"""
import os
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from olt import (authors, browse, common, datafiles, facets, placefacets, records, reference, regions, site, standing,  # noqa: E402
                 summary, views, words)
from test_hike import fake  # noqa: E402

SITE = site.Site("Long Hikes", "T", repo_url="https://github.com/o/r")


def mi(n):
    """The kilometres of a length in miles, unrounded, so a band's edge falls where the rule puts it."""
    return n * words.KM_PER_MI


def keys(recs, key):
    return [r["id"] for r in browse.members(browse.by_key(key), recs)]


class LengthBandTest(unittest.TestCase):
    def test_bands_split_at_the_mile_figures(self):
        recs = [fake(1, km=mi(99)), fake(2, km=mi(100)), fake(3, km=mi(199)), fake(4, km=mi(200)),
                fake(5, km=mi(499)), fake(6, km=mi(500)), fake(7, km=mi(999)), fake(8, km=mi(1000))]
        self.assertEqual(keys(recs, "under-100-miles"), ["t1"])
        self.assertEqual(sorted(keys(recs, "100-to-200-miles")), ["t2", "t3"])
        self.assertEqual(sorted(keys(recs, "200-to-500-miles")), ["t4", "t5"])
        self.assertEqual(sorted(keys(recs, "500-to-1000-miles")), ["t6", "t7"])
        self.assertEqual(keys(recs, "longest"), ["t8"])

    def test_each_trail_is_in_exactly_one_band(self):
        bands = ("under-100-miles", "100-to-200-miles", "200-to-500-miles", "500-to-1000-miles", "longest")
        recs = [fake(i, km=km) for i, km in enumerate(range(50, 3000, 37))]
        for r in recs:
            self.assertEqual(sum(1 for b in bands if browse.by_key(b).test(r)), 1, r["length_km"])

    def test_under_200_is_the_two_short_bands(self):
        recs = [fake(1, km=mi(50)), fake(2, km=mi(150)), fake(3, km=mi(250))]
        self.assertEqual(sorted(keys(recs, "under-200-miles")), ["t1", "t2"])
        self.assertTrue(browse.by_key("under-200-miles").search_title(9).startswith("Thru-Hikes Under 200 Miles"))


class TimeListTest(unittest.TestCase):
    def test_bands_by_days(self):
        stated = lambda i, days: fake(i, hike={"days": days})  # noqa: E731
        recs = [stated(1, [2, 4]), stated(2, [4, 4]), stated(3, [5, 7]), stated(4, [20, 28]), stated(5, [30, 60])]
        self.assertEqual(sorted(keys(recs, "weekend")), ["t1", "t2"])
        self.assertEqual(keys(recs, "two-to-four-weeks"), ["t4"])
        self.assertEqual(keys(recs, "a-month-or-more"), ["t5"])
        self.assertEqual(sorted(keys(recs, "a-week-or-less")), ["t1", "t2", "t3"])

    def test_note_says_how_many_are_stated_and_how_the_rest_were_estimated(self):
        recs = [fake(1, km=100, hike={"days": [3, 4]}), fake(2, km=100), fake(3, km=100)]
        note = browse.time_note(recs, recs)
        self.assertIn("A source states the time for 1 of these", note)
        self.assertIn("For the other 2 it is estimated from the length", note)
        self.assertIn("12 to 19 miles a day", note)
        self.assertIn("7 to 12", note)
        self.assertIn("all 1", browse.time_note(recs[:1], recs))
        self.assertIn("No source states the time", browse.time_note(recs[1:], recs))


class KindListTest(unittest.TestCase):
    def test_high_routes_by_name_or_designation(self):
        a, b, c, d = fake(1), fake(2), fake(3), fake(4)
        a["name"] = "Alpine High Route"
        b["name"] = "Uinta Highline Trail"          # a trail named Highline is not a high route
        c["common_name"] = "Big High Route"
        d["designation"] = "Person-defined high route"
        self.assertEqual(keys([a, b, c, d], "high-routes"), ["t1", "t3", "t4"])

    def test_mostly_cross_country_and_unfinished(self):
        recs = [fake(1, hike={"travel": "mostly-cross-country"}), fake(2, hike={"travel": "some-cross-country"}),
                fake(3, hike={"unfinished": "Half is built."}), fake(4)]
        self.assertEqual(keys(recs, "mostly-cross-country"), ["t1"])
        self.assertEqual(keys(recs, "off-trail"), ["t1", "t2"])
        self.assertEqual(keys(recs, "unfinished"), ["t3"])

    def test_holders_come_from_the_designation_alone(self):
        nrt, pc, fs, sp, club, route = (fake(i) for i in range(1, 7))
        nrt["designation"] = "National Recreation Trail (certified 2008), managed by the Bureau of Land Management"
        pc["designation"] = "Parks Canada, Jasper National Park"
        fs["designation"] = "National Recreation Trail #31 (Forest Service, Tonto National Forest)"
        sp["designation"] = "BC Parks (Naikoon Provincial Park)"
        club["designation"] = "Keystone Trails Association"
        route["designation"] = "Person-defined route (Jo); no agency or association"
        route["kind"] = "route"
        route["derived"]["kind"] = "route"
        recs = [nrt, pc, fs, sp, club, route]
        self.assertEqual(keys(recs, "national-recreation-trails"), ["t1", "t3"])
        self.assertEqual(keys(recs, "parks-canada"), ["t2"])
        self.assertEqual(keys(recs, "forest-service"), ["t3"])
        self.assertEqual(keys(recs, "state-and-provincial-parks"), ["t4"])
        # a route that says it has no association is not kept by one
        self.assertEqual(keys(recs, "clubs-and-associations"), ["t5"])


class MonthListTest(unittest.TestCase):
    def test_a_month_holds_the_trails_whose_months_include_it(self):
        recs = [fake(1, hike={"months": [6, 7]}), fake(2, hike={"months": [8]}), fake(3)]
        self.assertEqual(keys(recs, "hike-in-july"), ["t1"])
        self.assertEqual(keys(recs, "hike-in-august"), ["t2"])

    def test_a_month_needs_eight_trails_and_says_how_many_have_a_season(self):
        july = browse.by_key("hike-in-july")
        self.assertEqual(july.min_size, 8)
        self.assertFalse(browse.is_shown(7, 100, july.min_size))
        self.assertTrue(browse.is_shown(8, 100, july.min_size))
        recs = [fake(i, hike={"months": [7]}) for i in range(10)] + [fake(20 + i) for i in range(10)]
        shown = {lst.key for lst, _ in browse.shown(recs)}
        self.assertIn("hike-in-july", shown)
        self.assertNotIn("hike-in-august", shown)
        note = july.note(browse.members(july, recs), recs)
        self.assertIn("Only 10 of the 20 trails have a season on file", note)

    def test_every_list_has_a_group_and_every_group_a_heading(self):
        headings = {k for k, _, _ in browse.GROUPS}
        for lst in browse.LISTS:
            self.assertIn(lst.group, headings, lst.key)

    def test_titles_are_unique_and_short_enough(self):
        titles = [lst.search_title(99) for lst in browse.LISTS]
        self.assertEqual(len(titles), len(set(titles)))
        for t in titles:
            self.assertLessEqual(len(t), common.TITLE_LIMIT, t)


class PlaceFacetTest(unittest.TestCase):
    def setUp(self):
        # Eight trails in Arizona: six under 100 miles, three of them loops; two in Utah.
        self.recs = [fake(i, km=mi(50), regions=["AZ"], hike={"shape": "loop" if i < 3 else "point-to-point"})
                     for i in range(6)]
        self.recs += [fake(6, km=mi(150), regions=["AZ"]), fake(7, km=mi(150), regions=["AZ"])]
        self.recs += [fake(8, km=mi(50), regions=["UT"]), fake(9, km=mi(50), regions=["UT"])]
        # enough trails elsewhere that the lists are shown (no more than 75% of all trails)
        self.recs += [fake(20 + i, km=mi(400), regions=["NY"]) for i in range(12)]

    def pages(self):
        return placefacets.plan(self.recs)

    def test_a_page_needs_five_trails_in_the_place(self):
        pages = self.pages()
        self.assertTrue(pages)
        for p in pages:
            self.assertGreaterEqual(len(p["recs"]), browse.MIN_SIZE)
        self.assertNotIn("ut", {p["slug"].split("-")[1] for p in pages})   # two trails: no page

    def test_a_page_that_repeats_the_whole_place_is_left_out(self):
        for p in self.pages():
            self.assertLessEqual(len(p["recs"]), browse.MAX_SHARE * len(p["info"]["records"]))

    def test_three_loops_are_too_few(self):
        self.assertNotIn("loops", {p["lst"].key for p in self.pages()})

    def test_a_set_that_repeats_another_page_of_the_place_is_kept_once(self):
        # the six short trails are the same set under two lists: only one page for them
        sets = [frozenset(r["id"] for r in p["recs"]) for p in self.pages() if p["slug"] == "us-az"]
        self.assertEqual(len(sets), len(set(sets)))

    def test_title_and_path(self):
        p = self.pages()[0]
        self.assertEqual(p["path"], f"/regions/{p['slug']}/{p['lst'].key}/")
        title, desc, body, _ = placefacets.page(p, self.recs, SITE, self.pages())
        self.assertIn("Arizona", title)
        self.assertIn(f"{len(p['recs'])}", title)
        self.assertEqual(str(body).count("<h1>"), 1)


class RankingTest(unittest.TestCase):
    def test_highest_points_rank_only_records_that_state_one(self):
        recs = [fake(i, hike={"high_point_m": 1000 + i * 10, "high_point": f"P{i}"}) for i in range(1, 7)] + [fake(9), fake(10)]
        spec = next(s for s in standing.RANKINGS if s[0] == "highest-points")
        title, desc, body, have = standing.ranking_page(spec, recs, SITE)
        self.assertEqual(len(have), 6)
        self.assertIn("6 of the 8 trails have a high point stated", str(body))
        text = str(body)
        self.assertLess(text.index("P6"), text.index("P5"))       # highest first
        self.assertIn("Ranked by High Point", title)

    def test_a_ranking_with_fewer_than_five_is_not_built(self):
        recs = [fake(i, hike={"high_point_m": 2000}) for i in range(4)]
        spec = next(s for s in standing.RANKINGS if s[0] == "highest-points")
        self.assertIsNone(standing.ranking_page(spec, recs, SITE))

    def test_climb_leaves_out_a_track_that_covers_part_of_the_trail(self):
        whole = {"ascent_m": 1000, "coverage": 1.0, "highest": {"m": 5}, "source": {"limits": "Computed, not measured."}}
        partial = dict(whole, coverage=0.5)
        recs = [fake(i, km=100) for i in range(6)]
        for r, e in zip(recs, [whole] * 5 + [partial]):
            r["derived"]["elevation"] = e
        have = [r for r in recs if standing._climb(r) is not None]
        self.assertEqual(len(have), 5)
        self.assertEqual(standing._climb_rate(have[0]), 1000 / 100)


class CollectionTest(unittest.TestCase):
    def setUp(self):
        self.recs = [fake(i, km=1000 * i) for i in range(1, 4)]
        self.coll = {"id": "set", "name": "The Set", "members": ["t1", "t2", "t3"],
                     "definition": "A set of three.", "source_url": "https://example.org/", "source_publisher": "Someone"}

    def test_members_are_set_side_by_side_in_the_order_given(self):
        title, desc, body, recs = standing.collection_page(self.coll, self.recs, SITE)
        self.assertEqual([r["id"] for r in recs], ["t1", "t2", "t3"])
        self.assertIn("Compared", title)
        self.assertEqual(standing.collection_path(self.coll), "/set/")
        for word in ("best", "rank", "recommend"):
            self.assertNotIn(word, str(body).lower().replace("ranked", ""))

    def test_a_missing_member_means_no_page(self):
        self.coll["members"].append("nope")
        self.assertIsNone(standing.collection_page(self.coll, self.recs, SITE))


class AuthorTest(unittest.TestCase):
    def routes(self, credits):
        out = []
        for i, c in enumerate(credits):
            r = fake(i)
            r["kind"] = "route"
            r["derived"]["kind"] = "route"
            r["route"] = {"creator": c}
            out.append(r)
        return out

    def test_credits_in_authors_file_gather_one_person(self):
        recs = self.routes(["Andrew Skurka", "Andrew Skurka and Ryan Jordan", "Cam Honan"])
        gs = {g["name"]: g for g in authors.groups(recs, ROOT)}
        self.assertEqual(len(gs["Andrew Skurka"]["routes"]), 2)
        self.assertEqual(len(gs["Cam Honan"]["routes"]), 1)

    def test_a_shared_credit_is_on_each_persons_page_and_names_the_other(self):
        recs = self.routes(["Andrew Skurka and Ryan Jordan"])
        gs = {g["name"]: g for g in authors.groups(recs, ROOT)}
        self.assertEqual([r["id"] for r in gs["Ryan Jordan"]["routes"]], [r["id"] for r in recs])
        self.assertEqual(gs["Ryan Jordan"]["others"][recs[0]["id"]], ["Andrew Skurka"])
        g = gs["Ryan Jordan"]
        _, _, body, _, _, person = authors.author_page(g, recs, SITE, list(gs.values()))
        self.assertIn("also credited to <a href=\"/authors/andrew-skurka/\">Andrew Skurka</a>", str(body))
        self.assertEqual(person["@type"], "Person")

    def test_featured_authors_are_cards_with_lengths_that_follow_the_units_switch(self):
        recs = self.routes(["Cam Honan"] * 3 + ["A Club"])
        _, _, body, _ = authors.index_page(recs, SITE, ROOT)
        html = str(body)
        self.assertIn('<li class="shelf shelf--author">', html)
        self.assertIn('class="shelf__count"', html)
        self.assertIn('class="shelf__len"><span class="len len--inline"><span class="len__mi">', html)
        self.assertIn("All 3 routes by Cam Honan", html)
        self.assertNotIn("A Club</a></h3>", html)

    def test_every_author_has_a_page_however_few_routes(self):
        recs = self.routes(["Andrew Skurka"] * 3 + ["Andrew Skurka and Ryan Jordan"] * 2 + ["Cam Honan"] * 4 + ["A Club"])
        pages = {g["name"]: len(g["routes"]) for g in authors.author_pages(recs, ROOT)}
        self.assertEqual(pages, {"Andrew Skurka": 5, "Ryan Jordan": 2, "Cam Honan": 4, "A Club": 1})

    def test_a_single_route_page_has_substance_and_an_unlisted_credit_is_not_a_person(self):
        real = [r for r in records.load_records(ROOT) if r.get("kind") == "route"]
        gs = authors.author_pages(real, ROOT)
        one = next(g for g in gs if len(g["routes"]) == 1 and g["kind"] == "person")
        title, desc, body, _, routes, person = authors.author_page(one, real, SITE, gs)
        self.assertIn('class="trail-brief"', str(body))
        self.assertIn("<table", str(body))
        self.assertLessEqual(len(title), 60)
        self.assertEqual(person["name"], one["name"])
        club = next(g for g in gs if g["name"] == "Wilderness Mindset")
        self.assertEqual(club["kind"], "")
        self.assertIsNone(authors.author_page(club, real, SITE, gs)[5])

    def test_the_top_section_is_every_author_at_the_threshold_and_follows_it(self):
        real = [r for r in records.load_records(ROOT) if r.get("kind") == "route"]
        gs = authors.author_pages(real, ROOT)
        top = authors.prominent(gs)
        self.assertTrue(top)
        self.assertTrue(all(len(g["routes"]) >= authors.PROMINENT_MIN for g in top))
        self.assertEqual(len(top), sum(1 for g in gs if len(g["routes"]) >= authors.PROMINENT_MIN))
        counts = [len(g["routes"]) for g in top]
        self.assertEqual(counts, sorted(counts, reverse=True))
        body = str(authors.index_page(real, SITE, ROOT)[2])
        self.assertLess(body.index('id="most-routes"'), body.index('id="other-authors"'))
        for g in top:
            self.assertLess(body.index(f'<h3 class="shelf__title"><a href="/authors/{g["slug"]}/">'), body.index('id="other-authors"'))
        self.assertEqual(body.count('class="shelf shelf--author"'), len(top))
        old = authors.PROMINENT_MIN
        try:
            authors.PROMINENT_MIN = 5
            self.assertEqual({g["name"] for g in authors.prominent(gs)}, {"Brett Tucker", "Andrew Skurka"})
        finally:
            authors.PROMINENT_MIN = old

    def test_a_credit_in_a_route_page_links_each_named_author(self):
        recs = self.routes(["Andrew Skurka and Ryan Jordan"])
        links = authors.link_map(recs, ROOT)
        html = str(authors.credit_html("Andrew Skurka and Ryan Jordan", links["Andrew Skurka and Ryan Jordan"]))
        self.assertIn('<a href="/authors/andrew-skurka/">Andrew Skurka</a> and <a href="/authors/ryan-jordan/">Ryan Jordan</a>', html)

    def test_authors_file_matches_the_records(self):
        real = records.load_records(ROOT)
        creators = {r["route"]["creator"] for r in real if r.get("kind") == "route"}
        for a in datafiles.authors(ROOT):
            for c in a["credits"]:
                self.assertIn(c, creators)


class RecentTest(unittest.TestCase):
    def rec(self, i, added, changes=()):
        r = fake(i)
        r["history"] = [{"date": added, "change": "Added.", "fields": ["record"], "outcome": "applied"}]
        for d, fields, outcome in changes:
            r["history"].append({"date": d, "change": f"Changed {fields[0]}.", "fields": fields, "outcome": outcome})
        return r

    def test_whole_days_of_additions_until_enough(self):
        recs = [self.rec(i, "2026-11-16") for i in range(12)] + [self.rec(20 + i, "2026-11-15") for i in range(12)] \
            + [self.rec(40 + i, "2026-11-09") for i in range(12)]
        added = views.recent_added(recs)
        self.assertEqual([d for d, _ in added], ["2026-11-16", "2026-11-15"])
        self.assertEqual(sum(len(rs) for _, rs in added), 24)

    def test_changes_leave_out_additions_and_declined_requests(self):
        r = self.rec(1, "2026-11-10", [("2026-11-12", ["length_km"], "applied"), ("2026-11-13", ["length_km"], "declined")])
        rows, total = views.recent_changes([r])
        self.assertEqual(total, 1)
        self.assertEqual(rows[0][0], "2026-11-12")

    def test_newest_first(self):
        a = self.rec(1, "2026-11-10", [("2026-11-12", ["name"], "applied")])
        b = self.rec(2, "2026-11-10", [("2026-11-14", ["name"], "applied")])
        rows, _ = views.recent_changes([a, b])
        self.assertEqual([r[0] for r in rows], ["2026-11-14", "2026-11-12"])

    def test_no_page_with_fewer_than_five_added(self):
        self.assertIsNone(views.recent_page([self.rec(i, "2026-11-16") for i in range(4)], SITE))


class LinkedTest(unittest.TestCase):
    def test_a_group_is_a_trail_that_three_others_name(self):
        hub = fake(0)
        hub["name"] = "Grand Example Trail"
        recs = [hub]
        for i in range(1, 6):
            r = fake(i)
            r["name"] = f"Side Path {i}"
            r["hike"] = {"summary": "It joins the Grand Example Trail near the border." if i <= 3 else "It is a walk."}
            recs.append(r)
        groups = views.connections(recs)
        self.assertEqual([h["id"] for h, _ in groups], ["t0"])
        self.assertEqual([r["id"] for r in groups[0][1]], ["t1", "t2", "t3"])

    def test_two_namers_are_not_a_group(self):
        hub = fake(0)
        hub["name"] = "Grand Example Trail"
        recs = [hub] + [dict(fake(i), name=f"Side Path {i}", hike={"summary": "Meets the Grand Example Trail."})
                        for i in (1, 2)]
        self.assertEqual(views.connections(recs), [])


class SummaryTest(unittest.TestCase):
    def test_longest_and_shortest_come_from_the_lengths(self):
        recs = [fake(1, km=mi(60)), fake(2, km=mi(900)), fake(3, km=mi(300))]
        for r in recs:
            r["name"] = f"Name{r['id']}"
        text = str(summary.facts(recs, recs))
        self.assertIn("The longest is", text)
        self.assertLess(text.index("Namet2"), text.index("Namet1"))

    def test_a_small_place_gets_a_paragraph_for_each_trail(self):
        recs = [fake(1, hike={"summary": "First sentence. Second sentence here.", "high_point_m": 2000, "high_point": "Top"})]
        text = str(summary.details(recs))
        self.assertIn("Second sentence here.", text)
        self.assertIn("Its high point is Top", text)
        self.assertEqual(str(summary.details([fake(i) for i in range(summary.DETAIL_MAX + 1)])), "")

    def test_place_page_says_how_many_trails_and_the_share(self):
        recs = [fake(i, regions=["AZ"]) for i in range(4)] + [fake(5, regions=["UT"])]
        title, desc, body, _ = regions.region_page("us-az", recs, SITE)
        self.assertIn("4 trails of the 5 trails on this site, 80.0 percent", str(body))


class RealDataTest(unittest.TestCase):
    """The data files and the lists, against the repository's own records."""

    @classmethod
    def setUpClass(cls):
        cls.records = records.load_records(ROOT)
        cls.shown = browse.shown(cls.records)

    def test_no_list_page_has_fewer_than_five_trails(self):
        for lst, recs in self.shown:
            self.assertGreaterEqual(len(recs), browse.MIN_SIZE, lst.key)

    def test_the_new_lists_are_shown(self):
        have = {lst.key for lst, _ in self.shown}
        for key in ("100-to-200-miles", "200-to-500-miles", "500-to-1000-miles", "under-200-miles", "weekend",
                    "two-to-four-weeks", "a-month-or-more", "high-routes", "mostly-cross-country", "hike-in-july"):
            self.assertIn(key, have)

    def test_glossary_links_resolve_to_pages_that_are_built(self):
        known = {"/", "/lists/", "/routes/", "/authors/", "/method/", "/numbers/", "/glossary/", "/data/schema/"}
        known |= {browse.path(lst) for lst, _ in self.shown}
        known |= {standing.collection_path(c) for c in datafiles.collections(ROOT)}
        known |= {f"/numbers/{s[0]}/" for s in standing.RANKINGS}
        for t in reference.terms(ROOT):
            for p in t.get("see", []):
                self.assertIn(p, known, f"{t['id']} points at {p}")

    def test_glossary_covers_the_words_the_site_uses(self):
        ids = {t["id"] for t in reference.terms(ROOT)}
        for needed in ("thru-hike", "section-hike", "route", "high-route", "track", "gpx", "national-scenic-trail",
                       "cross-country", "resupply"):
            self.assertIn(needed, ids)

    def test_the_triple_crown_is_built_from_its_collection(self):
        coll = datafiles.collections(ROOT)[0]
        built = standing.collection_page(coll, self.records, SITE)
        self.assertIsNotNone(built)
        self.assertEqual(len(built[3]), 3)

    def test_the_method_page_counts_what_the_records_hold(self):
        title, desc, body = reference.method_page(self.records, SITE, ROOT)
        n_ver = len(reference.verified(self.records))
        self.assertIn(f"{n_ver} of the {len(self.records)} trails have a track", str(body))

    def test_every_place_page_has_a_summary_paragraph(self):
        by_slug, _ = regions.collect_regions(self.records)
        for slug in by_slug:
            _, _, body, _ = regions.region_page(slug, self.records, SITE)
            self.assertIn("place-summary", str(body))
            if len(by_slug[slug]["records"]) > 1:
                self.assertIn("The longest is", str(body))


if __name__ == "__main__":
    unittest.main()
