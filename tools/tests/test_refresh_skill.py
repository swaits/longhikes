"""Tests that the refresh runbook is whole: the skill's frontmatter parses, every file it
points to exists, the briefs point at the shared rules, the examples in the proposal format
are valid proposals, the commands it names exist, and the text keeps the house wording.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import os
import re
import sys
import tomllib
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import refresh as R  # noqa: E402

SKILL_DIR = os.path.join(R.ROOT, ".claude", "skills", "refresh-trails")
BRIEFS = ("verify-records", "recheck-left-out", "find-missing-trails", "find-routes", "tracks",
          "emblems", "review", "apply")


def text_of(*parts):
    with open(os.path.join(SKILL_DIR, *parts), encoding="utf-8") as f:
        return f.read()


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "no frontmatter"
    out = {}
    for line in m.group(1).split("\n"):
        k, _, v = line.partition(":")
        out[k.strip()] = v.strip().strip('"')
    return out


def all_docs():
    names = ["SKILL.md", "rules.md", "records.md", "proposal-format.md"] + [f"briefs/{b}.md" for b in BRIEFS]
    return {n: text_of(*n.split("/")) for n in names}


class SkillTest(unittest.TestCase):
    def test_frontmatter(self):
        fm = frontmatter(text_of("SKILL.md"))
        self.assertEqual(fm["name"], "refresh-trails")
        self.assertEqual(os.path.basename(SKILL_DIR), fm["name"])
        self.assertGreater(len(fm["description"]), 60)
        self.assertIn("Use when", fm["description"])

    def test_every_file_it_points_to_exists(self):
        skill = text_of("SKILL.md")
        for rel in sorted(set(re.findall(r"`((?:briefs/)?[a-z\-]+\.md)`", skill))):
            self.assertTrue(os.path.isfile(os.path.join(SKILL_DIR, rel)), rel)
        for b in BRIEFS:
            self.assertIn(f"briefs/{b}.md", skill)
            self.assertTrue(os.path.isfile(os.path.join(SKILL_DIR, "briefs", b + ".md")))
        for n, t in all_docs().items():
            base = os.path.dirname(os.path.join(SKILL_DIR, n))
            for rel in set(re.findall(r"`(\.\./[a-z\-]+\.md)`", t)):
                self.assertTrue(os.path.isfile(os.path.normpath(os.path.join(base, rel))), f"{n}: {rel}")

    def test_repository_files_it_names_exist(self):
        for n, t in all_docs().items():
            for rel in set(re.findall(r"`((?:tools|docs|web)/[A-Za-z0-9_./\-]+\.(?:py|md))`", t)):
                self.assertTrue(os.path.isfile(os.path.join(R.ROOT, rel)), f"{n}: {rel}")
        for rel in ("README.md", "CONTRIBUTING.md", "left-out.toml", "CHANGELOG.md", "SOURCES.md"):
            self.assertTrue(os.path.isfile(os.path.join(R.ROOT, rel)))

    def test_briefs_point_at_the_shared_files(self):
        for b in BRIEFS:
            t = text_of("briefs", b + ".md")
            self.assertTrue("../rules.md" in t, b)
            self.assertTrue("../proposal-format.md" in t, b)
            self.assertTrue(t.startswith("# "), b)
            self.assertTrue("## What this is for" in t, b)
            self.assertTrue("## Report" in t, b)

    def test_phases_are_in_order(self):
        skill = text_of("SKILL.md")
        found = re.findall(r"^\*\*(\d)\. ", skill, re.M)
        self.assertEqual(found, [str(i) for i in range(10)])
        self.assertIn("light", skill.lower())

    def test_commands_named_exist(self):
        parser = R.build_parser()
        names = set(parser._subparsers._group_actions[0].choices)
        skill = text_of("SKILL.md")
        for cmd in re.findall(r"tools/refresh\.py (\w+)", skill + text_of("briefs", "apply.md")):
            self.assertIn(cmd, names)
        self.assertEqual(names, {"preflight", "slices", "links", "collect", "apply"})

    def test_staging_is_ignored_by_git(self):
        with open(os.path.join(R.ROOT, ".gitignore"), encoding="utf-8") as f:
            lines = [l.strip() for l in f]
        self.assertIn("/refresh/", lines)

    def test_examples_in_the_proposal_format_are_valid(self):
        doc = text_of("proposal-format.md")
        blocks = re.findall(r"```toml\n(.*?)```", doc, re.S)
        self.assertGreaterEqual(len(blocks), 2)
        kinds = set()
        for block in blocks:
            data = tomllib.loads(block)
            for p in data["proposal"]:
                kinds.add(p["kind"])
                self.assertEqual(R.validate_proposal(p, {}), [], p)
        self.assertTrue({"verified", "change"} <= kinds)

    def test_every_kind_and_outcome_is_documented(self):
        doc = text_of("proposal-format.md")
        for kind in R.KINDS:
            self.assertIn(f"`{kind}`", doc)
        for outcome in R.OUTCOMES:
            if outcome != "not-found-emblem":
                self.assertIn(f"`{outcome}`", doc)

    def test_house_wording(self):
        for n, t in all_docs().items():
            body = re.sub(r"```.*?```", "", t, flags=re.S)
            self.assertNotIn("—", body, f"{n}: em dash")
            self.assertNotIn("–", body, f"{n}: en dash")
            self.assertIsNone(re.search(r"\S - \S", body), f"{n}: dash used as punctuation")
            for word in ("MUST", "NEVER", "ALWAYS", "CRITICAL", "IMPORTANT"):
                self.assertIsNone(re.search(rf"\b{word}\b", body), f"{n}: {word}")
            self.assertNotRegex(body, r"(?i)you are an? (expert|senior|world)")
            self.assertNotRegex(body, r"/tmp/|/home/")
            self.assertNotRegex(body, r"(?i)\bpurple\b|\bphrp\b")

    def test_briefs_that_may_start_a_process_forbid_killing_by_name(self):
        rules = text_of("rules.md")
        self.assertIn("pkill", rules)
        self.assertIn("killall", rules)
        for b in BRIEFS:
            self.assertIn("../rules.md", text_of("briefs", b + ".md"))


if __name__ == "__main__":
    unittest.main()
