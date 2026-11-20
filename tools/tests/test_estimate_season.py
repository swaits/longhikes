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


if __name__ == "__main__":
    unittest.main()
