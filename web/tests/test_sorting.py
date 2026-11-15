"""Tests for sorting every list of trails, and for sketching trails with no
track on maps from their start (and end) points.

Sort parity: the Python order (facets.sort_records) is compared with a Python
re-implementation of the app.js comparator over the rendered rows' data-*
attributes, for each of the eight keys, so the check needs no browser.
"""
import copy
import html
import os
import re
import sys
import unittest
from functools import cmp_to_key

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build  # noqa: E402
from olt import browse, docs, facets, hike, home, records, trail  # noqa: E402
from test_hike import GH, fake  # noqa: E402


def make(id_, name, km=100, days=None, climb=None, coverage=1.0, **kw):
    rec = fake(1, km=km, **kw)
    rec["id"], rec["name"] = id_, name
    if days is not None:
        rec["hike"] = dict(rec.get("hike") or {}, days=days)
    if climb is not None:
        rec["derived"]["elevation"] = {"ascent_m": climb, "coverage": coverage}
    return rec


def ids(recs):
    return [r["id"] for r in recs]


def row_data(rec):
    """The data-* values of a rendered row, as the script reads them."""
    row = home.entry(rec)
    attrs = dict(re.findall(r'data-(\w+)="([^"]*)"', row.split("\n", 1)[0]))
    return {k: html.unescape(v) for k, v in attrs.items()}


def _cmp(a, b):
    return (a > b) - (a < b)


def js_compare(x, y, key):
    """compareEntries in app.js, restated over parsed data-* strings."""
    if key == "name":
        return _cmp(x["name"], y["name"])
    if key == "name-desc":
        return _cmp(y["name"], x["name"])
    if key.startswith("climb"):
        xc = None if x["climb"] == "" else float(x["climb"])
        yc = None if y["climb"] == "" else float(y["climb"])
        if xc is None or yc is None:
            if xc is None and yc is None:
                return _cmp(x["name"], y["name"])
            return 1 if xc is None else -1
        return (_cmp(yc, xc) if key == "climb-desc" else _cmp(xc, yc)) or _cmp(x["name"], y["name"])
    field = "km" if key.startswith("length") else "days"
    order = _cmp(float(y[field]), float(x[field])) if key.endswith("-desc") else _cmp(float(x[field]), float(y[field]))
    return order or _cmp(x["name"], y["name"])


FIXTURES = [
    make("b-trail", "B Trail", km=300, days=[10, 20], climb=5000),
    make("a-trail", "The A Trail", km=100, days=[5, 20], climb=9000),
    make("c-trail", "C Trail", km=300, days=[3, 8]),                      # no climb
    make("d-trail", "D Trail", km=50, days=[30, 40], climb=1000, coverage=0.5),  # climb hidden
    make("e-trail", "E Trail", km=900, days=[60, 90], climb=9000),
]


class SortKeysTest(unittest.TestCase):
    def test_options_in_order_and_wording(self):
        self.assertEqual([label for _, label in facets.SORTS], [
            "Name, A to Z", "Name, Z to A", "Length, longest first", "Length, shortest first",
            "Time, quickest first", "Time, slowest first", "Climb, most first", "Climb, least first"])
        select = home.sort_select("length-asc")
        self.assertIn('<span class="results-sort__label">Sort by</span>', select)
        self.assertIn('<option value="length-asc" selected>Length, shortest first</option>', select)
        self.assertEqual([m for m in re.findall(r'<option value="([^"]+)"', select)],
                         [k for k, _ in facets.SORTS])

    def test_old_address_keys_still_work(self):
        for old, new in [("long", "length-desc"), ("short", "length-asc"),
                         ("quick", "time-asc"), ("climb", "climb-desc"), ("name", "name")]:
            self.assertEqual(facets.normalize_sort(old), new, old)
        self.assertEqual(facets.normalize_sort("bogus", "time-asc"), "time-asc")
        self.assertEqual(facets.normalize_sort(None), "name")

    def test_each_order(self):
        self.assertEqual(ids(facets.sort_records(FIXTURES, "name")),
                         ["a-trail", "b-trail", "c-trail", "d-trail", "e-trail"])
        self.assertEqual(ids(facets.sort_records(FIXTURES, "name-desc")),
                         ["e-trail", "d-trail", "c-trail", "b-trail", "a-trail"])
        # 300 km tie falls back to name
        self.assertEqual(ids(facets.sort_records(FIXTURES, "length-desc")),
                         ["e-trail", "b-trail", "c-trail", "a-trail", "d-trail"])
        self.assertEqual(ids(facets.sort_records(FIXTURES, "length-asc")),
                         ["d-trail", "a-trail", "b-trail", "c-trail", "e-trail"])
        # 20-day tie falls back to name
        self.assertEqual(ids(facets.sort_records(FIXTURES, "time-asc")),
                         ["c-trail", "a-trail", "b-trail", "d-trail", "e-trail"])
        self.assertEqual(ids(facets.sort_records(FIXTURES, "time-desc")),
                         ["e-trail", "d-trail", "a-trail", "b-trail", "c-trail"])
        # no climb (or a hidden one) goes last in both climb orders, by name
        self.assertEqual(ids(facets.sort_records(FIXTURES, "climb-desc")),
                         ["a-trail", "e-trail", "b-trail", "c-trail", "d-trail"])
        self.assertEqual(ids(facets.sort_records(FIXTURES, "climb-asc")),
                         ["b-trail", "a-trail", "e-trail", "c-trail", "d-trail"])

    def test_hidden_climb_is_empty_in_the_row(self):
        data = row_data(FIXTURES[3])  # coverage 0.5: the row hides its climb
        self.assertEqual(data["climb"], "")
        self.assertNotIn("<dt>Climb</dt>", home.entry(FIXTURES[3]))

    def test_python_order_matches_the_script_over_row_data(self):
        rows = [row_data(r) for r in FIXTURES]
        for key, _ in facets.SORTS:
            script_order = [d["id"] for d in sorted(rows, key=cmp_to_key(lambda a, b, k=key: js_compare(a, b, k)))]
            self.assertEqual(ids(facets.sort_records(FIXTURES, key)), script_order, key)

    def test_real_records_sort_by_name(self):
        recs = records.load_records()
        names = [facets.sort_name(r) for r in facets.sort_records(recs, "name")]
        self.assertEqual(names, sorted(names))


class ListDefaultsTest(unittest.TestCase):
    def test_only_four_lists_open_in_another_order(self):
        special = {lst.key: lst.sort for lst in browse.LISTS if lst.sort != "name"}
        self.assertEqual(special, {"longest": "length-desc", "under-100-km": "length-asc",
                                   "a-week-or-less": "time-asc", "one-to-two-weeks": "time-asc"})
        for lst in browse.LISTS:
            self.assertIn(lst.sort, facets.SORT_LABEL, lst.key)
            self.assertFalse(hasattr(lst, "order"), lst.key)

    def test_members_come_in_the_list_order(self):
        recs = [make("short", "Short", km=3000), make("long", "Long", km=5000), make("mid", "Mid", km=100)]
        self.assertEqual(ids(browse.members(browse.by_key("longest"), recs)), ["long", "short"])
        self.assertEqual(ids(browse.members(browse.by_key("under-100-km"),
                                             [make("a", "A", km=90), make("b", "B", km=10)])), ["b", "a"])


class ResultsHtmlTest(unittest.TestCase):
    def test_every_list_has_the_sort_control_in_its_default_order(self):
        doc = str(home.results(FIXTURES, default_sort="length-desc"))
        self.assertIn("Sort by", doc)
        self.assertIn('data-default-sort="length-desc"', doc)
        self.assertIn('<option value="length-desc" selected>', doc)
        self.assertEqual(re.findall(r'data-id="([^"]+)"', doc),
                         ids(facets.sort_records(FIXTURES, "length-desc")))
        self.assertIn('data-sort-status', doc)

    def test_column_heads_are_sort_buttons_that_agree(self):
        head = home.list_head("time-desc")
        self.assertIn('aria-hidden="true"', head)
        for col in ("name", "length", "time", "climb"):
            self.assertIn(f'data-sort-col="{col}"', head)
        self.assertNotIn('data-sort-col="gpx"', head)
        self.assertIn("GPX", head)
        # the active column is marked, the rest show the two-way mark
        self.assertIn('class="list-head__sort is-active" data-sort-col="time"', head)
        self.assertIn("↓", head)
        self.assertIn("↕", head)
        # buttons stay out of the tab order: the select is the one control
        self.assertEqual(head.count('tabindex="-1"'), 4)

    def test_grouped_lists_sort_within_each_group(self):
        groups = [("By B", [FIXTURES[0], FIXTURES[1]], None),
                  ("By A", [FIXTURES[4], FIXTURES[2]], None)]
        doc = str(home.results(groups=groups, default_sort="length-asc"))
        self.assertEqual(re.findall(r'data-id="([^"]+)"', doc),
                         ["a-trail", "b-trail", "c-trail", "e-trail"])
        self.assertLess(doc.index("By B"), doc.index("By A"))  # group order kept


def sketch_rec(id_="sk", name="Sketch Trail", start=(-110.0, 40.0), end=(-100.0, 45.0), **kw):
    hike_table = {"start": "Start Town", "shape": "point-to-point"}
    if start is not None:
        hike_table["start_lonlat"] = list(start)
    if end is not None:
        hike_table["end"] = "End Town"
        hike_table["end_lonlat"] = list(end)
    rec = make(id_, name, hike=hike_table, **kw)
    return rec


class SketchPointsTest(unittest.TestCase):
    def test_points_are_read_and_checked(self):
        self.assertEqual(hike.sketch_points(sketch_rec()), [[-110.0, 40.0], [-100.0, 45.0]])
        self.assertEqual(hike.sketch_points(sketch_rec(end=None)), [[-110.0, 40.0]])
        self.assertEqual(hike.sketch_points(sketch_rec(start=None)), [[-100.0, 45.0]])
        self.assertEqual(hike.sketch_end(sketch_rec(start=None)), "end")
        self.assertEqual(hike.sketch_end(sketch_rec(end=None)), "start")
        self.assertEqual(hike.sketch_end(sketch_rec()), "")
        bad = sketch_rec(end=None)
        bad["hike"]["start_lonlat"] = [999, 40]
        self.assertEqual(hike.sketch_points(bad), [])
        bad["hike"]["start_lonlat"] = "not a place"
        self.assertEqual(hike.sketch_points(bad), [])

    def test_a_track_suppresses_the_sketch(self):
        rec = sketch_rec()
        rec["derived"]["has_line"] = True
        rec["derived"]["files"] = {"line": "sk/line.geojson"}
        self.assertEqual(hike.sketch_points(rec), [])

    def test_sketch_is_never_a_track(self):
        rec = sketch_rec()
        self.assertEqual(facets.gpx(rec), "elsewhere")
        self.assertFalse(facets.gpx_here(rec))
        self.assertEqual(build.trail_outputs(rec["id"], {}, rec), ["sketch.json"])
        self.assertEqual(rec["derived"]["downloads"], [])
        self.assertIsNone(facets.row_climb_m(rec))

    def test_sketch_features(self):
        feats = build.sketch_features(sketch_rec())
        self.assertEqual([f["geometry"]["type"] for f in feats], ["LineString", "MultiPoint"])
        for f in feats:
            self.assertIs(f["properties"]["sketch"], True)
            self.assertEqual(f["properties"]["id"], "sk")
            self.assertEqual(f["properties"]["name"], "Sketch Trail")
        one = build.sketch_features(sketch_rec(end=None))
        self.assertEqual([f["geometry"]["type"] for f in one], ["MultiPoint"])
        self.assertEqual(one[0]["geometry"]["coordinates"], [[-110.0, 40.0]])
        self.assertEqual(build.sketch_features(make("plain", "Plain")), [])

    def test_overview_includes_sketches_only(self):
        fc = build.overview_geojson([sketch_rec(), make("plain", "Plain")], "/nonexistent")
        self.assertEqual(sorted({f["properties"]["id"] for f in fc["features"]}), ["sk"])


class SketchMapTest(unittest.TestCase):
    def test_sketches_count_toward_the_map_minimum(self):
        recs = [sketch_rec(f"s{i}", f"S{i}") for i in range(3)]
        doc = str(home.overview_map(recs, "Map"))
        self.assertIn('data-map="overview"', doc)
        self.assertIn("No GPX here: start and end only", doc)
        self.assertIn("dotted straight line between their start and end", doc)
        self.assertIn("That is not the trail&rsquo;s path.", doc)
        for i in range(3):
            self.assertIn(f"s{i}", doc)
        self.assertTrue(home.has_overview_map(recs))
        self.assertIn("-110.0000", home.overview_bbox(recs))

    def test_too_few_drawable_is_a_note_that_stays_true(self):
        doc = str(home.overview_map([sketch_rec()], "Map"))
        self.assertNotIn('data-map="overview"', doc)
        self.assertIn("a GPX here or a known start or end", doc)
        doc = str(home.overview_map([make("plain", "Plain")], "Map"))
        self.assertIn("or a known start or end, so there is nothing to draw", doc)
        self.assertFalse(home.has_overview_map([sketch_rec()]))

    def test_no_sketch_no_legend_entry(self):
        recs = []
        for i in range(3):
            rec = make(f"t{i}", f"T{i}")
            rec["derived"]["files"] = {"line": f"t{i}/line.geojson"}
            rec["derived"]["has_line"] = True
            recs.append(rec)
        doc = str(home.overview_map(recs, "Map"))
        self.assertIn("3 tracks, simplified for display.", doc)
        self.assertNotIn("start and end only", doc)

    def test_trail_page_shows_a_sketch_map(self):
        _t, _d, body, needs_map = trail.render(sketch_rec(), GH)
        self.assertTrue(needs_map)
        self.assertIn('data-map="sketch"', body)
        self.assertIn("/trails/sk/sketch.json", body)
        self.assertIn("Start Town", body)
        self.assertIn("End Town", body)
        self.assertIn("not the trail&rsquo;s path", body)
        self.assertIn("No GPX here", body)
        self.assertNotIn("map--empty", body)

    def test_trail_page_with_only_a_start_shows_a_ring(self):
        _t, _d, body, needs_map = trail.render(sketch_rec(end=None), GH)
        self.assertTrue(needs_map)
        self.assertIn("The ring marks Start Town", body)

    def test_trail_page_without_a_point_keeps_the_empty_frame(self):
        _t, _d, body, needs_map = trail.render(make("plain", "Plain Trail"), GH)
        self.assertFalse(needs_map)
        self.assertIn("map--empty", body)
        self.assertNotIn("sketch.json", body)


class ScriptAndDocsTest(unittest.TestCase):
    def test_script_has_the_dotted_sketch_and_the_sort_state(self):
        with open(os.path.join(WEB, "assets", "app.js"), encoding="utf-8") as f:
            js = f.read()
        for part in ("dash: [0, 2]", "olt-sketch-points", "No GPX here. The dotted line only joins",
                     "normalizeSortKey", "replaceState", "data-sort-col", "'long': 'length-desc'",
                     "fallback__ring", "fallback__line--sketch"):
            self.assertIn(part, js, part)

    def test_data_page_describes_sketches(self):
        text = " ".join(what for _, what, _ in docs.BULK_FILES)
        self.assertIn("sketch", text.lower())
        self.assertIn("not a track", text.lower())


if __name__ == "__main__":
    unittest.main()
