"""Nearest to me: the distance and the order (app.js, between the near markers, run under node), the
option in every list's sort control, and what the script keeps out of the address.

The position never reaches Python or the page's data; the browser exercise (a granted position)
is not part of the suite.
"""
import json
import math
import os
import shutil
import subprocess
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from olt import hike, home  # noqa: E402
from olt import records as recordsmod  # noqa: E402

NODE = shutil.which("node")
DENVER = (-104.9903, 39.7392)   # lon, lat
TORONTO = (-79.3832, 43.6532)


def js():
    with open(os.path.join(WEB, "assets", "app.js"), encoding="utf-8") as f:
        text = f.read()
    return text[text.index("/* near:begin"):text.index("/* near:end */")]


def run(expr, data=None):
    prog = js() + "\nvar input = JSON.parse(require('fs').readFileSync(0, 'utf8'));\nprocess.stdout.write(JSON.stringify(" + expr + "));"
    out = subprocess.run([NODE, "-e", prog], input=json.dumps(data), capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def haversine(a, b):
    (lo1, la1), (lo2, la2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lo2 - lo1) / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


def feature(tid, geometry, **props):
    return {"type": "Feature", "properties": dict(id=tid, **props), "geometry": geometry}


@unittest.skipUnless(NODE, "node is not installed")
class DistanceTest(unittest.TestCase):
    def test_a_point_to_a_point_is_the_great_circle_distance(self):
        fc = {"features": [feature("p", {"type": "MultiPoint", "coordinates": [list(TORONTO)]}, sketch=True)]}
        got = run("Near.distances(Near.shapesOf(input), %s, %s)" % (DENVER[0], DENVER[1]), fc)["p"]
        self.assertAlmostEqual(got, haversine(DENVER, TORONTO), delta=0.5)
        self.assertTrue(2000 < got < 2300)

    def test_a_line_is_reached_at_its_nearest_point_not_its_nearest_vertex(self):
        # a long east-west line along 40 N with its vertices far from the position: the position is 10 km north of its middle
        line = feature("l", {"type": "LineString", "coordinates": [[-110, 40], [-100, 40]]})
        pos = (-105, 40.09)
        got = run("Near.distances(Near.shapesOf(input), %s, %s)" % pos, {"features": [line]})["l"]
        # the great circle between the two vertices bows north of 40 N, so the position is within a few km of the line
        self.assertLess(got, 12)
        vertex = min(haversine(pos, (-110, 40)), haversine(pos, (-100, 40)))
        self.assertGreater(vertex, 400)

    def test_a_position_beyond_the_end_of_a_line_is_measured_to_the_end(self):
        line = feature("l", {"type": "LineString", "coordinates": [[-110, 40], [-109, 40]]})
        pos = (-107, 40)
        got = run("Near.distances(Near.shapesOf(input), %s, %s)" % pos, {"features": [line]})["l"]
        self.assertAlmostEqual(got, haversine(pos, (-109, 40)), delta=0.5)

    def test_a_multiline_takes_its_nearest_part(self):
        ml = feature("m", {"type": "MultiLineString", "coordinates": [[[-120, 30], [-119, 30]], [[-105, 39.8], [-104.9, 39.8]]]})
        got = run("Near.distances(Near.shapesOf(input), %s, %s)" % DENVER, {"features": [ml]})["m"]
        self.assertLess(got, 15)

    def test_a_sketch_is_its_points_not_its_dotted_line(self):
        line = feature("s", {"type": "LineString", "coordinates": [[-110, 40], [-100, 40]]}, sketch=True)
        pts = feature("s", {"type": "MultiPoint", "coordinates": [[-110, 40], [-100, 40]]}, sketch=True)
        got = run("Near.distances(Near.shapesOf(input), -105, 40.09)", {"features": [line, pts]})["s"]
        self.assertGreater(got, 400)

    def test_a_trail_the_file_does_not_hold_has_no_distance(self):
        got = run("Near.distances(Near.shapesOf(input), -105, 40)", {"features": []})
        self.assertEqual(got, {})
        self.assertIsNone(run("Near.kmTo({points: [], lines: []}, -105, 40)"))

    def test_across_the_antimeridian_and_at_the_poles_nothing_breaks(self):
        fc = {"features": [feature("a", {"type": "LineString", "coordinates": [[179.5, 60], [-179.5, 60]]})]}
        got = run("Near.distances(Near.shapesOf(input), 180, 60.0)", fc)["a"]
        self.assertLess(got, 1)
        got = run("Near.distances(Near.shapesOf(input), 0, 90)", fc)["a"]
        self.assertTrue(math.isfinite(got))


@unittest.skipUnless(NODE, "node is not installed")
class OrderTest(unittest.TestCase):
    def test_nearer_first_then_name_and_no_position_last(self):
        rows = [{"km": 50, "name": "b"}, {"km": None, "name": "a"}, {"km": 50, "name": "a"}, {"km": 10, "name": "z"},
                {"km": None, "name": "c"}]
        got = run("input.slice().sort(Near.compare)", rows)
        self.assertEqual([(r["km"], r["name"]) for r in got],
                         [(10, "z"), (50, "a"), (50, "b"), (None, "a"), (None, "c")])

    def test_real_start_points_are_ordered_as_an_independent_haversine_orders_them(self):
        recs = recordsmod.load_records(ROOT)
        feats, pts = [], {}
        for r in recs:
            p = hike.start_point(r)
            if p:
                pts[r["id"]] = tuple(p)
                feats.append(feature(r["id"], {"type": "MultiPoint", "coordinates": [p]}, sketch=True))
        self.assertGreater(len(pts), 50)
        for here in (DENVER, TORONTO):
            got = run("Near.distances(Near.shapesOf(input), %s, %s)" % here, {"features": feats})
            self.assertEqual(set(got), set(pts))
            want = sorted(pts, key=lambda i: (haversine(here, pts[i]), i))
            mine = sorted(got, key=lambda i: (round(got[i], 3), i))
            self.assertEqual(mine[:10], want[:10])
            for i in pts:
                self.assertAlmostEqual(got[i], haversine(here, pts[i]), delta=0.5)


class WiringTest(unittest.TestCase):
    def test_every_list_s_sort_control_ends_with_nearest_to_me(self):
        for select in (home.sort_select(), home.sort_select(saved=True), home.sort_select(ranked="Length"),
                       home.sort_select(wholly=lambda r: True)):
            self.assertTrue(select.rstrip().split("</select>")[0].rstrip().endswith('<option value="nearest">Nearest to me</option>'))

    def test_the_position_is_never_written_to_the_address_or_to_storage(self):
        with open(os.path.join(WEB, "assets", "app.js"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("if (key === defaultSortOf(root) || key === 'nearest') p.delete('sort')", text)
        self.assertIn("sort.value !== 'nearest') p.set('sort', sort.value)", text)
        self.assertIn("return key === 'nearest' ? '' : key;", text)
        self.assertIn("p.get('sort') === 'nearest' ? '' :", text)
        near = text[text.index("var nearAway = null;"):text.index("function applySortUI")]
        for forbidden in ("localStorage", "sessionStorage", "writePref", "history.", "window.location", "XMLHttpRequest", "sendBeacon"):
            self.assertNotIn(forbidden, near)
        # the only request is for the overview geometry the maps use
        self.assertEqual(near.count("fetch("), 1)
        self.assertIn("fetch('/data/overview.geojson'", near)
        self.assertEqual(near.count("getCurrentPosition("), 1)

    def test_the_privacy_line_and_the_fallbacks_are_worded(self):
        with open(os.path.join(WEB, "assets", "app.js"), encoding="utf-8") as f:
            text = f.read()
        for words in ("Your position stays in this browser: it is not stored, sent or put in the address.",
                      "Your position was not available, so the list is back in its earlier order.",
                      "no position on file"):
            self.assertIn(words, text)


if __name__ == "__main__":
    unittest.main()
