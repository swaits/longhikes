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

    def test_where_is_the_regions_most_trails_share(self):
        records = [rec("a", ["WY"], self.park_only), rec("b", ["WY", "CO"], self.park_only),
                   rec("c", ["WY"], self.park_only), rec("d", ["UT"], self.park_only)]
        p = P.propose(records, [self.park])
        self.assertEqual(p.per_place[("park", "alpha-park")].where, ["WY"])

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


if __name__ == "__main__":
    unittest.main()
