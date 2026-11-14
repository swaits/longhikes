"""Tests for tools/elevation.py: the parts that need no network.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import io
import json
import math
import os
import sys
import tempfile
import unittest
import urllib.error

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import elevation as E  # noqa: E402


def encode(elev):
    """Terrarium bytes for an elevation array (the inverse of decode_terrarium)."""
    v = np.asarray(elev, dtype=np.float64) + 32768.0
    r = np.floor(v / 256.0)
    g = np.floor(v - r * 256.0)
    b = np.floor((v - np.floor(v)) * 256.0)
    return np.stack([r, g, b], axis=-1).astype(np.uint8)


def png_bytes(rgb):
    buf = io.BytesIO()
    Image.fromarray(rgb, "RGB").save(buf, "PNG")
    return buf.getvalue()


class TileMaths(unittest.TestCase):
    def test_origin_and_far_corner(self):
        x, y = E.lonlat_to_pixel(-180.0, 85.0511287798, 3)
        self.assertAlmostEqual(float(x), 0.0, places=6)
        self.assertAlmostEqual(float(y), 0.0, places=3)
        x, y = E.lonlat_to_pixel(180.0, -85.0511287798, 3)
        self.assertAlmostEqual(float(x), 256 * 8, places=6)
        self.assertAlmostEqual(float(y), 256 * 8, places=3)

    def test_equator_and_prime_meridian_are_the_centre(self):
        x, y = E.lonlat_to_pixel(0.0, 0.0, 5)
        self.assertAlmostEqual(float(x), 256 * 16, places=6)
        self.assertAlmostEqual(float(y), 256 * 16, places=6)

    def test_known_tile(self):
        # Mount Rainier's summit at zoom 12, by the standard slippy-map formula
        lon, lat, z = -121.7603, 46.8523, 12
        n = 2 ** z
        want = (int((lon + 180.0) / 360.0 * n),
                int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n))
        x, y = E.lonlat_to_pixel(lon, lat, z)
        self.assertEqual((int(x // 256), int(y // 256)), want)
        self.assertEqual(want, (662, 1443))

    def test_round_trip(self):
        lon, lat = np.array([-121.7603, 10.5, 170.0]), np.array([46.8523, -33.0, 60.0])
        for z in (8, 12, 14):
            x, y = E.lonlat_to_pixel(lon, lat, z)
            lo, la = E.pixel_to_lonlat(x, y, z)
            np.testing.assert_allclose(lo, lon, atol=1e-9)
            np.testing.assert_allclose(la, lat, atol=1e-9)

    def test_ground_resolution(self):
        self.assertAlmostEqual(E.ground_m_per_pixel(0.0, 12), 38.2, delta=0.1)
        self.assertAlmostEqual(E.ground_m_per_pixel(40.0, 12), 29.3, delta=0.1)
        self.assertAlmostEqual(E.ground_m_per_pixel(40.0, 13), E.ground_m_per_pixel(40.0, 12) / 2, places=6)

    def test_tiles_needed_includes_neighbours_at_an_edge(self):
        # a point 0.2 pixel inside tile (1, 1) uses pixels from tile (0, 0) too
        tiles = E.tiles_needed(np.array([256.2]), np.array([256.2]))
        self.assertEqual(tiles, {(0, 0), (1, 0), (0, 1), (1, 1)})

    def test_tiles_needed_inside_one_tile(self):
        self.assertEqual(E.tiles_needed(np.array([300.5]), np.array([300.5])), {(1, 1)})


class Decoding(unittest.TestCase):
    def test_formula(self):
        rgb = np.array([[[128, 0, 0], [129, 4, 128], [127, 255, 0], [0, 0, 0]]], dtype=np.uint8)
        np.testing.assert_allclose(E.decode_terrarium(rgb)[0],
                                   [0.0, 260.5, -1.0, -32768.0])

    def test_round_trip_with_encode(self):
        elev = np.array([[-86.0, 0.0, 1.5, 4009.25, 8848.0]])
        np.testing.assert_allclose(E.decode_terrarium(encode(elev)), elev, atol=1 / 256)

    def test_png_load(self):
        elev = np.full((256, 256), 1234.5)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "t.png")
            with open(path, "wb") as f:
                f.write(png_bytes(encode(elev)))
            tile = E.load_tile(path)
        self.assertEqual(tile.shape, (256, 256))
        self.assertAlmostEqual(float(tile[10, 10]), 1234.5, places=2)

    def test_despike_removes_a_bad_line_and_keeps_a_cliff(self):
        t = np.full((256, 256), 100.0, dtype=np.float32)
        t[:, 128:] = 600.0            # a real step: stays
        t[40:44, 60] = -5400.0        # a one-pixel line of garbage: goes
        out = E.despike(t)
        self.assertTrue(np.all(out[40:44, 60] == 100.0))
        self.assertTrue(np.all(out[:, :128] == 100.0) and np.all(out[:, 128:] == 600.0))

    def test_despike_leaves_a_clean_tile_alone(self):
        t = (np.linspace(0, 200, 256)[None, :] + np.zeros((256, 1))).astype(np.float32)
        self.assertIs(E.despike(t), t)


class SeaLevel(unittest.TestCase):
    def test_below_sea_level_is_zero(self):
        t = np.array([[-50.0, 0.0, 12.5, -0.1]], dtype=np.float32)
        np.testing.assert_allclose(E.below_sea_level_to_zero(t), [[0.0, 0.0, 12.5, 0.0]])

    def test_load_tile_applies_it(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "t.png")
            with open(path, "wb") as f:
                f.write(png_bytes(encode(np.full((256, 256), -20.0))))
            self.assertEqual(float(E.load_tile(path).min()), 0.0)


class Bilinear(unittest.TestCase):
    def test_pixel_centres_and_midpoints(self):
        tile = np.zeros((256, 256), dtype=np.float32)
        tile[10, 10], tile[10, 11], tile[11, 10], tile[11, 11] = 0.0, 100.0, 200.0, 300.0
        get = lambda tx, ty: tile  # noqa: E731
        # the centre of pixel (10, 10) is at 10.5, 10.5
        self.assertAlmostEqual(float(E.bilinear(np.array([10.5]), np.array([10.5]), get)[0]), 0.0)
        self.assertAlmostEqual(float(E.bilinear(np.array([11.5]), np.array([10.5]), get)[0]), 100.0)
        self.assertAlmostEqual(float(E.bilinear(np.array([11.0]), np.array([11.0]), get)[0]), 150.0)

    def test_reads_across_a_tile_edge(self):
        left = np.full((256, 256), 100.0, dtype=np.float32)
        right = np.full((256, 256), 200.0, dtype=np.float32)
        get = lambda tx, ty: left if tx == 0 else right  # noqa: E731
        # exactly on the seam: halfway between the last pixel of one tile and the first of the next
        self.assertAlmostEqual(float(E.bilinear(np.array([256.0]), np.array([5.5]), get)[0]), 150.0)
        self.assertAlmostEqual(float(E.bilinear(np.array([255.5]), np.array([5.5]), get)[0]), 100.0)
        self.assertAlmostEqual(float(E.bilinear(np.array([256.5]), np.array([5.5]), get)[0]), 200.0)

    def test_plane_is_exact(self):
        yy, xx = np.mgrid[0:256, 0:256]
        tile = (3.0 * xx + 7.0 * yy).astype(np.float32)
        px, py = np.array([40.3, 100.9, 200.1]), np.array([12.2, 90.5, 30.7])
        got = E.bilinear(px, py, lambda tx, ty: tile)
        np.testing.assert_allclose(got, 3.0 * (px - 0.5) + 7.0 * (py - 0.5), atol=1e-3)


def line_km(km, lat=45.0, lon0=-110.0):
    """A west-to-east track of about km kilometres, with a point every 100 m."""
    step = 0.1 / (111.195 * math.cos(math.radians(lat)))
    n = int(km * 10) + 1
    return [(lon0 + i * step, lat) for i in range(n)]


class Track(unittest.TestCase):
    def test_haversine_one_degree_of_latitude(self):
        d = E.haversine_m(np.array([0.0, 0.0]), np.array([0.0, 1.0]))
        self.assertAlmostEqual(float(d[0]), 111195.0, delta=5)

    def test_parts_from_geojson(self):
        data = {"type": "FeatureCollection", "features": [
            {"geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]}},
            {"geometry": {"type": "MultiLineString", "coordinates": [[[2, 2], [3, 3]], [[4, 4]]]}},
            {"geometry": None},
            {"geometry": {"type": "Point", "coordinates": [0, 0]}},
        ]}
        self.assertEqual(E.track_parts(data), [[(0, 0), (1, 1)], [(2, 2), (3, 3)]])

    def test_join_chains_touching_ends_and_reverses(self):
        a = [(0.0, 45.0), (0.01, 45.0)]
        b = [(0.02, 45.0), (0.01, 45.0001)]      # its far end touches a's end; stored backwards
        c = [(0.5, 45.0), (0.51, 45.0)]          # touches nothing
        out = E.join_parts([a, b, c])
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0][0], (0.0, 45.0))
        self.assertEqual(out[0][-1], (0.02, 45.0))
        self.assertEqual(out[1], c)

    def test_join_does_not_invent_a_join_beyond_the_gap(self):
        a = [(0.0, 45.0), (0.01, 45.0)]
        b = [(0.0115, 45.0), (0.02, 45.0)]        # about 120 m away
        self.assertEqual(len(E.join_parts([a, b])), 2)
        self.assertEqual(len(E.join_parts([a, b], gap_m=200.0)), 1)

    def test_orientation_and_order_west_to_east(self):
        east = [(-100.0, 45.0), (-99.9, 45.0)]
        west = [(-100.2, 45.0), (-100.1, 45.0)]
        out, o = E.orient_and_order([east[::-1], west])
        self.assertEqual(o, "west-to-east")
        self.assertEqual(out, [west, east])

    def test_orientation_south_to_north(self):
        a = [(-100.0, 45.0), (-100.0, 45.5)]
        out, o = E.orient_and_order([a[::-1]])
        self.assertEqual(o, "south-to-north")
        self.assertEqual(out, [a])

    def test_a_loop_keeps_its_direction(self):
        ring = [(0, 0), (0.1, 0), (0.1, 0.1), (0, 0.1), (0.0, 0.0005)]
        out, _ = E.orient_and_order([ring])
        self.assertEqual(out[0], ring)

    def test_resample_spacing_and_ends(self):
        lon, lat, d = E.resample(line_km(1.0), 30.0)
        self.assertEqual(float(d[0]), 0.0)
        np.testing.assert_allclose(np.diff(d)[:-1], 30.0, atol=1e-6)
        self.assertLessEqual(float(np.diff(d)[-1]), 30.0 + 1e-6)
        self.assertAlmostEqual(float(d[-1]), 1000.0, delta=3.0)
        self.assertAlmostEqual(float(lon[-1]), line_km(1.0)[-1][0], places=6)

    def test_resample_short_part_keeps_both_ends(self):
        lon, lat, d = E.resample([(0.0, 0.0), (0.0001, 0.0)], 30.0)
        self.assertEqual(len(d), 2)
        self.assertAlmostEqual(float(d[-1]), 11.12, delta=0.05)

    def test_resample_ignores_repeated_points(self):
        lon, lat, d = E.resample([(0.0, 0.0), (0.0, 0.0), (0.001, 0.0)], 30.0)
        self.assertAlmostEqual(float(d[-1]), 111.2, delta=0.2)
        self.assertTrue(np.all(np.diff(d) > 0))


class Profile(unittest.TestCase):
    def test_smooth_keeps_a_constant_and_a_line(self):
        np.testing.assert_allclose(E.smooth(np.full(20, 7.0), 5), 7.0)
        ramp = np.arange(20.0)
        np.testing.assert_allclose(E.smooth(ramp, 5)[2:-2], ramp[2:-2])

    def test_smooth_shrinks_at_the_ends(self):
        out = E.smooth(np.array([0.0, 10.0, 20.0, 30.0, 40.0]), 5)
        self.assertAlmostEqual(float(out[0]), 10.0)    # mean of 0, 10, 20
        self.assertAlmostEqual(float(out[-1]), 30.0)   # mean of 20, 30, 40

    def test_smooth_window_one_changes_nothing_and_even_becomes_odd(self):
        x = np.array([1.0, 5.0, 2.0, 8.0])
        np.testing.assert_allclose(E.smooth(x, 1), x)
        np.testing.assert_allclose(E.smooth(x, 2), E.smooth(x, 3))

    def test_smooth_removes_a_spike(self):
        x = np.zeros(21)
        x[10] = 30.0
        self.assertAlmostEqual(float(E.smooth(x, 3)[10]), 10.0)

    def test_climb_plain_up_and_down(self):
        up = np.linspace(0, 100, 50)
        self.assertEqual(E.climb(up, 5.0), (100.0, 0.0))
        self.assertEqual(E.climb(up[::-1], 5.0), (0.0, 100.0))

    def test_climb_ignores_wiggles_below_the_threshold(self):
        wiggle = np.tile([0.0, 4.0], 100)            # 4 m wiggles
        a, d = E.climb(wiggle, 5.0)
        self.assertLessEqual(a, 4.0)
        self.assertLessEqual(d, 4.0)
        a, d = E.climb(wiggle * 2, 5.0)              # 8 m wiggles count in full
        self.assertGreater(a, 700.0)

    def test_climb_counts_every_big_hill(self):
        hills = np.tile(np.concatenate([np.linspace(0, 50, 25), np.linspace(50, 0, 25)]), 4)
        a, d = E.climb(hills, 10.0)
        self.assertAlmostEqual(a, 200.0)
        self.assertAlmostEqual(d, 200.0)

    def test_climb_net_change_is_within_the_threshold(self):
        rng = np.random.default_rng(3)
        e = np.cumsum(rng.normal(0, 3, 500))
        a, d = E.climb(e, 8.0)
        self.assertLessEqual(abs((a - d) - float(e[-1] - e[0])), 8.0)

    def test_climb_threshold_shrinks_total(self):
        rng = np.random.default_rng(4)
        e = np.cumsum(rng.normal(0, 3, 2000))
        totals = [sum(E.climb(e, t)) for t in (1.0, 5.0, 20.0)]
        self.assertGreater(totals[0], totals[1])
        self.assertGreater(totals[1], totals[2])

    def test_climb_short_input(self):
        self.assertEqual(E.climb(np.array([5.0]), 5.0), (0.0, 0.0))
        self.assertEqual(E.climb(np.array([]), 5.0), (0.0, 0.0))

    def test_thin_keeps_everything_when_small(self):
        d = np.arange(10.0)
        self.assertEqual(E.thin_profile(d, d * 2, 700), list(range(10)))

    def test_thin_respects_the_limit_and_keeps_ends_and_extremes(self):
        n = 5000
        d = np.linspace(0, 100, n)
        e = 500 * np.sin(d / 7.0) + 20 * np.sin(d * 3.1)
        hi, lo = int(np.argmax(e)), int(np.argmin(e))
        idx = E.thin_profile(d, e, 300, keep=[hi, lo])
        self.assertLessEqual(len(idx), 300)
        self.assertEqual(idx[0], 0)
        self.assertEqual(idx[-1], n - 1)
        self.assertIn(hi, idx)
        self.assertIn(lo, idx)
        self.assertEqual(idx, sorted(set(idx)))
        # the thinned profile stays close to the full one
        back = np.interp(d, d[idx], e[idx])
        self.assertLess(float(np.abs(back - e).max()), 60.0)

    def test_thin_is_deterministic(self):
        d = np.linspace(0, 50, 3000)
        e = np.cumsum(np.random.default_rng(1).normal(0, 2, 3000))
        self.assertEqual(E.thin_profile(d, e, 200), E.thin_profile(d, e, 200))


class Summary(unittest.TestCase):
    def parts(self):
        d = np.arange(0.0, 6000.0, 30.0)
        elev = 1000 + 400 * np.sin(d / 900.0) + (np.arange(len(d)) % 2) * 3.0
        lon = -110.0 + d / 78000.0
        lat = np.full(len(d), 45.0)
        return [{"lon": lon, "lat": lat, "dist_m": d, "elev": elev}]

    def test_facts(self):
        out = E.summarise(self.parts(), "west-to-east", 6)
        p = self.parts()[0]
        self.assertEqual(out["highest"]["m"], int(round(p["elev"].max())))
        self.assertEqual(out["lowest"]["m"], int(round(p["elev"].min())))
        self.assertGreaterEqual(out["highest"]["m"], out["lowest"]["m"])
        self.assertAlmostEqual(out["track_km"], 5.99, delta=0.1)
        self.assertAlmostEqual(out["coverage"], 1.0, delta=0.01)
        self.assertEqual(out["parts"], 1)
        self.assertNotIn("part_starts_km", out)
        self.assertGreater(out["ascent_m"], 0)
        # the 3 m zig-zag is below the threshold and adds nothing
        self.assertLess(out["ascent_m"], 1400)
        prof = out["profile"]
        dists = [x[0] for x in prof]
        self.assertEqual(dists, sorted(set(dists)))
        self.assertEqual(max(x[1] for x in prof), out["highest"]["m"])
        self.assertEqual(min(x[1] for x in prof), out["lowest"]["m"])

    def test_two_parts_are_not_joined(self):
        a, b = self.parts()[0], self.parts()[0]
        b = dict(b, elev=b["elev"] + 3000.0)
        out = E.summarise([a, b], "west-to-east", 12)
        one = E.summarise([a], "west-to-east", 6)
        # no climb across the 3000 m jump between the parts
        self.assertEqual(out["ascent_m"], one["ascent_m"] * 2)
        self.assertEqual(out["parts"], 2)
        self.assertEqual(len(out["part_starts_km"]), 1)
        self.assertAlmostEqual(out["part_starts_km"][0], one["track_km"], delta=0.05)

    def test_profile_distances_increase_except_at_a_part_start(self):
        a = self.parts()[0]
        out = E.summarise([a, dict(a), dict(a)], "west-to-east", 18)
        dists = [p[0] for p in out["profile"]]
        starts = out["part_starts_km"]
        for x, y in zip(dists, dists[1:]):
            self.assertTrue(y > x or (y == x and y in starts))
        for s in starts:
            self.assertIn(s, dists)

    def test_profile_is_thinned(self):
        d = np.arange(0.0, 600000.0, 30.0)
        elev = 1000 + 800 * np.sin(d / 20000.0) + 50 * np.sin(d / 130.0)
        part = {"lon": -110 + d / 78000.0, "lat": np.full(len(d), 45.0), "dist_m": d, "elev": elev}
        out = E.summarise([part], "west-to-east", 600)
        self.assertLessEqual(len(out["profile"]), E.PROFILE_POINTS)

    def test_json_is_compact_and_repeatable(self):
        out = E.summarise(self.parts(), "west-to-east", 6)
        a, b = E.dumps(out), E.dumps(json.loads(E.dumps(out)))
        self.assertEqual(a, b)
        self.assertNotIn(" ", a.replace("Terrain Tiles", ""))
        self.assertTrue(a.endswith("\n") and a.count("\n") == 1)


class Cache(unittest.TestCase):
    def test_fetch_writes_once_then_reads_the_cache(self):
        png = png_bytes(encode(np.full((256, 256), 50.0)))
        calls = []

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def opener(req, timeout=0):
            calls.append((req.full_url, req.get_header("User-agent")))
            return Resp(png)

        with tempfile.TemporaryDirectory() as d:
            p1 = E.fetch_tile(d, 12, 666, 1435, opener)
            p2 = E.fetch_tile(d, 12, 666, 1435, opener)
            self.assertEqual(p1, p2)
            self.assertTrue(p1.startswith(d))
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0], "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/12/666/1435.png")
            self.assertNotIn("@", calls[0][1])
            self.assertAlmostEqual(float(E.load_tile(p1)[0, 0]), 50.0, places=2)

    def test_a_missing_tile_is_an_error_not_a_retry_loop(self):
        def opener(req, timeout=0):
            raise urllib.error.HTTPError(req.full_url, 404, "not found", {}, None)

        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError):
                E.fetch_tile(d, 12, 1, 1, opener)

    def test_store_reads_tiles_from_cache_without_network(self):
        with tempfile.TemporaryDirectory() as d:
            path = E.tile_path(d, 12, 5, 6)
            os.makedirs(os.path.dirname(path))
            with open(path, "wb") as f:
                f.write(png_bytes(encode(np.full((256, 256), 321.0))))
            store = E.TileStore(12, d)
            store.prefetch({(5, 6)})
            self.assertEqual(store.fetched, 0)
            self.assertAlmostEqual(float(store.get(5, 6)[3, 3]), 321.0, places=2)


class WholeTrail(unittest.TestCase):
    def test_flat_world_gives_flat_answers(self):
        with tempfile.TemporaryDirectory() as d:
            store = E.TileStore(12, d)
            store.get = lambda x, y: np.full((256, 256), 250.0, dtype=np.float32)
            store.prefetch = lambda needed: None
            data = {"type": "FeatureCollection", "features": [
                {"geometry": {"type": "LineString", "coordinates": [list(c) for c in line_km(5.0)]}}]}
            doc = E.build("t", {"length_km": 10}, data, store, "2026-01-01")
        self.assertEqual(doc["highest"]["m"], 250)
        self.assertEqual(doc["lowest"]["m"], 250)
        self.assertEqual((doc["ascent_m"], doc["descent_m"]), (0, 0))
        self.assertAlmostEqual(doc["coverage"], 0.5, delta=0.01)
        self.assertEqual(doc["orientation"], "west-to-east")
        self.assertEqual(doc["source"]["zoom"], 12)
        self.assertEqual(doc["source"]["computed"], "2026-01-01")


class WriteIfChanged(unittest.TestCase):
    def test_keeps_the_date_when_nothing_else_changed(self):
        doc = {"a": 1, "source": {"computed": "2026-11-13"}}
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "elevation.json")
            self.assertTrue(E.write_if_changed(path, json.loads(json.dumps(doc))))
            later = {"a": 1, "source": {"computed": "2027-01-01"}}
            self.assertFalse(E.write_if_changed(path, later))
            self.assertEqual(later["source"]["computed"], "2026-11-13")
            changed = {"a": 2, "source": {"computed": "2027-01-01"}}
            self.assertTrue(E.write_if_changed(path, changed))
            with open(path, encoding="utf-8") as f:
                self.assertEqual(json.load(f)["source"]["computed"], "2027-01-01")


if __name__ == "__main__":
    unittest.main()
