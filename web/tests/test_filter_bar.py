"""The filter bar on every page that shows a set of trails, and the numbers beside its choices.

The bar (olt/home.py listing(), finder_form()) is the home page's, on each list, place and the Routes
page whose set has at least home.FILTER_MIN trails, built from that page's own trails. app.js counts
the choices again from the rows on the page every time anything changes (FacetCount, between the
facet-counts markers); this file runs that counting under node, on the rows the home page writes,
and checks it against counts made here straight from the records. Pages are rendered one at a time;
the site is not built.
"""
import collections
import html
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from olt import browse, facets, home, layout, leftout, regions, site, standing, views, words  # noqa: E402
from olt import records as recordsmod  # noqa: E402

SITE = site.load()


def read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def form_of(body):
    body = str(body)
    if 'id="finder-form"' not in body:
        return ""
    return body[body.index('<form class="filters"'):body.index("</form>")]


def facets_of(body):
    return re.findall(r'data-facet="(\w+)"', form_of(body))


def entry_ids(body):
    return re.findall(r'<li class="entry" data-id="([^"]+)"', str(body))


class Pages:
    _recs = None

    @classmethod
    def recs(cls):
        if Pages._recs is None:
            Pages._recs = recordsmod.load_records(ROOT)
        return Pages._recs


class WhichPagesHaveTheBarTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = Pages.recs()
        cls.shown = dict((lst.key, recs) for lst, recs in browse.shown(cls.records))

    def list_body(self, key):
        lst = browse.by_key(key)
        return regions.list_page(lst, self.shown[key], len(self.records), SITE, records=self.records)[2]

    def test_a_list_page_a_place_page_a_part_of_the_country_and_routes_have_it(self):
        self.assertGreaterEqual(len(self.shown["loops"]), home.FILTER_MIN)
        self.assertTrue(form_of(self.list_body("loops")))
        by_slug, _ = regions.collect_regions(self.records)
        self.assertGreaterEqual(len(by_slug["ca-on"]["records"]), home.FILTER_MIN)
        self.assertTrue(form_of(regions.region_page("ca-on", self.records, SITE)[2]))
        self.assertTrue(form_of(regions.group_page("central-canada", self.records, SITE)[2]))
        self.assertTrue(form_of(regions.routes_page(self.records, SITE)[2]))

    def test_a_set_under_the_threshold_has_the_plain_rows(self):
        small = [k for k, recs in self.shown.items() if len(recs) < home.FILTER_MIN and k != "routes"]
        self.assertTrue(small)
        for key in small:
            body = self.list_body(key)
            self.assertFalse(form_of(body), key)
            self.assertNotIn("data-finder", str(body), key)

    def test_the_tables_rankings_newest_authors_and_left_out_pages_do_not(self):
        bodies = {}
        for spec in standing.RANKINGS:
            built = standing.ranking_page(spec, self.records, SITE)
            if built:
                bodies[spec[0]] = built[2]
        from olt import datafiles
        for c in datafiles.collections(ROOT):
            built = standing.collection_page(c, self.records, SITE)
            if built:
                bodies[c["name"]] = built[2]
        built = views.recent_page(self.records, SITE)
        if built:
            bodies["recent"] = built[2]
        from olt import authors
        groups = authors.author_pages(self.records, ROOT)
        bodies["authors"] = authors.index_page(self.records, SITE, ROOT)[2]
        big = max(groups, key=lambda g: len(g["routes"]))
        bodies["author"] = authors.author_page(big, self.records, SITE, groups)[2]
        bodies["left-out"] = leftout.left_out_page(leftout.load_entries(ROOT), SITE, ROOT)[2]
        self.assertGreater(len(bodies), 4)
        for name, body in bodies.items():
            self.assertNotIn('id="finder-form"', str(body), name)
            self.assertNotIn("data-finder", str(body), name)

    def test_the_saved_page_has_no_bar(self):
        from olt import saved
        self.assertNotIn('id="finder-form"', str(saved.saved_page(self.records, SITE)[2]))

    def test_one_bar_one_script(self):
        # every page's bar is the same form, which app.js finds by the one id
        body = str(self.list_body("loops"))
        self.assertEqual(body.count('id="finder-form"'), 1)
        self.assertIn('<div class="results" data-finder', body)
        js = read(WEB, "assets", "app.js")
        self.assertIn("document.querySelector('.results[data-finder]')", js)
        self.assertEqual(js.count("function initFinder("), 1)


class FacetsFitThePageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = Pages.recs()
        cls.shown = dict((lst.key, recs) for lst, recs in browse.shown(cls.records))

    def test_loops_have_no_shape_filter_and_routes_no_kind(self):
        lst = browse.by_key("loops")
        body = regions.list_page(lst, self.shown["loops"], len(self.records), SITE, records=self.records)[2]
        self.assertNotIn("shape", facets_of(body))
        self.assertIn("where", facets_of(body))
        self.assertNotIn("kind", facets_of(regions.routes_page(self.records, SITE)[2]))

    def test_a_states_page_has_no_where(self):
        body = regions.region_page("ca-on", self.records, SITE)[2]
        self.assertNotIn("where", facets_of(body))
        self.assertNotIn('name="where"', form_of(body))

    def test_a_part_of_the_country_offers_itself_first_then_only_its_own_places(self):
        body = regions.group_page("central-canada", self.records, SITE)[2]
        recs = regions.group_records(self.records, "central-canada")
        where = re.search(r'<select class="select" id="where" name="where">(.*?)</select>', form_of(body), re.S).group(1)
        options = re.findall(r'<option value="([^"]*)" data-label="([^"]*)">([^<]*)</option>', where)
        self.assertEqual(options[0], ("", "All of Central Canada", f"All of Central Canada ({len(recs)})"))
        self.assertNotIn("<optgroup", where)
        allowed = {"CA-ON", "CA-QC", facets.ACROSS_CANADA}
        self.assertTrue(options[1:])
        for value, label, text in options[1:]:
            self.assertIn(value, allowed)
            n = sum(1 for r in recs if value in facets.where_tokens(r))
            self.assertEqual(text, f"{label} ({n})")

    def test_a_facet_that_cannot_narrow_is_left_out(self):
        recs = [r for r in self.records if facets.shape(r) == "loop"]
        form = home.finder_form(recs)
        self.assertNotIn('data-facet="shape"', form)
        # and one choice that holds every trail is no choice
        only_us = [r for r in self.records if common_countries(r) == ["US"]][:20]
        self.assertNotIn('value="US"', home.finder_form(only_us))

    def test_no_choice_is_written_that_would_show_nothing(self):
        body = regions.group_page("central-canada", self.records, SITE)[2]
        recs = regions.group_records(self.records, "central-canada")
        form = form_of(body)
        self.assertNotRegex(form, r'class="check__count">0<')
        have = {t for r in recs for t in facets.terrain(r)}
        written = set(re.findall(r'name="terrain" value="([^"]+)"', form))
        self.assertTrue(written)
        self.assertTrue(written <= have, written - have)
        self.assertNotIn("desert", written)


def common_countries(rec):
    from olt import common
    return common.countries(rec)


class AListPageCarriesItsOwnTrailsOnlyTest(unittest.TestCase):
    def test_rows_and_map_are_the_lists_own(self):
        records = Pages.recs()
        lst = browse.by_key("loops")
        recs = browse.members(lst, records)
        body = str(regions.list_page(lst, recs, len(records), SITE, records=records)[2])
        own = {r["id"] for r in recs}
        self.assertEqual(set(entry_ids(body)), own)
        self.assertNotIn("data-every-trail", body)
        ids = re.search(r'data-map="overview"[^>]* data-ids="([^"]*)"', body).group(1).split()
        self.assertTrue(set(ids) <= own)

    def test_the_canonical_address_is_the_plain_page(self):
        doc = layout.layout("Loops", "<p>x</p>", path="/lists/loops/", site=SITE)
        canon = re.search(r'<link rel="canonical" href="([^"]+)"', doc)
        if canon:
            self.assertTrue(canon.group(1).endswith("/lists/loops/"))
            self.assertNotIn("?", canon.group(1))


class NoFilterLinksTest(unittest.TestCase):
    def test_no_page_sends_a_visitor_to_the_home_page_with_a_filter_set(self):
        for name in os.listdir(os.path.join(WEB, "olt")):
            if name.endswith(".py"):
                text = read(WEB, "olt", name)
                self.assertNotIn("with the filters", text, name)
                self.assertNotIn('href="/?where', text, name)
                self.assertNotIn('href="/?kind', text, name)

    def test_the_places_index_links_each_part_to_its_page(self):
        body = str(regions.regions_index_page(Pages.recs(), SITE)[2])
        self.assertIn('<a href="/regions/central-canada/">All 15 trails in Central Canada</a>'.replace(
            "15", str(len(regions.group_records(Pages.recs(), "central-canada")))), body)


# Counting, as app.js does it, run under node ------------------------------------------------------

NODE = shutil.which("node")


def facet_count_source():
    js = read(WEB, "assets", "app.js")
    start = js.index("/* facet-counts:begin")
    end = js.index("/* facet-counts:end */")
    return js[start:end]


def rows_of(body):
    """The rows' data, as app.js reads it from each row's data-* attributes."""
    out = []
    for attrs in re.findall(r'<li class="entry"([^>]*)>', str(body)):
        d = {k: html.unescape(v) for k, v in re.findall(r' data-([a-z]+)="([^"]*)"', attrs)}
        split = lambda v: [x for x in v.split(" ") if x]  # noqa: E731
        out.append({"id": d["id"], "search": [" " + t + " " for t in d["search"].split("|")], "where": split(d["where"]), "km": float(d["km"]),
                    "time": d["time"], "months": split(d["months"]), "terrain": split(d["terrain"]),
                    "kind": d["kind"], "walking": d["walking"], "shape": d["shape"], "gpx": d["gpx"]})
    return out


def state(**kw):
    s = {"words": [], "where": "", "min": 0, "max": None, "month": "", "kind": "",
         "time": [], "terrain": [], "walking": [], "shape": [], "gpx": []}
    s.update(kw)
    return s


def run_counts(rows, s, steps=()):
    """FacetCount.count(rows, s, steps) under node. max None stands for no longest length."""
    prog = facet_count_source() + """
var input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
if (input.s.max === null) input.s.max = Infinity;
process.stdout.write(JSON.stringify(FacetCount.count(input.rows, input.s, input.steps)));
"""
    out = subprocess.run([NODE, "-e", prog], input=json.dumps({"rows": rows, "s": s, "steps": list(steps)}),
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@unittest.skipUnless(NODE, "node is not installed")
class CountsAreTrueTest(unittest.TestCase):
    """The maintainer's case: the home page at ?where=g:central-canada&time=week."""

    @classmethod
    def setUpClass(cls):
        cls.records = Pages.recs()
        cls.rows = rows_of(home.render(cls.records, SITE, ROOT))
        cls.cc = [r for r in cls.records if "central-canada" in facets.place_groups(r)]

    def test_the_home_page_rows_are_every_trail(self):
        self.assertEqual(len(self.rows), len(self.records))

    def test_with_central_canada_chosen_time_and_terrain_count_its_trails_only(self):
        c = run_counts(self.rows, state(where="g:central-canada"))
        self.assertEqual(c["total"], len(self.cc))
        self.assertEqual(c["time"], dict(collections.Counter(facets.time_band(r) for r in self.cc)))
        self.assertEqual(sum(c["time"].values()), len(self.cc))
        self.assertEqual(c["terrain"], dict(collections.Counter(t for r in self.cc for t in facets.terrain(r))))
        # every number is of trails that are there: nothing counts zero, and nothing absent is counted
        self.assertTrue(all(n > 0 for n in c["terrain"].values()))
        self.assertTrue(all(n > 0 for n in c["time"].values()))

    def test_with_a_week_or_less_also_chosen(self):
        c = run_counts(self.rows, state(where="g:central-canada", time=["week"]))
        week = [r for r in self.cc if facets.time_band(r) == "week"]
        self.assertEqual(c["total"], len(week))
        # Time is counted against Where only, not against its own choice: the bands add up to the place
        self.assertEqual(c["time"], dict(collections.Counter(facets.time_band(r) for r in self.cc)))
        self.assertEqual(c["base"]["time"], len(self.cc))
        # Terrain against both
        self.assertEqual(c["terrain"], dict(collections.Counter(t for r in week for t in facets.terrain(r))))
        # Where against the time only: "All of Central Canada" says how many of it take a week or less
        everywhere_week = [r for r in self.records if facets.time_band(r) == "week"]
        self.assertEqual(c["where"]["g:central-canada"], len(week))
        self.assertEqual(c["base"]["where"], len(everywhere_week))
        self.assertEqual(c["where"]["CA-ON"], sum(1 for r in everywhere_week if "CA-ON" in facets.place_keys(r)))

    def test_length_steps_count_from_the_chosen_bounds(self):
        steps = [[f"{n}mi", n * words.KM_PER_MI] for n in (100, 200, 500)]
        c = run_counts(self.rows, state(where="g:central-canada", max=500 * words.KM_PER_MI), steps)
        for value, km in steps:
            self.assertEqual(c["min"][value], sum(1 for r in self.cc if km <= r["length_km"] <= 500 * words.KM_PER_MI))
            self.assertEqual(c["max"][value], sum(1 for r in self.cc if r["length_km"] <= km))

    def test_search_counts_too(self):
        c = run_counts(self.rows, state(words=["trail"], kind="route"))
        said = lambda r: any(" trail" in t for t in r["search"])  # noqa: E731 (a word at the start of a word of any text)
        want = [r for r in self.rows if said(r) and r["kind"] == "route"]
        self.assertEqual(c["total"], len(want))
        self.assertEqual(c["kind"]["trail"], sum(1 for r in self.rows if said(r) and r["kind"] == "trail"))

    def test_the_script_takes_out_what_would_show_nothing(self):
        js = read(WEB, "assets", "app.js")
        self.assertIn("if (o.value && k === 0 && o.value !== chosen) return;", js)
        self.assertIn("label.hidden = n === 0 && !b.checked;", js)
        self.assertIn("field.hidden = !narrows && !isSet(f, s);", js)
        # the counts are made on every change, from the rows on the page
        self.assertIn("var c = FacetCount.count(rows, s, lengthSteps());", js)


class CountWordsTest(unittest.TestCase):
    """The count above a list: "35 trails" when none is left out, "12 of 35 trails" when some are."""

    @staticmethod
    def count_of(body):
        m = re.search(r'<p class="results-count"[^>]*><strong>([^<]*)</strong>([^<]*)</p>', str(body))
        return m.group(1) + m.group(2)

    def test_a_page_with_nothing_filtered_reads_the_plain_count(self):
        records = Pages.recs()
        lst = browse.LISTS[0]
        recs = browse.members(lst, records)
        pages = {"home": home.render(records, SITE, ROOT),
                 "list": regions.list_page(lst, recs, len(records), SITE, records=records)[2]}
        for name, body in pages.items():
            if 'id="results-count"' not in str(body):
                continue
            text = self.count_of(body)
            self.assertRegex(text, r"^[\d,]+ (trails?|routes?)$", name)
            self.assertNotRegex(str(body), r"\b(\d[\d,]*) of \1\b", name)

    @unittest.skipUnless(NODE, "node is not installed")
    def test_the_script_words_the_count_both_ways(self):
        prog = facet_count_source() + """
var c = [[35, 35, 'trails'], [12, 35, 'trails'], [1, 1, 'trail'], [1, 58, 'routes'], [0, 58, 'routes'], [58, 58, 'routes']]
  .map(function (a) { return a[0] + ' ' + FacetCount.countWords(a[0], a[1], a[2]); });
process.stdout.write(JSON.stringify(c));
"""
        out = subprocess.run([NODE, "-e", prog], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(out.stdout), ["35 trails", "12 of 35 trails", "1 trail", "1 of 58 routes",
                                                  "0 of 58 routes", "58 routes"])


class PanelInTheFlowTest(unittest.TestCase):
    def test_the_open_panel_is_not_laid_over_the_rows(self):
        css = read(WEB, "assets", "style.css")
        rule = re.search(r"\n\.filters__panels \{[^}]*\}", css).group(0)
        self.assertNotIn("position: absolute", rule)
        self.assertNotRegex(css, r"html\.js \.filters__panels \{[^}]*position: absolute")

    def test_the_panel_starts_closed_whatever_the_address_says(self):
        js = read(WEB, "assets", "app.js")
        self.assertNotIn("if (firstOn", js)
        self.assertIn("if (window.location.hash === '#filters') showPanels(true);", js)


class UnseasonedNoteTest(unittest.TestCase):
    """A month filter says how many trails it leaves out for having no season on file."""

    def test_a_finder_list_has_the_note_and_it_starts_hidden(self):
        recs = recordsmod.load_records(ROOT)
        body = str(home.results(recs, finder=True))
        self.assertIn('<p class="results-note" data-unseasoned hidden>', body)
        self.assertIn('data-unseasoned-show>Show them</button>', body)
        self.assertNotIn("data-unseasoned", str(home.results(recs)))

    def test_the_script_counts_it_over_the_rows_of_the_list_and_show_them_clears_the_month(self):
        js = read(WEB, "assets", "app.js")
        self.assertIn("if (!d.months.length && FacetCount.passes(d, s, 'month')) noSeason++;", js)
        self.assertIn("' trails with no season on file are not shown.'", js)
        self.assertIn("el.month.value = '';", js)

    @unittest.skipUnless(NODE, "node is not installed")
    def test_the_number_is_the_trails_that_pass_everything_else_and_have_no_season(self):
        recs = recordsmod.load_records(ROOT)
        rows = rows_of(home.render(recs, SITE, ROOT))
        prog = facet_count_source() + """
var input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
input.s.max = Infinity;
var n = 0, shown = 0;
input.rows.forEach(function (d) {
  if (FacetCount.passes(d, input.s, '')) shown++;
  else if (!d.months.length && FacetCount.passes(d, input.s, 'month')) n++;
});
process.stdout.write(JSON.stringify([shown, n]));
"""
        for s in (state(month="8"), state(month="8", kind="route"), state(month="8", where="US-CA")):
            out = subprocess.run([NODE, "-e", prog], input=json.dumps({"rows": rows, "s": s}),
                                 capture_output=True, text=True, check=True)
            shown, n = json.loads(out.stdout)
            def base(r):
                return ((not s["kind"] or facets.kind(r) == s["kind"])
                        and (not s["where"] or s["where"] in facets.where_tokens(r)))
            self.assertEqual(shown, sum(1 for r in recs if base(r) and 8 in facets.months(r)))
            self.assertEqual(n, sum(1 for r in recs if base(r) and not facets.months(r)))


if __name__ == "__main__":
    unittest.main()
