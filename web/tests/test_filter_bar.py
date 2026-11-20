"""The filter bar on every page that shows a set of trails, and the numbers beside its choices.

The bar (olt/home.py listing(), finder_form()) is the home page's, on each list, place and the Routes
page, whatever the number of trails, built from that page's own trails. app.js counts
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
                self.assertTrue(form_of(self.list_body("loops")))
        by_slug, _ = regions.collect_regions(self.records)
        self.assertTrue(form_of(regions.region_page("ca-on", self.records, SITE)[2]))
        self.assertTrue(form_of(regions.group_page("central-canada", self.records, SITE)[2]))
        self.assertTrue(form_of(regions.routes_page(self.records, SITE)[2]))

    def test_every_state_province_and_list_page_has_the_bar_however_few_trails(self):
        by_slug, _ = regions.collect_regions(self.records)
        small = [k for k, v in by_slug.items() if len(v["records"]) < 10]
        self.assertGreater(len(small), 40)
        for key in small:
            body = regions.region_page(key, self.records, SITE)[2]
            self.assertIn('id="finder-form"', str(body), key)
            self.assertIn("data-finder", str(body), key)
        small_lists = [k for k, recs in self.shown.items() if len(recs) < 10 and k != "routes"]
        self.assertTrue(small_lists)
        for key in small_lists:
            self.assertTrue(form_of(self.list_body(key)), key)

    def test_a_two_trail_page_offers_only_filters_that_narrow_it(self):
        by_slug, _ = regions.collect_regions(self.records)
        two = [k for k, v in by_slug.items() if len(v["records"]) == 2]
        self.assertTrue(two)
        for key in two:
            form = form_of(regions.region_page(key, self.records, SITE)[2])
            self.assertIn('name="q"', form, key)
            for sel in re.findall(r"<select[^>]*>(.*?)</select>", form, re.S):
                self.assertNotIn("<select></select>", sel)
                self.assertGreater(len(re.findall(r"<option", sel)), 1, key)

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
        bodies["left-out"] = leftout.left_out_page(leftout.load_entries(ROOT), SITE, ROOT)[2]
        self.assertGreater(len(bodies), 4)
        for name, body in bodies.items():
            self.assertNotIn('id="finder-form"', str(body), name)
            self.assertNotIn("data-finder", str(body), name)

    def test_an_authors_own_page_has_the_bar_however_few_routes(self):
        from olt import authors
        groups = authors.author_pages(self.records, ROOT)
        for g in (min(groups, key=lambda g: len(g["routes"])), max(groups, key=lambda g: len(g["routes"]))):
            body = authors.author_page(g, self.records, SITE, groups)[2]
            self.assertIn('id="finder-form"', str(body), g["name"])

    def test_a_set_with_no_trails_still_builds(self):
        self.assertIn("<form", str(home.finder_form([])))

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
                    "time": d["time"], "months": split(d["months"]), "estimate": d.get("estimate") == "yes", "terrain": split(d["terrain"]),
                    "kind": d["kind"], "walking": d["walking"], "shape": d["shape"], "gpx": d["gpx"]})
    return out


def state(**kw):
    s = {"words": [], "where": "", "min": 0, "max": None, "month": "", "stated": False, "kind": "",
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


class LeaveOutEstimatesTest(unittest.TestCase):
    """The month filter can leave estimated seasons out, and says nothing about trails with no season."""

    def test_the_month_field_has_the_checkbox_and_it_starts_disabled(self):
        recs = recordsmod.load_records(ROOT)
        form = home.finder_form(recs)
        field = form[form.index('data-facet="month"'):]
        field = field[:field.index("</div>")]
        self.assertIn('<input type="checkbox" name="stated" value="1" disabled>', field)
        self.assertIn("Leave out estimated seasons", field)

    def test_there_is_no_checkbox_where_no_trail_has_an_estimated_season(self):
        recs = [r for r in recordsmod.load_records(ROOT) if not facets.season_estimated(r)]
        self.assertNotIn('name="stated"', home.finder_form(recs))

    def test_the_results_have_no_unseasoned_note(self):
        recs = recordsmod.load_records(ROOT)
        for body in (str(home.results(recs, finder=True)), str(home.results(recs))):
            self.assertNotIn("data-unseasoned", body)
            self.assertNotIn("Show them", body)
            self.assertNotIn("no season on file", body)
        js = read(WEB, "assets", "app.js")
        self.assertNotIn("unseasoned", js.lower())
        self.assertNotIn("no season on file", js)

    def test_a_row_carries_whether_its_season_is_an_estimate(self):
        est = next(r for r in recordsmod.load_records(ROOT) if facets.season_estimated(r))
        stated = next(r for r in recordsmod.load_records(ROOT) if not facets.season_estimated(r))
        self.assertIn('data-estimate="yes"', str(home.entry(est)))
        self.assertNotIn("data-estimate", str(home.entry(stated)))

    def test_the_script_reads_the_checkbox_and_writes_it_in_the_address(self):
        js = read(WEB, "assets", "app.js")
        self.assertIn("if (s.month && s.stated && d.estimate) return false;", js)
        self.assertIn("if (s.month && s.stated) p.set('stated', '1');", js)
        self.assertIn("estimate: d.estimate === 'yes'", js)

    @unittest.skipUnless(NODE, "node is not installed")
    def test_with_stated_on_estimated_rows_leave_the_month_and_the_counts_follow(self):
        def row(i, months, estimate):
            return {"id": f"t{i}", "search": ["  ", "  ", "  ", "  "], "where": [], "km": 100.0, "time": "week",
                    "months": [str(m) for m in months], "estimate": estimate, "terrain": [], "kind": "trail", "walking": "",
                    "shape": "", "gpx": "none"}
        rows = [row(1, [7], True), row(2, [7], False), row(3, [7, 8], False), row(4, [8], True)]
        off = run_counts(rows, state(month="7"))
        on = run_counts(rows, state(month="7", stated=True))
        self.assertEqual((off["total"], off["month"]["7"], off["month"]["8"]), (3, 3, 2))
        self.assertEqual((on["total"], on["month"]["7"], on["month"]["8"]), (2, 2, 1))
        # with no month chosen it does nothing
        self.assertEqual(run_counts(rows, state(stated=True))["total"], 4)
        # and the shown number is the rows that pass
        prog = facet_count_source() + """
var input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
input.s.max = Infinity;
process.stdout.write(JSON.stringify(input.rows.filter(function (d) { return FacetCount.passes(d, input.s, ''); }).length));
"""
        out = subprocess.run([NODE, "-e", prog], input=json.dumps({"rows": rows, "s": state(month="7", stated=True)}),
                             capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(out.stdout), on["total"])

    @unittest.skipUnless(NODE, "node is not installed")
    def test_on_the_real_trails_the_counts_leave_out_exactly_the_estimates(self):
        recs = recordsmod.load_records(ROOT)
        rows = rows_of(home.render(recs, SITE, ROOT))
        for month in (1, 7):
            c = run_counts(rows, state(month=str(month), stated=True))
            want = sum(1 for r in recs if month in facets.months(r) and not facets.season_estimated(r))
            self.assertEqual(c["total"], want)
            self.assertEqual(c["month"][str(month)], want)


if __name__ == "__main__":
    unittest.main()
