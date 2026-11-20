"""Tests for tools/estimate_season.py. The rule tests use hand-made
normals, so they run with no network.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import estimate_season as E  # noqa: E402
import season_climate as C  # noqa: E402

PARAMS = E.Params(snow_cm_max=10.0, cold_c_min=5.0, heat_c_max=32.0)


def normals(elev, tmax, snow=None):
    return C.PointNormals(lat=45.0, lon=-110.0, elev_m=float(elev),
                          tmax_c=tuple(float(v) for v in tmax),
                          snow_cm=None if snow is None
                          else tuple(float(v) for v in snow))


class RuleTest(unittest.TestCase):
    def test_a_cold_high_point_closes_the_winter(self):
        point = normals(3000, [0, 1, 3, 6, 10, 15, 20, 20, 15, 10, 4, 1],
                        snow=[0] * 12)
        self.assertEqual(E.months_in_season([point], PARAMS),
                         [4, 5, 6, 7, 8, 9, 10])

    def test_snow_over_the_limit_closes_a_month(self):
        point = normals(3000, [10] * 12,
                        snow=[50, 50, 50, 50, 50, 50, 0, 0, 0, 0, 0, 0])
        self.assertEqual(E.months_in_season([point], PARAMS),
                         [7, 8, 9, 10, 11, 12])

    def test_heat_at_the_low_ground_closes_a_summer_month(self):
        desert = normals(400, [19, 22, 26, 31, 36, 42, 44, 43, 39, 32, 24, 19],
                         snow=[0] * 12)
        got = E.months_in_season([desert], PARAMS)
        self.assertEqual(set(got), {10, 11, 12, 1, 2, 3, 4})
        self.assertEqual(got, [1, 2, 3, 4, 10, 11, 12])

    def test_high_ground_is_the_upper_quartile_of_points(self):
        low = [normals(e, [15] * 12, snow=[0] * 12) for e in (100, 200, 300)]
        top_snow = [0, 0, 0, 0, 0, 50, 0, 0, 0, 0, 0, 0]
        high = normals(400, [15] * 12, snow=top_snow)
        got = E.months_in_season(low + [high], PARAMS)
        self.assertNotIn(6, got)  # only the highest point has June snow
        self.assertEqual(len(got), 11)

    def test_no_snow_measure_uses_temperature_alone(self):
        point = normals(3000, [0, 1, 3, 6, 10, 15, 20, 20, 15, 10, 4, 1],
                        snow=None)
        self.assertEqual(E.months_in_season([point], PARAMS),
                         [4, 5, 6, 7, 8, 9, 10])

    def test_a_wrapped_season_is_returned_sorted(self):
        point = normals(400, [15, 15, 15, 15, 15, 40, 40, 40, 40, 40, 15, 15],
                        snow=[0] * 12)
        self.assertEqual(E.months_in_season([point], PARAMS),
                         [1, 2, 3, 4, 5, 11, 12])

    def test_no_qualifying_month_is_none_with_a_reason(self):
        arctic = normals(500, [-5] * 12, snow=[30] * 12)
        self.assertIsNone(E.months_in_season([arctic], PARAMS))
        self.assertIn("no month", E.why_not([arctic], PARAMS))

    def test_all_twelve_months_is_allowed(self):
        coast = normals(20, [15] * 12, snow=[0] * 12)
        self.assertEqual(E.months_in_season([coast], PARAMS), list(range(1, 13)))
        self.assertEqual(E.why_not([coast], PARAMS), "")

    def test_a_point_with_missing_data_makes_the_trail_unestimable(self):
        point = normals(20, [15] * 12, snow=[0] * 12)
        self.assertIsNone(E.months_in_season([point, None], PARAMS))
        self.assertIn("no data", E.why_not([point, None], PARAMS))
        self.assertIsNone(E.months_in_season([], PARAMS))
        self.assertIn("no data", E.why_not([], PARAMS))


class SamplePointsTest(unittest.TestCase):
    def make_root(self, td, parts=None, profile=None, multi=False):
        import json
        import tempfile  # noqa: F401  (td is made by the caller)
        d = os.path.join(td, "trail-x")
        os.makedirs(os.path.join(td, "web"))
        os.makedirs(d)
        with open(os.path.join(td, "web", "place-bounds.toml"), "w") as f:
            f.write('[box]\n"US-VT" = [-73.5, 42.7, -71.5, 45.0]\n')
        if parts is not None:
            if multi:
                geom = {"type": "MultiLineString", "coordinates": parts}
            else:
                geom = {"type": "LineString", "coordinates": parts[0]}
            doc = {"type": "FeatureCollection",
                   "features": [{"type": "Feature", "geometry": geom}]}
            with open(os.path.join(d, "line.geojson"), "w") as f:
                json.dump(doc, f)
        if profile is not None:
            with open(os.path.join(d, "elevation.json"), "w") as f:
                json.dump({"profile": profile}, f)
        return td

    @staticmethod
    def meridian(lat0, lat1, step=0.1, lon=-110.0):
        n = int(round((lat1 - lat0) / step))
        return [[lon, lat0 + i * step] for i in range(n + 1)]

    def rec(self, **hike):
        base = {"summary": "x", "checked": "2026-01-01", "source": []}
        base.update(hike)
        return {"id": "trail-x", "country": "US", "regions": ["VT"],
                "source": {"line_file": "line.geojson"}, "hike": base}

    def test_a_track_gives_points_spaced_along_it(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self.make_root(td, parts=[self.meridian(43.0, 44.8)],
                                  profile=[[0, 1000], [200, 1000]])
            points, kind = E.sample_points(root, self.rec())
        self.assertEqual(kind, "track")
        self.assertEqual(len(points), 5)  # about 200 km, one per 50 km
        self.assertEqual(points[0].km, 0.0)
        self.assertAlmostEqual(points[0].lat, 43.0, places=3)
        self.assertLess(abs(points[-1].km - 200.15), 50)
        self.assertAlmostEqual(points[-1].lat, 44.8, places=3)

    def test_a_short_track_still_gets_three_points(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self.make_root(td, parts=[self.meridian(43.0, 43.09, 0.03)],
                                  profile=[[0, 500], [10, 500]])
            points, kind = E.sample_points(root, self.rec())
        self.assertEqual(len(points), 3)

    def test_a_very_long_track_is_capped_at_twelve(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self.make_root(td, parts=[self.meridian(35.0, 45.0, 0.5)],
                                  profile=[[0, 500], [1112, 500]])
            points, kind = E.sample_points(root, self.rec())
        self.assertEqual(len(points), 12)

    def test_a_multipart_track_is_sampled_along_all_parts(self):
        import tempfile
        parts = [self.meridian(43.0, 43.9), self.meridian(44.1, 45.0)]
        with tempfile.TemporaryDirectory() as td:
            root = self.make_root(td, parts=parts, multi=True,
                                  profile=[[0, 500], [200, 500]])
            points, kind = E.sample_points(root, self.rec())
        self.assertEqual(kind, "track")
        self.assertTrue(any(p.lat > 44.1 for p in points))
        self.assertTrue(any(p.lat < 43.9 for p in points))

    def test_elevation_comes_from_the_profile_by_distance(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self.make_root(td, parts=[self.meridian(43.0, 44.8)],
                                  profile=[[0, 1000], [100, 2000], [200, 1500]])
            points, kind = E.sample_points(root, self.rec())
        middle = points[len(points) // 2]
        self.assertLess(abs(middle.elev_m - 2000), 30)
        self.assertLess(abs(points[0].elev_m - 1000), 30)

    def test_a_track_without_a_profile_uses_the_high_point_for_the_top_only(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self.make_root(td, parts=[self.meridian(43.0, 44.8)])
            points, kind = E.sample_points(root, self.rec(high_point_m=3000))
        elevs = [p.elev_m for p in points]
        self.assertEqual(elevs.count(3000), 1)
        self.assertEqual(elevs.count(None), len(elevs) - 1)

    def test_no_track_uses_the_two_ends(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self.make_root(td)
            points, kind = E.sample_points(
                root, self.rec(start_lonlat=[-110.0, 43.0],
                               end_lonlat=[-109.0, 44.0]))
        self.assertEqual(kind, "ends")
        self.assertEqual(len(points), 2)
        self.assertEqual((points[0].lat, points[0].lon), (43.0, -110.0))
        self.assertEqual((points[1].lat, points[1].lon), (44.0, -109.0))

    def test_no_track_and_no_ends_uses_the_place_centre(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self.make_root(td)
            points, kind = E.sample_points(root, self.rec())
        self.assertEqual(kind, "place")
        self.assertEqual(len(points), 1)
        self.assertTrue(-73.5 <= points[0].lon <= -71.5)
        self.assertTrue(42.7 <= points[0].lat <= 45.0)
        self.assertAlmostEqual(points[0].lon, -72.5)
        self.assertAlmostEqual(points[0].lat, 43.85)


if __name__ == "__main__":
    unittest.main()
