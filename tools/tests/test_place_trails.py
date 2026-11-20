"""Tests for tools/place_trails.py. Needs the tool's venv (.venv-places); with the system
Python the whole file is skipped, not failed. No network: synthetic outlines and tracks.

    .venv-places/bin/python -m unittest discover tools/tests -p "test_place_trails.py"
"""
import json
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

try:
    import shapely  # noqa: F401
    HAVE = True
except ImportError:
    HAVE = False

if HAVE:
    from shapely.geometry import LineString, MultiLineString, Polygon
    import check_places as C
    import place_trails as P

# At latitude 43, 0.0063 degrees of latitude is about 0.70 km.
BOX = None  # built in setUp when shapely is there


def write_track(d, name, lines):
    feats = [{"type": "Feature", "properties": {},
              "geometry": {"type": "LineString", "coordinates": line}} for line in lines]
    with open(os.path.join(d, name), "w") as f:
        json.dump({"type": "FeatureCollection", "features": feats}, f)


def write_record(d, line_file="line.geojson"):
    with open(os.path.join(d, "trail.toml"), "w") as f:
        f.write(f'id = "x"\n[source]\nline_file = "{line_file}"\n')


@unittest.skipUnless(HAVE, "shapely (the .venv-places venv) is not installed")
class GeometryTest(unittest.TestCase):
    def setUp(self):
        self.box = Polygon([(-110.0, 43.0), (-109.0, 43.0), (-109.0, 44.0), (-110.0, 44.0)])

    def test_pieces_inside_are_summed(self):
        parts = [LineString([(-109.5 + 0.1 * i, 43.5), (-109.5 + 0.1 * i, 43.5063)]) for i in range(3)]
        km = P.km_inside(MultiLineString(parts), self.box)
        self.assertAlmostEqual(km, 2.1, delta=0.15)
        self.assertGreater(km, P.MIN_KM)

    def test_a_skimming_track_is_under_the_threshold(self):
        # about 1.5 km inside
        track = LineString([(-109.5, 43.5), (-109.5, 43.5135)])
        km = P.km_inside(track, self.box)
        self.assertAlmostEqual(km, 1.5, delta=0.1)
        self.assertLess(km, P.MIN_KM)

    def test_a_hole_is_not_inside(self):
        hole = [(-109.6, 43.4), (-109.4, 43.4), (-109.4, 43.6), (-109.6, 43.6)]
        outline = Polygon(self.box.exterior.coords, [hole])
        track = LineString([(-109.5, 43.45), (-109.5, 43.55)])
        self.assertEqual(P.km_inside(track, outline), 0.0)

    def test_alternates_are_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            write_record(d)
            write_track(d, "line.geojson", [[[-108.0, 43.5], [-108.0, 43.51]]])  # outside
            write_track(d, "alternates.geojson", [[[-109.5, 43.1], [-109.5, 43.9]]])  # long, inside
            track = P.main_track(d)
            self.assertIsNotNone(track)
            self.assertEqual(P.km_inside(track, self.box), 0.0)

    def test_a_record_with_no_line_file_has_no_track(self):
        with tempfile.TemporaryDirectory() as d:
            write_record(d, line_file="")
            self.assertIsNone(P.main_track(d))

    def test_box_of_is_west_south_east_north_rounded(self):
        outline = Polygon([(-110.004, 42.501), (-108.499, 42.501), (-108.499, 43.499), (-110.004, 43.499)])
        self.assertEqual(P.box_of(outline), [-110.0, 42.5, -108.5, 43.5])

    def test_track_hash_matches_the_validators(self):
        with tempfile.TemporaryDirectory() as d:
            write_record(d)
            write_track(d, "line.geojson", [[[-109.5, 43.5], [-109.4, 43.5]]])
            self.assertEqual(P.track_hash(d), C.track_hash(os.path.join(d, "line.geojson")))


def outline(kind, source_id, name, geom, slug=None, hint=()):
    return P.Outline(kind=kind, source="nps", source_id=source_id, name=name,
                     state_codes_hint=list(hint), geometry=geom, slug=slug or P.slugify(name))


def rec(rid, regions, track):
    return {"id": rid, "name": rid, "regions": regions, "track": track}


@unittest.skipUnless(HAVE, "shapely (the .venv-places venv) is not installed")
class ProposalTest(unittest.TestCase):
    def setUp(self):
        # Two overlapping places; vertical tracks of about 10 km inside each.
        self.park = outline("park", "P1", "Alpha Park",
                            Polygon([(-110, 43), (-109, 43), (-109, 44), (-110, 44)]), hint=["WY"])
        self.range = outline("range", "R1", "Beta Range",
                             Polygon([(-109.6, 43), (-108.6, 43), (-108.6, 44), (-109.6, 44)]))
        self.inside = LineString([(-109.5, 43.2), (-109.5, 43.29)])   # in both, ~10 km
        self.park_only = LineString([(-109.9, 43.2), (-109.9, 43.29)])
        self.outside = LineString([(-107.0, 43.2), (-107.0, 43.29)])

    def test_propose_lists_per_trail_places_and_per_place_trails(self):
        records = [rec("a", ["WY"], self.inside), rec("b", ["WY"], self.park_only),
                   rec("c", ["WY"], self.inside)]
        p = P.propose(records, [self.park, self.range])
        self.assertEqual({k for k, _ in p.per_trail["a"]}, {("park", "alpha-park"), ("range", "beta-range")})
        self.assertEqual({t for t, _ in p.per_place[("park", "alpha-park")].trails}, {"a", "b", "c"})
        self.assertEqual({t for t, _ in p.per_place[("range", "beta-range")].trails}, {"a", "c"})

    def test_a_trail_under_the_threshold_is_not_in_the_place(self):
        skim = LineString([(-109.5, 43.5), (-109.5, 43.509)])  # ~1.0 km
        p = P.propose([rec("a", ["WY"], skim)], [self.park])
        self.assertEqual(p.per_trail["a"], [])
        self.assertNotIn(("park", "alpha-park"), p.per_place)

    def test_places_with_fewer_than_three_trails_are_marked_no_page(self):
        records = [rec("a", ["WY"], self.inside), rec("b", ["WY"], self.park_only),
                   rec("c", ["WY"], self.inside)]
        p = P.propose(records, [self.park, self.range])
        self.assertTrue(p.per_place[("park", "alpha-park")].page)
        self.assertFalse(p.per_place[("range", "beta-range")].page)

    def test_near_threshold_items_are_listed_first_and_flagged(self):
        near = LineString([(-109.5, 43.5), (-109.5, 43.5153)])  # ~1.7 km: in, but near the line
        p = P.propose([rec("a", ["WY"], near), rec("b", ["WY"], self.inside)], [self.park])
        self.assertEqual(p.near[0].trail, "a")
        self.assertTrue(any(abs(km - P.MIN_KM) <= 0.5 for _, km in p.per_trail["a"]))

    def test_where_is_the_source_states_not_the_visiting_trails_states(self):
        # trails from other states visit the place: where stays the place's own
        records = [rec("a", ["WY"], self.park_only), rec("b", ["WY", "CO"], self.park_only),
                   rec("c", ["OR", "WA"], self.park_only), rec("d", ["UT"], self.park_only)]
        p = P.propose(records, [self.park])
        self.assertEqual(p.per_place[("park", "alpha-park")].where, ["WY"])

    def test_where_of_a_source_with_states_uses_them_and_drops_unknown_codes(self):
        o = outline("park", "P9", "Edge Park", self.park.geometry, hint=["MT", "ID", "PR"])
        self.assertEqual(P.where_of(o), ["ID", "MT"])

    def test_where_of_a_range_is_found_from_the_state_boxes(self):
        # wholly inside the Wyoming box, clear of every other state's box
        o = outline("range", "R5", "Wyoming Range", self.park.geometry)
        o.state_codes_hint = []
        self.assertEqual(P.where_of(o), ["WY"])

    def test_where_of_a_place_in_two_states_lists_both(self):
        both = Polygon([(-112.0, 40.0), (-110.0, 40.0), (-110.0, 42.0), (-112.0, 42.0)])
        o = outline("range", "R6", "Border Range", both)
        self.assertEqual(P.where_of(o), ["UT", "WY"])

    def test_a_hand_where_overrides_the_source_and_the_boxes(self):
        o = outline("range", "R7", "Hand Range", self.park.geometry, hint=["WY"])
        o.where_hand = ("WY", "MT")
        self.assertEqual(P.where_of(o), ["MT", "WY"])

    def test_yosemite_like_outline_is_california_only(self):
        yose = Polygon([(-120.0, 37.5), (-119.2, 37.5), (-119.2, 38.2), (-120.0, 38.2)])
        o = outline("park", "YOSE", "Yosemite National Park", yose, hint=["CA"])
        self.assertEqual(P.where_of(o), ["CA"])

    def test_a_slug_collision_inside_a_kind_gets_the_state_code(self):
        a = outline("park", "P1", "Glacier", self.park.geometry, slug=None, hint=["MT"])
        b = outline("park", "P2", "Glacier", self.range.geometry, slug=None, hint=["BC"])
        out = P.assign_slugs([a, b])
        self.assertEqual({o.slug for o in out}, {"glacier-mt", "glacier-bc"})

    def test_the_proposal_names_every_trail_with_no_track_as_needing_a_person(self):
        p = P.propose([rec("a", ["WY"], self.inside), rec("z", ["WY"], None)], [self.park])
        self.assertEqual(p.no_track, ["z"])
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "proposal.md")
            P.render_proposal(p, path)
            text = open(path).read()
        self.assertIn("needs a person", text)
        self.assertIn("z", text)

    def test_a_parent_range_is_not_stored_when_a_child_is(self):
        big = outline("range", "R0", "Big Range",
                      Polygon([(-111, 42), (-108, 42), (-108, 45), (-111, 45)]))
        big.path = "Continent > Big Range"
        self.range.path = "Continent > Big Range > Beta Range"
        p = P.propose([rec("a", ["WY"], self.inside)], [big, self.range])
        self.assertEqual({k for k, _ in p.per_trail["a"]}, {("range", "beta-range")})
        # the parent's page count still holds the trail, as measured
        self.assertEqual({t for t, _ in p.per_place[("range", "big-range")].trails}, {"a"})

    def test_one_gmba_id_outside_the_allow_list_is_not_proposed_but_is_listed_by_candidates(self):
        records = [rec(f"t{i}", ["WY"], self.inside) for i in range(3)]
        all_ranges = [dict(gmba_id="R1", name="Beta Range", path="Beta Range",
                           geometry=self.range.geometry)]
        p = P.propose(records, [])  # nothing allow-listed
        self.assertEqual(p.per_place, {})
        found = P.range_candidates(records, all_ranges, allowlisted=set())
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["gmba_id"], "R1")
        self.assertEqual(len(found[0]["trails"]), 3)


import re as _re
import tomllib as _tomllib


def make_repo(root):
    """Three tracked records and one trackless, minimal trail.toml files."""
    for rid, line in (("aa", True), ("bb", True), ("cc", True), ("zz", False)):
        d = os.path.join(root, rid)
        os.makedirs(d)
        with open(os.path.join(d, "trail.toml"), "w") as f:
            f.write(f'id = "{rid}"\nname = "{rid} Trail"\nregions = ["WY"]\n\n'
                    f'[source]\nline_file = "{"line.geojson" if line else ""}"\n\n'
                    '[[history]]\ndate = "2026-01-01"\nchange = "The record was added."\n'
                    'fields = ["record"]\nbasis = "The record\'s own source entry."\n'
                    'asked_by = "the dataset\'s own check"\noutcome = "applied"\n')
        if line:
            write_track(d, "line.geojson", [[[-109.5, 43.2], [-109.5, 43.29]]])
    with open(os.path.join(root, "places.toml"), "w") as f:
        f.write("# The place registry (test).\n")


def read_toml(path):
    with open(path, "rb") as f:
        return _tomllib.load(f)


@unittest.skipUnless(HAVE, "shapely (the .venv-places venv) is not installed")
class ApplyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        make_repo(self.root)
        self.park = outline("park", "P1", "Alpha Park",
                            Polygon([(-110, 43), (-109, 43), (-109, 44), (-110, 44)]), hint=["WY"])
        track = LineString([(-109.5, 43.2), (-109.5, 43.29)])
        records = [rec("aa", ["WY"], track), rec("bb", ["WY"], track),
                   rec("cc", ["WY"], track), rec("zz", ["WY"], None)]
        self.p = P.propose(records, [self.park])
        self.p.versions = {"nps": "2026-11-20"}
        self.pdir = os.path.join(self.root, "out")
        P.render_proposal(self.p, os.path.join(self.pdir, "proposal.md"))
        self.pjson = os.path.join(self.pdir, "proposal.json")

    def tearDown(self):
        self.tmp.cleanup()

    def trail_toml(self, rid):
        return os.path.join(self.root, rid, "trail.toml")

    def test_apply_adds_place_tables_stamp_and_hash_by_line_edits(self):
        before = open(self.trail_toml("aa")).read()
        written = P.apply(self.pjson, self.root, "2026-11-20")
        self.assertIn("aa", written)
        after = open(self.trail_toml("aa")).read()
        data = read_toml(self.trail_toml("aa"))
        self.assertEqual(data["places_checked"], "2026-11-20")
        self.assertEqual(data["places_track"],
                         C.track_hash(os.path.join(self.root, "aa", "line.geojson")))
        self.assertEqual(data["place"][0]["slug"], "alpha-park")
        # everything that was there before is still there, byte for byte, as lines
        for line in before.splitlines():
            if line.strip():
                self.assertIn(line, after.splitlines(), line)

    def test_apply_adds_one_history_entry_naming_place_with_no_distance_in_it(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        data = read_toml(self.trail_toml("aa"))
        self.assertEqual(len(data["history"]), 2)
        e = data["history"][-1]
        self.assertEqual(e["fields"], ["place"])
        self.assertEqual(e["asked_by"], "the dataset's own check")
        self.assertTrue(e["basis_url"].startswith("http"))
        self.assertIsNone(_re.search(r"\d\s*(km|mi)", e["change"] + e["basis"]))

    def test_a_rerun_that_only_changes_km_adds_no_history_and_keeps_the_stamp_date_rule(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        data = json.load(open(self.pjson))
        data["per_trail"]["aa"][0]["km"] += 1.25
        data["per_place"]["park/alpha-park"]["trails"][0]["km"] += 1.25
        p2 = os.path.join(self.pdir, "proposal2.json")
        json.dump(data, open(p2, "w"))
        P.apply(p2, self.root, "2026-12-01")
        rec = read_toml(self.trail_toml("aa"))
        self.assertEqual(len(rec["history"]), 2)  # no new entry
        self.assertEqual(rec["places_checked"], "2026-12-01")
        self.assertAlmostEqual(rec["place"][0]["km"], data["per_trail"]["aa"][0]["km"], delta=0.06)

    def test_a_rerun_that_adds_or_removes_a_place_adds_history(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        data = json.load(open(self.pjson))
        data["per_trail"]["aa"] = []
        p2 = os.path.join(self.pdir, "proposal2.json")
        json.dump(data, open(p2, "w"))
        P.apply(p2, self.root, "2026-12-01")
        rec = read_toml(self.trail_toml("aa"))
        self.assertEqual(len(rec["history"]), 3)
        self.assertNotIn("place", rec)

    def test_registry_lists_only_named_places_and_is_sorted(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        reg = read_toml(os.path.join(self.root, "places.toml"))["place"]
        self.assertEqual([e["slug"] for e in reg], ["alpha-park"])
        self.assertEqual(reg[0]["source_version"], "2026-11-20")
        self.assertEqual(reg[0]["box"], [-110.0, 43.0, -109.0, 44.0])

    def test_a_reviewed_where_in_the_registry_survives_a_rerun(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        path = os.path.join(self.root, "places.toml")
        text = open(path).read()
        self.assertIn('where = ["WY"]', text)
        open(path, "w").write(text.replace('where = ["WY"]', 'where = ["MT", "WY"]'))
        P.apply(self.pjson, self.root, "2026-12-01")
        self.assertEqual(read_toml(path)["place"][0]["where"], ["MT", "WY"])

    def test_stated_requires_an_http_source_a_quote_and_a_trackless_record(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        with self.assertRaises(ValueError):
            P.add_stated(self.root, "zz", "park", "alpha-park", "a book", "It says so.", "2026-11-20")
        with self.assertRaises(ValueError):
            P.add_stated(self.root, "zz", "park", "alpha-park", "https://example.org/", "", "2026-11-20")
        with self.assertRaises(ValueError):
            P.add_stated(self.root, "aa", "park", "alpha-park", "https://example.org/", "Q.", "2026-11-20")
        P.add_stated(self.root, "zz", "park", "alpha-park", "https://example.org/t",
                     "The trail crosses Alpha Park.", "2026-11-20")
        rec = read_toml(self.trail_toml("zz"))
        self.assertEqual(rec["place"][0]["basis"], "stated")
        self.assertEqual(rec["places_checked"], "2026-11-20")
        self.assertEqual(rec["history"][-1]["fields"], ["place"])

    def test_stamp_none_sets_places_checked_with_no_place_tables_and_no_history(self):
        P.stamp_none(self.root, "zz", "2026-11-20")
        rec = read_toml(self.trail_toml("zz"))
        self.assertEqual(rec["places_checked"], "2026-11-20")
        self.assertNotIn("place", rec)
        self.assertEqual(len(rec["history"]), 1)

    def test_check_reports_a_place_gained_lost_a_moved_boundary_and_a_place_crossing_three_trails(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        records = P.load_records(self.root)
        moved = outline("park", "P1", "Alpha Park",
                        Polygon([(-110, 43), (-109, 43), (-109, 43.25), (-110, 43.25)]), hint=["WY"])
        diffs = P.check(self.root, None, outlines=[moved], versions={"nps": "2026-11-20"},
                        records=records)
        text = "\n".join(diffs)
        self.assertIn("measurement changed", text)  # the moved boundary
        gone = outline("park", "P9", "Elsewhere Park",
                       Polygon([(-100, 43), (-99, 43), (-99, 44), (-100, 44)]), hint=["WY"])
        diffs = P.check(self.root, None, outlines=[gone], versions={"nps": "2026-11-20"},
                        records=records)
        text = "\n".join(diffs)
        self.assertIn("lost park/alpha-park", text)
        self.assertIn("crossed the 3-trail line", text)

    def test_check_exits_nonzero_with_differences_and_zero_without(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        records = P.load_records(self.root)
        self.assertEqual(P.check(self.root, None, outlines=[self.park],
                                 versions={"nps": "2026-11-20"}, records=records), [])

    def test_the_written_records_pass_check_places(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        P.stamp_none(self.root, "zz", "2026-11-20")
        trails = [read_toml(self.trail_toml(r)) for r in ("aa", "bb", "cc", "zz")]
        errors = []
        C.check(self.root, trails, errors)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
