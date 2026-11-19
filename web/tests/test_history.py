"""The "History of this record" section of a trail page, and the permission block in the credit box."""
import html
import os
import re
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from olt import records, site, trail, words  # noqa: E402
from test_hike import with_line  # noqa: E402
from test_pages import sample_record  # noqa: E402

S = site.Site("N", "T", repo_url="https://github.com/o/r")
QUOTE = "It's completely public and free to share."
ADDED = {"date": "2026-11-01", "change": "The record was added.", "fields": ["record"],
         "basis": "The record's own source entry: Example Trail Association.",
         "asked_by": "the dataset's own check", "outcome": "applied"}
CHANGED = {"date": "2026-11-12", "change": "The length was changed to 160 miles (257 km).",
           "fields": ["length_km", "length_note"], "basis": "The association's page for the trail gives 160 miles.",
           "basis_url": "https://example.org/trail?a=1&b=2", "asked_by": "the trail association's president",
           "outcome": "applied"}
DECLINED = {"date": "2026-11-14", "change": "A request to shorten it to 150 miles (241 km) was not applied.",
            "fields": ["length_km"], "basis": "The association's own page still says 160 miles.",
            "basis_url": "https://github.com/o/r/issues/9", "asked_by": "a hiker", "outcome": "declined"}


def with_history(*entries):
    rec = sample_record("Example Trail")
    rec["history"] = [dict(e) for e in entries]
    return rec


def flat(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text)))


def permission_record():
    rec = with_line(sample_record("Example Trail"))
    rec["source"].update({"licence": "stated-permission", "attribution": "Example Trail Association",
                          "licence_text": "The association's president answered a form on the issue tracker.",
                          "permission_quote": QUOTE, "permission_by": "the association's president",
                          "permission_date": "2026-11-16",
                          "permission_url": "https://github.com/o/r/issues/2"})
    return rec


class HistorySectionTest(unittest.TestCase):
    def section(self, *entries):
        return trail.history_section(with_history(*entries))

    def test_collapsed_section_beside_about_this_data(self):
        body = trail.render(with_history(ADDED, CHANGED), S)[2]
        self.assertIn('<details class="about-data about-data--history" id="record-history">', body)
        self.assertNotIn("<details class=\"about-data about-data--history\" id=\"record-history\" open", body)
        self.assertIn("<h2 id=\"record-history-title\">History of this record</h2>", body)
        self.assertLess(body.index('<details class="about-data" id="about-data">'), body.index("History of this record"))
        self.assertEqual(body.count("History of this record"), 1)

    def test_one_entry(self):
        part = self.section(ADDED, CHANGED)
        self.assertIn('<li class="history__entry history__entry--applied">', part)
        self.assertIn('<time datetime="2026-11-12">2026-11-12</time>', part)
        self.assertIn('<p class="history__change">The length was changed to 160 miles (257 km).</p>', part)
        self.assertIn('<p class="history__basis"><span class="history__label">Basis:</span> '
                      "The association&#x27;s page for the trail gives 160 miles. "
                      '<a href="https://example.org/trail?a=1&amp;b=2">https://example.org/trail?a=1&amp;b=2</a></p>', part)
        self.assertIn('<p class="history__who"><span class="history__label">Asked by:</span> '
                      "the trail association&#x27;s president</p>", part)
        self.assertIn("<li><code>length_km</code></li><li><code>length_note</code></li>", part)

    def test_entries_run_oldest_first_as_the_record_has_them(self):
        part = self.section(ADDED, CHANGED, DECLINED)
        self.assertLess(part.index("2026-11-01"), part.index("2026-11-12"))
        self.assertLess(part.index("2026-11-12"), part.index("2026-11-14"))
        self.assertIn("3 entries", part)
        self.assertIn("1 entry", self.section(ADDED))

    def test_declined_request_has_a_plain_label_and_applied_has_none(self):
        part = self.section(ADDED, DECLINED)
        self.assertIn('<li class="history__entry history__entry--declined">', part)
        self.assertEqual(part.count("Request declined"), 1)
        declined = part[part.index("history__entry--declined"):]
        self.assertIn('<strong class="history__outcome">Request declined</strong>', declined)
        self.assertNotIn("Request declined", part[:part.index("history__entry--declined")])

    def test_no_address_means_no_link(self):
        part = self.section(ADDED)
        self.assertNotIn("<a ", part)
        self.assertIn("The record&#x27;s own source entry: Example Trail Association.", part)

    def test_text_is_escaped(self):
        bad = dict(CHANGED, change="<script>alert(1)</script>", asked_by='"a" & <b>')
        part = self.section(ADDED, bad)
        self.assertNotIn("<script>", part)
        self.assertIn("&lt;script&gt;", part)
        self.assertIn("&amp; &lt;b&gt;", part)

    def test_a_record_with_no_history_has_no_section(self):
        rec = sample_record("Example Trail")
        self.assertEqual(trail.history_section(rec), "")
        self.assertNotIn("History of this record", trail.render(rec, S)[2])

    def test_it_is_generated_from_the_record_alone(self):
        words_in_page = flat(self.section(ADDED, CHANGED, DECLINED))
        for label in ("History of this record", "Basis:", "Asked by:", "Request declined"):
            self.assertIn(label, words_in_page)
        self.assertEqual(self.section(ADDED, CHANGED), self.section(ADDED, CHANGED))

    def test_the_source_block_is_not_changed_by_it(self):
        self.assertNotIn("record-history", trail.about_data(with_history(ADDED), S))

    def test_real_records_all_show_their_history(self):
        recs = records.load_records()
        self.assertEqual(len(recs), 222)
        for rec in recs:
            part = trail.history_section(rec)
            self.assertIn("History of this record", part, rec["id"])
            self.assertEqual(part.count('<li class="history__entry '), len(rec["history"]), rec["id"])

    def test_hoosier_heritage_trail_history(self):
        rec = next(r for r in records.load_records() if r["id"] == "hoosier-heritage-trail")
        part = trail.history_section(rec)
        self.assertEqual(part.count("history__entry--applied"), len(rec["history"]))
        self.assertGreaterEqual(len(rec["history"]), 2)
        self.assertIn("the trail association&#x27;s president", part)
        self.assertIn('<a href="https://github.com/swaits/longhikes/issues/2">', part)


class CreditBoxPermissionTest(unittest.TestCase):
    def credit_box(self, rec):
        page = trail.render(rec, S)[2]
        start = page.index('<div class="credit">')
        return page[start:page.index("</section>", start)]

    def test_the_credit_box_shows_the_quotation_who_when_and_a_link(self):
        box = self.credit_box(permission_record())
        self.assertIn('<blockquote cite="https://github.com/o/r/issues/2"><p>It&#x27;s completely public and free to share.</p></blockquote>', box)
        self.assertIn("Said by the association&#x27;s president on 2026-11-16.", box)
        self.assertIn('<a href="https://github.com/o/r/issues/2">https://github.com/o/r/issues/2</a>', box)

    def test_the_sentence_is_true_where_it_stands(self):
        box = self.credit_box(permission_record())
        self.assertIn("The statement is quoted below.", box)
        self.assertLess(box.index("The statement is quoted below."), box.index("<blockquote"))
        self.assertNotIn("quoted below", words.LICENCE_NOTES["stated-permission"])

    def test_the_about_block_still_shows_it_too(self):
        page = trail.render(permission_record(), S)[2]
        self.assertEqual(page.count("<blockquote"), 2)
        self.assertEqual(page.count("The statement is quoted below."), 2)

    def test_no_claim_without_a_quotation(self):
        rec = permission_record()
        del rec["source"]["permission_quote"]
        page = trail.render(rec, S)[2]
        self.assertNotIn("quoted below", page)
        self.assertNotIn("<blockquote", page)

    def test_other_licences_get_no_block(self):
        rec = permission_record()
        rec["source"]["licence"] = "CC-BY-4.0"
        box = self.credit_box(rec)
        self.assertNotIn("<blockquote", box)
        self.assertNotIn("Said by", box)

    def test_the_real_record(self):
        rec = next(r for r in records.load_records() if r["id"] == "hoosier-heritage-trail")
        rec["derived"].setdefault("downloads", [{"role": "main", "format": "GPX", "file": "x.gpx", "bytes": 1000}])
        box = self.credit_box(rec)
        self.assertIn("completely public and free to share", box)
        self.assertIn("Said by the association&#x27;s president on 2026-11-16.", box)
        self.assertIn("https://github.com/swaits/longhikes/issues/2", box)


if __name__ == "__main__":
    unittest.main()
