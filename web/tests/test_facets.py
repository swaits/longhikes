"""Tests for the site's taxonomy and vocabulary (olt/facets.py and the pages that use it):
each attribute's name and values, the time estimate, the place grouping, filtering
with missing values and the coverage threshold, one word for one thing on every
browsing page, and the URLs the live site has always had.

The fixture tests need no built site; BuiltVocabularyTest builds it (as test_pages does).
"""
import html
import os
import re
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from olt import facets, home, records, trail, words  # noqa: E402
from test_hike import GH, fake, text, top_part  # noqa: E402

import builtsite  # noqa: E402

OUT = builtsite.OUT


def route(i=1, policy="sold", **kw):
    rec = fake(i, **kw)
    rec["kind"] = "route"
    rec["derived"]["kind"] = "route"
    rec["route"] = {"creator": "Andrew Skurka", "year": 2018, "line_policy": policy}
    rec["guide"] = [{"title": "Guide", "author": "Andrew Skurka", "access": "purchase",
                     "url": "https://guide.example/", "format": "book"}]
    return rec


class AttributeTest(unittest.TestCase):
    def test_names(self):
        self.assertEqual((facets.WHERE, facets.LENGTH, facets.TIME, facets.SEASON, facets.TERRAIN,
                          facets.KIND, facets.WALKING, facets.SHAPE, facets.GPX),
                         ("Where", "Length", "Time", "Season", "Terrain", "Kind", "Walking", "Shape", "GPX"))

    def test_values(self):
        self.assertEqual(list(facets.TERRAIN_VALUES), ["alpine", "forest", "desert", "coast", "prairie",
                                                       "canyon", "tundra", "lakes", "farmland"])
        self.assertEqual(facets.WALKING_VALUES, {"trail": "On trail", "trail-and-road": "Trail and road",
                                                 "some-cross-country": "Some cross-country",
                                                 "mostly-cross-country": "Mostly cross-country"})
        self.assertEqual(facets.SHAPES, {"point-to-point": "End to end", "loop": "Loop", "network": "Network"})
        self.assertEqual(facets.KINDS, {"trail": "Official trail", "route": "Route"})
        self.assertEqual([label for _, label, _ in facets.TIME_BANDS],
                         ["A week or less", "One to two weeks", "Two to four weeks", "One to three months",
                          "More than three months"])
        self.assertEqual(facets.ROUTE_DEFINITION,
                         "A route is a trail that a hiker worked out and published. No agency or association "
                         "looks after it as one trail, and there may be no signs for it.")

    def test_kind_and_route_line(self):
        self.assertEqual(facets.kind(fake(1)), "trail")
        self.assertEqual(facets.route_by(fake(1)), "")
        r = route()
        self.assertEqual(facets.kind(r), "route")
        self.assertEqual(facets.route_by(r), "Route by Andrew Skurka, 2018")
        del r["route"]["year"]
        self.assertEqual(facets.route_by(r), "Route by Andrew Skurka")

    def test_walking_is_not_kind(self):
        # a route on maintained trail says so; an official trail can have road walks
        r = route(hike={"travel": "trail"})
        self.assertEqual(facets.walking(r), "trail")
        t = fake(2, hike={"travel": "trail-and-road"})
        self.assertEqual(facets.kind(t), "trail")
        self.assertEqual(facets.walking(t), "trail-and-road")
        page = text(top_part(trail.render(r, GH)[2]))
        self.assertIn("Walking On trail", page)
        self.assertIn("Route by Andrew Skurka, 2018", page)
        self.assertIn("What is a route?", page)
        self.assertIn(facets.ROUTE_DEFINITION, page)

    def test_gpx_status(self):
        cases = [(fake(1), "elsewhere"), (route(policy="open"), "free"), (route(policy="sold"), "sold"),
                 (route(policy="withheld"), "unpublished"), (route(policy="unclear"), "elsewhere")]
        for rec, want in cases:
            self.assertEqual(facets.gpx(rec), want, rec.get("route"))
        from test_hike import with_line
        partial = with_line(fake(1))
        self.assertEqual(facets.gpx(partial), "partial")
        whole = with_line(fake(1))
        whole["verification"]["difference_percent"] = -2.0
        self.assertEqual(facets.gpx(whole), "here")
        self.assertEqual(set(facets.GPX_STATUS.values()),
                         {"GPX to download here", "Partial GPX to download here", "Free from its author",
                          "Sold by its author", "Not published", "Not here, see the official site"})

    def test_designation_badge_only_for_nst(self):
        self.assertIn("National Scenic Trail", home.entry(fake(1, tier="national")))
        for tier in ("regional", "short", "deferred", "candidate"):
            self.assertNotIn("tag--", home.entry(fake(1, tier=tier)), tier)


class TimeTest(unittest.TestCase):
    def test_stated(self):
        rec = fake(1, hike={"days": [150, 210]})
        self.assertEqual(facets.time_days(rec), (150, 210, False))
        self.assertEqual(facets.time_text(rec), "5 to 7 months")
        self.assertEqual(facets.estimate_note(rec), "")
        self.assertEqual(facets.time_band(rec), "long")

    def test_estimate_from_length(self):
        rec = fake(1, km=300)  # 300 km at 20 to 30 km a day: 10 to 15 days
        self.assertEqual(facets.time_days(rec), (10, 15, True))
        self.assertEqual(facets.time_text(rec), "About 1 to 2 weeks")
        note = facets.estimate_note(rec)  # miles first: both in the HTML, CSS orders them
        self.assertTrue(note.startswith("Estimated from the length, at "))
        self.assertLess(note.index('<span class="len__mi">12 to 19 mi</span>'),
                        note.index('<span class="len__km">20 to 30 km</span>'))
        self.assertTrue(note.endswith(" a day."))
        self.assertEqual(facets.time_band(rec), "two-weeks")
        # cross-country is slower: 12 to 20 km a day
        rec = fake(2, km=300, hike={"travel": "mostly-cross-country"})
        self.assertEqual(facets.time_days(rec), (15, 25, True))
        self.assertIn("12 to 20 km", facets.estimate_note(rec))
        self.assertIn("7 to 12 mi", facets.estimate_note(rec))
        self.assertEqual(facets.time_band(rec), "month")

    def test_every_trail_has_a_time_and_its_label(self):
        for rec in records.load_records(ROOT):
            lo, hi, est = facets.time_days(rec)
            self.assertTrue(0 < lo <= hi, rec["id"])
            self.assertIn(facets.time_band(rec), facets.TIME_LABEL, rec["id"])
            self.assertEqual(bool(facets.estimate_note(rec)), est, rec["id"])
        row = text(home.entry(fake(1, km=300)))
        self.assertIn("About 1 to 2 weeks estimate", row)
        self.assertNotIn("estimate", text(home.entry(fake(1, hike={"days": [4, 6]}))))

    def test_bands(self):
        self.assertEqual(facets.time_band(fake(1, hike={"days": [5, 8]})), "week")  # middle 6.5 days
        self.assertEqual(facets.time_band(fake(1, hike={"days": [7, 21]})), "two-weeks")
        self.assertEqual(facets.time_band(fake(1, hike={"days": [20, 35]})), "month")


class PlaceTest(unittest.TestCase):
    def test_every_code_in_exactly_one_group(self):
        keys = [k for _, _, ks in facets.PLACE_GROUPS for k in ks]
        self.assertEqual(len(keys), len(set(keys)))
        every = {f"US-{c}" for c in words.US_STATES} | {f"CA-{c}" for c in words.CA_PROVINCES}
        self.assertEqual(set(keys), every)

    def test_every_code_the_records_use(self):
        for rec in records.load_records(ROOT):
            keys = facets.place_keys(rec)
            self.assertTrue(keys, rec["id"])
            for key in keys:
                self.assertTrue(key in facets.GROUP_OF or key == facets.ACROSS_CANADA, f"{rec['id']}: {key}")
            self.assertTrue(facets.place_groups(rec), rec["id"])

    def test_tokens(self):
        rec = fake(1, regions=["AZ", "NM"])
        self.assertEqual(facets.where_tokens(rec), ["US", "US-AZ", "US-NM", "g:southwest"])
        across = fake(2, regions=[words.ALL_CANADA], country="CA")
        self.assertEqual(facets.place_keys(across), ["CA-*"])
        self.assertEqual(set(facets.place_groups(across)),
                         {"north", "western-canada", "central-canada", "atlantic-canada"})
        # a US trail that names a province is in that province's group
        ect = fake(3, regions=["ME", "QC", "NB"])
        self.assertEqual(facets.place_keys(ect), ["US-ME", "CA-QC", "CA-NB"])
        self.assertIn("atlantic-canada", facets.place_groups(ect))

    def test_breadcrumb_by_place(self):
        body = trail.render(fake(1, regions=["CO"]), GH)[2]
        crumbs = body[body.index('<nav class="breadcrumb"'):body.index("</nav>")]
        self.assertIn('<a href="/regions/">Places</a>', crumbs)
        self.assertIn('<a href="/regions/mountain-west/">Mountain West</a>', crumbs)
        self.assertIn('<a href="/regions/us-co/">Colorado</a>', crumbs)


def est_hike(**kw):
    h = {"season": "June to September", "months": [6, 7, 8, 9], "season_basis": "estimate",
         "season_method": "Judged from the climate at the trail's elevation and from similar trails. "
                          "Snow keeps the high passes closed until June. Confidence: medium."}
    h.update(kw)
    return h


class SeasonTextTest(unittest.TestCase):
    def test_an_estimated_season_reads_about_and_has_a_note(self):
        rec = fake(1, hike=est_hike())
        self.assertTrue(facets.season_estimated(rec))
        self.assertEqual(facets.season_text(rec), "About June to September")
        note = facets.season_note(rec)
        for want in ("No page states a season", "estimated from the climate at the trail's elevation and from "
                     "similar trails", "Snow keeps the high passes closed until June.", "Confidence: medium.",
                     "This is the usual window, not a closure."):
            self.assertIn(want, note)
        self.assertNotIn("walk it outside", note)
        self.assertNotIn("Judged from", note)  # the standard lead is said once, in the note's own words

    def test_a_page_that_contradicts_itself_is_said_once_not_twice(self):
        rec = fake(1, hike=est_hike(season_method=(
            "A page was found but it contradicts itself, so no page is relied on. The season was estimated "
            "from the climate and similar trails: snow lies until June. Confidence: medium.")))
        note = facets.season_note(rec)
        self.assertTrue(note.startswith("No page states a season. A page was found but it contradicts itself"), note)
        self.assertEqual(note.count("estimated from the climate"), 1)
        self.assertTrue(note.endswith("This is the usual window, not a closure."))

    def test_a_season_judged_from_pages_is_not_called_estimated_from_climate(self):
        judged = fake(1, hike=est_hike(season_basis="sources", season_method="The pages differ. Confidence: low."))
        est = fake(2, hike=est_hike())
        self.assertEqual(facets.season_unstated_clause([est, est, judged]),
                         "2 are estimated from the climate and similar trails and 1 is set by judgement from "
                         "pages that differ")
        self.assertEqual(facets.season_unstated_clause([judged]), "1 is set by judgement from pages that differ")
        self.assertEqual(facets.season_unstated_clause([est]), "1 is estimated from the climate and similar trails")
        self.assertEqual(facets.season_unstated_clause([]), "")

    def test_a_stated_season_is_unchanged_and_has_no_note(self):
        rec = fake(1, hike={"season": "June to September", "months": [6, 7, 8, 9], "season_basis": "primary"})
        self.assertFalse(facets.season_estimated(rec))
        self.assertEqual(facets.season_text(rec), "June to September")
        self.assertEqual(facets.season_note(rec), "")

    def test_an_estimated_all_year_season_reads_about_all_year(self):
        rec = fake(1, hike=est_hike(season="All year", months=list(range(1, 13))))
        self.assertEqual(facets.season_text(rec), "About all year")

    def test_it_is_not_estimated_without_a_basis_or_a_method(self):
        self.assertFalse(facets.season_estimated(fake(1, hike={"season": "May", "months": [5]})))
        self.assertFalse(facets.season_estimated(fake(1)))
        self.assertEqual(facets.season_kind(fake(1)), "")

    def test_a_season_judged_from_pages_that_differ_says_so(self):
        rec = fake(1, hike=est_hike(season_basis="sources", season_method=(
            "The pages differ: one gives May to October and one gives June to November. It was set by "
            "judgement from both and from the climate. Confidence: medium.")))
        self.assertTrue(facets.season_estimated(rec))
        self.assertEqual(facets.season_kind(rec), "judged")
        self.assertEqual(facets.season_text(rec), "About June to September")
        note = facets.season_note(rec)
        self.assertIn("No one page states this season.", note)
        self.assertIn("The pages differ", note)
        self.assertNotIn("estimated from the climate at the trail's elevation", note)
        self.assertIn("It is a judgement", facets.season_basis_line(rec))

    def test_the_basis_line_gives_the_method_for_an_estimate(self):
        line = facets.season_basis_line(fake(1, hike=est_hike()))
        self.assertTrue(line.endswith("Confidence: medium. No page states a season."), line)


class MissingValuesTest(unittest.TestCase):
    def recs(self, n_with, n_without):
        return ([fake(i, hike={"months": [7, 8], "season": "July and August", "terrain": ["alpine"]})
                 for i in range(n_with)] + [fake(100 + i) for i in range(n_without)])

    def test_coverage_threshold(self):
        self.assertTrue(facets.offered(self.recs(4, 8), "season"))   # one third: offered
        self.assertFalse(facets.offered(self.recs(3, 8), "season"))  # less: not offered
        form = home.finder_form(self.recs(3, 8))
        self.assertNotIn('name="month"', form)
        self.assertNotIn('name="terrain"', form)
        form = home.finder_form(self.recs(4, 8))
        self.assertIn('name="month"', form)
        self.assertIn('name="terrain"', form)

    def test_missing_count_is_said(self):
        # the generic mechanism, shown with terrain: no real trail lacks a season any more
        form = home.finder_form(self.recs(10, 12))
        self.assertIn('data-missing="terrain" hidden>12 trails have no terrain on file.', form)
        self.assertEqual(facets.missing_text(1, "terrain"), "1 trail has no terrain on file.")
        self.assertEqual(facets.missing_text(0, "terrain"), "")
        # full coverage: no note
        self.assertNotIn('data-missing="terrain"', home.finder_form(self.recs(5, 0)))

    def test_rows_without_a_value_carry_none(self):
        row = home.entry(fake(1))
        self.assertIn('data-terrain=""', row)
        row = home.entry(fake(1, hike={"months": [7, 8, 9]}))
        self.assertIn('data-months="7 8 9"', row)

    def test_every_real_trail_has_months(self):
        for rec in records.load_records(ROOT):
            self.assertTrue(facets.months(rec), rec["id"])

    def test_script_leaves_out_missing_values(self):
        with open(os.path.join(WEB, "assets", "app.js"), encoding="utf-8") as f:
            js = f.read()
        self.assertIn("if (skip !== 'month' && s.month && !has(d.months, s.month)) return false;", js)
        self.assertIn("note.hidden = !on[note.dataset.missing]", js)

    def test_clearing_returns_the_lengths_to_any(self):
        # A form's reset picks the option marked as default, or else the first one.
        # "Any" is the last option of the longest-length list, so both the page and
        # the script (which rebuilds the lists in the reader's units) must mark it;
        # in the shortest-length list it is first.
        # (lengths that differ: a Length filter is written only where it can narrow the trails)
        form = home.finder_form(self.recs(3, 8) + [fake(300, km=900)])
        longest = re.search(r'<select[^>]* id="max"[^>]*>(.*?)</select>', form, re.S).group(1)
        self.assertEqual(re.findall(r'<option value="([^"]*)" selected', longest), [""])
        shortest = re.search(r'<select[^>]* id="min"[^>]*>(.*?)</select>', form, re.S).group(1)
        self.assertTrue(shortest.startswith('<option value="">Any</option>'))
        with open(os.path.join(WEB, "assets", "app.js"), encoding="utf-8") as f:
            js = f.read()
        self.assertIn("if (p.o.def) opt.defaultSelected = true;", js)
        self.assertIn("{ value: '', label: 'Any', counted: false, group: '', def: true }", js)


# Words that must not appear on a browsing page (home, places, lists, Routes, and a
# trail page above "About this data"). Record text can say what it likes; these are
# the site's own words, so they are checked in the site's own markup: headings,
# labels, legends, buttons, counts, empty states, alt text and descriptions.
BANNED = (r"\btrails and routes\b", r"\bperson-defined\b", r"\bways in\b", r"\bcollections?\b",
          r"\brecord only\b", r"\bregions\b", r"\btrack polic(y|ies)\b", r"\btier\b", r"\bheld\b",
          r"\bsource status\b", r"\bverification\b", r"\blisting\b", r"\bcreator\b", r"\bmaker\b",
          r"\brecords?\b", r"\bentry\b", r"\bdesignated trail\b")


def site_words(doc):
    """The text the site writes on a page, without the trails' own text: rows' descriptions,
    names, summaries and the record-sourced notes are dropped, and so is "About this data"."""
    if '<details class="about-data"' in doc:
        doc = doc[:doc.index('<details class="about-data"')]
    doc = doc[doc.index('<main id="main">'):]
    for cls in ("entry__desc", "entry__name", "trail-lede", "trail-summary", "titleblock__sub", "entry__partial",
                "note", "record-text", "map__reason", "glance__warn", "shelf__items", "onward__list"):
        doc = re.sub(rf'<(\w+) class="{cls}"[^>]*>.*?</\1>', " ", doc, flags=re.S)
    doc = re.sub(r"<dd>.*?</dd>", " ", doc, flags=re.S)  # glance values are the trail's facts
    doc = re.sub(r'<div class="notice notice--partial">.*?</div>', " ", doc, flags=re.S)  # quotes the record
    doc = re.sub(r'<li class="guide">.*?</li>', " ", doc, flags=re.S)
    doc = re.sub(r'<a [^>]*href="(?:https?:|/trails/)[^"]*"[^>]*>.*?</a>', " ", doc, flags=re.S)
    attrs = " ".join(re.findall(r'(?:alt|aria-label|title|placeholder|content)="([^"]*)"', doc))
    return html.unescape(re.sub(r"<[^>]+>", " ", doc) + " " + attrs)


class BuiltVocabularyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        builtsite.ensure()

    def read(self, rel):
        with open(os.path.join(OUT, *rel.split("/")), encoding="utf-8") as f:
            return f.read()

    def browsing_pages(self):
        rels = ["index.html", "regions/index.html", "lists/index.html", "routes/index.html", "404.html"]
        for d in ("regions", "lists", "parks", "ranges", "wilderness"):
            if not os.path.isdir(os.path.join(OUT, d)):
                continue
            for name in sorted(os.listdir(os.path.join(OUT, d))):
                if os.path.isfile(os.path.join(OUT, d, name, "index.html")):
                    rels.append(f"{d}/{name}/index.html")
        rels += [f"trails/{t}/index.html" for t in sorted(os.listdir(os.path.join(OUT, "trails")))
                 if os.path.isfile(os.path.join(OUT, "trails", t, "index.html"))]
        return rels

    def test_no_banned_word_on_a_browsing_page(self):
        bad = []
        for rel in self.browsing_pages():
            words_ = site_words(self.read(rel))
            for pattern in BANNED:
                m = re.search(pattern, words_, re.I)
                if m:
                    bad.append((rel, m.group(0), words_[max(0, m.start() - 40):m.end() + 40]))
        self.maxDiff = None
        self.assertEqual(bad[:40], [])

    def test_no_page_says_only_some_trails_have_a_season(self):
        found = []
        for dirpath, _dirs, files in os.walk(OUT):
            for name in files:
                if name.endswith(".html") and "changelog" not in dirpath:  # its old entries say what was
                    path = os.path.join(dirpath, name)
                    with open(path, encoding="utf-8") as f:
                        doc = f.read()
                    for phrase in ("Only some trails have a season", "season on file", "Not on file</td>",
                                   "data-unseasoned", "Show them"):
                        if phrase in doc:
                            found.append((os.path.relpath(path, OUT), phrase))
        self.assertEqual(found[:10], [])

    def test_an_estimated_season_reads_about_on_its_page_and_a_stated_one_does_not(self):
        est = [r for r in records.load_records(ROOT) if facets.season_estimated(r)]
        stated = [r for r in records.load_records(ROOT) if not facets.season_estimated(r)]
        self.assertEqual(len(est) + len(stated), 223)
        for rec in est[:10]:
            doc = self.read(f"trails/{rec['id']}/index.html")
            self.assertIn(facets.season_text(rec), html.unescape(doc), rec["id"])
            self.assertIn("This is the usual window, not a closure.", html.unescape(doc), rec["id"])
            self.assertNotIn("outside these months", html.unescape(doc), rec["id"])
        for rec in stated[:10]:
            self.assertNotIn("This is the usual window", html.unescape(self.read(f"trails/{rec['id']}/index.html")))

    def test_navigation_has_four_sections_and_saved(self):
        doc = self.read("index.html")
        nav = re.search(r'<nav class="site-nav" aria-label="Main"><ul class="nav">(.*?)</ul></nav>', doc).group(1)
        self.assertEqual(re.findall(r'<li><a href="[^"]*"[^>]*>([^<]+)</a>', nav), ["Trails", "Places", "Lists", "About"])
        self.assertIn('<li class="nav__saved js-only"><a href="/saved/">', nav)

    def test_one_count_noun(self):
        doc = self.read("index.html")
        n = len(re.findall(r'<li class="entry" ', doc))
        self.assertEqual(n, len(records.load_records(ROOT)))
        self.assertIn(f"<strong>{n}</strong> trails</p>", doc)
        self.assertNotIn(f"{n} of {n}", doc)
        self.assertIn(f"{n} trails. Narrow them", doc)

    def test_route_badges_link_to_the_routes_list(self):
        for rel in ("index.html", "routes/index.html"):
            doc = self.read(rel)
            for m in re.finditer(r'<(\w+) class="tag tag--route"([^>]*)>Route<', doc):
                self.assertEqual((m.group(1), m.group(2)), ("a", ' href="/routes/"'), rel)

    def test_old_urls_still_built(self):
        recs = records.load_records(ROOT)
        paths = ["index.html", "regions/index.html", "routes/index.html", "about/index.html", "data/index.html",
                 "data/schema/index.html", "data/changelog/index.html", "sources/index.html",
                 "logos/index.html", "404.html", "data/trails.csv", "data/trails.json", "data/index.geojson",
                 "data/overview.geojson", "data/all-gpx.zip", "data/all-geojson.zip", "licences/LICENSE"]
        paths += [f"trails/{r['id']}/index.html" for r in recs]
        paths += [f"trails/{r['id']}/trail.toml" for r in recs]
        for key in {k for r in recs for k in facets.place_keys(r) if k != facets.ACROSS_CANADA}:
            paths.append(f"regions/{key.lower()}/index.html")
        for rel in paths:
            self.assertTrue(os.path.isfile(os.path.join(OUT, *rel.split("/"))), rel)

    def test_about_holds_the_dataset_terms(self):
        doc = self.read("about/index.html")
        for want in ('id="how-trails-are-chosen"', "Held", "Candidate", "Track policy",
                     'href="/data/"', 'href="/sources/"', 'href="/logos/"', 'id="correct-or-add"'):
            self.assertIn(want, doc, want)
        for rel in ("data/index.html", "sources/index.html", "logos/index.html", "data/schema/index.html"):
            self.assertIn('<li><a href="/about/">About</a></li>', self.read(rel), rel)

    def test_trail_page_ways_onward(self):
        doc = self.read("trails/sierra-high-route/index.html")
        foot = doc[doc.index('<nav class="onward"'):doc.index('<details class="about-data"')]
        self.assertIn("More in California", foot)
        doc = self.read("trails/kings-canyon-high-basin-route/index.html")
        self.assertIn("More routes by Andrew Skurka", doc)
        self.assertIn('href="/trails/yosemite-high-route/"', doc[doc.index('<nav class="onward"'):])


if __name__ == "__main__":
    unittest.main()
