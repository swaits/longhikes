import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import build  # noqa: E402


class CopyStaticTest(unittest.TestCase):
    def test_copies_tree_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            static = os.path.join(tmp, "static")
            out = os.path.join(tmp, "out")
            contents = {
                "_headers": "/*\n  X-Content-Type-Options: nosniff\n",
                os.path.join("assets", "site.css"): "body { margin: 0 }\n",
                os.path.join("assets", "sub", "app.js"): "0;\n",
            }
            for rel, text in contents.items():
                path = os.path.join(static, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
            os.makedirs(out)

            stats = build.Stats()
            build.copy_static(static, out, stats)

            self.assertEqual(stats.written, len(contents))
            for rel, text in contents.items():
                with open(os.path.join(out, rel), encoding="utf-8") as f:
                    self.assertEqual(f.read(), text)

    def test_missing_static_dir_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out")
            os.makedirs(out)
            stats = build.Stats()
            build.copy_static(os.path.join(tmp, "nonexistent"), out, stats)
            self.assertEqual(stats.written, 0)
            self.assertEqual(os.listdir(out), [])

    def test_cache_is_outside_the_publish_directory(self):
        # The cache lives beside build.py, under web/, not under _site.
        self.assertEqual(build.CACHE_DIR, os.path.join(build.HERE, ".cache"))


REAL_ROOT = build.ROOT
SMALL = ("batona", "avon", "canol")


class FakePages:
    """Stands in for olt.pages: records what render_site was given."""
    calls = []

    @classmethod
    def render_site(cls, recs, out_dir, root):
        cls.calls.append([r["id"] for r in recs])


class BuildTreeTest(unittest.TestCase):
    """Builds a few real trail directories into a throwaway tree."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = os.path.join(tmp.name, "repo")
        self.out = os.path.join(tmp.name, "site")
        os.makedirs(self.root)
        for tid in SMALL:
            shutil.copytree(os.path.join(REAL_ROOT, tid), os.path.join(self.root, tid))
        # These tests use avon as a record with no alternates file; its real one has one since the re-cut.
        alt = os.path.join(self.root, "avon", "alternates.geojson")
        if os.path.exists(alt):
            os.remove(alt)
        for name in ("trails.csv", "index.geojson"):
            shutil.copyfile(os.path.join(REAL_ROOT, name), os.path.join(self.root, name))
        FakePages.calls = []
        for p in (mock.patch.object(build, "ROOT", self.root),
                  mock.patch.object(build, "CACHE_DIR", os.path.join(tmp.name, "cache")),
                  mock.patch.object(build, "import_pages", lambda: FakePages)):
            p.start()
            self.addCleanup(p.stop)

    def build(self, *extra):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            build.main(["--out", self.out, *extra])
        return err.getvalue()

    def path(self, *parts):
        return os.path.join(self.out, *parts)

    def trails_json(self):
        with open(self.path("data", "trails.json"), encoding="utf-8") as f:
            return {r["id"]: r for r in json.load(f)}

    def overview_ids(self):
        with open(self.path("data", "overview.geojson"), encoding="utf-8") as f:
            return sorted(ft["properties"]["id"] for ft in json.load(f)["features"])

    def add_alternates(self, tid):
        with open(os.path.join(self.root, tid, "line.geojson"), encoding="utf-8") as f:
            parts = build.geo.parts_from_geojson(json.load(f))
        alt = {"type": "Feature", "properties": {},
               "geometry": {"type": "MultiLineString", "coordinates": parts[:1]}}
        with open(os.path.join(self.root, tid, "alternates.geojson"), "w", encoding="utf-8") as f:
            json.dump(alt, f)

    def map_roles(self, tid):
        with open(self.path("trails", tid, "map.json"), encoding="utf-8") as f:
            return [ft["properties"]["role"] for ft in json.load(f)["features"]]

    def test_deleted_line_file_removes_outputs_and_cache(self):
        self.add_alternates("batona")
        self.build()
        self.assertEqual(self.map_roles("batona"), ["main", "alternate"])
        self.assertIn("bbox", self.trails_json()["batona"]["derived"])
        os.remove(os.path.join(self.root, "batona", "line.geojson"))
        warnings = self.build()
        self.assertIn("batona", warnings)
        tdir = self.path("trails", "batona")
        self.assertFalse(os.path.exists(os.path.join(tdir, "batona.geojson")))
        self.assertFalse(os.path.exists(os.path.join(tdir, "batona.gpx")))
        self.assertEqual(self.map_roles("batona"), ["alternate"])
        derived = self.trails_json()["batona"]["derived"]
        self.assertNotIn("bbox", derived)
        self.assertEqual([d["role"] for d in derived["downloads"]], ["alternates"] * 2)
        self.assertNotIn("batona", self.overview_ids())

        os.remove(os.path.join(self.root, "batona", "alternates.geojson"))
        self.build()
        self.assertEqual(sorted(os.listdir(tdir)), [])
        self.assertEqual(self.trails_json()["batona"]["derived"]["downloads"], [])

    def test_pages_files_survive_cleanup(self):
        self.build()
        tdir = self.path("trails", "avon")
        for name in ("index.html", "trail.toml", "release.txt"):
            with open(os.path.join(tdir, name), "w") as f:
                f.write("x")
        os.remove(os.path.join(self.root, "avon", "line.geojson"))
        self.build()
        # The trail's own logo file, where the record has one, is copied beside its page.
        logo = [f for f in ("shield.png", "shield.svg") if os.path.exists(os.path.join(self.root, "avon", f))]
        self.assertEqual(sorted(os.listdir(tdir)), sorted(["index.html", "release.txt", "trail.toml"] + logo))

    def test_removed_trail_directory_is_pruned(self):
        self.build()
        shutil.rmtree(os.path.join(self.root, "canol"))
        self.build("--only", "avon")
        self.assertTrue(os.path.isdir(self.path("trails", "canol")))  # --only never prunes
        self.build()
        self.assertFalse(os.path.exists(self.path("trails", "canol")))
        self.assertTrue(os.path.isdir(self.path("trails", "avon")))
        self.assertNotIn("canol", self.trails_json())

    def test_only_keeps_site_wide_data_complete(self):
        self.build()
        full_ids = sorted(self.trails_json())
        overview = self.overview_ids()
        self.assertEqual(full_ids, sorted(SMALL))
        self.build("--only", "avon")
        self.assertEqual(sorted(self.trails_json()), full_ids)
        self.assertEqual(self.overview_ids(), overview)
        self.assertEqual(FakePages.calls[-1], sorted(SMALL))
        # a non-selected trail with no cache entry is built, not dropped
        shutil.rmtree(build.CACHE_DIR)
        self.build("--only", "avon")
        self.assertEqual(self.overview_ids(), overview)
        self.assertIn("bbox", self.trails_json()["batona"]["derived"])

    def test_empty_feature_collection_is_no_line(self):
        self.build()
        with open(os.path.join(self.root, "batona", "line.geojson"), "w") as f:
            json.dump({"type": "FeatureCollection", "features": []}, f)
        warnings = self.build()
        self.assertEqual(len(warnings.splitlines()), 1)
        self.assertIn("batona", warnings)
        tdir = self.path("trails", "batona")
        self.assertEqual([n for n in os.listdir(tdir) if n.endswith((".json", ".gpx", ".geojson"))], [])
        derived = self.trails_json()["batona"]["derived"]
        self.assertEqual(derived["downloads"], [])
        self.assertNotIn("batona", self.overview_ids())
        self.assertIn("avon", self.overview_ids())

    def test_collapsed_line_after_rounding_is_no_line(self):
        self.build()
        with mock.patch.object(build.geo, "round_coords", lambda parts, decimals: []):
            warnings = self.build("--force")
        self.assertIn("batona", warnings)
        self.assertFalse(os.path.exists(self.path("trails", "batona", "map.json")))

    def test_map_bbox_contains_every_written_coordinate(self):
        self.build()
        for tid in SMALL:
            with open(self.path("trails", tid, "map.json"), encoding="utf-8") as f:
                fc = json.load(f)
            w, s, e, n = fc["bbox"]
            for ft in fc["features"]:
                for part in ft["geometry"]["coordinates"]:
                    for c in part:
                        self.assertTrue(w <= c[0] <= e and s <= c[1] <= n, (tid, c, fc["bbox"]))

    def test_bbox_is_computed_from_rounded_coordinates(self):
        # 0.0000004 rounds to 0: the source box would poke past the published line.
        line = {"type": "Feature", "properties": {}, "geometry": {
            "type": "LineString", "coordinates": [[0.0000004, 0.0000004], [1.0000004, 1.0000004]]}}
        with open(os.path.join(self.root, "avon", "line.geojson"), "w") as f:
            json.dump(line, f)
        self.build()
        with open(self.path("trails", "avon", "map.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["bbox"], [0.0, 0.0, 1.0, 1.0])

    def test_unchanged_tree_is_up_to_date(self):
        self.build()
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            build.main(["--out", self.out])
        self.assertIn("trails processed 0", out.getvalue())

    def test_archives_rebuilt_only_when_an_input_is_newer(self):
        self.build()
        gpx, geojson = self.path("data", "all-gpx.zip"), self.path("data", "all-geojson.zip")
        with zipfile.ZipFile(gpx) as zf:
            names = zf.namelist()
            readme = zf.read("README.txt").decode("utf-8")
        self.assertEqual(names[0], "README.txt")
        for tid in SMALL:
            self.assertIn(f"{tid}/{tid}.gpx", names)
            self.assertIn(f"{tid}/release.txt", names)
        self.assertIn("trails.csv", names)
        self.assertIn("5 m", readme)
        with zipfile.ZipFile(geojson) as zf:
            self.assertIn("avon/avon.geojson", zf.namelist())
            self.assertIsNone(zf.testzip())
        stamps = (os.path.getmtime(gpx), os.path.getmtime(geojson))
        self.build()
        self.assertEqual((os.path.getmtime(gpx), os.path.getmtime(geojson)), stamps)
        # a trail gone from the dataset is gone from the archives, though no input is newer
        shutil.rmtree(os.path.join(self.root, "canol"))
        self.build()
        with zipfile.ZipFile(gpx) as zf:
            self.assertFalse(any(n.startswith("canol/") for n in zf.namelist()))
        stamps = (os.path.getmtime(gpx), os.path.getmtime(geojson))
        self.build()
        self.assertEqual((os.path.getmtime(gpx), os.path.getmtime(geojson)), stamps)
        # a newer input (here a release.txt) rebuilds both archives
        later = max(stamps) + 10
        os.utime(os.path.join(self.root, "avon", "release.txt"), (later, later))
        self.build()
        self.assertNotEqual(os.path.getmtime(gpx), stamps[0])
        self.assertNotEqual(os.path.getmtime(geojson), stamps[1])

    def test_missing_declared_line_warns(self):
        os.remove(os.path.join(self.root, "avon", "line.geojson"))
        warnings = self.build()
        self.assertIn("avon", warnings)
        self.assertEqual(self.trails_json()["avon"]["derived"]["downloads"], [])


if __name__ == "__main__":
    unittest.main()
