"""The build's shortcuts must never change what it writes: simplifying for two tolerances at once,
the workers that build the trails side by side, and the store that keeps a trail's derived files
(web/build.py). Each is checked against doing the work the slow way."""
import ast
import contextlib
import filecmp
import io
import json
import os
import random
import shutil
import sys
import tempfile
import time
import unittest
import zipfile
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import build  # noqa: E402
from olt import geo, records  # noqa: E402

REAL_ROOT = build.ROOT


class FakePages:
    @staticmethod
    def render_site(recs, out_dir, root):
        pass


def walk(path, tol_walk=0.0004, n=3000, seed=1):
    rnd = random.Random(seed)
    lon, lat, out = -110.0, 40.0, []
    for _ in range(n):
        lon += rnd.gauss(0, tol_walk)
        lat += rnd.gauss(0.0001, tol_walk)
        out.append([round(lon, 6), round(lat, 6), round(rnd.uniform(1000, 3000), 1)])
    return out


class SimplifyTogetherTest(unittest.TestCase):
    def test_both_tolerances_in_one_walk_equal_two_walks(self):
        parts = [walk("a", seed=1), walk("b", 0.0001, 5000, 2), walk("c", 0.002, 800, 3), [[0, 0], [1, 1]]]
        for tols in ([5.0, 30.0], [30.0, 5.0], [750.0, 5.0, 30.0], [5.0, 5.0], [0.0, 1.0]):
            together = geo.simplify_multi(parts, tols)
            for tol, got in zip(tols, together):
                self.assertEqual(got, geo.simplify(parts, tol), tol)

    def test_a_real_track_gives_the_same_points(self):
        parts = geo.read_parts(os.path.join(REAL_ROOT, "batona", "line.geojson"))
        a, b = geo.simplify_multi(parts, [build.GPX_TOL_M, build.MAP_TOL_M])
        self.assertEqual(a, geo.simplify(parts, build.GPX_TOL_M))
        self.assertEqual(b, geo.simplify(parts, build.MAP_TOL_M))
        self.assertLess(geo.point_count(b), geo.point_count(a))


class CodeFilesTest(unittest.TestCase):
    def test_the_files_a_trail_is_built_from_are_closed_under_their_imports(self):
        # The store's key is made of these files: one that is missing would let a change to it
        # leave stale files in the store.
        olt = os.path.join(build.HERE, "olt")
        listed = {os.path.abspath(p) for p in build.CODE_FILES}
        for path in sorted(listed):
            if os.path.dirname(path) != olt:
                continue
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level == 1:
                    names = [node.module] if node.module else [a.name for a in node.names]
                    for name in names:
                        self.assertIn(os.path.join(olt, name + ".py"), listed,
                                      f"{os.path.basename(path)} imports olt.{name}, which the build's key does not cover")


def tree_files(root):
    found = {}
    for base, _, names in os.walk(root):
        for n in names:
            found[os.path.relpath(os.path.join(base, n), root)] = os.path.join(base, n)
    return found


def same_tree(case, a, b):
    """Every file the same, byte for byte; a zip by its members (their dates are the time they were written)."""
    fa, fb = tree_files(a), tree_files(b)
    case.assertEqual(sorted(fa), sorted(fb))
    for rel in fa:
        if rel.endswith(".zip"):
            za, zb = zipfile.ZipFile(fa[rel]), zipfile.ZipFile(fb[rel])
            case.assertEqual(za.namelist(), zb.namelist(), rel)
            for name in za.namelist():
                case.assertEqual(za.read(name), zb.read(name), f"{rel}: {name}")
        else:
            case.assertTrue(filecmp.cmp(fa[rel], fb[rel], shallow=False), rel)


class BuildShortcutsTest(unittest.TestCase):
    """A small repository of real trails: the smallest PARALLEL_FROM + 2 of them."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = os.path.join(cls.tmp.name, "repo")
        os.makedirs(cls.root)
        sizes = sorted((build.tree_size(d), d) for d in os.listdir(REAL_ROOT)
                       if os.path.isfile(os.path.join(REAL_ROOT, d, "trail.toml")))
        cls.ids = [d for _, d in sizes if "line" in records.load_record(REAL_ROOT, d)["derived"]["files"]][:build.PARALLEL_FROM + 2]
        cls.ids += [d for _, d in sizes if d not in cls.ids][:2]  # and two that may have no track
        for tid in cls.ids:
            shutil.copytree(os.path.join(REAL_ROOT, tid), os.path.join(cls.root, tid))
        for name in ("trails.csv", "index.geojson"):
            shutil.copyfile(os.path.join(REAL_ROOT, name), os.path.join(cls.root, name))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def build(self, out, cache, jobs, *extra):
        err = io.StringIO()
        patches = (mock.patch.object(build, "ROOT", self.root), mock.patch.object(build, "CACHE_DIR", cache),
                   mock.patch.object(build, "import_pages", lambda: FakePages),
                   mock.patch.dict(os.environ, {"LONGHIKES_JOBS": str(jobs)}))
        with contextlib.ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            stack.enter_context(contextlib.redirect_stderr(err))
            build.main(["--out", out, *extra])
        return err.getvalue()

    def key(self, tid):
        with mock.patch.object(build, "ROOT", self.root):
            return build.trail_key(tid)

    def dirs(self, name):
        base = os.path.join(self.tmp.name, name)
        return os.path.join(base, "site"), os.path.join(base, "cache")

    def test_workers_write_what_one_process_writes(self):
        self.assertGreaterEqual(len(self.ids), build.PARALLEL_FROM)
        (one, c1), (many, c2) = self.dirs("one"), self.dirs("many")
        w1 = self.build(one, c1, 1)
        w2 = self.build(many, c2, 4)
        same_tree(self, one, many)
        self.assertEqual(sorted(w1.splitlines()), sorted(w2.splitlines()))
        with open(os.path.join(many, "data", "trails.json"), encoding="utf-8") as f:
            self.assertEqual(sorted(r["id"] for r in json.load(f)), sorted(self.ids))

    def test_files_from_the_store_are_the_files_that_were_worked_out(self):
        (first, cache), (again, _) = self.dirs("store1"), self.dirs("store2")
        self.build(first, cache, 1)
        kept = os.path.join(cache, "store")
        self.assertTrue(os.path.isdir(kept))
        self.build(again, cache, 1, "--force")        # worked out again, nothing read from the store
        shutil.rmtree(again)
        os.remove(os.path.join(cache, self.ids[0] + ".json"))
        for name in os.listdir(cache):                 # the store alone: no per-trail cache files
            if name.endswith(".json"):
                os.remove(os.path.join(cache, name))
        self.build(again, cache, 1)                    # a new directory, filled from the store
        same_tree(self, first, again)

    def test_the_worker_count_follows_the_cores_this_process_may_use_and_the_setting(self):
        with mock.patch.dict(os.environ, {"LONGHIKES_JOBS": ""}):
            with mock.patch.object(os, "sched_getaffinity", lambda pid: {0}):
                self.assertEqual(build.job_count(), 1)
            with mock.patch.object(os, "sched_getaffinity", lambda pid: set(range(32))):
                self.assertEqual(build.job_count(), 8)
        with mock.patch.dict(os.environ, {"LONGHIKES_JOBS": "1"}):
            self.assertEqual(build.job_count(), 1)

    def test_a_worker_that_raises_fails_the_build_and_leaves_no_site(self):
        out, cache = self.dirs("raises")
        real = build.compute_trail

        def broken(rec, files, tdir, stats):
            if rec["id"] == self.ids[3]:
                raise RuntimeError("worker trouble")
            return real(rec, files, tdir, stats)

        for jobs in (1, 4):
            with self.subTest(jobs=jobs), mock.patch.object(build, "compute_trail", broken):
                with self.assertRaisesRegex(RuntimeError, "worker trouble"):
                    self.build(out, cache + str(jobs), jobs)
                self.assertFalse(os.path.exists(os.path.join(out, "index.html")))
                self.assertFalse(os.path.exists(os.path.join(out, "data", "trails.json")))

    def test_a_worker_that_dies_fails_the_build_instead_of_hanging(self):
        out, cache = self.dirs("dies")

        def dying(rec, files, tdir, stats):
            os._exit(3)

        with mock.patch.object(build, "compute_trail", dying):
            started = time.time()
            with self.assertRaises(Exception):
                self.build(out, cache, 4)
            self.assertLess(time.time() - started, 120)

    def test_a_changed_source_is_worked_out_again(self):
        out, cache = self.dirs("change")
        self.build(out, cache, 1)
        tid = next(t for t in self.ids if os.path.isfile(os.path.join(self.root, t, "line.geojson")))
        line = os.path.join(self.root, tid, "line.geojson")
        with open(line, encoding="utf-8") as f:
            original = f.read()
        with open(os.path.join(out, "trails", tid, f"{tid}.gpx"), encoding="utf-8") as f:
            gpx_before = f.read()
        key_before = self.key(tid)
        try:
            moved = [[[c[0] + 0.5, *c[1:]] for c in part] for part in geo.parts_from_geojson(json.loads(original))]
            with open(line, "w", encoding="utf-8") as f:
                json.dump({"type": "Feature", "properties": {},
                           "geometry": {"type": "MultiLineString", "coordinates": moved}}, f)
            self.assertNotEqual(self.key(tid), key_before)
            (with_store, _), (without, empty) = self.dirs("change2"), self.dirs("change3")
            self.build(with_store, cache, 1)      # the store holds the old track's files, under the old key
            self.build(without, empty, 1)         # nothing kept
            same_tree(self, with_store, without)
            with open(os.path.join(with_store, "trails", tid, f"{tid}.gpx"), encoding="utf-8") as f:
                self.assertNotEqual(f.read(), gpx_before)
        finally:
            with open(line, "w", encoding="utf-8") as f:
                f.write(original)
        self.assertEqual(self.key(tid), key_before)


    def test_a_rebuild_into_the_same_directory_follows_content_not_modification_times(self):
        out, cache = self.dirs("same")
        self.build(out, cache, 1)
        tid = next(t for t in self.ids if os.path.isfile(os.path.join(self.root, t, "line.geojson")))
        line = os.path.join(self.root, tid, "line.geojson")
        with open(line, encoding="utf-8") as f:
            original = f.read()
        stat = os.stat(line)
        try:
            moved = [[[c[0] + 0.5, *c[1:]] for c in part] for part in geo.parts_from_geojson(json.loads(original))]
            with open(line, "w", encoding="utf-8") as f:
                json.dump({"type": "Feature", "properties": {},
                           "geometry": {"type": "MultiLineString", "coordinates": moved}}, f)
            long_ago = time.mktime((2020, 1, 1, 0, 0, 0, 0, 0, -1))
            os.utime(line, (long_ago, long_ago))
            os.utime(os.path.join(self.root, tid), (long_ago, long_ago))
            self.build(out, cache, 1)                  # the same directory, the same cache
            fresh, empty = self.dirs("same-fresh")
            self.build(fresh, empty, 1)
            same_tree(self, out, fresh)
        finally:
            with open(line, "w", encoding="utf-8") as f:
                f.write(original)
            os.utime(line, ns=(stat.st_atime_ns, stat.st_mtime_ns))


if __name__ == "__main__":
    unittest.main()
