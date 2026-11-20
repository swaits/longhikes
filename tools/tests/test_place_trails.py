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


if __name__ == "__main__":
    unittest.main()
