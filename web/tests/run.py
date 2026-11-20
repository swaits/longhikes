#!/usr/bin/env python3
"""Run the site's tests with the test modules in processes of their own, side by side.

    python3 web/tests/run.py [-j N] [module ...]

It runs exactly the tests `python3 -m unittest discover -s web/tests` runs (every test_*.py here),
and fails when any of them fails, any module cannot be loaded or no test runs. What it adds is time:
the site is built once, up front, into a directory it names to every module it starts
(LONGHIKES_TEST_SITE, see builtsite.py), and the modules, which share no files that they write, run
together, N at a time (the cores this process may use, at most 8, unless -j says). The tests that
read no built page start at once, while the site is being built. Python 3 standard library only.
"""
import argparse
import concurrent.futures
import glob
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import builtsite  # noqa: E402

# The slowest modules start first, so that none is left running alone at the end.
SLOW_FIRST = ("test_thumbs", "test_google_tag", "test_pages", "test_saved", "test_images", "test_short_links",
              "test_fingerprint", "test_extra", "test_structured_data", "test_views", "test_onward_order")


def cores():
    return getattr(os, "process_cpu_count", os.cpu_count)() or 1


def modules_under(only):
    names = sorted(os.path.basename(p)[:-3] for p in glob.glob(os.path.join(HERE, "test_*.py")))
    if only:
        unknown = [m for m in only if m not in names]
        if unknown:
            raise SystemExit(f"no such test module: {', '.join(unknown)}")
        names = [m for m in names if m in only]
    return sorted(names, key=lambda m: (SLOW_FIRST.index(m) if m in SLOW_FIRST else len(SLOW_FIRST), m))


def reads_the_site(module):
    with open(os.path.join(HERE, module + ".py"), encoding="utf-8") as f:
        return "builtsite" in f.read()


def build_and_scan(site):
    """Build the site, then split every page into its tags once, on all the cores (builtsite.warm)."""
    assert site == builtsite.OUT
    builtsite.build(site)
    builtsite.warm()


def run_module(module, site):
    """(module, tests run, passed, seconds, output) for one module run in a process of its own."""
    start = time.time()
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", HERE, "-p", module + ".py"],
                          capture_output=True, text=True,
                          env=dict(os.environ, LONGHIKES_TEST_SITE=site) if site else os.environ)
    ran = re.search(r"^Ran (\d+) tests? in", done.stderr, re.M)
    return module, int(ran.group(1)) if ran else 0, done.returncode == 0 and bool(ran), \
        time.time() - start, done.stderr + done.stdout


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run the site's tests, modules side by side.")
    ap.add_argument("modules", nargs="*", help="test modules to run (default: all)")
    ap.add_argument("-j", "--jobs", type=int, default=min(cores(), 8), help="modules at a time")
    args = ap.parse_args(argv)
    start = time.time()
    modules = modules_under(args.modules)
    wants_site = [m for m in modules if reads_the_site(m)]
    site = ""
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs) + 1) as pool:
        building = None
        if wants_site:
            site = os.path.join(builtsite.CACHE, f"test-site-{os.getpid()}")
            os.makedirs(builtsite.CACHE, exist_ok=True)
            building = pool.submit(build_and_scan, site)
        try:
            lanes = concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs))
            with lanes:
                waiting = [lanes.submit(run_module, m, "") for m in modules if m not in wants_site]
                if building is not None:
                    building.result()  # a failed build stops the run
                waiting += [lanes.submit(run_module, m, site) for m in modules if m in wants_site]
                for job in concurrent.futures.as_completed(waiting):
                    results.append(job.result())
                    module, ran, ok, seconds, _ = results[-1]
                    print(f"{'ok  ' if ok else 'FAIL'} {module:<32} {ran:>4} tests {seconds:6.1f} s", flush=True)
        finally:
            if site:
                shutil.rmtree(site, ignore_errors=True)
                shutil.rmtree(builtsite.SCANS, ignore_errors=True)
    failed = [r for r in results if not r[2]]
    for module, ran, ok, seconds, output in sorted(failed):
        print(f"\n{'=' * 70}\n{module}\n{output}")
    total = sum(r[1] for r in results)
    print(f"\nRan {total} tests in {len(results)} modules in {time.time() - start:.1f} s: "
          + (f"FAILED in {', '.join(sorted(r[0] for r in failed))}" if failed else "OK"))
    return 1 if failed or not total else 0


if __name__ == "__main__":
    sys.exit(main())
