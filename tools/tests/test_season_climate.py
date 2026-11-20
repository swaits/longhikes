"""Tests for tools/season_climate.py. All offline: an injected opener
serves the canned responses in fixtures/season/.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import io
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import season_climate as C  # noqa: E402
import validate as V  # noqa: E402

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "season")


def fixture_bytes(name):
    with open(os.path.join(FIX, name), "rb") as f:
        return f.read()


class FakeResponse(io.BytesIO):
    headers = {}


class FakeOpener:
    """Routes by address to a fixture and counts the calls."""

    def __init__(self, open_meteo="open_meteo_alpine.json"):
        self.calls = []
        self.open_meteo = open_meteo

    def __call__(self, req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        self.calls.append(url)
        if "archive-api.open-meteo.com" in url:
            return FakeResponse(fixture_bytes(self.open_meteo))
        if "ghcnd-stations.txt" in url:
            return FakeResponse(fixture_bytes("noaa_stations.txt"))
        if "normals-monthly" in url:
            for sid in ("USW00000001", "USW00000002", "USW00000003"):
                if sid in url:
                    return FakeResponse(fixture_bytes(f"noaa_{sid}.csv"))
            raise AssertionError(url)
        if "api.weather.gc.ca" in url:
            return FakeResponse(fixture_bytes("eccc_normals.geojson"))
        raise AssertionError(url)


class OpenMeteoTest(unittest.TestCase):
    def setUp(self):
        C.DELAY_S = 0

    def test_a_fixture_response_becomes_point_normals(self):
        with tempfile.TemporaryDirectory() as cache:
            got = C.fetch_normals(37.7, -119.5, 3400.0, cache=cache, opener=FakeOpener())
        self.assertIsNotNone(got)
        self.assertEqual(len(got.tmax_c), 12)
        self.assertEqual(len(got.snow_cm), 12)
        self.assertEqual(got.tmax_c[0], -2.0)    # January, degrees C
        self.assertEqual(got.tmax_c[6], 21.0)    # July
        self.assertEqual(got.snow_cm[0], 120.0)  # 1.2 metres of snow, in cm
        self.assertEqual(got.snow_cm[7], 0.0)

    def test_values_are_rounded_to_a_tenth(self):
        with tempfile.TemporaryDirectory() as cache:
            got = C.fetch_normals(37.7, -119.5, None, cache=cache, opener=FakeOpener())
        for value in list(got.tmax_c) + list(got.snow_cm):
            self.assertEqual(value, round(value, 1))

    def test_cell_elevation_is_used_when_none_is_asked_for(self):
        with tempfile.TemporaryDirectory() as cache:
            got = C.fetch_normals(37.7, -119.5, None, cache=cache, opener=FakeOpener())
        self.assertEqual(got.elev_m, 3400.0)

    def test_a_second_call_reads_the_cache_not_the_network(self):
        opener = FakeOpener()
        with tempfile.TemporaryDirectory() as cache:
            first = C.fetch_normals(37.7, -119.5, 3400.0, cache=cache, opener=opener)
            second = C.fetch_normals(37.7, -119.5, 3400.0, cache=cache, opener=opener)
        self.assertEqual(first, second)
        self.assertEqual(len(opener.calls), 1)

    def test_a_point_with_no_data_returns_none_not_zeros(self):
        with tempfile.TemporaryDirectory() as cache:
            got = C.fetch_normals(0.0, 0.0, None, cache=cache,
                                  opener=FakeOpener("open_meteo_nodata.json"))
        self.assertIsNone(got)

    def test_the_desert_and_coast_fixtures_parse(self):
        with tempfile.TemporaryDirectory() as cache:
            desert = C.fetch_normals(32.2, -110.9, 800.0, cache=cache,
                                     opener=FakeOpener("open_meteo_desert.json"))
            coast = C.fetch_normals(47.6, -122.3, 10.0, cache=cache,
                                    opener=FakeOpener("open_meteo_coast.json"))
        self.assertEqual(desert.tmax_c[6], 44.0)
        self.assertTrue(all(v == 0.0 for v in desert.snow_cm))
        self.assertEqual(coast.tmax_c[0], 9.0)


class NoaaTest(unittest.TestCase):
    def setUp(self):
        C.DELAY_S = 0

    def test_noaa_fixture_becomes_point_normals(self):
        with tempfile.TemporaryDirectory() as cache:
            got = C.fetch_noaa(37.71, -119.51, 1500.0, cache=cache, opener=FakeOpener())
        self.assertIsNotNone(got)
        self.assertEqual(len(got.tmax_c), 12)
        self.assertEqual(got.tmax_c[0], 10.0)  # 50 F in C, no lapse change
        self.assertIsNone(got.snow_cm)  # the normals carry no snow depth

    def test_noaa_lapse_adjusts_to_the_point_elevation(self):
        with tempfile.TemporaryDirectory() as cache:
            got = C.fetch_noaa(37.71, -119.51, 2500.0, cache=cache, opener=FakeOpener())
        self.assertEqual(got.tmax_c[0], 3.5)  # 10 C less 6.5 C for 1000 m

    def test_noaa_returns_none_far_from_any_station(self):
        with tempfile.TemporaryDirectory() as cache:
            got = C.fetch_noaa(66.5, -65.0, None, cache=cache, opener=FakeOpener())
        self.assertIsNone(got)


class EcccTest(unittest.TestCase):
    def setUp(self):
        C.DELAY_S = 0

    def test_eccc_fixture_becomes_point_normals(self):
        with tempfile.TemporaryDirectory() as cache:
            got = C.fetch_eccc(49.25, -123.05, None, cache=cache, opener=FakeOpener())
        self.assertIsNotNone(got)
        self.assertEqual(got.tmax_c[0], 6.0)   # the nearer of the two stations
        self.assertEqual(got.tmax_c[6], 24.0)
        self.assertIsNone(got.snow_cm)


class SourceTest(unittest.TestCase):
    def test_the_cache_is_outside_the_repository(self):
        self.assertFalse(os.path.abspath(C.CACHE_DIR).startswith(os.path.abspath(V.ROOT)))

    def test_the_source_says_its_licence_and_period(self):
        for key in ("name", "publisher", "url", "licence", "period"):
            self.assertIn(key, C.SOURCE)
            self.assertTrue(str(C.SOURCE[key]).strip())
        self.assertIn("CC BY 4.0", C.SOURCE["licence"])


if __name__ == "__main__":
    unittest.main()
