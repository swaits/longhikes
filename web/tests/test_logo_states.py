"""What a trail page says for each state of [shield], from the record alone."""
import html
import os
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from olt import trail, words  # noqa: E402
from test_pages import sample_record  # noqa: E402


def logo_text(status, note):
    rec = sample_record("Example Trail")
    rec["shield"].update({"status": status, "note": note})
    return html.unescape(str(trail.logo_block(rec)))


class LogoStatesTest(unittest.TestCase):
    def test_no_emblem_of_its_own(self):
        text = logo_text("no-logo-exists", "Looked at the association's site.")
        self.assertIn("No emblem of its own", text)
        self.assertIn("Looked at the association's site.", text)
        self.assertNotIn("Emblem not found", text)

    def test_emblem_not_found(self):
        text = logo_text("logo-not-found", "A sign shows one.")
        self.assertIn("Emblem not found", text)
        self.assertIn("exists or may exist", text)
        self.assertIn("A sign shows one.", text)
        self.assertNotIn("No emblem of its own", text)

    def test_words_agree_with_the_block(self):
        self.assertEqual(words.label(words.SHIELD_STATUS, "no-logo-exists"), "No emblem of its own")
        self.assertEqual(words.label(words.SHIELD_STATUS, "logo-not-found"), "Emblem not found")


if __name__ == "__main__":
    unittest.main()
