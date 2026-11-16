"""Tests for tools/refresh.py: slices, links, collect and apply. No internet: the link tests
talk to servers on 127.0.0.1, and the rest work on a small fixture repository in a temporary
directory.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import contextlib
import csv
import http.server
import io
import os
import shutil
import sys
import tempfile
import threading
import tomllib
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import refresh as R  # noqa: E402
import trail_history as H  # noqa: E402

TODAY = "2026-12-01"


def record(tid, name, checked="2026-11-13", extra_hike="", hike=True):
    text = f'''# Long-trail record. Field meanings: docs/schema.md in this repository.

id = "{tid}"
name = "{name}"
country = "US"
regions = ["VT"]
length_km = 100
length_note = "62 mi published"
tier = "regional"
designation = "Example Club"
wave = 1

[source]
status = "osm-only"
publisher = "Example Club"
url = "https://example.org/{tid}/data"
licence = "ODbL-1.0"
source_checked = "2026-11-10"
line_file = ""

[osm]
relation = 0
note = "Not searched."
'''
    if hike:
        text += f'''
[hike]
summary = "Runs north to south. See https://example.org/{tid}/about."
official_url = "https://example.org/{tid}/"
start = "North Gap"   # as the club writes it
terrain = ["forest"]
permit = "No permit is needed."
checked = "{checked}"
{extra_hike}
[[hike.source]]
url = "https://example.org/{tid}/"
publisher = "Example Club"
facts = ["summary", "official_url", "start", "terrain", "permit"]

[[hike.source]]
url = "https://example.org/{tid}/permits"
publisher = "Example Club"
facts = ["permit"]
'''
    text += f'''
[[link]]
title = "{name}"
publisher = "Wiki"
url = "https://en.wikipedia.org/wiki/{tid}"

# History of this record, oldest first. Add to it; never rewrite it.
# See docs/schema.md, section [[history]].

[[history]]
date = "2026-11-13"
change = "The record was added: {name}."
fields = ["record"]
basis = "The record's own source entry: Example Club."
asked_by = "the dataset's own check"
outcome = "applied"
'''
    return text


LEFT_OUT = '''# Left out. Entries are sorted by name.

[[trail]]
id = "alpha-trail"
name = "Alpha Trail"
country = "US"
regions = ["PA"]
length_mi = 42.0
length_km = 68
reason = "below-floor"
note = "The holder gives it as 42 miles. See https://example.org/alpha."
source_url = "https://example.org/alpha"
decided = "2026-11-14"
was_listed = false

[[trail]]
id = "gamma-trail"
name = "Gamma Trail"
country = "US"
regions = ["PA"]
reason = "waiting"
note = "Not yet one trail."
source_url = "https://example.org/gamma"
decided = "2026-11-14"
was_listed = false
waiting_for = "It is designated."
'''


def make_repo(tmp, trails=None):
    root = os.path.join(tmp, "repo")
    os.makedirs(root)
    for tid, name, kw in trails or [("aaa", "Aaa Trail", {}), ("bbb", "Bbb Trail", {"checked": "2026-10-01"}),
                                    ("ccc", "Ccc Route", {"hike": False})]:
        os.makedirs(os.path.join(root, tid))
        with open(os.path.join(root, tid, "trail.toml"), "w", encoding="utf-8") as f:
            f.write(record(tid, name, **kw))
    with open(os.path.join(root, "left-out.toml"), "w", encoding="utf-8") as f:
        f.write(LEFT_OUT)
    return root


def main(root, *argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = R.main(["--root", root, "--today", TODAY, *argv])
    return code, out.getvalue() + err.getvalue()


def read(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = make_repo(self.tmp)
        self.d = os.path.join(self.tmp, "stage")
        os.makedirs(self.d)


class SliceTest(Tmp):
    def slice_files(self):
        sdir = os.path.join(self.d, "slices")
        return {n: [x.strip() for x in read(sdir, n).splitlines() if x.strip()]
                for n in sorted(os.listdir(sdir)) if n.endswith(".txt")}

    def test_every_id_once_and_left_out_apart(self):
        code, out = main(self.root, "--dir", self.d, "slices", "--n", "2")
        self.assertEqual(code, 0, out)
        files = self.slice_files()
        trails = sorted(i for n, ids in files.items() if n.startswith("trails") for i in ids)
        self.assertEqual(trails, ["aaa", "bbb", "ccc"])
        left = sorted(i for n, ids in files.items() if n.startswith("left-out") for i in ids)
        self.assertEqual(left, ["alpha-trail", "gamma-trail"])
        self.assertIn("trails-01.txt", files)
        self.assertIn("trails-02.txt", files)

    def test_more_slices_than_ids(self):
        main(self.root, "--dir", self.d, "slices", "--n", "9")
        self.assertEqual(len([n for n in self.slice_files() if n.startswith("trails")]), 3)

    def test_since_uses_hike_checked_then_source_checked(self):
        # today 2026-12-01: aaa checked 11-13 (18 days), bbb 10-01 (61 days),
        # ccc has no [hike] and falls back to source_checked 11-10 (21 days)
        code, out = main(self.root, "--dir", self.d, "slices", "--n", "2", "--since", "20")
        self.assertEqual(code, 0)
        ids = sorted(i for n, v in self.slice_files().items() if n.startswith("trails") for i in v)
        self.assertEqual(ids, ["bbb", "ccc"])
        self.assertIn("hike.checked", out)
        main(self.root, "--dir", self.d, "slices", "--n", "2", "--since", "90")
        ids = [i for n, v in self.slice_files().items() if n.startswith("trails") for i in v]
        self.assertEqual(ids, [])

    def test_rerun_replaces_old_slices(self):
        main(self.root, "--dir", self.d, "slices", "--n", "3")
        main(self.root, "--dir", self.d, "slices", "--n", "1")
        self.assertEqual([n for n in self.slice_files() if n.startswith("trails")], ["trails-01.txt"])

    def test_effective_check(self):
        self.assertEqual(R.effective_check({"hike": {"checked": "2026-01-02"}, "source": {"source_checked": "2026-05-05"}}),
                         ("2026-01-02", "hike.checked"))
        self.assertEqual(R.effective_check({"source": {"source_checked": "2026-05-05"}}),
                         ("2026-05-05", "source.source_checked"))
        self.assertEqual(R.effective_check({}), (None, None))

    def test_real_tree_is_covered(self):
        code, out = main(R.ROOT, "--dir", self.d, "slices", "--n", "6")
        self.assertEqual(code, 0, out)
        files = self.slice_files()
        ids = [i for n, v in files.items() if n.startswith("trails") for i in v]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), set(R.trail_ids(R.ROOT)))
        sizes = [len(v) for n, v in files.items() if n.startswith("trails")]
        self.assertEqual(len(sizes), 6)
        self.assertLessEqual(max(sizes) - min(sizes), 12)


class StagingDirTest(Tmp):
    def test_default_is_newest_and_preflight_starts_today(self):
        base = os.path.join(self.root, "refresh")
        os.makedirs(os.path.join(base, "2026-10-01"))
        os.makedirs(os.path.join(base, "2026-10-20"))
        self.assertTrue(R.staging_dir(self.root).endswith("2026-10-20"))
        self.assertTrue(R.staging_dir(self.root, today=TODAY, fresh=True, create=True).endswith(TODAY))
        self.assertTrue(os.path.isdir(os.path.join(base, TODAY)))
        self.assertTrue(R.staging_dir(self.root).endswith(TODAY))

    def test_preflight_reports_a_dirty_tree_and_an_unignored_staging_directory(self):
        import subprocess
        git = lambda *a: subprocess.run(["git", *a], cwd=self.root, capture_output=True, check=True)
        git("init", "-q")
        git("config", "user.email", "t@example.org")
        git("config", "user.name", "t")
        git("add", ".")
        git("commit", "-q", "-m", "x")
        code, out = main(self.root, "preflight", "--no-tests", "--no-validate")
        self.assertEqual(code, 1)
        self.assertIn("is not ignored by git", out)
        write(os.path.join(self.root, ".gitignore"), "/refresh/\n")
        git("add", ".")
        git("commit", "-q", "-m", "ignore")
        code, out = main(self.root, "preflight", "--no-tests", "--no-validate")
        self.assertEqual(code, 0, out)
        self.assertIn("preflight OK", out)
        write(os.path.join(self.root, "aaa", "trail.toml"), "id = 'aaa'\n")
        code, out = main(self.root, "preflight", "--no-tests", "--no-validate")
        self.assertEqual(code, 1)
        self.assertIn("not clean", out)


class AddressTest(unittest.TestCase):
    def test_urls_in_strips_punctuation(self):
        rec = {"a": "See https://example.org/x. And (https://example.org/y) and https://e.org/z_(w).",
               "b": ["http://e.org/q,"], "n": 5}
        urls = sorted(u for u, _ in R.urls_in(rec))
        self.assertEqual(urls, ["http://e.org/q", "https://e.org/z_(w)", "https://example.org/x",
                                "https://example.org/y"])

    def test_collect_addresses_reads_records_and_left_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp)
            found = R.collect_addresses(root)
            self.assertIn("https://example.org/aaa/about", found)  # inside the summary text
            self.assertIn("https://example.org/alpha", found)
            owners = {o for o, _ in found["https://example.org/alpha"]}
            self.assertEqual(owners, {"left-out:alpha-trail"})


class Handler(http.server.BaseHTTPRequestHandler):
    hits = []
    lock = threading.Lock()

    def log_message(self, *a):
        pass

    def _answer(self, head):
        with Handler.lock:
            Handler.hits.append((self.command, self.path, self.headers.get("User-Agent")))
        path = self.path
        if path == "/robots.txt":
            body = b"User-agent: *\nDisallow: /private\n"
            return self._send(200, body, head)
        if path == "/ok":
            return self._send(200, b"fine", head)
        if path == "/redir":
            self.send_response(301)
            self.send_header("Location", "/ok")
            self.end_headers()
            return
        if path == "/slash":
            self.send_response(301)
            self.send_header("Location", "/slash/")
            self.end_headers()
            return
        if path == "/slash/":
            return self._send(200, b"x", head)
        if path == "/gone":
            return self._send(404, b"no", head)
        if path == "/forbidden":
            return self._send(403, b"no", head)
        if path == "/limited":
            return self._send(429, b"slow down", head)
        if path == "/headbad":
            return self._send(405 if head else 200, b"ok", head)
        if path == "/challenge":
            return self._send(200, b"<title>Just a moment...</title>", head)
        if path == "/private":
            return self._send(200, b"secret", head)
        return self._send(200, b"other", head)

    def _send(self, code, body, head):
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def do_HEAD(self):
        self._answer(True)

    def do_GET(self):
        self._answer(False)


class LinkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        Handler.hits.clear()
        self.base = f"http://127.0.0.1:{self.port}"
        self.p = R.Prober(delay=0, timeout=5)

    def hits_for(self, path):
        return [h for h in Handler.hits if h[1] == path]

    def test_ok_uses_head_only(self):
        row = self.p.probe(self.base + "/ok")
        self.assertEqual(row["status"], 200)
        self.assertEqual(row["method"], "HEAD")
        self.assertEqual([h[0] for h in self.hits_for("/ok")], ["HEAD"])

    def test_generic_user_agent_and_no_extra_headers(self):
        self.p.probe(self.base + "/ok")
        uas = {h[2] for h in Handler.hits}
        self.assertEqual(uas, {R.USER_AGENT})
        self.assertNotIn("swaits", R.USER_AGENT.lower())
        self.assertNotIn("longhikes", R.USER_AGENT.lower())

    def test_redirect_target_recorded(self):
        row = self.p.probe(self.base + "/redir")
        self.assertEqual(row["status"], 200)
        self.assertEqual(row["final_url"], self.base + "/ok")
        self.assertEqual(R.redirect_kind(self.base + "/slash", self.base + "/slash/"), "slash")
        self.assertEqual(R.redirect_kind(self.base + "/redir", self.base + "/ok"), "path")
        self.assertEqual(R.redirect_kind("http://a.org/x", "https://a.org/x"), "scheme")
        self.assertEqual(R.redirect_kind("http://a.org/x", "http://a.org/x"), "")

    def test_head_refused_falls_back_to_get(self):
        row = self.p.probe(self.base + "/headbad")
        self.assertEqual(row["status"], 200)
        self.assertEqual([h[0] for h in self.hits_for("/headbad")], ["HEAD", "GET"])

    def test_not_found_is_an_error_not_a_refusal(self):
        row = self.p.probe(self.base + "/gone")
        self.assertEqual(row["status"], 404)
        self.assertEqual(row["refused"], "")

    def test_refusal_is_recorded_and_never_retried(self):
        row = self.p.probe(self.base + "/forbidden")
        self.assertEqual(row["status"], 403)
        self.assertEqual(row["refused"], "yes")
        self.assertEqual(len(self.hits_for("/forbidden")), 1)

    def test_429_stops_the_whole_host(self):
        row = self.p.probe(self.base + "/limited")
        self.assertEqual(row["refused"], "yes")
        after = self.p.probe(self.base + "/ok")
        self.assertEqual(after["refused"], "host")
        self.assertEqual(after["status"], "")
        self.assertEqual(self.hits_for("/ok"), [])
        self.assertEqual(len(self.hits_for("/limited")), 1)

    def test_challenge_page_counts_as_refusal(self):
        # HEAD sees 200 with no body; the GET fallback is not tried, so make HEAD uninformative
        # by calling the body check directly, as the GET path does
        self.assertTrue(R.Prober.is_challenge({}, b"<title>Just a moment...</title>"))
        self.assertTrue(R.Prober.is_challenge({"CF-Mitigated": "challenge"}, b""))
        self.assertFalse(R.Prober.is_challenge({}, b"<title>Trail</title>"))

    def test_robots_disallow_is_honoured(self):
        row = self.p.probe(self.base + "/private")
        self.assertEqual(row["refused"], "robots")
        self.assertEqual(self.hits_for("/private"), [])

    def test_robots_txt_fetched_once_per_host(self):
        self.p.probe(self.base + "/ok")
        self.p.probe(self.base + "/gone")
        self.assertEqual(len(self.hits_for("/robots.txt")), 1)

    def test_no_answer_is_an_error_row(self):
        row = R.Prober(delay=0, timeout=2).probe("http://127.0.0.1:9/nothing")
        self.assertEqual(row["status"], "")
        self.assertTrue(row["error"])

    def test_delay_between_requests_to_one_host(self):
        slow = R.Prober(delay=0.15, timeout=5)
        import time
        t0 = time.monotonic()
        slow.probe(self.base + "/ok")
        slow.probe(self.base + "/gone")
        self.assertGreaterEqual(time.monotonic() - t0, 0.3)  # robots + two probes, spaced

    def test_links_command_writes_csv_once_per_address(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, trails=[("aaa", "Aaa Trail", {})])
            path = os.path.join(root, "aaa", "trail.toml")
            text = read(root, "aaa/trail.toml").replace("https://example.org/aaa/permits", self.base + "/ok")
            text = text.replace('official_url = "https://example.org/aaa/"', f'official_url = "{self.base}/ok"')
            write(path, text)
            d = os.path.join(tmp, "stage")
            os.makedirs(d)
            code, out = main(root, "--dir", d, "links", "--delay", "0", "--timeout", "2",
                             "--only-prefix", self.base)
            self.assertEqual(code, 0, out)
            with open(os.path.join(d, "links.csv"), newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual([r["url"] for r in rows], [self.base + "/ok"])
            self.assertEqual(rows[0]["status"], "200")
            self.assertIn("aaa", rows[0]["used_by"])
            self.assertEqual(len(self.hits_for("/ok")), 1)  # used twice in the record, fetched once


# ----------------------------------------------------------------------------- collect and apply

def propose(stage, worker, tid, body, files=None):
    pdir = os.path.join(stage, "staged", worker, tid)
    os.makedirs(pdir, exist_ok=True)
    with open(os.path.join(pdir, "proposal.toml"), "w", encoding="utf-8") as f:
        f.write(body)
    for name, data in (files or {}).items():
        os.makedirs(os.path.dirname(os.path.join(pdir, name)), exist_ok=True)
        with open(os.path.join(pdir, name), "w", encoding="utf-8") as f:
            f.write(data)
    return pdir


PERMIT_CHANGE = '''
[[proposal]]
kind = "change"
id = "aaa"
date = "2026-11-30"
summary = "The permit sentence changed."

[[proposal.edit]]
field = "hike.permit"
old = "No permit is needed."
new = "A free permit is needed from the ranger district."
page = "https://example.org/aaa/permits"
quote = "Hikers need a free permit from the ranger district."

[proposal.history]
change = "The permit sentence now says a free permit is needed."
basis = "The club's permit page says a free permit is needed."
basis_url = "https://example.org/aaa/permits"
asked_by = "the dataset's own check"
'''


class CollectTest(Tmp):
    def collect(self):
        code, out = main(self.root, "--dir", self.d, "collect")
        return code, out

    def collected(self):
        return tomllib.loads(read(self.d, "collected.toml"))

    def test_empty_staging_directory(self):
        code, out = self.collect()
        self.assertEqual(code, 0, out)
        self.assertIn("0 proposals", out)
        self.assertIn("No proposals are staged", read(self.d, "summary.md"))

    def test_missing_staging_directory_is_an_error_message(self):
        code, out = main(self.root, "--dir", os.path.join(self.tmp, "nope"), "collect")
        self.assertEqual(code, 2)
        self.assertIn("preflight", out)

    def test_valid_change_is_collected_with_digest(self):
        propose(self.d, "trails-01", "aaa", PERMIT_CHANGE)
        code, out = self.collect()
        self.assertEqual(code, 0, out)
        p = self.collected()["proposal"][0]
        self.assertEqual(p["pid"], "trails-01:aaa:1")
        self.assertEqual(p["status"], "proposed")
        self.assertEqual(len(p["digest"]), 10)
        s = read(self.d, "summary.md")
        self.assertIn("hike.permit", s)
        self.assertIn("Hikers need a free permit", s)
        self.assertIn("https://example.org/aaa/permits", s)

    def test_fact_change_needs_history(self):
        body = PERMIT_CHANGE.split("[proposal.history]")[0]
        propose(self.d, "trails-01", "aaa", body)
        code, out = self.collect()
        self.assertEqual(code, 1)
        self.assertIn("needs [proposal.history]", out)

    def test_non_fact_change_needs_no_history(self):
        body = '''
[[proposal]]
kind = "change"
id = "aaa"
date = "2026-11-30"
summary = "Reword."

[[proposal.edit]]
field = "hike.summary"
old = "Runs north to south. See https://example.org/aaa/about."
new = "Runs north to south."
page = "https://example.org/aaa/"
quote = "The trail runs north to south."
'''
        propose(self.d, "trails-01", "aaa", body)
        self.assertEqual(self.collect()[0], 0)

    def test_edit_needs_page_and_quote_and_known_field(self):
        body = PERMIT_CHANGE.replace('quote = "Hikers need a free permit from the ranger district."\n', "")
        body = body.replace('field = "hike.permit"', 'field = "hike.permitt"')
        propose(self.d, "trails-01", "aaa", body)
        code, out = self.collect()
        self.assertEqual(code, 1)
        self.assertIn("quote is required", out + read(self.d, "summary.md"))
        self.assertIn("not a field of the record", read(self.d, "summary.md"))

    def test_unknown_kind_and_bad_toml(self):
        propose(self.d, "trails-01", "aaa", '[[proposal]]\nkind = "fix"\nid = "aaa"\n')
        propose(self.d, "trails-01", "bbb", "this is not toml")
        code, out = self.collect()
        self.assertEqual(code, 1)
        text = read(self.d, "summary.md")
        self.assertIn("kind must be one of", text)
        self.assertIn("does not parse", text)

    def test_report_rules(self):
        os.makedirs(os.path.join(self.d, "staged", "trails-01"))
        with open(os.path.join(self.d, "staged", "trails-01", "report.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(R.REPORT_COLUMNS)
            w.writerow(["aaa", "verified", "https://example.org/aaa/", ""])
            w.writerow(["bbb", "could-not-check", "", ""])
            w.writerow(["ccc", "bogus", "x", "y"])
        os.makedirs(os.path.join(self.d, "slices"))
        write(os.path.join(self.d, "slices", "trails-01.txt"), "aaa\nbbb\nccc\nddd\n")
        code, out = self.collect()
        self.assertEqual(code, 1)
        text = out + read(self.d, "summary.md")
        self.assertIn("needs pages", text)
        self.assertIn("needs a remark", text)
        self.assertIn("outcome 'bogus'", text)
        self.assertIn("ddd", read(self.d, "summary.md"))  # not reported
        self.assertIn("reported verified but has no `verified` proposal", read(self.d, "summary.md"))
        self.assertIn("## Could not check", read(self.d, "summary.md"))

    def test_verified_with_cited_pages_missing_is_a_warning(self):
        os.makedirs(os.path.join(self.d, "staged", "trails-01"))
        with open(os.path.join(self.d, "staged", "trails-01", "report.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(R.REPORT_COLUMNS)
            w.writerow(["aaa", "verified", "http://www.example.org/aaa", ""])
        body = ('''
[[proposal]]
kind = "verified"
id = "aaa"
date = "2026-11-30"
summary = "Nothing changed."
pages = ["https://example.org/aaa/"]
''')
        propose(self.d, "trails-01", "aaa", body)
        self.collect()
        text = read(self.d, "summary.md")
        self.assertIn("aaa: 1 of 2 cited pages are not listed as opened", text)
        self.assertIn("example.org/aaa/permits", text)

    def test_not_found_must_say_where_it_looked(self):
        os.makedirs(os.path.join(self.d, "staged", "region-x"))
        with open(os.path.join(self.d, "staged", "region-x", "report.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(R.REPORT_COLUMNS)
            w.writerow(["Idaho", "not-found", "", "nothing"])
        code, out = self.collect()
        self.assertEqual(code, 1)
        self.assertIn("needs pages", out + read(self.d, "summary.md"))

    def test_decisions_and_digest(self):
        propose(self.d, "trails-01", "aaa", PERMIT_CHANGE)
        self.collect()
        digest = self.collected()["proposal"][0]["digest"]
        os.makedirs(os.path.join(self.d, "review"))
        path = os.path.join(self.d, "review", "r1.csv")

        def write(rows):
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(("pid", "digest", "decision", "note"))
                w.writerows(rows)

        write([("trails-01:aaa:1", digest, "accept", "page says so")])
        self.collect()
        self.assertEqual(self.collected()["proposal"][0]["status"], "accepted")
        write([("trails-01:aaa:1", "deadbeef00", "accept", "")])
        self.collect()
        self.assertEqual(self.collected()["proposal"][0]["status"], "proposed")
        self.assertIn("proposal changed after review", read(self.d, "summary.md"))
        write([("trails-01:aaa:1", digest, "accept", "")])
        with open(os.path.join(self.d, "review", "r2.csv"), "w", newline="") as f:
            f.write(f"pid,digest,decision,note\ntrails-01:aaa:1,{digest},reject,quote not on page\n")
        self.collect()
        self.assertEqual(self.collected()["proposal"][0]["status"], "rejected")
        with open(os.path.join(self.d, "owner.csv"), "w", newline="") as f:
            f.write(f"pid,digest,decision,note\ntrails-01:aaa:1,{digest},accept,owner agreed\n")
        self.collect()
        self.assertEqual(self.collected()["proposal"][0]["status"], "accepted")

    def test_new_record_checks(self):
        body = '''
[[proposal]]
kind = "new-record"
id = "ddd"
date = "2026-11-30"
summary = "A new trail."
basis_url = "https://example.org/ddd/"
'''
        propose(self.d, "region-1", "ddd", body, {"trail.toml": record("ddd", "Ddd Trail")})
        self.assertEqual(self.collect()[0], 0)
        propose(self.d, "region-2", "aaa", body.replace('"ddd"', '"aaa"'), {"trail.toml": record("aaa", "Aaa")})
        code, out = self.collect()
        self.assertEqual(code, 1)
        self.assertIn("already exists in the repository", read(self.d, "summary.md"))

    def test_new_record_still_in_left_out_needs_removal(self):
        body = '''
[[proposal]]
kind = "new-record"
id = "gamma-trail"
date = "2026-11-30"
summary = "Gamma is now a trail."
basis_url = "https://example.org/gamma"
'''
        propose(self.d, "region-1", "gamma-trail", body, {"trail.toml": record("gamma-trail", "Gamma Trail")})
        self.collect()
        self.assertIn("needs a left-out-remove proposal", read(self.d, "summary.md"))

    def test_candidates_and_duplicates_are_listed(self):
        body = '''
[[proposal]]
kind = "candidate"
id = "delta-trail"
date = "2026-11-30"
name = "Delta Trail"
country = "US"
regions = ["OR"]
length_mi = 55
source_url = "https://example.org/delta"
recommendation = "owner"
borderline = true
summary = "Delta might be a network."
'''
        propose(self.d, "region-1", "delta-trail", body)
        self.assertEqual(self.collect()[0], 0)
        self.assertIn("| Delta Trail |", read(self.d, "summary.md"))


class ApplyTest(Tmp):
    def stage_and_accept(self, worker, tid, body, files=None, accept=True):
        propose(self.d, worker, tid, body, files)

    def collect_accept_all(self):
        code, out = main(self.root, "--dir", self.d, "collect")
        self.assertEqual(code, 0, out)
        coll = tomllib.loads(read(self.d, "collected.toml"))
        os.makedirs(os.path.join(self.d, "review"), exist_ok=True)
        with open(os.path.join(self.d, "review", "r.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(("pid", "digest", "decision", "note"))
            for p in coll["proposal"]:
                if p["kind"] in R.APPLIED_KINDS:
                    w.writerow((p["pid"], p["digest"], "accept", ""))
        code, out = main(self.root, "--dir", self.d, "collect")
        self.assertEqual(code, 0, out)

    def apply(self, *extra):
        return main(self.root, "--dir", self.d, "apply", *extra)

    def rec(self, tid):
        return tomllib.loads(read(self.root, f"{tid}/trail.toml"))

    def test_edit_changes_one_line_and_adds_history(self):
        before = read(self.root, "aaa/trail.toml")
        propose(self.d, "trails-01", "aaa", PERMIT_CHANGE)
        self.collect_accept_all()
        code, out = self.apply()
        self.assertEqual(code, 0, out)
        after = read(self.root, "aaa/trail.toml")
        old_lines, new_lines = before.split("\n"), after.split("\n")
        removed = [l for l in old_lines if l not in new_lines]
        self.assertEqual(removed, ['permit = "No permit is needed."'])
        added = [l for l in new_lines if l not in old_lines]
        self.assertIn('permit = "A free permit is needed from the ranger district."', added)
        self.assertEqual(new_lines.count("[[history]]"), 2)
        # hand formatting survives: comment after start, header comments
        self.assertIn('start = "North Gap"   # as the club writes it', after)
        self.assertIn("# History of this record, oldest first.", after)
        rec = self.rec("aaa")
        self.assertEqual(rec["hike"]["permit"], "A free permit is needed from the ranger district.")
        entry = rec["history"][-1]
        self.assertEqual(entry["date"], TODAY)
        self.assertEqual(entry["fields"], ["hike.permit"])
        self.assertEqual(entry["outcome"], "applied")
        self.assertEqual(entry["asked_by"], "the dataset's own check")
        errors = []
        H.check_entries("aaa", rec, errors)
        self.assertEqual(errors, [])

    def test_only_accepted_proposals_apply(self):
        propose(self.d, "trails-01", "aaa", PERMIT_CHANGE)
        main(self.root, "--dir", self.d, "collect")
        before = read(self.root, "aaa/trail.toml")
        code, out = self.apply()
        self.assertEqual(code, 0)
        self.assertEqual(read(self.root, "aaa/trail.toml"), before)

    def test_refuses_when_old_value_no_longer_matches(self):
        propose(self.d, "trails-01", "aaa", PERMIT_CHANGE)
        self.collect_accept_all()
        path = os.path.join(self.root, "aaa", "trail.toml")
        text = read(self.root, "aaa/trail.toml").replace("No permit is needed.", "Permits are free.")
        write(path, text)
        code, out = self.apply()
        self.assertEqual(code, 1)
        self.assertIn("not the proposal's old value", out)
        self.assertEqual(read(self.root, "aaa/trail.toml"), text)
        self.assertIn("refused", read(self.d, "apply-log.csv"))

    def test_second_run_says_already_applied(self):
        propose(self.d, "trails-01", "aaa", PERMIT_CHANGE)
        self.collect_accept_all()
        self.apply()
        once = read(self.root, "aaa/trail.toml")
        code, out = self.apply()
        self.assertEqual(code, 0, out)
        self.assertIn("already applied", out)
        self.assertEqual(read(self.root, "aaa/trail.toml"), once)

    def test_refuses_when_proposal_changed_after_collect(self):
        propose(self.d, "trails-01", "aaa", PERMIT_CHANGE)
        self.collect_accept_all()
        propose(self.d, "trails-01", "aaa", PERMIT_CHANGE.replace("A free permit", "A paid permit"))
        before = read(self.root, "aaa/trail.toml")
        code, out = self.apply()
        self.assertEqual(code, 1)
        self.assertIn("changed after it was collected", out)
        self.assertEqual(read(self.root, "aaa/trail.toml"), before)

    def test_dry_run_writes_nothing(self):
        propose(self.d, "trails-01", "aaa", PERMIT_CHANGE)
        self.collect_accept_all()
        before = read(self.root, "aaa/trail.toml")
        code, out = self.apply("--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("would apply", out)
        self.assertEqual(read(self.root, "aaa/trail.toml"), before)

    def test_add_remove_and_array_edits(self):
        body = '''
[[proposal]]
kind = "change"
id = "aaa"
date = "2026-11-30"
summary = "Add a caution, drop the permit, change a source, add a source and a link."

[[proposal.edit]]
field = "hike.caution"
new = "Most of the trail has no water."
page = "https://example.org/aaa/"
quote = "There is no water on most of the trail."

[[proposal.edit]]
field = "hike.permit"
old = "No permit is needed."
page = "https://example.org/aaa/permits"
quote = "The page no longer mentions a permit."

[[proposal.edit]]
field = "hike.source[1].facts"
old = ["permit"]
new = ["permit", "caution"]
page = "https://example.org/aaa/permits"
quote = "x"

[[proposal.edit]]
field = "length_km"
old = 100
new = 105
page = "https://example.org/aaa/"
quote = "65 miles"

[[proposal.append]]
table = "hike.source"
page = "https://example.org/aaa/water"
quote = "There is no water on most of the trail."
[proposal.append.entry]
url = "https://example.org/aaa/water"
publisher = "Example Club"
facts = ["caution"]

[[proposal.append]]
table = "link"
page = "https://example.org/aaa/more"
quote = "More about the trail"
[proposal.append.entry]
title = "More"
publisher = "Another Club"
url = "https://example.org/aaa/more"

[proposal.history]
change = "The caution was added, the permit sentence removed and the length changed."
basis = "The club's pages say so."
basis_url = "https://example.org/aaa/"
asked_by = "a hiker"
'''
        propose(self.d, "trails-01", "aaa", body)
        self.collect_accept_all()
        code, out = self.apply()
        self.assertEqual(code, 0, out)
        rec = self.rec("aaa")
        self.assertEqual(rec["hike"]["caution"], "Most of the trail has no water.")
        self.assertNotIn("permit", rec["hike"])
        self.assertEqual(rec["hike"]["source"][1]["facts"], ["permit", "caution"])
        self.assertEqual(rec["length_km"], 105)
        self.assertEqual([s["url"] for s in rec["hike"]["source"]][-1], "https://example.org/aaa/water")
        self.assertEqual([x["url"] for x in rec["link"]][-1], "https://example.org/aaa/more")
        self.assertEqual(len(rec["history"]), 2)
        self.assertEqual(rec["history"][-1]["fields"],
                         ["hike.caution", "hike.permit", "hike.source.facts", "length_km",
                          "hike.source", "link"])
        text = read(self.root, "aaa/trail.toml")
        # the new link block sits after the old one and before the history comment
        self.assertLess(text.index("https://en.wikipedia.org/wiki/aaa"), text.index("https://example.org/aaa/more"))
        self.assertLess(text.index("https://example.org/aaa/more"), text.index("# History of this record"))
        self.assertLess(text.index("https://example.org/aaa/permits"), text.index("https://example.org/aaa/water"))

    def test_edit_in_a_record_without_the_table_is_refused(self):
        body = PERMIT_CHANGE.replace('id = "aaa"', 'id = "ccc"')
        propose(self.d, "trails-01", "ccc", body)
        self.collect_accept_all()
        code, out = self.apply()
        self.assertEqual(code, 1)
        self.assertIn("ccc", out)

    def test_verified_sets_checked_date(self):
        body = '''
[[proposal]]
kind = "verified"
id = "aaa"
date = "2026-11-30"
summary = "Nothing changed."
pages = ["https://example.org/aaa/", "https://example.org/aaa/permits"]

[[proposal]]
kind = "verified"
id = "ccc"
date = "2026-11-30"
summary = "Nothing changed."
pages = ["https://example.org/ccc/data"]
'''
        propose(self.d, "trails-01", "aaa", body.split("[[proposal]]")[1].join(["[[proposal]]", ""]))
        propose(self.d, "trails-01", "ccc", "[[proposal]]" + body.split("[[proposal]]")[2])
        self.collect_accept_all()
        code, out = self.apply()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.rec("aaa")["hike"]["checked"], "2026-11-30")
        self.assertEqual(len(self.rec("aaa")["history"]), 1)  # not a fact: no history entry
        self.assertEqual(self.rec("ccc")["source"]["source_checked"], "2026-11-30")

    def test_declined_adds_only_a_history_entry(self):
        body = '''
[[proposal]]
kind = "declined"
id = "aaa"
date = "2026-11-30"
summary = "A request to change the length lost to the holder's page."

[proposal.history]
change = "A request for 70 miles was not applied."
basis = "The club's own page gives 62 miles."
basis_url = "https://example.org/aaa/"
asked_by = "a hiker"
fields = ["length_km", "length_note"]
'''
        propose(self.d, "trails-01", "aaa", body)
        self.collect_accept_all()
        before = read(self.root, "aaa/trail.toml")
        code, out = self.apply()
        self.assertEqual(code, 0, out)
        after = read(self.root, "aaa/trail.toml")
        self.assertTrue(after.startswith(before.rstrip("\n")))
        self.assertEqual(self.rec("aaa")["history"][-1]["outcome"], "declined")

    def test_left_out_add_keeps_order_remove_and_change(self):
        add = '''
[[proposal]]
kind = "left-out-add"
id = "beta-trail"
date = "2026-11-30"
summary = "Beta is below the floor."
basis_url = "https://example.org/beta"

[proposal.entry]
id = "beta-trail"
name = "Beta Trail"
country = "US"
regions = ["NY"]
reason = "below-floor"
note = "It is 30 miles."
decided = "2026-11-30"
was_listed = false
'''
        change = '''
[[proposal]]
kind = "change"
target = "left-out"
id = "gamma-trail"
date = "2026-11-30"
summary = "Gamma still waits."

[[proposal.edit]]
field = "note"
old = "Not yet one trail."
new = "Still not one trail."
page = "https://example.org/gamma"
quote = "x"
'''
        remove = '''
[[proposal]]
kind = "left-out-remove"
id = "alpha-trail"
date = "2026-11-30"
summary = "Alpha is now a record."
why = "It is listed."
basis_url = "https://example.org/alpha"
'''
        propose(self.d, "left-out-01", "beta-trail", add)
        propose(self.d, "left-out-01", "gamma-trail", change)
        propose(self.d, "left-out-01", "alpha-trail", remove)
        self.collect_accept_all()
        code, out = self.apply()
        self.assertEqual(code, 0, out)
        doc = tomllib.loads(read(self.root, "left-out.toml"))
        self.assertEqual([e["id"] for e in doc["trail"]], ["beta-trail", "gamma-trail"])
        self.assertEqual(doc["trail"][1]["note"], "Still not one trail.")
        text = read(self.root, "left-out.toml")
        self.assertTrue(text.startswith("# Left out. Entries are sorted by name."))
        self.assertNotIn("\n\n\n", text)

    def test_left_out_add_in_the_middle_and_at_the_end(self):
        def add(tid, name):
            return f'''
[[proposal]]
kind = "left-out-add"
id = "{tid}"
date = "2026-11-30"
summary = "x"
basis_url = "https://example.org/x"

[proposal.entry]
id = "{tid}"
name = "{name}"
country = "US"
regions = ["NY"]
reason = "below-floor"
note = "It is 30 miles."
decided = "2026-11-30"
was_listed = false
'''
        propose(self.d, "left-out-01", "beta-trail", add("beta-trail", "Beta Trail"))
        propose(self.d, "left-out-01", "zeta-trail", add("zeta-trail", "Zeta Trail"))
        propose(self.d, "left-out-01", "a-first", add("a-first", "A First Trail"))
        self.collect_accept_all()
        code, out = self.apply()
        self.assertEqual(code, 0, out)
        ids = [e["id"] for e in tomllib.loads(read(self.root, "left-out.toml"))["trail"]]
        self.assertEqual(ids, ["a-first", "alpha-trail", "beta-trail", "gamma-trail", "zeta-trail"])

    def test_new_record_is_copied_without_the_proposal_file(self):
        body = '''
[[proposal]]
kind = "new-record"
id = "ddd"
date = "2026-11-30"
summary = "A new trail."
basis_url = "https://example.org/ddd/"
'''
        propose(self.d, "region-1", "ddd", body, {"trail.toml": record("ddd", "Ddd Trail"), "shield.png": "png"})
        self.collect_accept_all()
        code, out = self.apply()
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(os.listdir(os.path.join(self.root, "ddd"))), ["shield.png", "trail.toml"])
        code, out = self.apply()  # the directory now exists
        self.assertEqual(code, 1)
        self.assertIn("already exists", out)

    def test_file_operations_need_matching_hash(self):
        import hashlib
        os.makedirs(os.path.join(self.root, "aaa"), exist_ok=True)
        with open(os.path.join(self.root, "aaa", "shield.png"), "w") as f:
            f.write("old logo")
        good = hashlib.sha256(b"old logo").hexdigest()
        body = f'''
[[proposal]]
kind = "change"
id = "aaa"
date = "2026-11-30"
summary = "A better logo."

[[proposal.file]]
to = "shield.png"
from = "files/shield.png"
old_sha256 = "{good}"
source_url = "https://example.org/aaa/logo"

[proposal.history]
change = "The logo was replaced."
basis = "The club's page shows this emblem."
basis_url = "https://example.org/aaa/logo"
asked_by = "the dataset's own check"
'''
        propose(self.d, "emblems-1", "aaa", body, {"files/shield.png": "new logo"})
        self.collect_accept_all()
        code, out = self.apply()
        self.assertEqual(code, 0, out)
        self.assertEqual(read(self.root, "aaa/shield.png"), "new logo")
        self.assertEqual(self.rec("aaa")["history"][-1]["fields"], ["shield.logo_file"])
        # a second proposal against the same old hash is now stale
        stale = body.replace("A better logo.", "Another logo.")
        propose(self.d, "emblems-2", "aaa", stale, {"files/shield.png": "third"})
        self.collect_accept_all()
        code, out = self.apply("--only", "emblems-2:aaa:1")
        self.assertEqual(code, 1)
        self.assertIn("sha256 differs", out)
        self.assertEqual(read(self.root, "aaa/shield.png"), "new logo")

    def test_target_file_name_is_limited(self):
        body = '''
[[proposal]]
kind = "change"
id = "aaa"
date = "2026-11-30"
summary = "Bad."

[[proposal.file]]
to = "../escape.txt"
from = "x.png"
source_url = "https://example.org/"

[proposal.history]
change = "x"
basis = "x"
basis_url = "https://example.org/"
asked_by = "a hiker"
'''
        propose(self.d, "emblems-1", "aaa", body, {"x.png": "x"})
        code, out = main(self.root, "--dir", self.d, "collect")
        self.assertEqual(code, 1)
        self.assertIn("to must be", read(self.d, "summary.md"))


class DocTest(unittest.TestCase):
    def test_comment_after_value_is_kept(self):
        d = R.Doc('[hike]\nstart = "A # B"   # note\nend = "C"\n')
        span = d.span("hike")
        d.set_value(span, "start", "D", "A # B", True)
        self.assertEqual(d.text(), '[hike]\nstart = "D" # note\nend = "C"\n')

    def test_new_key_goes_after_last_key_of_its_table(self):
        d = R.Doc('[hike]\nstart = "A"\n\n# a comment\n[other]\nx = 1\n')
        d.set_value(d.span("hike"), "end", "B", None, False)
        self.assertEqual(d.text(), '[hike]\nstart = "A"\nend = "B"\n\n# a comment\n[other]\nx = 1\n')

    def test_multiline_value_is_refused(self):
        d = R.Doc('[hike]\nterrain = [\n  "a",\n]\n')
        with self.assertRaises(R.RefreshError):
            d.set_value(d.span("hike"), "terrain", ["b"], ["a"], True)

    def test_dump_toml_round_trip(self):
        doc = {"a": 1, "s": 'q"uote\nnew', "l": ["x", "y"], "t": {"k": True},
               "arr": [{"n": 1, "sub": {"z": 2.5}}, {"n": 2}]}
        self.assertEqual(tomllib.loads(R.dump_toml(doc)), doc)

    def test_scalar_non_ascii_is_kept(self):
        self.assertEqual(R._scalar("Dän"), '"Dän"')


if __name__ == "__main__":
    unittest.main()
