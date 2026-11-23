"""Tests for the latitude and longitude limits on a hike's start and end points.

The limit on latitude is 84 degrees north, which takes in Ellesmere Island (Canada's
land reaches 83.1 N); the limit on longitude keeps Greenland out.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import validate as V  # noqa: E402


def range_errors(name, lonlat):
    """The out-of-range errors check_hike gives for a point; other faults are ignored."""
    place = name.replace("_lonlat", "")
    rec = {"length_km": 120, "hike": {"start": "A", "end": "B", name: lonlat}}
    rec["hike"][place] = "A place"
    errors = []
    V.check_hike("t", rec, errors)
    return [e for e in errors if "is out of range" in e]


class LonLatBoundsTests(unittest.TestCase):
    def test_a_start_at_81_north_passes(self):
        self.assertEqual(range_errors("start_lonlat", [-76.9, 81.0]), [])

    def test_a_start_at_85_north_fails(self):
        errors = range_errors("start_lonlat", [-76.9, 85.0])
        self.assertEqual(len(errors), 1)
        self.assertIn("latitude 24.0 to 84.0", errors[0])

    def test_an_end_follows_the_same_limit(self):
        self.assertEqual(range_errors("end_lonlat", [-76.9, 81.0]), [])
        self.assertEqual(len(range_errors("end_lonlat", [-76.9, 85.0])), 1)

    def test_longitude_still_keeps_greenland_out(self):
        self.assertEqual(len(range_errors("start_lonlat", [-40.0, 81.0])), 1)


if __name__ == "__main__":
    unittest.main()
