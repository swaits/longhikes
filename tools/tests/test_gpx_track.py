"""Tests for tools/gpx_track.py: no network.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import argparse
import json
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gpx_track as G  # noqa: E402

GPX = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Some Device 9000" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata><name>Jane Doe's hikes</name><author><name>Jane Doe</name></author></metadata>
  <wpt lat="40.5" lon="-100.5"><name>Camp</name></wpt>
  <trk><name>Day 1 by Jane</name><desc>private note</desc>
    <trkseg>
      <trkpt lat="40.0" lon="-100.0"><ele>12.5</ele><time>2020-01-01T10:00:00Z</time></trkpt>
      <trkpt lat="40.0" lon="-100.0"><ele>12.5</ele><time>2020-01-01T10:00:05Z</time></trkpt>
      <trkpt lat="40.001" lon="-100.0"><ele>13</ele><time>2020-01-01T10:01:00Z</time></trkpt>
      <trkpt lat="40.002" lon="-100.0000004"><ele>14</ele></trkpt>
    </trkseg>
    <trkseg>
      <trkpt lat="40.002" lon="-100.0"/>
      <trkpt lat="40.003" lon="-100.0"/>
    </trkseg>
  </trk>
  <trk><trkseg>
      <trkpt lat="41.0" lon="-100.0"/>
      <trkpt lat="41.001" lon="-100.0"/>
  </trkseg></trk>
</gpx>"""


def args_for(tmp, gpx, **kw):
    d = dict(gpx=gpx, id="t", out=tmp, source="S", licence="L", attribution="A",
             route_name=None, gap_km=1.0, dry=False, force=False)
    d.update(kw)
    return argparse.Namespace(**d)


class ParseTests(unittest.TestCase):
    def test_counts_and_order(self):
        p = G.parse(GPX)
        self.assertEqual(len(p["tracks"]), 2)
        self.assertEqual([len(s) for s in p["segments"]], [3, 2, 2])  # repeat dropped
        self.assertEqual(p["waypoints"], 1)
        self.assertEqual(p["segments"][0][0], [-100.0, 40.0])
        self.assertEqual(p["segments"][2][0], [-100.0, 41.0])

    def test_rounding(self):
        self.assertEqual(G.parse(GPX)["segments"][0][-1], [-100.0, 40.002])

    def test_html_refused(self):
        with self.assertRaises(G.TrackError):
            G.parse("<!DOCTYPE html>\n<html><body>lost</body></html>")

    def test_doctype_refused(self):
        with self.assertRaises(G.TrackError):
            G.parse('<?xml version="1.0"?><!DOCTYPE gpx [<!ENTITY a "b">]><gpx/>')

    def test_not_gpx_and_empty_refused(self):
        with self.assertRaises(G.TrackError):
            G.parse("<kml/>")
        with self.assertRaises(G.TrackError):
            G.parse('<gpx><trk><trkseg><trkpt lat="1" lon="1"/></trkseg></trk></gpx>')
        with self.assertRaises(G.TrackError):
            G.parse("not xml")

    def test_bad_point_refused(self):
        with self.assertRaises(G.TrackError):
            G.parse('<gpx><trk><trkseg><trkpt lat="95" lon="1"/><trkpt lat="1" lon="1"/>'
                    "</trkseg></trk></gpx>")

    def test_gpx_10_namespace(self):
        p = G.parse('<gpx xmlns="http://www.topografix.com/GPX/1/0"><trk><trkseg>'
                    '<trkpt lat="1" lon="1"/><trkpt lat="1.001" lon="1"/></trkseg></trk></gpx>')
        self.assertEqual(len(p["segments"]), 1)


class FigureTests(unittest.TestCase):
    def test_gap_and_parts(self):
        f = G.figures(G.parse(GPX))
        self.assertEqual((f["tracks"], f["segments"], f["points"]), (2, 3, 7))
        self.assertEqual(f["parts"], 2)          # first two join, third is ~111 km away
        self.assertEqual(len(f["gaps"]), 1)
        self.assertEqual(f["gaps"][0]["after_segment"], 2)
        self.assertAlmostEqual(f["gaps"][0]["km"], 110.6, delta=1)
        self.assertAlmostEqual(f["measured_km"], 0.4448, delta=0.01)


class RunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.mkdir(os.path.join(self.tmp, "t"))
        self.gpx = os.path.join(self.tmp, "in.gpx")
        with open(self.gpx, "w") as f:
            f.write(GPX)
        self.log = []

    def test_writes_geometry_only(self):
        G.run(args_for(self.tmp, self.gpx, route_name="The Trail"),
              today=__import__("datetime").date(2026, 11, 16), out=self.log.append)
        text = open(os.path.join(self.tmp, "t", "line.geojson")).read()
        doc = json.loads(text)
        self.assertEqual(len(doc["features"]), 3)
        self.assertEqual(doc["features"][0]["properties"], {"route_name": "The Trail"})
        for leak in ("Jane", "Device", "2020", "Camp", "private", "12.5", "ele", "time"):
            self.assertNotIn(leak, text)
        rel = open(os.path.join(self.tmp, "t", "release.txt")).read()
        self.assertIn("Source read: 2026-11-16", rel)
        self.assertNotIn("Jane", rel)
        self.assertTrue(any(l.startswith("gap after segment 2") for l in self.log))

    def test_dry_writes_nothing(self):
        G.run(args_for(self.tmp, self.gpx, dry=True), out=self.log.append)
        self.assertEqual(os.listdir(os.path.join(self.tmp, "t")), [])

    def test_force_and_missing_dir(self):
        G.run(args_for(self.tmp, self.gpx), out=self.log.append)
        with self.assertRaises(G.TrackError):
            G.run(args_for(self.tmp, self.gpx), out=self.log.append)
        G.run(args_for(self.tmp, self.gpx, force=True), out=self.log.append)
        with self.assertRaises(G.TrackError):
            G.run(args_for(self.tmp, self.gpx, id="nope"), out=self.log.append)

    def test_needs_release_fields(self):
        with self.assertRaises(G.TrackError):
            G.run(args_for(self.tmp, self.gpx, licence=None), out=self.log.append)

    def test_main_reports_html_cleanly(self):
        bad = os.path.join(self.tmp, "bad.gpx")
        with open(bad, "w") as f:
            f.write("<!DOCTYPE html><html></html>")
        self.assertEqual(G.main([bad, "--id", "t", "--out", self.tmp, "--dry"]), 1)


if __name__ == "__main__":
    unittest.main()
