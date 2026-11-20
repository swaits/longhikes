"""The audit checklist, the monthly places workflow and the pieces that point at them."""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def text_of(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class AuditDocTest(unittest.TestCase):
    def test_every_record_must_have_places_checked_now(self):
        import sys
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import check_places
        self.assertTrue(check_places.REQUIRE_PLACES_CHECKED)

    def test_the_audit_checklist_exists_and_names_each_step(self):
        doc = text_of("docs", "audit.md")
        for needle in ("/refresh-trails", "python3 tools/refresh.py links",
                       "place_trails.py --check", "python3 tools/validate.py",
                       "python3 tools/check_history.py",
                       "python3 -m unittest discover tools/tests",
                       "python3 -m unittest discover -s web/tests",
                       "stated", "by hand"):
            self.assertIn(needle, doc)

    def test_the_monthly_workflow_runs_the_check_and_installs_only_the_tool_requirements(self):
        wf = text_of(".github", "workflows", "places.yml")
        self.assertIn("schedule", wf)
        self.assertIn("cron", wf)
        self.assertIn("tools/place_trails.requirements.txt", wf)
        self.assertIn("place_trails.py --check", wf)
        self.assertNotIn("pip install", text_of(".github", "workflows", "validate.yml"))

    def test_the_apply_brief_places_new_records(self):
        self.assertIn("place_trails.py", text_of(".claude", "skills", "refresh-trails", "briefs", "apply.md"))

    def test_the_skill_and_contributing_point_at_the_places(self):
        self.assertIn("docs/audit.md", text_of(".claude", "skills", "refresh-trails", "SKILL.md"))
        self.assertIn("place_trails.py", text_of("CONTRIBUTING.md"))

    def test_docs_audit_keeps_the_house_wording(self):
        body = re.sub(r"```.*?```", "", text_of("docs", "audit.md"), flags=re.S)
        self.assertNotIn("—", body)
        self.assertNotIn("–", body)
        self.assertIsNone(re.search(r"\S - \S", body))


if __name__ == "__main__":
    unittest.main()
