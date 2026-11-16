"""Tests for [[history]]: the validator's checks and tools/check_history.py.

No network. The check runs against small git repositories made in a temporary directory.
Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)

import build_index  # noqa: E402
import check_history as C  # noqa: E402
import trail_history as H  # noqa: E402

OWN = H.OWN_CHECK


def entry(date="2026-11-10", change="Changed it.", fields=("length_km",), basis="A page said so.",
          url="https://example.org/page", who=OWN, outcome="applied"):
    lines = ["[[history]]", f'date = "{date}"', f'change = "{change}"',
             "fields = [" + ", ".join(f'"{f}"' for f in fields) + "]", f'basis = "{basis}"']
    if url:
        lines.append(f'basis_url = "{url}"')
    lines += [f'asked_by = "{who}"', f'outcome = "{outcome}"']
    return "\n".join(lines) + "\n"


ADDED = entry("2026-11-01", "The record was added.", ("record",), "The record's own source entry.", None)


def record(length=100, summary="A trail.", measured=99.0, extra="", history=ADDED, line_file=""):
    return f'''id = "t"
name = "Test Trail"
length_km = {length}

[source]
line_file = "{line_file}"

[verification]
measured_km = {measured}

[hike]
summary = "{summary}"
caution = "Water is scarce."

{extra}
{history}'''


class Repo:
    """A scratch git repository with one trail, `t`, committed as the base."""

    def __init__(self, test, text):
        self.dir = tempfile.TemporaryDirectory()
        test.addCleanup(self.dir.cleanup)
        self.root = self.dir.name
        self.git("init", "-q")
        os.makedirs(os.path.join(self.root, "t"))
        self.write(text)
        self.git("add", "-A")
        self.commit("base")
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        done = subprocess.run(["git", "-C", self.root, "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                               *args], capture_output=True, text=True, check=True)
        return done.stdout

    def commit(self, message):
        self.git("commit", "-q", "-m", message)

    def write(self, text, name="trail.toml", tid="t"):
        os.makedirs(os.path.join(self.root, tid), exist_ok=True)
        with open(os.path.join(self.root, tid, name), "w", encoding="utf-8") as f:
            f.write(text)

    def run(self, **kwargs):
        lines = []
        status = C.run(self.root, self.base, out=lines.append, **kwargs)
        return status, "\n".join(lines)


class ClassifyTest(unittest.TestCase):
    def test_facts_and_not_facts(self):
        for path in ("name", "length_km", "length_note", "kind", "source.licence", "source.line_file",
                     "source.publisher_url", "route.creator", "route.line_policy", "hike.start", "hike.caution",
                     "hike.official_url", "shield.logo_file", "shield.logo_owner", "short_name_url", "guide.url",
                     "osm.relation", "a_field_added_later"):
            self.assertTrue(H.is_fact(path), path)
        for path in ("history", "history.outcome", "verification.measured_km", "verification.date",
                     "source.source_checked", "hike.summary", "hike.checked", "hike.source.url", "guide.price",
                     "link.url", "shield.note", "osm.note", "wave"):
            self.assertFalse(H.is_fact(path), path)

    def test_every_schema_field_is_classified_somewhere(self):
        self.assertIn("source.licence", H.SCHEMA_FIELDS)
        self.assertNotIn("history", H.SCHEMA_FIELDS)
        self.assertNotIn("record", H.SCHEMA_FIELDS)

    def test_changed_paths_handles_tables_and_lists(self):
        old = {"name": "A", "regions": ["VT"], "guide": [{"title": "x", "url": "u"}], "history": [{"date": "1"}]}
        new = {"name": "A", "regions": ["VT", "NH"], "guide": [{"title": "x", "url": "u"}, {"title": "y", "url": "v"}],
               "history": [{"date": "1"}, {"date": "2"}], "route": {"creator": "C"}}
        self.assertEqual(H.changed_paths(old, new), ["guide.title", "guide.url", "regions", "route.creator"])

    def test_an_entry_covers_its_field_and_what_is_under_a_table(self):
        e = {"fields": ["source"]}
        self.assertTrue(H.entry_covers(e, "source.licence"))
        self.assertFalse(H.entry_covers({"fields": ["source.licence"]}, "source.licence_text"))
        self.assertFalse(H.entry_covers({"fields": ["record"]}, "name"))


class EntryShapeTest(unittest.TestCase):
    def check(self, history, **kw):
        errors = []
        rec = {"history": history} if history is not None else {}
        H.check_entries("t", rec, errors)
        return errors

    def good(self, **kw):
        e = {"date": "2026-11-01", "change": "Added.", "fields": ["record"], "basis": "Source.",
             "asked_by": OWN, "outcome": "applied"}
        e.update(kw)
        return e

    def second(self, **kw):
        e = {"date": "2026-11-02", "change": "Changed.", "fields": ["length_km"], "basis": "A page.",
             "basis_url": "https://example.org/", "asked_by": "a hiker", "outcome": "declined"}
        e.update(kw)
        return e

    def test_good(self):
        self.assertEqual(self.check([self.good(), self.second()]), [])

    def test_the_added_entry_may_leave_out_the_address(self):
        self.assertEqual(self.check([self.good()]), [])
        second = self.second()
        del second["basis_url"]
        self.assertTrue(any("missing basis_url" in e for e in self.check([self.good(), second])))

    def test_no_history_is_an_error(self):
        self.assertTrue(any("no [[history]]" in e for e in self.check(None)))
        self.assertTrue(any("no [[history]]" in e for e in self.check([])))

    def test_missing_and_unknown_fields(self):
        e = self.good()
        del e["asked_by"]
        e["extra"] = 1
        errors = self.check([e])
        self.assertTrue(any("missing asked_by" in x for x in errors))
        self.assertTrue(any("unknown field extra" in x for x in errors))

    def test_outcome(self):
        errors = self.check([self.good(), self.second(outcome="maybe")])
        self.assertTrue(any("outcome must be one of applied, declined" in x for x in errors))

    def test_dates(self):
        self.assertTrue(any("YYYY-MM-DD" in x for x in self.check([self.good(date="11/01/2026")])))
        self.assertTrue(any("not a real date" in x for x in self.check([self.good(date="2026-02-30")])))
        errors = self.check([self.good(date="2026-11-05"), self.second(date="2026-11-02")])
        self.assertTrue(any("earlier than the entry before" in x for x in errors))
        self.assertEqual(self.check([self.good(date="2026-11-02"), self.second(date="2026-11-02")]), [])

    def test_fields(self):
        self.assertTrue(any("non-empty list" in x for x in self.check([self.good(fields=[])])))
        errors = self.check([self.good(), self.second(fields=["lenght_km"])])
        self.assertTrue(any("not a field of the record" in x for x in errors))
        self.assertTrue(any("not a field of the record" in x for x in self.check([self.good(), self.second(fields=["history"])])))
        self.assertEqual(self.check([self.good(), self.second(fields=["source", "hike.source", "guide.price"])]), [])

    def test_record_entry_comes_first_and_alone(self):
        self.assertTrue(any("first entry must be" in x for x in self.check([self.second()])))
        self.assertTrue(any("only the first entry" in x for x in self.check([self.good(), self.good(date="2026-11-03")])))
        self.assertTrue(any("cannot be listed with other" in x for x in self.check([self.good(fields=["record", "name"])])))

    def test_basis_url_is_an_address(self):
        self.assertTrue(any("http(s) address" in x for x in self.check([self.good(), self.second(basis_url="page")])))

    def test_real_records_all_have_valid_history(self):
        root = os.path.dirname(TOOLS)
        errors = []
        for tid in build_index.trail_dirs(root):
            H.check_entries(tid, build_index.load_toml(os.path.join(root, tid, "trail.toml")), errors)
        self.assertEqual(errors, [])


class CheckTest(unittest.TestCase):
    def test_a_fact_changed_with_no_entry_fails_and_names_record_and_field(self):
        repo = Repo(self, record())
        repo.write(record(length=120))
        status, out = repo.run()
        self.assertEqual(status, 1)
        self.assertIn("FAIL  t: facts changed and no new history entry was added. Changed: length_km.", out)

    def test_a_fact_changed_with_its_entry_passes(self):
        repo = Repo(self, record())
        repo.write(record(length=120, history=ADDED + "\n" + entry("2026-11-12", fields=("length_km",))))
        status, out = repo.run()
        self.assertEqual(status, 0, out)
        self.assertIn("OK history", out)

    def test_an_entry_for_another_field_does_not_cover(self):
        repo = Repo(self, record())
        repo.write(record(length=120, history=ADDED + "\n" + entry("2026-11-12", fields=("name",))))
        status, out = repo.run()
        self.assertEqual(status, 1)
        self.assertIn('no new history entry with outcome "applied" names length_km', out)

    def test_a_declined_entry_does_not_cover_a_change(self):
        repo = Repo(self, record())
        repo.write(record(length=120, history=ADDED + "\n" + entry("2026-11-12", outcome="declined")))
        self.assertEqual(repo.run()[0], 1)

    def test_a_declined_entry_alone_is_fine(self):
        repo = Repo(self, record())
        repo.write(record(history=ADDED + "\n" + entry("2026-11-12", outcome="declined", who="a hiker")))
        status, out = repo.run()
        self.assertEqual(status, 0, out)

    def test_not_facts_need_no_entry(self):
        repo = Repo(self, record())
        repo.write(record(summary="A different sentence.", measured=95.5))
        status, out = repo.run()
        self.assertEqual(status, 0, out)
        self.assertIn("not facts", out)
        self.assertIn("hike.summary", out)

    def test_a_hiker_fact_needs_an_entry(self):
        repo = Repo(self, record())
        repo.write(record().replace("Water is scarce.", "Water is scarce in August."))
        status, out = repo.run()
        self.assertEqual(status, 1)
        self.assertIn("Changed: hike.caution", out)

    def test_a_changed_track_file_counts_as_a_change_to_source_line_file(self):
        repo = Repo(self, record(line_file="line.geojson"))
        repo.write("{}", "line.geojson")
        repo.git("add", "-A")
        repo.commit("track")
        repo.base = repo.git("rev-parse", "HEAD").strip()
        repo.write('{"type":"FeatureCollection"}', "line.geojson")
        status, out = repo.run()
        self.assertEqual(status, 1)
        self.assertIn("Changed: source.line_file", out)
        repo.write(record(line_file="line.geojson", history=ADDED + "\n" + entry(
            "2026-11-12", fields=("source.line_file",), change="A newer track.")))
        self.assertEqual(repo.run()[0], 0)

    def test_earlier_entry_for_the_same_field_is_printed(self):
        past = ADDED + "\n" + entry("2026-11-05", change="Changed the length.", basis="The holder's page says 100 km.",
                                    url="https://holder.example/trail")
        repo = Repo(self, record(history=past))
        repo.write(record(length=120, history=past + "\n" + entry("2026-11-12")))
        status, out = repo.run()
        self.assertEqual(status, 0, out)
        self.assertIn("length_km of t was last changed on 2026-11-05 at the request of the dataset's own check, "
                      "because The holder's page says 100 km (https://holder.example/trail); outcome applied.", out)
        self.assertNotIn("!!", out)

    def test_an_earlier_request_by_someone_else_is_printed_loudly(self):
        past = ADDED + "\n" + entry("2026-11-05", who="the trail association's president")
        repo = Repo(self, record(history=past))
        repo.write(record(length=120, history=past + "\n" + entry("2026-11-12")))
        status, out = repo.run()
        self.assertEqual(status, 0, out)
        loud = [line for line in out.split("\n") if line.startswith("!!")]
        self.assertEqual(len(loud), 1, out)
        self.assertIn("the trail association's president", loud[0])
        self.assertIn("NOT the dataset's own check", loud[0])

    def test_an_earlier_declined_request_is_printed_loudly(self):
        past = ADDED + "\n" + entry("2026-11-05", who="a hiker", outcome="declined",
                                    basis="The holder's page says 100 km.")
        repo = Repo(self, record(history=past))
        repo.write(record(length=120, history=past + "\n" + entry("2026-11-12")))
        status, out = repo.run()
        self.assertEqual(status, 0, out)
        loud = [line for line in out.split("\n") if line.startswith("!!")]
        self.assertEqual(len(loud), 1, out)
        self.assertIn("DECLINED", loud[0])
        self.assertIn("A request to change length_km on 2026-11-05 at the request of a hiker", loud[0])

    def test_earlier_entries_about_other_fields_are_not_printed(self):
        past = ADDED + "\n" + entry("2026-11-05", fields=("name",), who="a hiker", outcome="declined")
        repo = Repo(self, record(history=past))
        repo.write(record(length=120, history=past + "\n" + entry("2026-11-12")))
        status, out = repo.run()
        self.assertEqual(status, 0, out)
        self.assertNotIn("!!", out)
        self.assertNotIn("a hiker", out)

    def test_github_annotations(self):
        past = ADDED + "\n" + entry("2026-11-05", who="a hiker", outcome="declined")
        repo = Repo(self, record(history=past))
        repo.write(record(length=120))
        os.environ["GITHUB_ACTIONS"] = "true"
        self.addCleanup(os.environ.pop, "GITHUB_ACTIONS", None)
        status, out = repo.run()
        self.assertEqual(status, 1)
        self.assertIn("::error file=t/trail.toml::", out)
        self.assertIn("::warning file=t/trail.toml::", out)

    def test_earlier_entries_cannot_be_rewritten(self):
        past = ADDED + "\n" + entry("2026-11-05")
        repo = Repo(self, record(history=past))
        repo.write(record(history=ADDED + "\n" + entry("2026-11-05", basis="Another reason.")))
        status, out = repo.run()
        self.assertEqual(status, 1)
        self.assertIn("earlier history entries were changed or removed", out)
        self.assertEqual(repo.run(allow_edits=True)[0], 0)

    def test_a_new_record_needs_its_added_entry(self):
        repo = Repo(self, record())
        repo.write(record(history=entry("2026-11-12")).replace('id = "t"', 'id = "u"'), tid="u")
        status, out = repo.run()
        self.assertEqual(status, 1)
        self.assertIn('a new record needs a history entry with fields = ["record"]', out)
        repo.write(record(history=ADDED).replace('id = "t"', 'id = "u"'), tid="u")
        status, out = repo.run()
        self.assertEqual(status, 0, out)
        self.assertIn("new record", out)

    def test_an_entry_naming_a_field_that_did_not_change_is_noted(self):
        repo = Repo(self, record())
        repo.write(record(history=ADDED + "\n" + entry("2026-11-12", fields=("name",))))
        status, out = repo.run()
        self.assertEqual(status, 0, out)
        self.assertIn("says name changed, but it did not change here", out)

    def test_only_changed_records_are_looked_at(self):
        repo = Repo(self, record())
        repo.write(record(length=999, history=""), tid="u")  # untracked, a new record without history
        repo.git("add", "-A")
        repo.commit("u")
        repo.base = repo.git("rev-parse", "HEAD").strip()
        status, out = repo.run()
        self.assertEqual(status, 0, out)
        self.assertIn("0 changed records", out)

    def test_work_is_compared_with_the_merge_base(self):
        repo = Repo(self, record())
        repo.git("checkout", "-q", "-b", "other")
        repo.write(record(length=120, history=ADDED + "\n" + entry("2026-11-12")))
        repo.git("add", "-A")
        repo.commit("someone else's change")
        repo.git("checkout", "-q", "-")
        repo.base = "other"  # the work here leaves the record as it was
        status, out = repo.run()
        self.assertEqual(status, 0, out)
        self.assertIn("0 changed records", out)

    def test_a_base_that_cannot_be_read_says_so(self):
        repo = Repo(self, record())
        repo.base = "no-such-revision"
        with self.assertRaises(C.BaseError):
            repo.run()
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            self.assertEqual(C.main(["--facts"]), 0)
        self.assertIn("length_km", printed.getvalue())

    def test_an_all_zero_base_falls_back_to_the_default(self):
        repo = Repo(self, record())
        repo.git("branch", "-m", "main")
        repo.base = "0" * 40
        status, out = repo.run()
        self.assertEqual(status, 0, out)


if __name__ == "__main__":
    unittest.main()
