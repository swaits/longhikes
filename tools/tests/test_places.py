"""Tests for tools/check_places.py: the places.toml registry and the record's place fields.

Standard library only. Run from the repository root:
    python3 -m unittest discover tools/tests -p "test_places.py"
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import build_index  # noqa: E402
import check_places as C  # noqa: E402


def entry(**kw):
    base = {"slug": "wind-river-range", "kind": "range", "name": "Wind River Range",
            "where": ["WY"], "source": "gmba-v2", "source_id": "1",
            "source_version": "2026-11-20", "box": [-110.0, 42.5, -108.5, 43.5]}
    base.update(kw)
    return base


def record(**kw):
    base = {"id": "x", "source": {"line_file": ""}}
    base.update(kw)
    return base


REGISTRY = {("range", "wind-river-range"): entry()}


def registry_errors(entries):
    errors = []
    C.check_registry(entries, errors)
    return errors


def record_errors(rec, tdir=None, registry=REGISTRY):
    errors = []
    C.check_record(rec.get("id", "x"), rec, tdir or "/no-such-dir", registry, errors)
    return errors


class RegistryTest(unittest.TestCase):
    def test_registry_entry_needs_every_field(self):
        e = entry()
        del e["box"]
        self.assertTrue(any("box" in m for m in registry_errors([e])))

    def test_kind_must_be_park_range_or_wilderness(self):
        self.assertTrue(any("kind" in m for m in registry_errors([entry(kind="forest")])))
        for kind in ("park", "range", "wilderness"):
            self.assertEqual(registry_errors([entry(kind=kind)]), [], kind)

    def test_same_slug_in_two_kinds_is_allowed_and_twice_in_one_kind_is_not(self):
        a = entry(slug="glacier", kind="park")
        b = entry(slug="glacier", kind="wilderness")
        self.assertEqual(registry_errors([a, b]), [])
        self.assertTrue(any("glacier" in m for m in registry_errors([a, dict(a)])))

    def test_within_names_existing_ranges_and_has_no_cycle(self):
        parent = entry(slug="rocky-mountains", name="Rocky Mountains")
        child = entry(within=["rocky-mountains"])
        self.assertEqual(registry_errors([parent, child]), [])
        self.assertTrue(any("within" in m for m in registry_errors([entry(within=["no-such"])])))
        park_parent = entry(slug="some-park", kind="park")
        self.assertTrue(any("within" in m for m in registry_errors([park_parent, entry(within=["some-park"])])))
        a = entry(slug="a", within=["b"])
        b = entry(slug="b", within=["a"])
        self.assertTrue(any("within" in m for m in registry_errors([a, b])))

    def test_source_id_is_a_string_or_a_list_of_strings(self):
        self.assertEqual(registry_errors([entry(source_id=["1", "2"])]), [])
        self.assertTrue(any("source_id" in m for m in registry_errors([entry(source_id=7)])))
        self.assertTrue(any("source_id" in m for m in registry_errors([entry(source_id=[])])))

    def test_box_is_west_south_east_north_inside_the_world(self):
        for bad in ([-108.5, 42.5, -110.0, 43.5], [-190.0, 42.5, -108.5, 43.5],
                    [-110.0, 42.5, -108.5, 95.0], [-110.0, 42.5, -108.5], "x"):
            self.assertTrue(any("box" in m for m in registry_errors([entry(box=bad)])), bad)


class RecordTest(unittest.TestCase):
    def test_record_place_must_be_in_the_registry(self):
        rec = record(place=[{"kind": "range", "slug": "no-such", "basis": "stated",
                             "source": "https://example.org/x"}])
        self.assertTrue(any("not in places.toml" in m for m in record_errors(rec)))

    def test_track_basis_needs_km_and_forbids_source_and_stated_the_reverse(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "line.geojson"), "w") as f:
                f.write("{}")
            h = C.track_hash(os.path.join(d, "line.geojson"))
            base = record(source={"line_file": "line.geojson"}, places_checked="2026-11-20",
                          places_track=h)
            ok = dict(base, place=[{"kind": "range", "slug": "wind-river-range",
                                    "basis": "track", "km": 12.3}])
            self.assertEqual(record_errors(ok, d), [])
            no_km = dict(base, place=[{"kind": "range", "slug": "wind-river-range", "basis": "track"}])
            self.assertTrue(any("km" in m for m in record_errors(no_km, d)))
            with_src = dict(base, place=[{"kind": "range", "slug": "wind-river-range",
                                          "basis": "track", "km": 1.0, "source": "https://x/"}])
            self.assertTrue(any("source" in m for m in record_errors(with_src, d)))
        stated_km = record(place=[{"kind": "range", "slug": "wind-river-range", "basis": "stated",
                                   "km": 3.0, "source": "https://example.org/x"}])
        self.assertTrue(any("km" in m for m in record_errors(stated_km)))

    def test_stated_needs_a_source_url_and_a_trackless_record(self):
        no_url = record(place=[{"kind": "range", "slug": "wind-river-range",
                                "basis": "stated", "source": "a book"}])
        self.assertTrue(any("source" in m for m in record_errors(no_url)))
        tracked = record(source={"line_file": "line.geojson"},
                         place=[{"kind": "range", "slug": "wind-river-range",
                                 "basis": "stated", "source": "https://example.org/x"}])
        self.assertTrue(any("stated" in m for m in record_errors(tracked)))

    def test_a_place_is_listed_once_per_record(self):
        one = {"kind": "range", "slug": "wind-river-range", "basis": "stated",
               "source": "https://example.org/x"}
        self.assertTrue(any("once" in m or "twice" in m for m in record_errors(record(place=[one, dict(one)]))))

    def test_places_track_must_match_the_track_file(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "line.geojson"), "w") as f:
                f.write("{}")
            rec = record(source={"line_file": "line.geojson"}, places_checked="2026-11-20",
                         places_track="0" * 16)
            self.assertTrue(any("track has changed since" in m for m in record_errors(rec, d)))

    def test_a_record_with_a_track_needs_places_track_and_one_without_must_not_have_it(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "line.geojson"), "w") as f:
                f.write("{}")
            rec = record(source={"line_file": "line.geojson"}, places_checked="2026-11-20")
            self.assertTrue(any("places_track" in m for m in record_errors(rec, d)))
        no_track = record(places_checked="2026-11-20", places_track="a" * 16)
        self.assertTrue(any("places_track" in m for m in record_errors(no_track)))

    def test_places_checked_required_only_when_switched_on(self):
        rec = record()
        with mock.patch.object(C, "REQUIRE_PLACES_CHECKED", True):
            self.assertTrue(any("places_checked" in m for m in record_errors(rec)))
        with mock.patch.object(C, "REQUIRE_PLACES_CHECKED", False):
            self.assertEqual(record_errors(rec), [])
        bad = record(places_checked="yesterday")
        self.assertTrue(any("places_checked" in m for m in record_errors(bad)))

    def test_a_trackless_trail_given_a_track_later_is_refused(self):
        rec = record(source={"line_file": "line.geojson"}, places_checked="2026-11-20",
                     place=[{"kind": "range", "slug": "wind-river-range",
                             "basis": "stated", "source": "https://example.org/x"}])
        errors = record_errors(rec)
        self.assertTrue(any("stated" in m for m in errors))
        self.assertTrue(any("places_track" in m for m in errors))


class WholeRepoTest(unittest.TestCase):
    def test_every_registry_entry_is_named_by_a_record(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "places.toml"), "w") as f:
                f.write('[[place]]\nslug = "wind-river-range"\nkind = "range"\n'
                        'name = "Wind River Range"\nwhere = ["WY"]\nsource = "gmba-v2"\n'
                        'source_id = "1"\nsource_version = "2026-11-20"\n'
                        'box = [-110.0, 42.5, -108.5, 43.5]\n')
            errors = []
            C.check(d, [record()], errors)
            self.assertTrue(any("named by no record" in m for m in errors))

    def test_the_real_repository_passes(self):
        trails = []
        for tid in build_index.trail_dirs(ROOT):
            trails.append(build_index.load_toml(os.path.join(ROOT, tid, "trail.toml")))
        errors = []
        C.check(ROOT, trails, errors)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()


class PlaceLiesInTheTrailsRegionsTest(unittest.TestCase):
    def stated(self, **kw):
        return record(regions=kw.pop("regions"), places_checked="2026-11-20",
                      place=[{"kind": "range", "slug": "wind-river-range", "basis": "stated",
                              "source": "https://example.org/x"}])

    def test_a_place_in_one_of_the_trails_states_passes(self):
        errs = record_errors(self.stated(regions=["ID", "WY"]))
        self.assertEqual([e for e in errs if "lies in" in e], [])

    def test_a_place_in_none_of_the_trails_states_fails(self):
        errs = record_errors(self.stated(regions=["AZ", "NM"]))
        self.assertTrue(any("range/wind-river-range lies in WY, none of the record's regions (AZ, NM)" in e
                            for e in errs), errs)
