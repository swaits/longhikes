"""Tests for tools/osm_track.py: no network.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import argparse
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import osm_track as T  # noqa: E402

# Nodes lie on a line of latitude, 0.001 degree (about 80 m) apart.
# way 10: n1-n2-n3, way 11: n4-n3 (reversed, joins way 10 at n3),
# way 12: n4-n5 (continues), way 13: far away (gap -> second part),
# way 20: side way, way 30: in a side sub-relation, way 40: in the sub-relation.
NODES = {i: (-100.0 + 0.001 * i, 40.0) for i in range(1, 6)}
NODES[6] = (-99.0, 40.0)
NODES[7] = (-99.0, 40.001)
NODES[8] = (-100.0, 40.01)
NODES[9] = (-100.0, 40.011)
NODES[10] = (-99.5, 40.5)
NODES[11] = (-99.5, 40.501)
NODES[12] = (-98.0, 40.0)
NODES[13] = (-98.0, 40.001)


def response():
    els = [{"type": "node", "id": i, "lon": lon, "lat": lat}
           for i, (lon, lat) in NODES.items()]

    def way(i, nodes, **tags):
        return {"type": "way", "id": i, "nodes": nodes, "tags": tags}

    els += [
        way(10, [1, 2, 3], name="Main", highway="path"),
        way(11, [4, 3], highway="track"),
        way(12, [4, 5]),
        way(13, [6, 7], name="After the gap"),
        way(20, [8, 9], highway="footway"),
        way(30, [10, 11]),
        way(40, [12, 13]),
    ]
    els.append({"type": "relation", "id": 2, "tags": {"type": "route", "name": "Sub"},
                "members": [{"type": "way", "ref": 40, "role": ""}]})
    els.append({"type": "relation", "id": 3, "tags": {"type": "route", "name": "Side"},
                "members": [{"type": "way", "ref": 30, "role": "main"}]})
    els.append({"type": "relation", "id": 1, "version": 7, "timestamp": "2026-01-02T03:04:05Z",
                "tags": {"type": "route", "route": "hiking", "name": "Test Trail"},
                "members": [
                    {"type": "node", "ref": 1, "role": "stop"},
                    {"type": "way", "ref": 10, "role": ""},
                    {"type": "way", "ref": 11, "role": "forward"},
                    {"type": "way", "ref": 12, "role": "main"},
                    {"type": "way", "ref": 10, "role": ""},          # listed twice
                    {"type": "way", "ref": 20, "role": "alternative"},
                    {"type": "way", "ref": 13, "role": "backward"},
                    {"type": "relation", "ref": 2, "role": ""},
                    {"type": "relation", "ref": 3, "role": "connection"},
                    {"type": "way", "ref": 11, "role": "oddity"},    # already seen
                ]})
    return {"elements": els}


def quiet():
    msgs = []
    return msgs, msgs.append


class ParseTests(unittest.TestCase):
    def setUp(self):
        self.warnings, warn = quiet()
        self.track = T.parse(response(), 1, warn=warn)

    def ids(self, key):
        return [w["osm_id"] for w in self.track[key]]

    def test_roles_split_in_member_order(self):
        self.assertEqual(self.ids("main"), ["10", "11", "12", "13", "40"])
        self.assertEqual(self.ids("side"), ["20", "30"])

    def test_sub_relation_side_role_covers_its_ways(self):
        self.assertIn("30", self.ids("side"))   # role "main" inside a "connection" relation

    def test_way_listed_twice_once(self):
        self.assertEqual(self.ids("main").count("10"), 1)

    def test_role_counts(self):
        r = self.track["roles"]
        self.assertEqual(r["way:(empty)"], 3)
        self.assertEqual(r["way:alternative"], 1)
        self.assertEqual(r["relation:connection"], 1)
        self.assertEqual(r["way:oddity"], 1)

    def test_version_and_properties(self):
        self.assertEqual((self.track["version"], self.track["timestamp"]),
                         (7, "2026-01-02T03:04:05Z"))
        w = self.track["main"][0]
        self.assertEqual((w["name"], w["highway"]), ("Main", "path"))
        self.assertNotIn("name", self.track["main"][1])

    def test_unknown_role_is_side_with_warning(self):
        doc = response()
        for el in doc["elements"]:
            if el["id"] == 1 and el["type"] == "relation":
                el["members"].append({"type": "way", "ref": 40, "role": "odd"})
        # way 40 was already seen through the sub-relation, so use a new way
        doc["elements"].append({"type": "way", "id": 50, "nodes": [1, 2]})
        for el in doc["elements"]:
            if el["id"] == 1 and el["type"] == "relation":
                el["members"].append({"type": "way", "ref": 50, "role": "odd"})
        msgs, warn = quiet()
        track = T.parse(doc, 1, warn=warn)
        self.assertIn("50", [w["osm_id"] for w in track["side"]])
        self.assertTrue(any("odd" in m for m in msgs))

    def test_way_main_in_one_place_and_side_in_another_is_main(self):
        doc = response()
        for el in doc["elements"]:
            if el["type"] == "relation" and el["id"] == 3:
                el["members"].append({"type": "way", "ref": 10, "role": ""})
        t = T.parse(doc, 1, warn=lambda m: None)
        self.assertIn("10", [w["osm_id"] for w in t["main"]])
        self.assertNotIn("10", [w["osm_id"] for w in t["side"]])

    def test_not_a_route(self):
        doc = response()
        for el in doc["elements"]:
            if el["type"] == "relation" and el["id"] == 1:
                el["tags"]["type"] = "boundary"
        with self.assertRaisesRegex(T.TrackError, "not type=route"):
            T.parse(doc, 1, warn=lambda m: None)

    def test_no_ways(self):
        doc = {"elements": [{"type": "relation", "id": 1, "tags": {"type": "route"},
                             "members": [{"type": "node", "ref": 1, "role": ""}]}]}
        with self.assertRaisesRegex(T.TrackError, "no way members"):
            T.parse(doc, 1)

    def test_cycle_does_not_loop(self):
        doc = response()
        for el in doc["elements"]:
            if el["type"] == "relation" and el["id"] == 2:
                el["members"].append({"type": "relation", "ref": 1, "role": ""})
        T.parse(doc, 1, warn=lambda m: None)


class FigureTests(unittest.TestCase):
    def test_figures_and_parts(self):
        track = T.parse(response(), 1, warn=lambda m: None)
        fig = T.figures(track)
        self.assertEqual((fig["main_ways"], fig["alternate_ways"]), (5, 2))
        # ways 10, 11 (reversed), 12 chain into one; 13 and 40 are apart
        self.assertEqual(fig["parts"], 3)
        self.assertAlmostEqual(fig["measured_km"], 0.563, places=2)

    def test_join_matches_elevation(self):
        try:
            import elevation
        except ImportError:
            self.skipTest("numpy or Pillow not installed")
        track = T.parse(response(), 1, warn=lambda m: None)
        parts = [[tuple(c) for c in w["coords"]] for w in track["main"]]
        self.assertEqual(T.join_parts(parts), elevation.join_parts(parts))


class OutputTests(unittest.TestCase):
    def test_geojson_compact_ordered_rounded(self):
        track = T.parse(response(), 1, warn=lambda m: None)
        text = T.geojson_text(track["main"])
        self.assertNotIn(" ", text.replace("Test", "").replace("After the gap", "")
                         .replace("Main", ""))
        doc = json.loads(text)
        self.assertEqual(doc["type"], "FeatureCollection")
        f = doc["features"][0]
        self.assertEqual(f["properties"], {"osm_id": "10", "name": "Main", "highway": "path"})
        self.assertEqual(f["geometry"]["coordinates"][0], [-99.999, 40.0])
        self.assertEqual(text, T.geojson_text(track["main"]))

    def test_rounding(self):
        doc = {"elements": [
            {"type": "node", "id": 1, "lon": 1.23456789, "lat": 2.0000004},
            {"type": "node", "id": 2, "lon": 1.2, "lat": 2.1},
            {"type": "way", "id": 5, "nodes": [1, 2]},
            {"type": "relation", "id": 9, "tags": {"type": "route"},
             "members": [{"type": "way", "ref": 5, "role": ""}]}]}
        t = T.parse(doc, 9)
        self.assertEqual(t["main"][0]["coords"][0], [1.234568, 2.0])

    def test_release_text(self):
        text = T.release_text("loyalsock", 3134579, "2026-11-10")
        with open(os.path.join(T.ROOT, "loyalsock", "release.txt"), encoding="utf-8") as f:
            self.assertEqual(text, f.read())


class RunTests(unittest.TestCase):
    def args(self, tmp, **kw):
        d = dict(relation=1, id="t", out=tmp, dry=False, force=False)
        d.update(kw)
        return argparse.Namespace(**d)

    def test_missing_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(T.TrackError, "does not exist"):
                T.run(self.args(tmp), fetcher=lambda r: response(), out=lambda m: None)

    def test_write_refuse_force_dry(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.mkdir(os.path.join(tmp, "t"))
            fetch = lambda r: response()  # noqa: E731
            msgs = []
            import datetime
            T.run(self.args(tmp, dry=True), fetcher=fetch, out=msgs.append)
            self.assertEqual(os.listdir(os.path.join(tmp, "t")), [])
            T.run(self.args(tmp), fetcher=fetch, out=msgs.append,
                  today=datetime.date(2026, 1, 2))
            self.assertEqual(sorted(os.listdir(os.path.join(tmp, "t"))),
                             ["alternates.geojson", "line.geojson", "release.txt"])
            with self.assertRaisesRegex(T.TrackError, "--force"):
                T.run(self.args(tmp), fetcher=fetch, out=msgs.append)
            T.run(self.args(tmp, force=True), fetcher=fetch, out=msgs.append)
            self.assertTrue(any(m.startswith("parts") for m in msgs))

    def test_no_alternates_file_when_no_side_ways(self):
        doc = response()
        doc["elements"] = [e for e in doc["elements"]
                           if not (e["type"] == "way" and e["id"] in (20, 30))]
        for el in doc["elements"]:
            if el["type"] == "relation" and el["id"] == 1:
                el["members"] = [m for m in el["members"]
                                 if m["ref"] not in (20, 3, 30)]
        with tempfile.TemporaryDirectory() as tmp:
            os.mkdir(os.path.join(tmp, "t"))
            T.run(self.args(tmp), fetcher=lambda r: doc, out=lambda m: None)
            self.assertNotIn("alternates.geojson", os.listdir(os.path.join(tmp, "t")))


class FetchTests(unittest.TestCase):
    def test_retry_then_mirror(self):
        calls, sleeps = [], []

        def opener(req, timeout):
            calls.append((req.full_url, req.get_header("User-agent"), timeout))
            if len(calls) <= 5:
                code = 429 if len(calls) % 2 else 504
                raise urllib.error.HTTPError(req.full_url, code, "busy", {}, None)
            return io.BytesIO(b'{"elements": []}')

        out = T.fetch(1, opener=opener, sleep=sleeps.append)
        self.assertEqual(out, {"elements": []})
        self.assertEqual(calls[0][0], T.ENDPOINTS[0])
        self.assertEqual(calls[4][0], T.ENDPOINTS[1])
        self.assertEqual(sleeps, [10, 30, 60, 10])
        self.assertEqual(calls[0][1], T.USER_AGENT)
        self.assertTrue(calls[0][2])

    def test_other_error_stops(self):
        def opener(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 400, "bad", {}, None)
        with self.assertRaises(T.TrackError):
            T.fetch(1, opener=opener, sleep=lambda s: None)


if __name__ == "__main__":
    unittest.main()
