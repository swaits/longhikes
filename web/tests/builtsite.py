"""One build of the real site per test run, shared by every test that reads built pages.

Building the site is the slowest thing the suite does, and the pages and files it writes do not
change from one test to the next, so a run builds it once, into a directory of its own, and each
test module reads from there. Nothing in the suite writes into it. The directory is under
web/.cache (ignored by git), is named for the process that made it, and is removed when that
process ends, so two runs never share one and none leaves one behind. (run.py builds it for
the processes it starts and removes it itself, and says so in LONGHIKES_TEST_SITE.)

    import builtsite
    OUT = builtsite.OUT          # where the site will be; a path, nothing is built yet
    builtsite.ensure()           # builds it, the first time this is called in the process

The build is the one a person runs (web/build.py), in a process of its own: the build sets module
state in olt (the authors, the place names, the map drawings) that the tests that call olt
directly must not inherit. It uses the build's store (web/.cache/store), so a build after a change
that touches no trail's files does not work the tracks out again.
"""
import atexit
import os
import shutil
import subprocess
import sys

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(WEB, ".cache")
# A runner that has built the site already (web/tests/run.py, which runs the modules in
# processes of their own) names it here, and no process then builds or removes one.
PREBUILT = os.environ.get("LONGHIKES_TEST_SITE", "")
OUT = PREBUILT or os.path.join(CACHE, f"test-site-{os.getpid()}")
_built = bool(PREBUILT)


def build(out, *extra, env=None):
    """Run the site build into out (a directory that need not exist). Raises when it fails."""
    done = subprocess.run([sys.executable, os.path.join(WEB, "build.py"), "--out", out, *extra],
                          stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, env=env)
    if done.returncode:
        raise RuntimeError(f"the site build failed ({done.returncode}):\n{done.stderr[-2000:]}")


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _remove_left_behind():
    """Sites of runs that were killed before they could remove their own."""
    for name in os.listdir(CACHE):
        pid = name[len("test-site-"):].removesuffix(".scans")
        if name.startswith("test-site-") and pid.isdigit() and not _alive(int(pid)):
            shutil.rmtree(os.path.join(CACHE, name), ignore_errors=True)


def ensure():
    """Build the shared site if this process has not yet; returns its directory."""
    global _built
    if not _built:
        os.makedirs(CACHE, exist_ok=True)
        _remove_left_behind()
        atexit.register(shutil.rmtree, OUT, ignore_errors=True)
        build(OUT)
        atexit.register(shutil.rmtree, SCANS, ignore_errors=True)
        warm()
        _built = True
    return OUT


# Reading the pages -------------------------------------------------------------------------
# Several tests walk every built page with an html.parser handler of their own. Splitting a page
# into tags is the slow part (the whole site takes about 8 s), and it is the same for all of them,
# so it is done once per page, by all the cores together, right after the build: each page's calls
# are written beside the site (OUT + ".scans"), and a handler is then given the same calls, in the
# same order, from there.
import marshal  # noqa: E402
import multiprocessing  # noqa: E402
from html.parser import HTMLParser  # noqa: E402

SCANS = OUT + ".scans"
_CALLS = ("handle_starttag", "handle_endtag", "handle_startendtag", "handle_data",
          "handle_comment", "handle_decl", "handle_pi", "unknown_decl")
_recordings = {}


class _Recorder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.calls = []


def _recording(name):
    def record(self, *args):
        self.calls.append((name, args))
    return record


for _name in _CALLS:
    setattr(_Recorder, _name, _recording(_name))


def _record(key):
    """((size, mtime), the calls html.parser makes for the page at key)."""
    stat = os.stat(key)
    recorder = _Recorder()
    with open(key, encoding="utf-8") as f:
        recorder.feed(f.read())
    return (stat.st_size, stat.st_mtime_ns), recorder.calls


def _scan_file(key):
    rel = os.path.relpath(key, OUT)
    return os.path.join(SCANS, rel.replace(os.sep, "__") + ".bin")


def _scan_one(key):
    stamp, calls = _record(key)
    path = _scan_file(key)
    with open(path + ".tmp", "wb") as f:
        marshal.dump((stamp, calls), f)
    os.replace(path + ".tmp", path)


def warm(workers=None):
    """Record every page of the site, on all the cores; feed() reads the recordings."""
    keys = [os.path.join(base, n) for base, _, names in os.walk(OUT) for n in names if n.endswith(".html")]
    if "fork" not in multiprocessing.get_all_start_methods():
        return
    os.makedirs(SCANS, exist_ok=True)
    count = workers or min(getattr(os, "process_cpu_count", os.cpu_count)() or 1, 8)
    with multiprocessing.get_context("fork").Pool(count) as pool:
        for _ in pool.imap_unordered(_scan_one, keys, chunksize=8):
            pass


def _saved(key, stamp):
    try:
        with open(_scan_file(key), "rb") as f:
            kept_stamp, calls = marshal.load(f)
    except (OSError, ValueError, EOFError):
        return None
    return calls if kept_stamp == stamp else None


def feed(path, handler):
    """Give `handler` (an HTMLParser with convert_charrefs=True) the page at `path`, as
    handler.feed(open(path).read()) would. Returns the handler."""
    assert handler.convert_charrefs, "a recording replays what convert_charrefs=True gives"
    key = os.path.abspath(path)
    stat = os.stat(key)
    stamp = (stat.st_size, stat.st_mtime_ns)
    held = _recordings.get(key)
    if held is None or held[0] != stamp:
        calls = _saved(key, stamp) if key.startswith(OUT + os.sep) else None
        if calls is None:
            calls = _record(key)[1]
        held = _recordings[key] = (stamp, calls)
    for name, args in held[1]:
        getattr(handler, name)(*args)
    return handler
