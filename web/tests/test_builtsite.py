"""The shared test build is always a fresh one: nothing in the directory tests read can be left over
from an earlier build, such as a page that another branch wrote and this one does not."""
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import builtsite  # noqa: E402


class FreshBuildTest(unittest.TestCase):
    def test_a_page_left_by_an_earlier_build_is_not_there_when_the_next_build_starts(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "site")
            os.makedirs(os.path.join(out, "regions", "gone"))
            for rel in (os.path.join("regions", "gone", "index.html"), "old.json"):
                with open(os.path.join(out, rel), "w") as f:
                    f.write("left over")
            seen = []

            def fake_build(cmd, **kwargs):
                seen.append(sorted(os.listdir(out)) if os.path.isdir(out) else None)
                os.makedirs(out, exist_ok=True)
                return subprocess.CompletedProcess(cmd, 0, "", "")

            with mock.patch.object(builtsite.subprocess, "run", fake_build):
                builtsite.build(out)
            self.assertIn(seen[0], (None, []))
            self.assertEqual(os.listdir(out), [])

    def test_the_shared_site_is_in_a_directory_named_for_this_process(self):
        if not builtsite.PREBUILT:
            self.assertTrue(builtsite.OUT.endswith(f"test-site-{os.getpid()}"))


if __name__ == "__main__":
    unittest.main()
