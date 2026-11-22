"""Tests for the written audit checklist and the monthly season check.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import os
import re
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import estimate_season as E  # noqa: E402

ROOT = E.ROOT


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def section(text, heading):
    start = text.index(f"## {heading}")
    nxt = text.find("\n## ", start + 1)
    return text[start:nxt if nxt != -1 else len(text)]


class AuditChecklistTest(unittest.TestCase):
    def test_the_audit_checklist_has_a_seasons_section_naming_both_steps(self):
        doc = read("docs", "audit.md")
        seasons = section(doc, "Seasons")
        self.assertIn("estimate_season.py check", seasons)
        self.assertIn("estimate_season.py estimates", seasons)
        self.assertIn("docs/season-research.md", seasons)
        self.assertIn("search afresh for a page that states the season", seasons.lower().replace("\n", " "))
        self.assertIn("downloads nothing", seasons)
        self.assertIn("fixed published dataset", seasons)
        self.assertIn("1. ", seasons)
        self.assertIn("2. ", seasons)

    def test_the_commands_it_names_exist(self):
        import contextlib
        import io
        import season_judge
        for module, subs in ((E, ("check", "estimates")), (season_judge, ("inputs", "packets", "score", "proposals"))):
            for sub in subs:
                out = io.StringIO()
                with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as stop:
                    module.main([sub, "--help"])
                self.assertEqual(stop.exception.code, 0, sub)
                self.assertIn(f" {sub}", out.getvalue())

    def test_every_command_in_the_audit_runs_as_written(self):
        """Each `python3 tools/<script>.py ...` the audit names must be accepted by that script's own
        argument parser: the subcommand exists and the options and required arguments are given."""
        import subprocess
        doc = read("docs", "audit.md")
        commands = re.findall(r"`((?:\.venv-places/bin/)?python3? (?:tools|web)/[^`]+)`", doc)
        self.assertGreaterEqual(len(commands), 8)
        for command in commands:
            words = [w for w in command.split() if not w.startswith("<")][1:]
            script, args = words[0], words[1:]
            if script in ("web/build.py", "tools/validate.py", "tools/place_trails.py"):
                continue   # no argument parser to ask, or one that needs its own venv
            # a placeholder trail id is replaced by a real one
            args = ["finger-lakes" if a == "<id>" else a for a in args]
            run = subprocess.run([sys.executable, os.path.join(ROOT, script), *args, "--help"],
                                 capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(run.returncode, 0, (command, run.stderr[-300:]))
        # the packets command has a required output directory
        self.assertTrue(any(c.startswith("python3 tools/season_judge.py packets --out ") for c in commands))
        self.assertFalse(any(c.endswith("season_judge.py packets") for c in commands))

    def test_the_estimates_command_prints_one_id_a_line(self):
        ids = E.estimates(ROOT)
        expected = [tid for tid, rec in E._records(ROOT)
                    if (rec.get("hike") or {}).get("season_basis") == "estimate"]
        self.assertEqual(len(ids), len(expected))
        self.assertGreater(len(ids), 0)
        self.assertEqual(ids, sorted(ids))

    def test_house_wording_in_the_audit_doc_and_workflow(self):
        dash = re.compile("[\u2013\u2014]")
        for rel in (("docs", "audit.md"), ("docs", "season-judging.md")):
            text = re.sub(r"`[^`]*`", "", read(*rel))
            self.assertIsNone(dash.search(text), rel)
            self.assertNotIn(" - ", text, rel)
        # in the workflow a dash is YAML's own, so only its comments are read
        comments = " ".join(l for l in read(".github", "workflows", "season-check.yml").splitlines()
                            if l.lstrip().startswith("#"))
        self.assertIsNone(dash.search(comments))
        self.assertNotIn(" - ", comments)


class MonthlyWorkflowTest(unittest.TestCase):
    def test_the_monthly_workflow_runs_the_check_on_a_schedule(self):
        text = read(".github", "workflows", "season-check.yml")
        for want in ("schedule", "workflow_dispatch", "estimate_season.py check", "cron:"):
            self.assertIn(want, text)
        # offline: it downloads nothing and keeps no climate cache
        self.assertNotIn("longhikes-climate", text)
        self.assertNotIn("actions/cache", text)


if __name__ == "__main__":
    unittest.main()
