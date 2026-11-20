"""Tests for tools/estimate_season.py. The rule tests use hand-made
normals, so they run with no network.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import csv
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import estimate_season as E  # noqa: E402
import test_refresh as TR  # noqa: E402
import season_climate as C  # noqa: E402

PARAMS = E.Params(cold_c_min=5.0, heat_c_max=32.0)


def normals(elev, tmax, snow=None):
    return C.PointNormals(lat=45.0, lon=-110.0, elev_m=float(elev),
                          tmax_c=tuple(float(v) for v in tmax),
                          snow_cm=None if snow is None
                          else tuple(float(v) for v in snow))


class RuleTest(unittest.TestCase):
    """The thresholds on their own: with no sourced trails to compare
    with, the model is the cold and heat limits."""

    def test_a_cold_high_point_closes_the_winter(self):
        point = normals(3000, [0, 1, 3, 6, 10, 15, 20, 20, 15, 10, 4, 1])
        self.assertEqual(E.months_in_season([point], PARAMS),
                         [4, 5, 6, 7, 8, 9, 10])

    def test_heat_at_the_low_ground_closes_a_summer_month(self):
        desert = normals(400, [19, 22, 26, 31, 36, 42, 44, 43, 39, 32, 24, 19])
        self.assertEqual(E.months_in_season([desert], PARAMS),
                         [1, 2, 3, 4, 10, 11, 12])

    def test_high_ground_is_the_upper_quartile_of_points(self):
        low = [normals(e, [15] * 12) for e in (100, 200, 300)]
        high = normals(400, [15, 15, 15, 15, 15, 0, 15, 15, 15, 15, 15, 15])
        got = E.months_in_season(low + [high], PARAMS)
        self.assertNotIn(6, got)  # only the highest point is cold in June
        self.assertEqual(len(got), 11)

    def test_a_wrapped_season_is_returned_sorted(self):
        point = normals(400, [15, 15, 15, 15, 15, 40, 40, 40, 40, 40, 15, 15])
        self.assertEqual(E.months_in_season([point], PARAMS),
                         [1, 2, 3, 4, 5, 11, 12])

    def test_a_trail_that_never_qualifies_still_gets_three_months(self):
        arctic = normals(500, [-5, -4, -2, 0, 3, 4, 4, 3, 1, -1, -3, -5])
        got = E.months_in_season([arctic], PARAMS)
        self.assertEqual(got, [5, 6, 7])  # the three nearest the cold limit

    def test_all_twelve_months_is_allowed(self):
        coast = normals(20, [15] * 12)
        self.assertEqual(E.months_in_season([coast], PARAMS), list(range(1, 13)))

    def test_a_point_with_missing_data_makes_the_trail_unestimable(self):
        point = normals(20, [15] * 12)
        self.assertIsNone(E.months_in_season([point, None], PARAMS))
        self.assertIsNone(E.months_in_season([], PARAMS))


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


class ReportTest(unittest.TestCase):
    def loo(self, **kw):
        """loo entries (mask, (match, classified, jaccard)) by id."""
        return {tid: (0, v) for tid, v in kw.items()}

    def test_report_counts_matches_and_no_data(self):
        med = ((15.0,) * 12, (15.0,) * 12)
        sourced = [("a", med, [7, 8], "g"), ("b", med, [7, 8], "g"),
                   ("c", None, [6, 7, 8], "h")]
        loo = self.loo(a=(1.0, 1.0, 1.0), b=(0.0, 0.5, 0.25))
        rep = E.report(sourced, loo)
        self.assertEqual((rep["n"], rep["within1"], rep["worse"], rep["no_data"]),
                         (3, 1, 1, 1))
        self.assertEqual(rep["within1"] + rep["worse"] + rep["no_data"], rep["n"])
        self.assertEqual(rep["classified"], 0.75)
        self.assertEqual(rep["jaccard"], 0.625)
        self.assertEqual(rep["by_group"]["g"]["within1"], 1)
        self.assertEqual(rep["by_group"]["h"]["no_data"], 1)

    def test_passes_is_false_below_the_bar_and_true_at_it(self):
        def rep(within1, no_data=0, n=100):
            return {"n": n, "within1": within1,
                    "worse": n - within1 - no_data, "no_data": no_data}
        self.assertFalse(E.passes_bar(rep(74)))
        self.assertTrue(E.passes_bar(rep(75)))
        self.assertFalse(E.passes_bar(rep(90, no_data=11)))  # coverage 89%

    def test_the_report_splits_by_kind(self):
        med = ((20.0,) * 12, (20.0,) * 12)
        sourced = [("a", med, list(range(1, 13)), "x")]
        rep = E.report(sourced, self.loo(a=(1.0, 1.0, 1.0)))
        self.assertEqual(rep["by_kind"]["year-round"]["n"], 1)
        self.assertEqual(rep["by_kind"]["year-round"]["within1"], 1)
        self.assertEqual(rep["by_kind"]["alpine"]["n"], 0)

    def test_the_same_input_gives_the_same_fit_twice(self):
        med = lambda v: (tuple([v] * 12), tuple([v] * 12))
        sourced = [(f"t{i}", med(10.0 + i), [5, 6, 7, 8], "g") for i in range(6)]
        first = E.fit_sourced(sourced)
        second = E.fit_sourced(sourced)
        self.assertEqual(first[0], second[0])
        self.assertEqual(first[1], second[1])


def mild_fetch(lat, lon, elev):
    return C.PointNormals(lat=float(lat), lon=float(lon),
                          elev_m=float(elev if elev is not None else 100.0),
                          tmax_c=tuple([15.0] * 12))


def warm_with_latitude(lat, lon, elev):
    """Warmer to the south: five degrees a degree of latitude."""
    return C.PointNormals(lat=float(lat), lon=float(lon),
                          elev_m=float(elev if elev is not None else 100.0),
                          tmax_c=tuple([15.0 + 5.0 * (43.0 - float(lat))] * 12))


def none_fetch(lat, lon, elev):
    return None


def bounds_root(td):
    os.makedirs(os.path.join(td, "web"))
    with open(os.path.join(td, "web", "place-bounds.toml"), "w") as f:
        f.write('[box]\n"US-VT" = [-73.5, 42.7, -71.5, 45.0]\n')
    return td


def ends_rec(tid="trail-x", lat=43.0, extra=None):
    hike = {"summary": "x", "checked": "2026-01-01", "source": [],
            "start_lonlat": [-110.0, lat], "end_lonlat": [-109.0, lat + 1.0]}
    hike.update(extra or {})
    return {"id": tid, "country": "US", "regions": ["VT"],
            "source": {"line_file": "line.geojson"}, "hike": hike}


class EstimateTest(unittest.TestCase):
    def test_a_no_track_record_is_flagged(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            est = E.estimate(bounds_root(td), ends_rec(), PARAMS, fetch=mild_fetch)
        self.assertIn("no-track", est["flags"])
        self.assertEqual(est["months"], list(range(1, 13)))
        self.assertEqual(est["phrase"], "All year")

    def test_a_trail_with_no_data_is_listed_not_estimated(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            est = E.estimate(bounds_root(td), ends_rec(), PARAMS, fetch=none_fetch)
        self.assertIsNone(est["months"])
        self.assertIn("no-data", est["flags"])
        self.assertIn("no data", est["reason"])

    def test_flags_include_far_north_above_sixty_degrees(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            est = E.estimate(bounds_root(td), ends_rec(lat=61.0), PARAMS,
                             fetch=mild_fetch)
        self.assertIn("far-north", est["flags"])

    def test_nothing_in_estimate_touches_the_network_without_a_fetch(self):
        import tempfile

        def raising(lat, lon, elev):
            raise AssertionError("network touched")

        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(AssertionError):
                E.estimate(bounds_root(td), ends_rec(), PARAMS, fetch=raising)

    def test_comparable_trails_are_listed_nearest_first(self):
        import tempfile, shutil
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = TR.make_repo(tmp, trails=[
            ("near-one", "Near", {"extra_hike":
                'season = "June to September"\nmonths = [6, 7, 8, 9]\n'
                'season_basis = "source"\n'
                'start_lonlat = [-110.0, 43.1]\nend_lonlat = [-110.0, 43.3]\n'}),
            ("far-one", "Far", {"extra_hike":
                'season = "July to August"\nmonths = [7, 8]\n'
                'season_basis = "source"\n'
                'start_lonlat = [-100.0, 35.0]\nend_lonlat = [-100.0, 35.2]\n'}),
            ("target-one", "Target", {"extra_hike":
                'start_lonlat = [-110.0, 43.0]\nend_lonlat = [-110.0, 43.2]\n'}),
        ])
        os.makedirs(os.path.join(root, "web"))
        with open(os.path.join(root, "web", "place-bounds.toml"), "w") as f:
            f.write('[box]\n"US-VT" = [-73.5, 42.7, -71.5, 45.0]\n')
        import refresh as R
        rec = R.load_toml(os.path.join(root, "target-one", "trail.toml"))
        # fixture records claim line_file "" so sampling uses the ends
        rec["source"]["line_file"] = "line.geojson"
        est = E.estimate(root, rec, PARAMS, fetch=warm_with_latitude)
        self.assertEqual(est["comparable"], "near-one")
        self.assertEqual(est["comparable_phrase"], "June to September")
        self.assertEqual([n[0] for n in est["neighbours"]],
                         ["near-one", "far-one"])
        self.assertEqual(est["confidence"], "low")  # the location is a fallback


class ProposeCheckTest(unittest.TestCase):
    def fit_doc(self, root, passes=True, within1=3, n=4):
        os.makedirs(os.path.join(root, "tools"), exist_ok=True)
        doc = {"computed": "2026-11-20", "rule_version": E.RULE_VERSION,
               "dataset": "test", "period": "2011-2020",
               "params": E.Params(5.0, 32.0).as_dict(),
               "loo": {"n": n, "within1": within1, "worse": n - within1,
                       "no_data": 0, "classified": 0.8, "jaccard": 0.6,
                       "by_group": {}, "by_kind": {}},
               "confidence": None, "bar": E.BAR, "passes": passes}
        with open(os.path.join(root, "tools", "season_fit.json"), "w") as f:
            json.dump(doc, f)

    def repo_with(self, tmp, trails):
        root = TR.make_repo(tmp, trails=trails)
        os.makedirs(os.path.join(root, "web"))
        with open(os.path.join(root, "web", "place-bounds.toml"), "w") as f:
            f.write('[box]\n"US-VT" = [-73.5, 42.7, -71.5, 45.0]\n')
        # fixture records name no track file; point them at the default
        for tid, _name, _kw in trails:
            path = os.path.join(root, tid, "trail.toml")
            text = TR.read(root, f"{tid}/trail.toml").replace(
                'line_file = ""', 'line_file = "line.geojson"')
            TR.write(path, text)
        return root

    ENDS = 'start_lonlat = [-110.0, 43.0]\nend_lonlat = [-110.0, 43.2]\n'

    def test_propose_writes_one_row_per_unsourced_trail(self):
        import tempfile, shutil, csv
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = self.repo_with(tmp, [
            ("aaa", "Aaa", {"extra_hike": self.ENDS}),
            ("bbb", "Bbb", {"extra_hike":
                'season = "June to September"\nmonths = [6, 7, 8, 9]\n'
                'season_basis = "source"\n' + self.ENDS}),
            ("ccc", "Ccc", {"hike": False}),
        ])
        stage = os.path.join(tmp, "stage")
        n = E.propose(root, PARAMS, mild_fetch, stage)
        self.assertEqual(n, 2)  # aaa and ccc have no season
        with open(os.path.join(stage, "season", "estimates.csv"),
                  newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual([r["id"] for r in rows], ["aaa", "ccc"])
        # the one sourced trail has the same climate, so its June to
        # September carries the estimate
        self.assertEqual(rows[0]["phrase"], "June to September")

    def est_repo(self, tmp, months_extra):
        return self.repo_with(tmp, [
            ("aaa", "Aaa", {"extra_hike": months_extra + self.ENDS}),
        ])

    def test_check_passes_when_nothing_changed(self):
        import tempfile, shutil
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = self.est_repo(
            tmp,
            'season = "All year"\n'
            'months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]\n'
            'season_basis = "estimate"\nseason_method = "Estimated."\n')
        self.fit_doc(root)
        ok, lines = E.check(root, mild_fetch)
        self.assertTrue(ok, lines)

    def test_check_names_the_trail_whose_estimate_changed(self):
        import tempfile, shutil
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = self.est_repo(
            tmp,
            'season = "June to July"\nmonths = [6, 7]\n'
            'season_basis = "estimate"\nseason_method = "Estimated."\n')
        self.fit_doc(root)
        ok, lines = E.check(root, mild_fetch)
        self.assertFalse(ok)
        self.assertTrue(any("aaa" in line and "[6, 7]" in line
                            for line in lines), lines)

    def test_check_fails_when_the_fit_got_worse(self):
        import tempfile, shutil
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        # one sourced trail that mild all-year normals cannot match
        extra = ('season = "June"\nmonths = [6]\n'
                 'season_basis = "source"\n' + self.ENDS)
        root = self.repo_with(tmp, [("only", "Only", {"extra_hike": extra})])
        self.fit_doc(root, within1=4, n=4)
        ok, lines = E.check(root, mild_fetch)
        self.assertFalse(ok)
        self.assertTrue(any("fit got worse" in line for line in lines), lines)

    def test_proposals_collect_cleanly(self):
        import tempfile, shutil, csv
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = self.repo_with(tmp, [("aaa", "Aaa", {"extra_hike": self.ENDS})])
        stage = os.path.join(tmp, "stage")
        os.makedirs(os.path.join(stage, "season"))
        reviewed = os.path.join(stage, "season", "estimates.reviewed.csv")
        with open(reviewed, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "proposed_months", "phrase", "kind", "flags",
                        "comparable", "comparable_phrase", "note"])
            w.writerow(["aaa", "6 7 8 9", "June to September", "ends",
                        "no-track", "", "", ""])
        self.assertEqual(E.proposals(root, reviewed, stage), 1)
        code, out = TR.main(root, "--dir", stage, "collect")
        self.assertEqual(code, 0, out)
        import refresh as R
        coll = R.load_toml(os.path.join(stage, "collected.toml"))
        props = coll["proposal"]
        self.assertEqual(len(props), 1)
        self.assertEqual(props[0]["status"], "proposed", out)


class SeasonKindTest(unittest.TestCase):
    def test_kinds_of_sourced_seasons(self):
        self.assertEqual(E.season_kind(list(range(1, 13))), "year-round")
        self.assertEqual(E.season_kind([7, 8, 9]), "alpine")
        self.assertEqual(E.season_kind([10, 11, 12, 1, 2, 3, 4]), "cool-season")
        self.assertEqual(E.season_kind([4, 5, 6, 7, 8, 9, 10]), "other")


if __name__ == "__main__":
    unittest.main()
