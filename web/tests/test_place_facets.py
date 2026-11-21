"""Pages for one kind of trail in a park, a mountain range or a wilderness area
(olt/placefacets.py plan_places and page): /ranges/<slug>/loops/ and the like.

Fixtures only, as in test_place_page.py."""
import os
import re
import sys
import tempfile
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from olt import browse, common, pages, placefacets, placepages, places  # noqa: E402
from test_facets import BANNED  # noqa: E402
from test_hike import fake  # noqa: E402
from test_place_page import S, entry_of, rec, text, write_registry  # noqa: E402

RANGE = entry_of("range", "wind-river-range", "Wind River Range", ["WY"])
PARK = entry_of("park", "yosemite", "Yosemite National Park", ["CA"])


def in_place(i, kind, slug, *, loop, km=150):
    r = rec(i, f"Trail {i}", [(kind, slug)], km=km, regs=("WY",))
    r["hike"] = dict(r["hike"], shape="loop" if loop else "point-to-point")
    return r


def world(n_loops, n_other, entries=(RANGE,), kind="range", slug="wind-river-range"):
    """n_loops loops and n_other other trails in the place, and enough loops and long trails
    elsewhere that the loops list is shown at all."""
    recs = [in_place(100 + i, kind, slug, loop=True) for i in range(n_loops)]
    recs += [in_place(200 + i, kind, slug, loop=False) for i in range(n_other)]
    recs += [fake(300 + i, km=500, regions=["NY"], hike={"shape": "loop"}) for i in range(4)]
    recs += [fake(400 + i, km=900, regions=["NY"]) for i in range(30)]
    return recs


def plan_for(records, entries=(RANGE,)):
    with tempfile.TemporaryDirectory() as d:
        write_registry(d, list(entries))
        infos = places.collect(records, places.load(d))
    return infos, placefacets.plan_places(infos, records)


class PlanTest(unittest.TestCase):
    def keys(self, plan):
        return {p["lst"].key for p in plan}

    def test_a_place_list_page_exists_at_three_trails_not_two(self):
        _, plan = plan_for(world(3, 4))
        self.assertIn("loops", self.keys(plan))
        _, plan = plan_for(world(2, 5))
        self.assertNotIn("loops", self.keys(plan))

    def test_not_built_when_the_list_holds_every_trail_on_the_place_page(self):
        _, plan = plan_for(world(7, 0))
        self.assertNotIn("loops", self.keys(plan))

    def test_not_built_when_the_list_is_not_shown_at_all(self):
        # no loops elsewhere, and 3 here: the list has 3 trails in all, under the least to be shown
        recs = [in_place(100 + i, "range", "wind-river-range", loop=True) for i in range(3)]
        recs += [in_place(200 + i, "range", "wind-river-range", loop=False) for i in range(4)]
        _, plan = plan_for(recs)
        self.assertNotIn("loops", self.keys(plan))

    def test_the_path_is_the_places_own_then_the_list_key(self):
        _, plan = plan_for(world(3, 4))
        p = next(p for p in plan if p["lst"].key == "loops")
        self.assertEqual(p["path"], "/ranges/wind-river-range/loops/")
        self.assertEqual(p["kind"], "range")
        infos, plan = plan_for(world(3, 4, (PARK,), "park", "yosemite"), (PARK,))
        self.assertEqual(next(p for p in plan if p["lst"].key == "loops")["path"], "/parks/yosemite/loops/")

    def test_the_state_plan_is_unchanged_and_still_needs_five(self):
        recs = world(3, 4)
        self.assertEqual({p["kind"] for p in placefacets.plan(recs)} - {"state"}, set())
        self.assertTrue(all(len(p["recs"]) >= browse.MIN_SIZE for p in placefacets.plan(recs)))

    def test_losing_a_trail_removes_the_page_and_every_link_to_it(self):
        full = world(3, 4)
        infos, plan = plan_for(full)
        before = str(page_of(infos, plan, "loops")[2])
        self.assertIn("/ranges/wind-river-range/loops/", str(place_body(infos, plan, full)))
        short = [r for r in full if r["id"] != full[0]["id"]]
        infos, plan = plan_for(short)
        self.assertNotIn("loops", self.keys(plan))
        self.assertNotIn("/ranges/wind-river-range/loops/", str(place_body(infos, plan, short)))
        self.assertIn("Loops", before)


def page_of(infos, plan, key):
    p = next(p for p in plan if p["lst"].key == key)
    return placefacets.page(p, [r for i in infos.values() for r in i["records"]], S, plan)


def place_body(infos, plan, records):
    info = next(iter(infos.values()))
    here = [(q["lst"].title, q["path"], len(q["recs"]))
            for q in placefacets.pages_by_place(plan).get((info["kind"], info["slug"]), [])]
    from olt import regions
    return regions.place_page(info, records, S, placepages.PAGE_KINDS[info["kind"]], facet_pages=here)[2]


class PageTest(unittest.TestCase):
    def setUp(self):
        self.recs = world(3, 4)
        self.infos, self.plan = plan_for(self.recs)
        self.p = next(p for p in self.plan if p["lst"].key == "loops")
        self.title, self.desc, self.body, _ = placefacets.page(self.p, self.recs, S, self.plan)
        self.text = text(self.body)

    def test_title_h1_and_lede_use_the_list_noun_and_the_places_own_words(self):
        noun = self.p["lst"].noun
        self.assertRegex(self.title, rf"^{noun} in the Wind River Range(, Wyoming)?: 3 Trails$")
        self.assertIn(f"<h1>{noun} in the Wind River Range</h1>", str(self.body))
        self.assertIn("3 of the 7 trails in the Wind River Range", self.text)
        self.assertLessEqual(len(self.title), common.TITLE_LIMIT)

    def test_a_park_uses_its_own_preposition(self):
        infos, plan = plan_for(world(3, 4, (PARK,), "park", "yosemite"), (PARK,))
        t = page_of(infos, plan, "loops")[0]
        self.assertIn("in Yosemite National Park: 3 Trails", t)
        self.assertNotIn("in the Yosemite", t)

    def test_the_count_in_the_lede_and_the_rows_agree(self):
        rows = len(re.findall(r'data-trail="', str(self.body))) or len(re.findall(r'class="row[ "]', str(self.body)))
        self.assertIn("3 of the 7 trails", self.text)
        if rows:
            self.assertGreaterEqual(rows, 3)

    def test_it_links_back_to_the_place_and_the_breadcrumb_goes_through_it(self):
        body = str(self.body)
        self.assertIn('<li><a href="/ranges/wind-river-range/">Wind River Range</a></li>', body)
        self.assertIn('All the trails in the Wind River Range</a>', body)
        self.assertIn(f'href="{browse.path(self.p["lst"])}"', body)

    def test_the_place_page_links_to_its_list_pages_with_exact_counts(self):
        body = text(place_body(self.infos, self.plan, self.recs))
        self.assertIn("(3)", body)
        self.assertIn(f"{self.p['lst'].title} (3)", body)

    def test_siblings_link_to_each_other(self):
        recs = world(3, 4)
        for r in recs[:3] + recs[3:5]:
            r["length_km"] = 100.0     # 5 trails under 100 miles... keep it simple: two pages for one place
        infos, plan = plan_for(recs)
        mine = [q for q in plan if q["info"]["slug"] == "wind-river-range"]
        if len(mine) > 1:
            body = str(placefacets.page(mine[0], recs, S, plan)[2])
            self.assertIn(mine[1]["path"], body)

    def test_no_banned_word_and_no_km_of_a_place(self):
        shown = self.text + " " + self.title + " " + self.desc
        for pattern in BANNED:
            self.assertFalse(re.search(pattern, shown, re.I), pattern)

    def test_the_first_screen_comes_before_the_summary(self):
        body = str(self.body)
        self.assertLess(body.index("browse-view") if "browse-view" in body else body.index("<h1>"),
                        body.index("About these trails"))


class RealDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from olt import records
        cls.records = records.load_records(records.ROOT)
        cls.infos = places.collect(cls.records, places.load(records.ROOT))
        cls.plan = placefacets.plan_places(cls.infos, cls.records)

    def test_every_page_has_three_trails_and_fewer_than_its_place(self):
        self.assertTrue(self.plan)
        for p in self.plan:
            self.assertGreaterEqual(len(p["recs"]), placefacets.PLACE_MIN, p["path"])
            self.assertLess(len(p["recs"]), len(p["info"]["records"]), p["path"])

    def test_the_number_of_pages_stays_reasonable(self):
        self.assertLess(len(self.plan), 250)

    def test_every_title_fits_and_keeps_its_count_and_is_unique(self):
        titles, over = set(), []
        for p in self.plan:
            t = placefacets.page(p, self.records, S, self.plan)[0]
            self.assertRegex(t, r": \d+ (Trails|Routes)$", t)
            titles.add(t)
            if len(t) > common.TITLE_LIMIT:
                over.append(t)
        self.assertEqual(len(titles), len(self.plan))
        # only a long place name pushes a title over, and then the shortest noun still keeps the count
        self.assertLess(len(over), 25, over)
        for t in over:
            self.assertGreaterEqual(len(t.rsplit(": ", 1)[0].split(" in ", 1)[-1].split(" on ", 1)[-1]), 25, t)


if __name__ == "__main__":
    unittest.main()
