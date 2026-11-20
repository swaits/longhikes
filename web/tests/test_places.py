"""The place loader: registry, membership closed over `within`, and which places
get a page (olt/places.py). Fixtures only; no built site."""
import os
import sys
import tempfile
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from olt import places  # noqa: E402
from test_hike import fake  # noqa: E402


def entry(kind, slug, name, where=("WY",), within=()):
    return {"kind": kind, "slug": slug, "name": name, "where": list(where),
            "within": list(within), "source": "gmba-v2", "source_id": "1",
            "source_version": "2026-11-20", "box": [-110.0, 42.5, -108.5, 43.5]}


def registry(*entries):
    return {(e["kind"], e["slug"]): e for e in entries}


def rec(i, *pls, name=None):
    r = fake(i)
    if name:
        r["name"] = name
    r["place"] = [{"kind": k, "slug": s, "basis": b,
                   **({"km": 10.0} if b == "track" else {"source": "https://example.org/"})}
                  for k, s, b in pls]
    return r


WIND = entry("range", "wind-river-range", "Wind River Range")
YOSE = entry("park", "yosemite", "Yosemite National Park", where=("CA",))


class CollectTest(unittest.TestCase):
    def test_a_range_gets_a_page_at_three_trails_and_not_at_two(self):
        reg = registry(WIND)
        two = [rec(1, ("range", "wind-river-range", "track")),
               rec(2, ("range", "wind-river-range", "track"))]
        self.assertEqual(places.collect(two, reg), {})
        three = two + [rec(3, ("range", "wind-river-range", "track"))]
        got = places.collect(three, reg)
        self.assertEqual(list(got), [("range", "wind-river-range")])
        info = got[("range", "wind-river-range")]
        self.assertEqual(info["path"], "/ranges/wind-river-range/")
        self.assertEqual(info["key"], "range/wind-river-range")
        self.assertEqual([r["id"] for r in info["records"]], ["t1", "t2", "t3"])

    def test_stated_and_track_trails_both_count(self):
        reg = registry(WIND)
        recs = [rec(1, ("range", "wind-river-range", "track")),
                rec(2, ("range", "wind-river-range", "stated")),
                rec(3, ("range", "wind-river-range", "track"))]
        self.assertIn(("range", "wind-river-range"), places.collect(recs, reg))

    def test_a_trail_in_a_nested_range_is_on_every_parent(self):
        teton = entry("range", "teton-range", "Teton Range", within=("rocky-mountains",))
        rocky = entry("range", "rocky-mountains", "Rocky Mountains",
                      where=("WY", "CO", "MT"), within=("cordillera",))
        cord = entry("range", "cordillera", "Cordillera", where=("WY", "CO"))
        reg = registry(teton, rocky, cord)
        recs = [rec(i, ("range", "teton-range", "track")) for i in (1, 2, 3)]
        mem = places.membership(recs, reg)
        for slug in ("teton-range", "rocky-mountains", "cordillera"):
            self.assertEqual([r["id"] for r in mem[("range", slug)]], ["t1", "t2", "t3"], slug)
        self.assertIn(("range", "rocky-mountains"), places.collect(recs, reg))

    def test_slugs_repeat_across_kinds(self):
        park = entry("park", "glacier", "Glacier National Park", where=("MT",))
        wild = entry("wilderness", "glacier", "Glacier Peak Wilderness", where=("WA",))
        reg = registry(park, wild)
        recs = [rec(i, ("park", "glacier", "track")) for i in (1, 2, 3)]
        recs += [rec(i, ("wilderness", "glacier", "track")) for i in (4, 5, 6)]
        got = places.collect(recs, reg)
        self.assertEqual(got[("park", "glacier")]["path"], "/parks/glacier/")
        self.assertEqual(got[("wilderness", "glacier")]["path"], "/wilderness/glacier/")
        self.assertEqual([r["id"] for r in got[("park", "glacier")]["records"]], ["t1", "t2", "t3"])
        self.assertEqual([r["id"] for r in got[("wilderness", "glacier")]["records"]], ["t4", "t5", "t6"])

    def test_a_parent_is_counted_once_when_a_trail_is_in_two_children(self):
        a = entry("range", "a-range", "A Range", within=("parent-range",))
        b = entry("range", "b-range", "B Range", within=("parent-range",))
        p = entry("range", "parent-range", "Parent Range")
        reg = registry(a, b, p)
        recs = [rec(1, ("range", "a-range", "track"), ("range", "b-range", "track"))]
        mem = places.membership(recs, reg)
        self.assertEqual([r["id"] for r in mem[("range", "parent-range")]], ["t1"])

    def test_a_doubled_wilderness_gets_no_page_when_the_park_holds_the_same_trails(self):
        park = entry("park", "example", "Example National Park", where=("CA",))
        wild = entry("wilderness", "example", "Example National Park Wilderness", where=("CA",))
        reg = registry(park, wild)
        recs = [rec(i, ("park", "example", "track"), ("wilderness", "example", "track"))
                for i in (1, 2, 3)]
        got = places.collect(recs, reg)
        self.assertIn(("park", "example"), got)
        self.assertNotIn(("wilderness", "example"), got)
        # different sets: both keep their pages
        recs.append(rec(4, ("wilderness", "example", "track")))
        self.assertIn(("wilderness", "example"), places.collect(recs, reg))

    def test_a_range_gets_no_page_when_a_park_of_the_same_stem_holds_the_same_trails(self):
        park = entry("park", "olympic-national-park", "Olympic National Park", where=("WA",))
        rng = entry("range", "olympic-mountains", "Olympic Mountains", where=("WA",))
        other = entry("range", "teton-range", "Teton Range", where=("WY",))
        gt = entry("park", "grand-teton-national-park", "Grand Teton National Park")
        reg = registry(park, rng, other, gt)
        recs = [rec(i, ("park", "olympic-national-park", "track"),
                    ("range", "olympic-mountains", "track"),
                    ("park", "grand-teton-national-park", "track"),
                    ("range", "teton-range", "track")) for i in (1, 2, 3)]
        got = places.collect(recs, reg)
        self.assertIn(("park", "olympic-national-park"), got)
        self.assertNotIn(("range", "olympic-mountains"), got)
        # Grand Teton and the Teton Range do not share a stem: both keep their pages
        self.assertIn(("park", "grand-teton-national-park"), got)
        self.assertIn(("range", "teton-range"), got)
        # a range with a different set of trails keeps its page
        recs.append(rec(4, ("range", "olympic-mountains", "track")))
        self.assertIn(("range", "olympic-mountains"), places.collect(recs, reg))

    def test_records_are_a_to_z(self):
        reg = registry(WIND)
        recs = [rec(1, ("range", "wind-river-range", "track"), name="Zebra Trail"),
                rec(2, ("range", "wind-river-range", "track"), name="The Apple Trail"),
                rec(3, ("range", "wind-river-range", "track"), name="Middle Trail")]
        got = places.collect(recs, reg)[("range", "wind-river-range")]
        self.assertEqual([r["name"] for r in got["records"]],
                         ["The Apple Trail", "Middle Trail", "Zebra Trail"])

    def test_title_name_adds_the_state_for_a_range_with_one_state_only(self):
        reg = registry(WIND, YOSE)
        recs = [rec(i, ("range", "wind-river-range", "track"), ("park", "yosemite", "track"))
                for i in (1, 2, 3)]
        got = places.collect(recs, reg)
        self.assertEqual(got[("range", "wind-river-range")]["title_name"],
                         "Wind River Range, Wyoming")
        self.assertEqual(places.title_name(got[("range", "wind-river-range")]),
                         "Wind River Range, Wyoming")
        self.assertEqual(got[("park", "yosemite")]["title_name"], "Yosemite National Park")
        multi = dict(got[("range", "wind-river-range")], where=["WY", "CO", "MT", "UT"])
        self.assertEqual(places.title_name(multi), "Wind River Range")

    def test_of_record_leaves_out_a_place_below_the_minimum(self):
        small = entry("park", "small", "Small Park", where=("WY",))
        reg = registry(WIND, small)
        recs = [rec(1, ("range", "wind-river-range", "track"), ("park", "small", "track"))]
        recs += [rec(i, ("range", "wind-river-range", "track")) for i in (2, 3)]
        infos = places.collect(recs, reg)
        mine = places.of_record(recs[0], infos)
        self.assertEqual([(i["kind"], i["slug"]) for i in mine], [("range", "wind-river-range")])

    def test_of_record_includes_a_parent_range(self):
        teton = entry("range", "teton-range", "Teton Range", within=("rocky-mountains",))
        rocky = entry("range", "rocky-mountains", "Rocky Mountains", where=("WY", "CO"))
        reg = registry(teton, rocky)
        recs = [rec(i, ("range", "teton-range", "track")) for i in (1, 2, 3)]
        infos = places.collect(recs, reg)
        names = [i["name"] for i in places.of_record(recs[0], infos)]
        self.assertEqual(names, ["Rocky Mountains", "Teton Range"])

    def test_in_state_matches_the_registry_where(self):
        reg = registry(WIND, YOSE)
        recs = [rec(i, ("range", "wind-river-range", "track"), ("park", "yosemite", "track"))
                for i in (1, 2, 3)]
        infos = places.collect(recs, reg)
        wy = places.in_state(infos, "US-WY")
        self.assertEqual([i["name"] for i in wy], ["Wind River Range"])
        self.assertEqual(places.in_state(infos, "US-UT"), [])

    def test_path_and_kinds(self):
        self.assertEqual(places.path("park", "glacier"), "/parks/glacier/")
        self.assertEqual(places.path("range", "wind-river-range"), "/ranges/wind-river-range/")
        self.assertEqual(places.path("wilderness", "bob-marshall"), "/wilderness/bob-marshall/")
        self.assertEqual(places.KINDS["park"].segment, "parks")
        self.assertEqual(places.KINDS["range"].segment, "ranges")
        self.assertEqual(places.KINDS["wilderness"].segment, "wilderness")
        self.assertEqual(places.PAGE_MIN, 3)

    def test_load_reads_places_toml_keyed_by_kind_and_slug(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "places.toml"), "w", encoding="utf-8") as f:
                f.write('[[place]]\nslug = "wind-river-range"\nkind = "range"\n'
                        'name = "Wind River Range"\nwhere = ["WY"]\nsource = "gmba-v2"\n'
                        'source_id = "1"\nsource_version = "2026-11-20"\n'
                        'box = [-110.0, 42.5, -108.5, 43.5]\n')
            reg = places.load(d)
        self.assertEqual(reg[("range", "wind-river-range")]["name"], "Wind River Range")

    def test_an_unknown_place_on_a_record_is_ignored(self):
        reg = registry(WIND)
        recs = [rec(1, ("range", "nowhere", "track"))]
        self.assertEqual(places.collect(recs, reg), {})
        self.assertEqual(places.membership(recs, reg)[("range", "wind-river-range")], [])


if __name__ == "__main__":
    unittest.main()
