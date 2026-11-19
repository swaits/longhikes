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
                    {"type": "way", "ref": 11, "role": "route"},     # already seen
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
        self.assertEqual(r["way:route"], 1)

    def test_version_and_properties(self):
        self.assertEqual((self.track["version"], self.track["timestamp"]),
                         (7, "2026-01-02T03:04:05Z"))
        w = self.track["main"][0]
        self.assertEqual((w["name"], w["highway"]), ("Main", "path"))
        self.assertNotIn("name", self.track["main"][1])

    def test_wiki_main_roles_are_main(self):
        doc = response()
        for i, role in enumerate(["route", "north", "south", "east", "west"]):
            wid = 100 + i
            doc["elements"].append({"type": "way", "id": wid, "nodes": [1, 2]})
            for el in doc["elements"]:
                if el["type"] == "relation" and el["id"] == 1:
                    el["members"].append({"type": "way", "ref": wid, "role": role})
        track = T.parse(doc, 1, warn=lambda m: None)
        ids = [w["osm_id"] for w in track["main"]]
        for i in range(5):
            self.assertIn(str(100 + i), ids)

    def test_wiki_side_roles_are_side(self):
        doc = response()
        for i, role in enumerate(["alternative", "excursion", "approach", "connection"]):
            wid = 200 + i
            doc["elements"].append({"type": "way", "id": wid, "nodes": [1, 2]})
            for el in doc["elements"]:
                if el["type"] == "relation" and el["id"] == 1:
                    el["members"].append({"type": "way", "ref": wid, "role": role})
        track = T.parse(doc, 1, warn=lambda m: None)
        for i in range(4):
            self.assertIn(str(200 + i), [w["osm_id"] for w in track["side"]])
            self.assertNotIn(str(200 + i), [w["osm_id"] for w in track["main"]])

    def test_unknown_role_among_other_roles_stops_the_tool(self):
        doc = response()
        doc["elements"].append({"type": "way", "id": 50, "nodes": [1, 2]})
        for el in doc["elements"]:
            if el["id"] == 1 and el["type"] == "relation":
                el["members"].append({"type": "way", "ref": 50, "role": "odd"})
        with self.assertRaisesRegex(T.TrackError, "odd.*do not define|do(es)? not define.*odd"):
            T.parse(doc, 1, warn=lambda m: None)

    def test_unknown_role_on_every_member_is_main_with_loud_warning(self):
        doc = {"elements": [
            {"type": "node", "id": 1, "lon": 0.0, "lat": 0.0},
            {"type": "node", "id": 2, "lon": 0.0, "lat": 0.01},
            {"type": "way", "id": 5, "nodes": [1, 2]},
            {"type": "relation", "id": 1, "tags": {"type": "route"},
             "members": [{"type": "way", "ref": 5, "role": "odd"}]}]}
        msgs, warn = quiet()
        track = T.parse(doc, 1, warn=warn)
        self.assertEqual([w["osm_id"] for w in track["main"]], ["5"])
        self.assertTrue(any("UNKNOWN ROLE" in m and "odd" in m for m in msgs))

    def test_teton_shaped_relation_keeps_route_role_ways(self):
        # Relation 3895101 (Teton Crest Trail): 36 of 49 ways carry the role
        # "route", the other 13 the empty role; all are the main line, 57.5 km.
        step = 0.0146                      # degrees of longitude, about 1.17 km at 43.7 N
        els, members = [], []
        for i in range(50):
            els.append({"type": "node", "id": 1000 + i, "lon": -110.9 + step * i, "lat": 43.7})
        for i in range(49):
            els.append({"type": "way", "id": 2000 + i, "nodes": [1000 + i, 1001 + i]})
            members.append({"type": "way", "ref": 2000 + i,
                            "role": "" if i % 4 == 0 and i < 49 and sum(
                                1 for j in range(i) if j % 4 == 0) < 13 else "route"})
        roles = [m["role"] for m in members]
        self.assertEqual((roles.count("route"), roles.count("")), (36, 13))
        els.append({"type": "relation", "id": 3895101, "version": 1, "tags": {"type": "route"},
                    "members": members})
        track = T.parse({"elements": els}, 3895101, warn=lambda m: None)
        self.assertEqual((len(track["main"]), len(track["side"])), (49, 0))
        self.assertAlmostEqual(T.figures(track)["measured_km"], 57.5, delta=0.3)

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


class MultiRelationTests(unittest.TestCase):
    def test_release_text_lists_each_relation(self):
        one = T.release_text("x", 5, "2026-01-02")
        self.assertEqual(one, T.release_text("x", [5], "2026-01-02"))
        two = T.release_text("x", [5, 6], "2026-01-02")
        self.assertIn("Source: https://www.openstreetmap.org/relation/5\n"
                      "Source: https://www.openstreetmap.org/relation/6\n", two)

    def test_two_relations_joined_once_per_way(self):
        import datetime
        calls = []

        def fetch(r):
            calls.append(r)
            return response()
        with tempfile.TemporaryDirectory() as tmp:
            os.mkdir(os.path.join(tmp, "t"))
            ns = argparse.Namespace(relation=[1, 1], id="t", out=tmp, dry=False,
                                    force=False)
            T.run(ns, fetcher=fetch, out=lambda m: None,
                  today=datetime.date(2026, 1, 2))
            self.assertEqual(calls, [1, 1])
            single = T.parse(response(), 1)
            with open(os.path.join(tmp, "t", "line.geojson"), encoding="utf-8") as f:
                self.assertEqual(f.read(), T.geojson_text(single["main"]))
            with open(os.path.join(tmp, "t", "release.txt"), encoding="utf-8") as f:
                self.assertEqual(f.read().count("Source: "), 2)

    def test_merge_main_wins_over_side(self):
        a = {"version": 1, "timestamp": "x", "name": "a", "roles": {"way:(empty)": 1},
             "main": [{"osm_id": "1", "coords": [[0, 0], [1, 1]]}], "side": []}
        b = {"version": 2, "timestamp": "y", "name": "b", "roles": {"way:(empty)": 1},
             "main": [{"osm_id": "2", "coords": [[1, 1], [2, 2]]}],
             "side": [{"osm_id": "1", "coords": [[0, 0], [1, 1]]},
                      {"osm_id": "3", "coords": [[5, 5], [6, 6]]}]}
        m = T.merge_tracks([a, b])
        self.assertEqual([w["osm_id"] for w in m["main"]], ["1", "2"])
        self.assertEqual([w["osm_id"] for w in m["side"]], ["3"])
        self.assertEqual(m["roles"]["way:(empty)"], 2)


class ExcludeNameTests(unittest.TestCase):
    """--exclude-name leaves out ways of other trails and changes nothing else."""

    def test_no_option_gives_the_same_track(self):
        plain = T.parse(response(), 1)
        self.assertEqual(plain["excluded"], [])
        again = T.parse(response(), 1, exclude_names=())
        self.assertEqual(T.geojson_text(plain["main"]), T.geojson_text(again["main"]))
        self.assertEqual(T.geojson_text(plain["side"]), T.geojson_text(again["side"]))

    def test_named_way_is_left_out_of_main(self):
        t = T.parse(response(), 1, exclude_names=["main"])      # way 10 is named "Main"
        self.assertEqual(t["excluded"], [("10", "Main")])
        self.assertNotIn("10", [w["osm_id"] for w in t["main"]])
        plain = T.parse(response(), 1)
        self.assertEqual([w["osm_id"] for w in t["main"]],
                         [w["osm_id"] for w in plain["main"] if w["osm_id"] != "10"])
        self.assertEqual(t["side"], plain["side"])

    def test_unnamed_ways_and_other_names_stay(self):
        t = T.parse(response(), 1, exclude_names=["Some Other Trail"])
        self.assertEqual(t["excluded"], [])
        self.assertEqual(t["main"], T.parse(response(), 1)["main"])

    def test_release_text_says_what_was_left_out(self):
        text = T.release_text("x", 5, "2026-01-02", ["Castle Pass Trail", "Three Fools Creek Trail"])
        self.assertIn("except that ways named Castle Pass Trail, Three Fools Creek Trail were left out", text)
        self.assertEqual(T.release_text("x", 5, "2026-01-02", []), T.release_text("x", 5, "2026-01-02"))

    def test_run_writes_without_the_ways_and_says_so(self):
        import datetime
        msgs = []
        with tempfile.TemporaryDirectory() as tmp:
            os.mkdir(os.path.join(tmp, "t"))
            ns = argparse.Namespace(relation=[1], id="t", out=tmp, dry=False, force=False,
                                    exclude_name=["Main"])
            T.run(ns, fetcher=lambda r: response(), out=msgs.append, today=datetime.date(2026, 1, 2))
            with open(os.path.join(tmp, "t", "line.geojson"), encoding="utf-8") as f:
                self.assertNotIn('"osm_id":"10"', f.read())
            with open(os.path.join(tmp, "t", "release.txt"), encoding="utf-8") as f:
                self.assertIn("ways named Main were left out", f.read())
        self.assertIn("left out: 1 way named 'Main'", msgs)

    def test_command_line_takes_the_option_more_than_once(self):
        calls = []
        real = T.run
        try:
            T.run = lambda args, **kw: calls.append(args)
            T.main(["5", "--id", "t", "--exclude-name", "A", "--exclude-name", "B"])
        finally:
            T.run = real
        self.assertEqual(calls[0].exclude_name, ["A", "B"])


class FetchTests(unittest.TestCase):
    def test_next_endpoint_before_any_wait(self):
        calls, sleeps = [], []

        def opener(req, timeout):
            calls.append((req.full_url, req.get_header("User-agent"), timeout))
            if len(calls) <= 4:
                code = 429 if len(calls) % 2 else 504
                raise urllib.error.HTTPError(req.full_url, code, "busy", {}, None)
            return io.BytesIO(b'{"elements": []}')

        out = T.fetch(1, opener=opener, sleep=sleeps.append)
        self.assertEqual(out, {"elements": []})
        n = len(T.ENDPOINTS)
        self.assertEqual([c[0] for c in calls[:n]], T.ENDPOINTS)
        self.assertEqual(calls[4][0], T.ENDPOINTS[1])
        self.assertEqual(sleeps, [10])      # only one wait: after a full round
        self.assertEqual(calls[0][1], T.USER_AGENT)
        self.assertTrue(calls[0][2])
        self.assertIn("overpass.openstreetmap.fr", " ".join(T.ENDPOINTS))

    def test_gives_up_after_all_rounds(self):
        sleeps = []

        def opener(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 502, "bad", {}, None)
        with self.assertRaises(T.TrackError):
            T.fetch(1, opener=opener, sleep=sleeps.append)
        self.assertEqual(sleeps, list(T.RETRY_WAITS_S))

    def test_other_error_stops(self):
        def opener(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 400, "bad", {}, None)
        with self.assertRaises(T.TrackError):
            T.fetch(1, opener=opener, sleep=lambda s: None)


if __name__ == "__main__":
    unittest.main()
