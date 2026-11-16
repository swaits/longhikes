"""The wording for the stated-permission licence on trail pages and the sources page."""
import html
import os
import re
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import xml.etree.ElementTree as ET

from olt import docs, geo, site, trail, words  # noqa: E402
from test_hike import with_line  # noqa: E402
from test_pages import sample_record  # noqa: E402

S = site.Site("N", "T", repo_url="https://github.com/o/r")
QUOTE = "It's completely public and free to share."


def permission_record():
    rec = with_line(sample_record("Example Trail"))
    rec["source"].update({"licence": "stated-permission", "attribution": "Example Trail Association",
                          "licence_text": "The association's president answered a form on the issue tracker.",
                          "permission_quote": QUOTE, "permission_by": "the association's president",
                          "permission_date": "2026-11-16",
                          "permission_url": "https://github.com/o/r/issues/2"})
    return rec


def flat(html_text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", html_text)))


class StatedPermissionWordsTest(unittest.TestCase):
    def test_label_and_note(self):
        self.assertEqual(words.LICENCES["stated-permission"], "Shared with permission")
        note = words.LICENCE_NOTES["stated-permission"]
        self.assertTrue(note.startswith("Shared with permission. The holder has said in writing"))
        self.assertIn("not a Creative Commons licence", note)

    def test_trail_page_says_it_in_plain_words(self):
        body = flat(trail.render(permission_record(), S)[2])
        self.assertGreaterEqual(body.count("Shared with permission. The holder has said in writing"), 2)
        self.assertIn("Licence: Shared with permission", body)
        self.assertIn(QUOTE, body)
        for wrong in ("CC BY", "Public domain", "US public domain", "ODbL"):
            self.assertNotIn(wrong, body)

    def test_trail_page_shows_the_quotation_who_when_and_a_link(self):
        raw = trail.render(permission_record(), S)[2]
        self.assertIn('<blockquote cite="https://github.com/o/r/issues/2"><p>It&#x27;s completely public and free to share.</p></blockquote>', raw)
        self.assertIn("Said by the association&#x27;s president on 2026-11-16.", raw)
        self.assertIn('<a href="https://github.com/o/r/issues/2">https://github.com/o/r/issues/2</a>', raw)

    def test_no_quotation_for_other_licences(self):
        rec = permission_record()
        rec["source"]["licence"] = "CC-BY-4.0"
        raw = trail.render(rec, S)[2]
        self.assertNotIn("Said by", raw)
        self.assertNotIn("<blockquote", raw)

    def test_gpx_description_carries_the_quote_and_address(self):
        src = permission_record()["source"]
        fields = {k: src[k] for k in ("permission_quote", "permission_by", "permission_date", "permission_url")}
        text = geo.gpx_text([[[0, 0], [1, 1]]], "N", licence=src["licence"], licence_text=src["licence_text"],
                            permission=fields)
        desc = ET.fromstring(text).find("{http://www.topografix.com/GPX/1/1}metadata/"
                                        "{http://www.topografix.com/GPX/1/1}desc").text
        self.assertIn(f'Permission: "{QUOTE}"', desc)
        self.assertIn("Said by the association's president on 2026-11-16.", desc)
        self.assertIn("https://github.com/o/r/issues/2", desc)
        plain = ET.fromstring(geo.gpx_text([[[0, 0], [1, 1]]], "N", licence="ODbL-1.0", licence_text="ODbL"))
        self.assertNotIn("Permission", plain.find("{http://www.topografix.com/GPX/1/1}metadata/"
                                                  "{http://www.topografix.com/GPX/1/1}desc").text)

    def test_other_licences_get_no_note(self):
        rec = permission_record()
        rec["source"]["licence"] = "CC-BY-4.0"
        self.assertNotIn("has said in writing", flat(trail.render(rec, S)[2]))

    def test_data_page_row(self):
        rows = docs.line_licence_rows([permission_record()], os.path.dirname(WEB))
        what, terms, url = rows[0]
        self.assertIn("Tracks shared with permission: 1 record", str(what))
        self.assertIn("The holder has said in writing", str(terms))
        self.assertEqual(url, "/sources/")


if __name__ == "__main__":
    unittest.main()
