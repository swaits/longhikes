"""Tests for the length facts on a trail page: the canonical length, the holder's larger figure
and the built length of an unfinished trail (docs/schema.md, "What length_km counts").

These render fixtures; they do not need the built site.
"""
import copy
import os
import re
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from olt import browse, common, facets, seo, site, trail, words  # noqa: E402
from test_hike import FULL_HIKE, GH, fake, render, top_part  # noqa: E402
from test_hike import text as _text  # noqa: E402

def text(fragment):
    """The words of a fragment, with the space the tags add before a comma taken out."""
    return _text(fragment).replace(" ,", ",")


NOTE = "all designated trail, official side trail and connecting roadwalks"


def with_lengths(i, km, **more):
    rec = fake(i, km=km, hike=copy.deepcopy(FULL_HIKE))
    rec["derived"]["length_mi"] = round(km / words.KM_PER_MI)
    rec.update(more)
    return rec


def florida():
    rec = with_lengths(1, 1818, system_km=2549, system_note=NOTE)
    del rec["hike"]["unfinished"]
    return rec


def unfinished():
    return with_lengths(2, 523, built_km=467)


def glance_length(rec):
    body = top_part(render(rec))
    start = body.index('<dt>Length</dt>')
    return body[start:body.index("</div>", start)]


class GlanceTest(unittest.TestCase):
    def test_the_length_is_the_canonical_one_and_the_system_figure_sits_beneath_it(self):
        row = glance_length(florida())
        self.assertIn('<span class="len__mi">1,130 mi</span><span class="len__km">1,818 km</span>', row)
        self.assertIn(f"Whole system: 1,584 mi 2,549 km, counting {NOTE}", text(row))
        self.assertLess(row.index("len--stack"), row.index("Whole system"))
        self.assertIn("<small>", row)

    def test_the_built_figure_sits_beneath_the_length(self):
        row = glance_length(unfinished())
        self.assertIn('<span class="len__mi">325 mi</span><span class="len__km">523 km</span>', row)
        self.assertIn("290 mi 467 km built", text(row))
        self.assertNotIn("Whole system", row)

    def test_a_record_with_neither_shows_neither(self):
        row = glance_length(with_lengths(3, 523))
        self.assertNotIn("built", row)
        self.assertNotIn("Whole system", row)

    def test_both_may_show_together_and_the_note_is_escaped(self):
        rec = with_lengths(4, 523, built_km=467, system_km=700, system_note="side trails <b>too</b>")
        row = glance_length(rec)
        self.assertIn("built", row)
        self.assertIn("counting side trails &lt;b&gt;too&lt;/b&gt;", row)

    def test_the_not_finished_panel_still_follows_the_unfinished_sentence(self):
        body = top_part(render(unfinished()))
        self.assertIn("<strong>Not finished.</strong>", body)


class BriefAndDescriptionTest(unittest.TestCase):
    def test_in_brief_uses_the_canonical_length_and_may_add_the_built_figure(self):
        first = text(trail.brief_sentences(florida())[0])
        self.assertIn("1,130-mile (1,818 km)", first)
        self.assertNotIn("1,584", first)
        self.assertNotIn("built", first)
        first = text(trail.brief_sentences(unfinished())[0])
        self.assertIn("325-mile (523 km)", first)
        self.assertIn("with 290 miles (467 km) built", first)

    def test_the_description_uses_the_canonical_length(self):
        self.assertIn("1,130 miles (1,818 km)", trail.description(florida()))
        self.assertNotIn("1,584", trail.description(florida()))
        self.assertIn("325 miles (523 km), 290 miles built,", trail.description(unfinished()))
        self.assertLessEqual(len(trail.description(unfinished())), common.DESCRIPTION_LIMIT)


class StructuredDataTest(unittest.TestCase):
    def props(self, rec):
        return {(p["name"], p.get("unitCode")): p for p in seo.place_node(rec, GH)["additionalProperty"]}

    def test_the_length_stays_canonical_and_the_system_figure_is_labelled(self):
        props = self.props(florida())
        self.assertEqual(props[("Published length", "KMT")]["value"], 1818)
        self.assertEqual(props[("Published length", "SMI")]["value"], 1130)
        self.assertEqual(props[("Whole system length", "KMT")]["value"], 2549)
        self.assertEqual(props[("Whole system length", "SMI")]["value"], 1584)
        self.assertEqual(props[("Whole system length", "SMI")]["description"], f"Counting {NOTE}")
        self.assertNotIn(("Built length", "KMT"), props)

    def test_the_built_length_is_labelled_and_a_plain_record_has_neither(self):
        props = self.props(unfinished())
        self.assertEqual(props[("Built length", "KMT")]["value"], 467)
        self.assertEqual(props[("Built length", "SMI")]["value"], 290)
        self.assertNotIn(("Whole system length", "KMT"), props)
        props = self.props(with_lengths(5, 523))
        self.assertFalse([k for k in props if k[0] in ("Built length", "Whole system length")])


class OnlyTheCanonicalLengthCountsTest(unittest.TestCase):
    def test_bands_time_estimates_and_lists_ignore_the_larger_figure(self):
        plain, big = with_lengths(6, 1818), florida()
        for rec in (plain, big):
            del rec["hike"]["days"]
        self.assertEqual(facets.time_days(plain), facets.time_days(big))
        self.assertEqual(facets.time_band(plain), facets.time_band(big))
        for key in ("under-100-miles", "longest"):
            self.assertEqual(browse.by_key(key).test(plain), browse.by_key(key).test(big), key)
        # the band follows length_km: raising only the system figure moves nothing
        longer = copy.deepcopy(big)
        longer["system_km"] = 9000
        self.assertEqual(facets.time_days(big), facets.time_days(longer))

    def test_the_record_panel_names_both_figures_apart(self):
        body = render(florida())
        panel = text(body[body.index('id="record-title"'):])
        self.assertIn("Length 1,130 mi 1,818 km", panel)
        self.assertIn("Whole system 1,584 mi 2,549 km, counting", panel)
        panel = text(render(unfinished())[render(unfinished()).index('id="record-title"'):])
        self.assertIn("Built length 290 mi 467 km built", panel)


class WordsTest(unittest.TestCase):
    def test_the_glossary_and_the_method_page_say_what_length_means(self):
        import tomllib
        with open(os.path.join(os.path.dirname(WEB), "glossary.toml"), "rb") as f:
            terms = {t["id"]: t for t in tomllib.load(f)["term"]}
        definition = terms["published-length"]["definition"]
        self.assertIn("end-to-end length", definition)
        self.assertIn("canonical path", definition)
        self.assertIn("no system total", definition)

    def test_the_schema_defines_length_and_names_the_new_fields(self):
        with open(os.path.join(os.path.dirname(WEB), "docs", "schema.md"), encoding="utf-8") as f:
            schema = f.read()
        for needle in ("What `length_km` counts", "`system_km`", "`system_note`", "`built_km`",
                       "canonical path", "Florida"):
            self.assertIn(needle, schema)


if __name__ == "__main__":
    unittest.main()
