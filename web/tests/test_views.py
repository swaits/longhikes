"""Tests for the views built from the records: the extra lists, the place-by-list pages, tables, rankings,
authors, recent changes, linked trails, the glossary and the method page.

Each view's selection rule is tested on small fixtures; the data files are checked against the real records.
These do not need the built site.

    python3 -m unittest discover -s web/tests
"""
import os
import re
from html import unescape as html_unescape
import shutil
import tempfile
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from olt import (authors, browse, common, datafiles, facets, placefacets, records, reference, regions, site, standing,  # noqa: E402
                 summary, views, words)
import builtsite  # noqa: E402
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
        self.assertTrue(browse.by_key("under-200-miles").search_title(9).startswith("Thru-Hikes and Loops Under 200 Miles"))


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

    def test_a_month_needs_eight_trails(self):
        july = browse.by_key("hike-in-july")
        self.assertEqual(july.min_size, 8)
        self.assertFalse(browse.is_shown(7, 100, july.min_size))
        self.assertTrue(browse.is_shown(8, 100, july.min_size))
        recs = [fake(i, hike={"months": [7]}) for i in range(10)] + [fake(20 + i) for i in range(10)]
        shown = {lst.key for lst, _ in browse.shown(recs)}
        self.assertIn("hike-in-july", shown)
        self.assertNotIn("hike-in-august", shown)

    def est(self, i, months=(7,)):
        return fake(i, hike={"months": list(months), "season": "July", "season_basis": "estimate",
                             "season_method": "Judged. Confidence: low."})

    def test_a_month_note_counts_stated_and_estimated_exactly(self):
        july = browse.by_key("hike-in-july")
        recs = [fake(i, hike={"months": [7], "season": "July", "season_basis": "primary"}) for i in range(10)] \
            + [self.est(20 + i) for i in range(5)]
        note = july.note(browse.members(july, recs), recs)
        self.assertEqual(note, "A source states the season for 10 of these. For the other 5 it is estimated "
                               "from the climate and similar trails, and marked.")

    def test_a_month_note_tells_estimated_from_judged_from_pages_that_differ(self):
        july = browse.by_key("hike-in-july")
        judged = fake(90, hike={"months": [7], "season": "July", "season_basis": "sources",
                                "season_method": "The pages differ. Confidence: low."})
        stated = fake(91, hike={"months": [7], "season": "July", "season_basis": "primary"})
        recs = [stated, judged] + [self.est(20 + i) for i in range(3)]
        self.assertEqual(july.note(browse.members(july, recs), recs),
                         "A source states the season for 1 of these. For the other 4, 3 are estimated from the climate "
                         "and similar trails and 1 is set by judgement from pages that differ, and marked.")
        recs = [judged, judged]
        self.assertEqual(july.note(browse.members(july, recs), recs),
                         "No source states the season for these, so each is set by judgement from pages that differ.")

    def test_a_month_list_with_no_estimates_says_so(self):
        july = browse.by_key("hike-in-july")
        recs = [fake(i, hike={"months": [7], "season": "July", "season_basis": "primary"}) for i in range(10)]
        self.assertEqual(july.note(browse.members(july, recs), recs), "A source states the season for all 10.")
        recs = [self.est(i) for i in range(3)]
        self.assertEqual(july.note(browse.members(july, recs), recs),
                         "No source states the season for these, so each is estimated from the climate and similar trails.")

    def test_the_month_blurb_no_longer_says_only_some_trails(self):
        group = {key: blurb for key, _title, blurb in browse.GROUPS}["month"]
        self.assertEqual(group, "Trails normally hiked in the month. Estimated seasons are marked.")
        self.assertEqual(browse.by_key("hike-in-july").blurb,
                         "Trails normally hiked in July. Estimated seasons are marked.")
        for lst in browse.LISTS:
            self.assertNotIn("Only some trails", lst.blurb)
            self.assertNotIn("season on file", lst.blurb)

    def test_every_list_has_a_group_and_every_group_a_heading(self):
        headings = {k for k, _, _ in browse.GROUPS}
        for lst in browse.LISTS:
            self.assertIn(lst.group, headings, lst.key)

    def test_titles_are_unique_and_short_enough(self):
        titles = [lst.search_title(99) for lst in browse.LISTS]
        self.assertEqual(len(titles), len(set(titles)))
        for t in titles:
            self.assertLessEqual(len(t), common.TITLE_LIMIT, t)


class MonthListsAreASetOfTwelveTest(unittest.TestCase):
    def test_a_month_in_nearly_every_trail_is_still_shown(self):
        # every trail has a season now, so September holds far more than MAX_SHARE of them
        recs = [fake(i, hike={"months": [9]}) for i in range(100)]
        shown = {lst.key for lst, _ in browse.shown(recs)}
        self.assertIn("hike-in-september", shown)
        self.assertFalse(browse.is_shown(100, 100))   # an ordinary list over the cap still is not
        self.assertTrue(browse.is_shown(100, 100, browse.by_key("hike-in-september").min_size, capped=False))

    def test_all_twelve_month_pages_exist_on_the_real_data(self):
        recs = records.load_records(ROOT)
        shown = {lst.key for lst, _ in browse.shown(recs)}
        for name in facets.MONTHS:
            self.assertIn(f"hike-in-{name.lower()}", shown)


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


BIO = "Jo Walker has walked " + "a long way " * 20 + "and written guides to it."
AUTHORS_FIXTURE = f'''
[[author]]
name = "Jo Walker"
credits = ["Jo Walker", "Jo Walker and Sam Hill"]
url = "https://jowalker.example/"
summary = "Jo Walker is a hiker who works out long desert routes."
bio = "{BIO}"
checked = 2026-11-17
[[author.source]]
url = "https://jowalker.example/about/"
publisher = "Jo Walker's site"
[[author.source]]
url = "https://magazine.example/jo/"
publisher = "A Magazine"

[[author]]
name = "Sam Hill"
credits = ["Jo Walker and Sam Hill"]

[[author]]
name = "Ann and Bo"
kind = "people"
credits = ["Ann and Bo"]
summary = "Ann and Bo are a couple who hike long routes together."
checked = 2026-11-17
[[author.source]]
url = "https://annandbo.example/"
publisher = "Ann and Bo"

[[author]]
name = "Big Club"
kind = "organisation"
credits = ["Big Club"]
summary = "Big Club is a club that the checker would refuse to describe."
bio = "{BIO}"
'''
PRONOUN = re.compile(r"\b(he|she|him|his|her|hers|they|them|their|theirs)\b", re.I)


class AuthorTest(unittest.TestCase):
    def fixture_root(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        with open(os.path.join(d, "authors.toml"), "w") as f:
            f.write(AUTHORS_FIXTURE)
        return d

    def fixture(self, credits):
        root = self.fixture_root()
        recs = self.routes(credits)
        gs = authors.author_pages(recs, root)
        return recs, root, {g["name"]: g for g in gs}, gs

    def page(self, name, credits):
        recs, root, by, gs = self.fixture(credits)
        return authors.author_page(by[name], recs, SITE, gs)

    @staticmethod
    def head(body):
        html = str(body)
        return html[:html.index('class="container section place"')]

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
        self.assertIn('<p class="entry__by">With <a href="/authors/andrew-skurka/">Andrew Skurka</a></p>', str(body))
        self.assertEqual(person["@type"], "Person")

    def test_featured_authors_lead_the_page_with_their_routes_as_the_site_s_rows(self):
        recs = self.routes(["Cam Honan"] * 3 + ["A Club"])
        _, _, body, _ = authors.index_page(recs, SITE, ROOT)
        html = str(body)
        self.assertNotIn("<table", html)
        self.assertNotIn("shelf", html)
        head = '<h2 class="results__group"><a href="/authors/cam-honan/">Cam Honan</a> <span class="results__n">3 routes</span></h2>'
        self.assertIn(head, html)
        rows = html[html.index(head):]
        self.assertEqual(rows[:rows.index("</ol>")].count('<li class="entry"'), 3)
        self.assertIn('class="len__mi"', rows)  # lengths follow the units switch
        self.assertNotIn('class="results__group"><a href="/authors/a-club/"', html)
        self.assertIn('/authors/a-club/', html)  # listed among the other authors

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
        self.assertNotIn("<table", str(body))
        self.assertIn('<li class="entry"', str(body))
        self.assertLessEqual(len(title), 60)
        self.assertEqual(person["name"], one["name"])
        club = next(g for g in gs if g["kind"] == "")  # a credit with no entry in authors.toml
        self.assertEqual(club["kind"], "")
        self.assertIsNone(authors.author_page(club, real, SITE, gs)[5])

    def test_the_top_section_is_every_author_at_the_threshold_and_follows_it(self):
        real = [r for r in records.load_records(ROOT) if r.get("kind") == "route"]
        gs = authors.author_pages(real, ROOT)
        top = authors.prominent(gs)
        self.assertTrue(top)
        self.assertTrue(all(len(g["routes"]) >= authors.PROMINENT_MIN for g in top))
        self.assertEqual(len(top), sum(1 for g in gs if len(g["routes"]) >= authors.PROMINENT_MIN and authors.is_human(g)))
        self.assertTrue(all(authors.is_human(g) for g in top))  # only people lead
        counts = [len(g["routes"]) for g in top]
        self.assertEqual(counts, sorted(counts, reverse=True))
        body = str(authors.index_page(real, SITE, ROOT)[2])
        self.assertLess(body.index('id="most-routes"'), body.index('class="browse-about"'))
        for g in top:
            self.assertLess(body.index(f'<h2 class="results__group"><a href="/authors/{g["slug"]}/">'), body.index('class="browse-about"'))
        self.assertEqual(body.count('<h2 class="results__group">'), len(top))
        old = authors.PROMINENT_MIN
        try:
            authors.PROMINENT_MIN = 5
            self.assertEqual({g["name"] for g in authors.prominent(gs)}, {"Brett Tucker", "Andrew Skurka", "Bruce Grubbs", "Douglas Lorain", "Mike White"})
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


    def test_the_head_is_the_name_the_summary_and_a_line_of_facts(self):
        title, desc, body, _, _, _ = self.page("Jo Walker", ["Jo Walker", "Jo Walker", "Jo Walker and Sam Hill"])
        head = self.head(body)
        self.assertIn('<p class="kicker">Route author</p><h1>Jo Walker</h1>', head)
        self.assertIn('<p class="page-head__lede">Jo Walker is a hiker who works out long desert routes.</p>', head)
        self.assertIn('<p class="page-head__facts"><span>3 routes</span>', head)
        self.assertIn('<a href="https://jowalker.example/">jowalker.example</a>', head)
        self.assertNotIn("Routes by", head)
        self.assertNotIn("Sam Hill", head)  # the joint credit is in its row only
        self.assertNotIn("credit", head.lower())
        self.assertTrue(desc.startswith("Jo Walker is a hiker"))
        self.assertLessEqual(len(desc), common.DESCRIPTION_LIMIT)
        self.assertLessEqual(len(title), authors.TITLE_LIMIT)
        self.assertTrue(title.startswith("Jo Walker"))

    def test_the_joint_credit_is_named_on_its_row_and_nowhere_else(self):
        _, _, body, _, _, _ = self.page("Jo Walker", ["Jo Walker", "Jo Walker and Sam Hill"])
        html = str(body)
        row = '<p class="entry__by">With <a href="/authors/sam-hill/">Sam Hill</a></p>'
        self.assertEqual(html.count(row), 1)
        rows = html[:html.index('class="browse-about"')]
        self.assertEqual(rows.count("Sam Hill"), 1)  # (each route's "In brief" after the rows gives its credit as written)
        self.assertEqual(html.count('class="entry__by"'), 1)  # the route that is Jo's alone has no author line
        self.assertNotIn("also credited", html)

    def test_the_rest_of_a_credit_that_names_no_one_else_is_given_on_its_row(self):
        recs = self.routes(["Andrew Skurka", "Andrew Skurka and friends"])
        g = {"name": "Andrew Skurka", "slug": "andrew-skurka", "kind": "person", "entry": {}, "credits": set(),
             "routes": recs, "others": {}}
        self.assertEqual(authors.with_html(g, recs[0], {}), "")
        self.assertEqual(str(authors.with_html(g, recs[1], {})), "With friends")

    def test_the_about_section_follows_the_rows_with_its_sources(self):
        _, _, body, _, _, _ = self.page("Jo Walker", ["Jo Walker"])
        html = str(body)
        self.assertIn('<h2 id="about-author">About Jo Walker</h2>', html)
        self.assertLess(html.index('class="entries"'), html.index('id="about-author"'))
        self.assertLess(html.index('id="about-author"'), html.index('id="in-brief"'))
        about = html[html.index('id="about-author"'):html.index('id="in-brief"')]
        self.assertIn(f'<p class="author-about__bio">{BIO}</p>', about.replace("&#x27;", "'"))
        self.assertIn('<a href="https://jowalker.example/about/">Jo Walker&#x27;s site</a>', about.replace("&#39;", "&#x27;"))
        self.assertIn('<a href="https://magazine.example/jo/">A Magazine</a>', about)
        self.assertIn('<time datetime="2026-11-17">2026-11-17</time>', about)

    def test_with_no_summary_the_head_is_a_plain_sentence_of_fact_and_no_pronoun(self):
        for name, credits in (("Sam Hill", ["Jo Walker and Sam Hill", "Jo Walker and Sam Hill"]),
                              ("Lone Hiker", ["Lone Hiker"]), ("Big Club", ["Big Club", "Big Club"])):
            title, desc, body, _, _, _ = self.page(name, credits)
            head = self.head(body)
            self.assertIn(f'<p class="page-head__lede">{name} is credited with ', head)
            self.assertNotIn('id="about-author"', str(body))
            text = re.sub(r"<[^>]+>", " ", str(body))
            self.assertIsNone(PRONOUN.search(re.sub(r"In brief\..*", "", text, flags=re.S)), name)
            self.assertIsNone(PRONOUN.search(title + " " + desc), name)

    def test_an_organisation_shows_nothing_about_itself_and_is_not_a_person(self):
        _, desc, body, _, _, jsonld = self.page("Big Club", ["Big Club"])
        html = str(body)
        self.assertNotIn("checker would refuse", html + desc)
        self.assertNotIn("a long way", html)
        self.assertIsNone(jsonld)

    def test_each_kind(self):
        recs, root, by, gs = self.fixture(["Jo Walker", "Ann and Bo", "Big Club", "Nobody Listed"])
        self.assertEqual({n: g["kind"] for n, g in by.items()},
                         {"Jo Walker": "person", "Ann and Bo": "people", "Big Club": "organisation", "Nobody Listed": ""})
        self.assertEqual([n for n, g in by.items() if authors.is_human(g)], ["Ann and Bo", "Jo Walker"])
        _, _, body, _, _, jsonld = authors.author_page(by["Ann and Bo"], recs, SITE, gs)
        self.assertIn('<p class="kicker">Route authors</p><h1>Ann and Bo</h1>', str(body))
        self.assertIn("Ann and Bo are a couple", str(body))
        self.assertIsNone(jsonld)  # a pair is not one Person
        self.assertIsNone(authors.author_page(by["Nobody Listed"], recs, SITE, gs)[5])

    def test_a_person_s_json_ld_carries_the_summary_and_own_site(self):
        _, _, _, _, _, node = self.page("Jo Walker", ["Jo Walker"])
        self.assertEqual(node["@type"], "Person")
        self.assertEqual(node["name"], "Jo Walker")
        self.assertEqual(node["description"], "Jo Walker is a hiker who works out long desert routes.")
        self.assertEqual(node["url"], "https://jowalker.example/")
        self.assertEqual(node["sameAs"], ["https://jowalker.example/"])
        _, _, _, _, _, bare = self.page("Sam Hill", ["Jo Walker and Sam Hill"])
        self.assertNotIn("description", bare)

    def test_only_people_lead_the_index(self):
        credits = ["Jo Walker"] * 3 + ["Ann and Bo"] * 3 + ["Big Club"] * 4 + ["Nobody Listed"] * 5 + ["Sam Hill and Jo Walker"]
        recs = self.routes(credits)
        root = self.fixture_root()
        gs = authors.author_pages(recs, root)
        self.assertEqual([g["name"] for g in authors.prominent(gs)], ["Ann and Bo", "Jo Walker"])
        html = str(authors.index_page(recs, SITE, root)[2])
        lead = html[:html.index('class="browse-about"')]
        self.assertIn('<div class="results__lead"><h2 class="results__group"><a href="/authors/jo-walker/">Jo Walker</a>', lead)
        self.assertIn('<p class="results__intro">Jo Walker is a hiker who works out long desert routes.</p>', lead)
        self.assertIn('/authors/ann-and-bo/">Ann and Bo</a>', lead)
        for name in ("big-club", "nobody-listed"):
            self.assertNotIn(f'class="results__group"><a href="/authors/{name}/"', lead)
            self.assertIn(f'/authors/{name}/', html)
        rest = html[html.index('class="author-list"'):]
        self.assertGreater(rest.index("/authors/big-club/"), rest.index("/authors/nobody-listed/"))  # organisations last
        self.assertNotIn("checker would refuse", html)
        self.assertNotIn("<table", html)

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

    def test_the_routes_and_authors_clause_can_be_left_out(self):
        recs = [fake(i, km=mi(100 * i)) for i in (1, 2, 3)]
        for r in recs:
            r["name"] = f"Name{r['id']}"
            r["derived"] = {**r.get("derived", {}), "kind": "route"}
            r["route"] = {"creator": "A" if r["id"] == "t1" else "B"}
        self.assertIn("routes by 2 authors", str(summary.facts(recs, recs)))
        self.assertNotIn("routes by", str(summary.facts(recs, recs, by_authors=False)))
        self.assertNotIn("are routes", str(summary.facts(recs, recs, by_authors=False)))

    def test_a_publisher_with_two_pages_is_named_once_with_numbered_links(self):
        html = authors.source_links([
            {"publisher": "The Trek", "url": "https://a/1"}, {"publisher": "Gear", "url": "https://g"},
            {"publisher": "The Trek", "url": "https://a/2"}])
        self.assertEqual(html, ['The Trek (<a href="https://a/1">1</a>, <a href="https://a/2">2</a>)',
                                '<a href="https://g">Gear</a>'])

    def test_a_small_place_gets_a_paragraph_for_each_trail(self):
        recs = [fake(1, hike={"summary": "First sentence. Second sentence here.", "high_point_m": 2000, "high_point": "Top"})]
        text = str(summary.details(recs))
        self.assertIn("Second sentence here.", text)
        self.assertIn("Its high point is Top", text)
        self.assertEqual(str(summary.details([fake(i) for i in range(summary.DETAIL_MAX + 1)])), "")

    def test_place_page_says_what_its_trails_are_after_the_rows_without_arithmetic(self):
        recs = [fake(i, regions=["AZ"]) for i in range(4)] + [fake(5, regions=["UT"])]
        title, desc, body, _ = regions.region_page("us-az", recs, SITE)
        body = str(body)
        self.assertIn("The longest is", body)
        self.assertNotIn("percent", body)
        self.assertLess(body.index('class="browse__list"'), body.index("The longest is"))
        self.assertEqual(body[body.index('class="browse-about"'):].count("<p>"), 1)  # one short paragraph


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

    def method_text(self):
        title, desc, body = reference.method_page(self.records, SITE, ROOT)
        return re.sub(r"\s+", " ", html_unescape(re.sub(r"<[^>]+>", " ", str(body))))

    def test_the_reference_page_counts_stated_and_estimated_seasons(self):
        text = self.method_text()
        kinds = {k: sum(1 for r in self.records if facets.season_kind(r) == k) for k in ("stated", "judged", "estimated")}
        self.assertEqual(sum(kinds.values()), len(self.records))
        self.assertIn(f"A season a page states Records with it {kinds['stated']} Records without {len(self.records) - kinds['stated']}", text)
        self.assertIn(f"A season estimated from the climate and similar trails Records with it {kinds['estimated']} Records without {len(self.records) - kinds['estimated']}", text)
        self.assertIn(f"A season set from pages that differ Records with it {kinds['judged']} Records without {len(self.records) - kinds['judged']}", text)
        self.assertIn(f"All trails Trails {len(self.records)}", text)

    def test_the_reference_page_gives_the_blind_test_from_its_file(self):
        blind = datafiles.blind_test(ROOT)
        text = self.method_text()
        self.assertIn(f"the method was run blind on {blind['tested']} trails whose seasons a page does state", text)
        self.assertIn(f"{blind['matched']} of {blind['tested']} ({round(blind['share'] * 100)} percent) had their first "
                      f"and last months within a month of the page\u2019s; {blind['strict_matched']} "
                      f"({round(blind['strict_share'] * 100)} percent) also had no wrong gap in the middle", text)
        for name, v in blind["by_confidence"].items():
            self.assertIn(f"{name} {v['matched']} of {v['tested']} ({round(v['share'] * 100)} percent) and "
                          f"{v['strict_matched']} ({round(v['strict_share'] * 100)} percent)", text)
        self.assertIn("not a promise for any one trail", text)

    def test_the_glossary_no_longer_says_only_some_records_state_a_season(self):
        season = next(t for t in reference.terms(ROOT) if t["id"] == "season")
        self.assertNotIn("Only some", season["definition"])
        self.assertIn("estimated", season["definition"])

    def test_every_place_page_has_a_summary_paragraph(self):
        by_slug, _ = regions.collect_regions(self.records)
        for slug in by_slug:
            with open(os.path.join(builtsite.ensure(), "regions", slug, "index.html"), encoding="utf-8") as f:
                body = f.read()
            self.assertIn('class="browse-about"', body)
            if len(by_slug[slug]["records"]) > 1:
                # "The longest is" where every trail is wholly in the place, else "passes through" (olt/summary.py)
                self.assertTrue("The longest is" in str(body) or "The longest trail that passes through" in str(body))


if __name__ == "__main__":
    unittest.main()
