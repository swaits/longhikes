"""The search box reads more than a trail's name: its author, the places it lies in and starts and ends at,
the land unit or body its record names, and its summary (olt/searchtext.py writes the words into each
row's data-search; app.js, between the facet-counts markers, matches them and ranks the rows).

The matching is run under node, on the rows the home page writes from the real records, and checked
against the records' own fields; nothing here names a trail's expected rank except where a case is
spelled out. The site is not built.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from olt import facets, home, searchtext, words  # noqa: E402
import test_filter_bar as bar  # noqa: E402

NODE = shutil.which("node")
NAME, AUTHOR, PLACES, SUMMARY, NONE = 0, 1, 2, 3, 9


def match_under_node(rows, queries):
    """{query: {id: how well it matches (0 name, 1 author, 2 places, 3 summary)}} for the rows that match."""
    prog = bar.facet_count_source() + """
var input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
var out = {};
input.queries.forEach(function (q) {
  var typed = FacetCount.wordsOf(q), hits = {};
  input.rows.forEach(function (r) {
    var m = FacetCount.match(r.search, typed);
    if (m !== FacetCount.NOT_FOUND) hits[r.id] = m;
  });
  out[q] = hits;
});
process.stdout.write(JSON.stringify(out));
"""
    out = subprocess.run([NODE, "-e", prog], input=json.dumps({"rows": rows, "queries": list(queries)}),
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def plain(text):
    text = unicodedata.normalize("NFD", text.lower().replace("'", "").replace("’", ""))
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in text if not unicodedata.combining(c)))


def starts_a_word(text, typed):
    return any(w.startswith(typed) for w in plain(text).split())


class FoldTest(unittest.TestCase):
    def test_accents_apostrophes_hyphens_and_case(self):
        self.assertEqual(searchtext.fold("Road’s End, Cedar Grove"), "roads end cedar grove")
        self.assertEqual(searchtext.fold("Road's End"), "roads end")
        self.assertEqual(searchtext.fold("Québec"), "quebec")
        self.assertEqual(searchtext.fold("Long-Distance  TRAIL"), "long distance trail")
        self.assertEqual(searchtext.fold(""), "")
        self.assertEqual(searchtext.fold(None), "")

    @unittest.skipUnless(NODE, "node is not installed")
    def test_the_script_folds_as_the_page_builder_does(self):
        recs = bar.Pages.recs()
        samples = [t for r in recs for t in searchtext.tier_texts(r)] + [
            "Road’s End", "Québec", "Long-Distance", "  spaced   out ", "Nèw-Brünswick", "100 mi", "4x4 tracks", "St. John’s"]
        prog = bar.facet_count_source() + """
var input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(input.map(FacetCount.fold)));
"""
        out = subprocess.run([NODE, "-e", prog], input=json.dumps(samples), capture_output=True, text=True, check=True)
        got = json.loads(out.stdout)
        bad = [(s, g, searchtext.fold(s)) for s, g in zip(samples, got) if g != searchtext.fold(s)]
        self.assertEqual(bad, [])


class RowWordsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recs = bar.Pages.recs()
        cls.by_id = {r["id"]: r for r in cls.recs}

    def test_four_tiers_and_each_word_once(self):
        for rec in self.recs:
            attr = searchtext.attribute(rec)
            self.assertEqual(attr.count("|"), searchtext.TIERS - 1, rec["id"])
            seen = [w for tier in attr.split("|") for w in tier.split()]
            self.assertEqual(len(seen), len(set(seen)), rec["id"])
            self.assertEqual(attr, attr.lower())

    def test_the_name_tier_has_the_name_the_abbreviation_and_the_id(self):
        rec = self.by_id["john-muir"]
        name = searchtext.tiers(rec)[NAME]
        for word in ("john", "muir", "jmt"):
            self.assertIn(word, name)

    def test_the_places_tier_has_full_state_names_both_ends_and_the_body(self):
        rec = self.by_id["rae-lakes-loop"]
        places = searchtext.tiers(rec)[PLACES]
        for word in ("california", "united", "states", "cedar", "grove", "roads", "end", "kings", "canyon", "national", "park", "service"):
            self.assertTrue(word in places or word in searchtext.tiers(rec)[NAME], word)
        # the code is not what is written: the name is
        self.assertNotIn("ca", places)

    def test_a_route_by_a_person_has_no_body_in_the_places_tier(self):
        for rec in self.recs:
            if rec.get("designation", "").lower().startswith(("person-defined route", "guidebook route")):
                self.assertNotIn("agency", " ".join(searchtext.tiers(rec)[PLACES]).split(), rec["id"])

    def test_a_route_author_is_in_the_author_tier_or_the_name(self):
        for rec in self.recs:
            who = facets.author(rec)
            if not who:
                continue
            have = set(searchtext.tiers(rec)[NAME] + searchtext.tiers(rec)[AUTHOR])
            self.assertTrue(set(searchtext.fold(who).split()) <= have, rec["id"])

    def test_the_summary_keeps_no_word_of_fewer_than_three_letters(self):
        for rec in self.recs:
            self.assertTrue(all(len(w) >= searchtext.SUMMARY_MIN for w in searchtext.tiers(rec)[SUMMARY]), rec["id"])

    def test_only_a_list_with_a_search_box_carries_the_words(self):
        recs = self.recs[:12]
        with_box = home.results(recs, finder=True)
        without = home.results(recs)
        self.assertEqual(str(with_box).count(' data-search="'), len(recs))
        self.assertNotIn(" data-search=", str(without))

    def test_the_words_are_written_where_the_script_reads_them(self):
        body = str(home.render(self.recs, bar.SITE, bar.ROOT))
        self.assertEqual(body.count(' data-search="'), len(self.recs))


@unittest.skipUnless(NODE, "node is not installed")
class QueriesTest(unittest.TestCase):
    """What each query returns, on the home page's rows from the real records."""

    @classmethod
    def setUpClass(cls):
        cls.recs = bar.Pages.recs()
        cls.rows = bar.rows_of(home.render(cls.recs, bar.SITE, bar.ROOT))
        cls.queries = ["grand canyon", "canyon grand", "glacier", "mount whitney", "roads end", "road's end", "ROADS  END",
                       "new mexico", "colorado", "québec", "quebec", "jamal green", "green jamal", "zzzqx", "at", "jmt",
                       "long-distance", "grand zzzqx"]
        cls.hits = match_under_node(cls.rows, cls.queries)

    def ids(self, query):
        return set(self.hits[query])

    def fields(self, rec):
        h = rec.get("hike", {})
        return [rec["name"], rec.get("common_name", ""), rec.get("short_name", ""), rec["id"], facets.author(rec),
                " ".join(words.region_name(c) for c in rec.get("regions", [])), h.get("start", ""), h.get("end", ""),
                rec.get("designation", ""), h.get("summary", "")]

    def expected(self, *typed):
        """Every record in whose fields each typed word starts a word, worked out from the fields themselves."""
        return {r["id"] for r in self.recs
                if all(any(starts_a_word(f, w) for f in self.fields(r)) for w in typed)}

    def test_grand_canyon_finds_the_trails_that_go_there(self):
        got = self.ids("grand canyon")
        self.assertGreaterEqual(len(got), 7)
        self.assertLessEqual(got, self.expected("grand", "canyon"))
        # everything the fields say, but for the designation of a route that only says who made it
        missing = self.expected("grand", "canyon") - got
        for rid in missing:
            self.assertTrue(starts_a_word(self.by(rid).get("designation", ""), "grand") or starts_a_word(self.by(rid).get("designation", ""), "canyon"), rid)
        for rid in ("tonto-trail", "powell-plateau-loop", "nankoweap-bright-angel-loop"):
            self.assertIn(rid, got)
        self.assertNotIn("appalachian", got)
        self.assertNotIn("pacific-crest", got)

    def by(self, rid):
        return next(r for r in self.recs if r["id"] == rid)

    def test_words_in_any_order_find_the_same_trails_with_the_same_rank(self):
        self.assertEqual(self.hits["grand canyon"], self.hits["canyon grand"])

    def test_glacier_finds_the_trails_that_name_a_glacier_place_or_say_so(self):
        got = self.ids("glacier")
        self.assertGreaterEqual(len(got), 7)
        self.assertEqual(got, self.expected("glacier"))
        self.assertIn("ptarmigan-glenns-lake-highline-loop", got)
        self.assertNotIn("appalachian", got)

    def test_mount_whitney(self):
        got = self.ids("mount whitney")
        self.assertIn("john-muir", got)
        self.assertEqual(got, self.expected("mount", "whitney"))
        self.assertNotIn("appalachian", got)

    def test_roads_end_finds_road_s_end_with_or_without_the_apostrophe_and_case(self):
        got = self.ids("roads end")
        self.assertEqual(got, self.ids("road's end"))
        self.assertEqual(got, self.ids("ROADS  END"))
        self.assertIn("rae-lakes-loop", got)
        self.assertEqual(got, self.expected("roads", "end"))
        self.assertNotIn("appalachian", got)

    def test_a_state_s_full_name_finds_the_trails_in_it(self):
        got = self.ids("new mexico")
        for r in self.recs:
            if "NM" in r.get("regions", []):
                self.assertIn(r["id"], got, r["id"])
        self.assertEqual(got, self.expected("new", "mexico"))
        self.assertIn("continental-divide", got)

    def test_a_province_with_an_accent_is_found_without_it(self):
        self.assertEqual(self.hits["québec"], self.hits["quebec"])
        self.assertTrue(self.hits["quebec"])
        for r in self.recs:
            if "QC" in r.get("regions", []):
                self.assertIn(r["id"], self.hits["quebec"], r["id"])

    def test_an_author_s_name_finds_the_route_in_either_order(self):
        who = next(r for r in self.recs if r["id"] == "across-utah-route")
        self.assertEqual(facets.author(who), "Jamal Green")
        self.assertEqual(self.hits["jamal green"], self.hits["green jamal"])
        self.assertEqual(self.hits["jamal green"].get("across-utah-route"), AUTHOR)

    def test_the_abbreviation_finds_the_trail_first(self):
        self.assertEqual(self.hits["jmt"], {"john-muir": NAME})
        self.assertEqual(self.hits["at"]["appalachian"], NAME)

    def test_a_word_of_the_name_ranks_above_one_of_the_places(self):
        hits = self.hits["colorado"]
        names = [i for i, t in hits.items() if t == NAME]
        self.assertTrue({"colorado-trail"} <= set(names))
        self.assertGreater(len(set(hits.values())), 1)
        # a trail in the state whose name does not say so is still found, after
        self.assertEqual(hits["continental-divide"], PLACES)
        self.assertLess(max(hits[i] for i in names), hits["continental-divide"])

    def test_the_summary_is_the_weakest_place_to_match(self):
        hits = self.hits["glacier"]
        for rid, how in hits.items():
            text = self.fields(self.by(rid))
            in_place = any(starts_a_word(f, "glacier") for f in text[:9])
            self.assertEqual(how == SUMMARY, not in_place, rid)

    def test_every_word_has_to_be_found(self):
        self.assertEqual(self.hits["zzzqx"], {})
        self.assertEqual(self.hits["grand zzzqx"], {})

    def test_a_short_word_is_not_looked_for_in_the_summary(self):
        self.assertTrue(all(how != SUMMARY for how in self.hits["at"].values()))

    def test_a_hyphenated_word_is_two_words(self):
        self.assertEqual(self.hits["long-distance"], match_under_node(self.rows, ["long distance"])["long distance"])

    def test_a_nonsense_word_leaves_the_no_results_state_to_show(self):
        js = bar.read(WEB, "assets", "app.js")
        self.assertIn("if (empty) empty.hidden = shown.length > 0;", js)
        page = str(home.render(self.recs, bar.SITE, bar.ROOT))
        self.assertIn('id="empty-state" hidden', page)
        self.assertIn("No trails match these filters.", page)


class ScriptTest(unittest.TestCase):
    """What the filter bar does with the rank, read from the script."""

    def test_the_rows_are_ranked_while_words_are_typed_and_in_their_own_order_otherwise(self):
        js = bar.read(WEB, "assets", "app.js")
        self.assertIn("d.li.dataset.match = String(m)", js)
        self.assertIn("if (m === -1) delete d.li.dataset.match", js)
        self.assertIn("return cmpNum(Number(a.dataset.match), Number(b.dataset.match));", js)
        # ranked before the counts, and the line only for a match beyond the name
        self.assertIn("var says = m > 0 && m < FacetCount.NOT_FOUND ? 'Matches: ' + MATCH_SAYS[m] : '';", js)

    def test_the_search_stays_in_the_address(self):
        js = bar.read(WEB, "assets", "app.js")
        self.assertIn("if (s.q) p.set('q', s.q);", js)
        self.assertIn("el.q.value = p.get('q') || '';", js)


if __name__ == "__main__":
    unittest.main()
