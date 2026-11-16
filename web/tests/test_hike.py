"""Tests for the hiker's part of the site: the [hike] facts on a trail page, the
"About this data" part, the words on the browsing surfaces, and the home page's
collections (olt/hike.py, olt/browse.py, olt/trail.py, olt/home.py).

These render fixtures; they do not need the built site.
"""
import copy
import html
import os
import re
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from olt import browse, hike, home, site, trail, words  # noqa: E402
from test_pages import sample_record  # noqa: E402

GH = site.Site("N", "T", repo_url="https://github.com/o/r")

FULL_HIKE = {
    "summary": "A long walk along the crest of the Example Range. It crosses three passes. Water is scarce in Mt. Dry country.",
    "official_url": "https://trail.example/",
    "start": "South Gate, Arizona",
    "end": "North Gate, Utah",
    "shape": "point-to-point",
    "days": [150, 210],
    "season": "March to October",
    "high_point": "Example Peak",
    "high_point_m": 2025,
    "terrain": ["forest", "alpine"],
    "permit": "A permit is needed for the national park section",
    "unfinished": "Forty miles are still on roads",
    "checked": "2026-11-13",
    "source": [{"url": "https://trail.example/facts", "publisher": "Example Trail Association",
                "facts": ["start", "end", "days", "season"]}],
}


def with_line(rec):
    """A fixture record with a track and its downloads, so the download panel is drawn."""
    rec = copy.deepcopy(rec)
    rec["source"].update({"status": "verified", "licence": "CC-BY-4.0", "attribution": "Example Trail Association (CC BY 4.0)",
                          "line_source": "Example Trail Association", "line_file": "line.geojson",
                          "line_absent_reason": ""})
    rec["verification"] = {"verified": True, "date": "2026-11-10", "measured_km": 60.0,
                           "difference_percent": -40.0, "parts": 3, "note": "Only part is built."}
    rec["source"]["length_gap_note"] = "The trail is not finished."
    rec["derived"].update({"has_line": True, "status": "included", "files": {"line": "x/line.geojson"},
                           "downloads": [{"role": "main", "format": "GPX", "file": "x.gpx", "bytes": 1000},
                                         {"role": "main", "format": "GeoJSON", "file": "x.geojson", "bytes": 3000}]})
    return rec


def render(rec, s=GH):
    return trail.render(rec, s)[2]


def top_part(body):
    """The hiker's part of a trail page: everything before "About this data"."""
    return body[:body.index('<details class="about-data"')]


def text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment)))


DATASET_WORDS = ("record", "Record", "tier", "Tier", "Held", "held", "Deferred", "Candidate", "wave",
                 "person-defined", "Person-defined", "track policy", "Track policy", "creator", "Creator",
                 "maker", "listing", "Listing", "collection", "Collection", "Ways in", "trails and routes",
                 "Trails and routes", "record only", "source status", "Source status", "verification",
                 "Verification", "line", "Line", "Regions", "entry")


class FormatTest(unittest.TestCase):
    def test_days(self):
        cases = {(4, 6): "4 to 6 days", (1, 1): "1 day", (5, 5): "5 days", (10, 14): "10 to 14 days",
                 (14, 21): "2 to 3 weeks", (20, 35): "3 to 5 weeks", (21, 21): "about 3 weeks",
                 (150, 210): "5 to 7 months", (40, 70): "1 to 2 months", (180, 180): "about 6 months"}
        for days, want in cases.items():
            self.assertEqual(words.fmt_days(list(days)), want, days)
        self.assertEqual(words.fmt_days(7), "7 days")
        self.assertEqual(words.fmt_days([]), "")
        self.assertEqual(words.fmt_days(None), "")

    def test_elevation_follows_the_unit_toggle(self):
        e = str(words.elevation(2025))
        # the same mi/km pair as lengths: feet first, and html[data-units="km"] puts metres first
        self.assertIn('<span class="len__km">2,025 m</span>', e)
        self.assertIn('<span class="len__mi">6,644 ft</span>', e)
        self.assertLess(e.index("len__mi"), e.index("len__km"))
        self.assertIn('class="len len--inline"', e)

    def test_first_sentence(self):
        self.assertEqual(hike.first_sentence("One. Two."), "One.")
        self.assertEqual(hike.first_sentence("Past Mt. Hood and St. Helens. Then on."), "Past Mt. Hood and St. Helens.")
        self.assertEqual(hike.first_sentence("By J. Smith in 1970. More."), "By J. Smith in 1970.")
        self.assertEqual(hike.first_sentence("Only one"), "Only one")


class TrailPageTest(unittest.TestCase):
    def test_full_hike_table(self):
        rec = sample_record("X Trail")
        rec["hike"] = copy.deepcopy(FULL_HIKE)
        top = top_part(render(rec))
        t = text(top)
        self.assertIn("A long walk along the crest of the Example Range. It crosses three passes.", t)
        self.assertIn('href="https://trail.example/"', top)
        self.assertIn("Official site", t)
        for want in ("Time 5 to 7 months", "Season March to October", "Example Peak",
                     "6,644 ft 2,025 m", "Shape End to end. South Gate, Arizona to North Gate, Utah",
                     "Terrain Forest, Alpine", "Permits A permit is needed for the national park section.",
                     "Not finished. Forty miles are still on roads."):
            self.assertIn(want, t, want)
        self.assertNotIn("Estimated from the length", t)  # a source states the time
        self.assertIn("Walking is not on file for this trail yet.", t)
        # where the facts were read: in "About this data", with the facts in plain words
        about = render(rec)[render(rec).index('<details class="about-data"'):]
        self.assertIn("Where the hiking facts come from", about)
        self.assertIn('href="https://trail.example/facts"', about)
        self.assertIn("For start, end, time and season", text(about))
        self.assertIn("Checked 2026-11-13.", text(about))
        self.assertTrue(trail.description(rec).startswith(
            "A trail of 62 miles (100 km) in Arizona, usually 5 to 7 months. A long walk along the crest"))

    def test_partial_hike_table(self):
        rec = sample_record("X Trail")
        rec["hike"] = {"shape": "loop", "start": "Lake Camp", "days": [4, 6], "checked": "2026-11-13"}
        top = top_part(render(rec))
        t = text(top)
        self.assertIn("Shape Loop. Starts and ends at Lake Camp", t)
        self.assertIn("Time 4 to 6 days", t)
        self.assertIn("Season, terrain and walking are not on file for this trail yet.", t)
        for absent in ("Season March", "High point", "Terrain Alpine", "Permits", "Not finished", "Official site"):
            self.assertNotIn(absent, t, absent)
        # no summary: the lede is built from the record
        self.assertIn("A trail of 62 mi 100 km in Arizona, United States.", t)
        about = render(rec)[render(rec).index('<details class="about-data"'):]
        self.assertIn("The record names no page for these facts.", about)

    def test_no_hike_table(self):
        rec = sample_record("X Trail")
        body = render(rec)
        top = top_part(body)
        t = text(top)
        self.assertIn("A trail of 62 mi 100 km in Arizona, United States.", t)
        self.assertIn("Length", t)
        self.assertIn("Where Arizona , United States", t)
        # every trail has a time: here estimated from its 100 km, and labelled so
        self.assertIn("Time About 4 to 5 days Estimated from the length, at 12 to 19 mi 20 to 30 km a day.", t)
        self.assertIn("Season, terrain and walking are not on file for this trail yet.", t)
        self.assertNotIn("Where the hiking facts come from", body)
        # no track: the page says so plainly and points at the source
        self.assertIn("No GPX here", t)
        self.assertIn("GPX Not here, see the official site", t)
        self.assertIn('href="#track"', top)
        self.assertIn('id="track"', top)

    def test_top_of_page_uses_plain_words(self):
        for hike_table in (None, FULL_HIKE):
            for rec in (sample_record("X Trail"), with_line(sample_record("X Trail"))):
                rec = copy.deepcopy(rec)
                rec["wave"] = "held"
                rec["tier"] = "deferred"
                if hike_table:
                    rec["hike"] = copy.deepcopy(hike_table)
                t = text(top_part(render(rec)))
                for word in DATASET_WORDS:
                    self.assertNotRegex(t, rf"\b{word}", word)

    def test_about_this_data_is_collapsed_and_complete(self):
        rec = with_line(sample_record("X Trail"))
        body = render(rec)
        about = body[body.index('<details class="about-data"'):]
        self.assertTrue(about.startswith('<details class="about-data" id="about-data">'))  # closed by default
        for part in ('id="record-title"', 'id="verify-title"', 'id="source-title"', 'id="osm-title"',
                     'id="logo-title"', 'id="links-title"', 'id="correct-title"', '<details class="rawrecord">'):
            self.assertIn(part, about, part)
            self.assertNotIn(part, top_part(body), part)

    def test_credit_licence_and_partial_warning_stay_in_view(self):
        rec = with_line(sample_record("X Trail"))
        top = top_part(render(rec))
        # the credit and licence beside the downloads, and on the map's caption
        panel = top[top.index('id="download"'):]
        self.assertIn('id="credit-text">Example Trail Association (CC BY 4.0)<', panel)
        self.assertIn('Licence: <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>', panel)
        self.assertLess(panel.index('<ul class="downloads">'), panel.index('class="credit"'))
        caption = top[top.index('<figcaption class="mapfig__caption">'):]
        self.assertIn("Credit: Example Trail Association (CC BY 4.0).", caption)
        # the partial warning above the buttons, and in the glance
        self.assertLess(panel.index("notice--partial"), panel.index('<ul class="downloads">'))
        self.assertIn("Partial GPX to download here", top)
        self.assertIn("Track measures 37.3 mi 60.0 km of 62 mi 100 km published", text(top))

    def test_report_a_problem_stays_in_view(self):
        top = top_part(render(sample_record("X Trail")))
        self.assertIn('>Report a problem</a>', top)
        self.assertIn("template=correction.yml", top)
        self.assertIn("Not for navigation", top)
        # without a repository there is nothing to link
        self.assertNotIn("Report a problem", top_part(render(sample_record("X Trail"), site.Site("N", "T"))))


def fake(i, km=100, **kw):
    rec = sample_record(f"T{i}")
    rec["id"] = f"t{i}"
    rec["length_km"] = km
    rec["derived"] = dict(rec["derived"])
    for k, v in kw.items():
        if k == "hike":
            rec["hike"] = v
        elif k == "tier":
            rec["tier"] = v
        elif k == "line":
            rec["derived"]["has_line"] = v
        elif k == "regions":
            rec["regions"] = v
        elif k == "country":
            rec["country"] = v
    return rec


def by_key(key):
    return browse.by_key(key)


class ListTest(unittest.TestCase):
    def test_each_rule(self):
        route = fake(1)
        route["derived"]["kind"] = "route"
        cases = {
            "national-scenic-trails": (fake(1, tier="national"), fake(2)),
            "routes": (route, fake(2)),
            "longest": (fake(1, km=1609.35), fake(2, km=1609.3)),
            "under-100-miles": (fake(1, km=160.9), fake(2, km=161)),
            # by Time: stated, or estimated from the length
            "a-week-or-less": (fake(1, hike={"days": [4, 7]}), fake(2, hike={"days": [20, 35]})),
            "one-to-two-weeks": (fake(1, km=250), fake(2, km=100)),
            "loops": (fake(1, hike={"shape": "loop"}), fake(2, hike={"shape": "point-to-point"})),
            "with-gpx": (fake(1, line=True), fake(2)),
            "canada": (fake(1, regions=["ON"], country="CA"), fake(2)),
            "united-states": (fake(1), fake(2, regions=["ON"], country="CA")),
            "off-trail": (fake(1, hike={"travel": "some-cross-country"}), fake(2, hike={"travel": "trail-and-road"})),
            "terrain-desert": (fake(1, hike={"terrain": ["desert"]}), fake(2, hike={"terrain": ["forest"]})),
        }
        for key, (inside, outside) in cases.items():
            lst = by_key(key)
            self.assertTrue(lst.test(inside), key)
            self.assertFalse(lst.test(outside), key)
        self.assertTrue(by_key("a-week-or-less").test(fake(3, km=100)))  # 4 to 5 days, estimated
        # a trail without [hike] is in no list that needs a [hike] fact
        for key in ("loops", "terrain-alpine", "off-trail"):
            self.assertFalse(by_key(key).test(fake(3)), key)

    def test_paths(self):
        self.assertEqual(browse.path(by_key("routes")), "/routes/")
        self.assertEqual(browse.path(by_key("loops")), "/lists/loops/")

    def test_threshold(self):
        self.assertFalse(browse.is_shown(browse.MIN_SIZE - 1, 100))
        self.assertTrue(browse.is_shown(browse.MIN_SIZE, 100))
        self.assertTrue(browse.is_shown(75, 100))
        self.assertFalse(browse.is_shown(76, 100))

    def test_thin_list_is_not_shown(self):
        # four loops among twenty trails: below MIN_SIZE, so no link and no page
        recs = [fake(i, hike={"shape": "loop"} if i < 4 else {"shape": "point-to-point"}) for i in range(20)]
        for i in range(5):
            recs[i]["tier"] = "national"
        keys = [lst.key for lst, _ in browse.shown(recs)]
        self.assertNotIn("loops", keys)
        self.assertIn("national-scenic-trails", keys)
        self.assertNotIn("united-states", keys)  # every one of them: nearly everything
        body = home.render(recs, GH)
        self.assertNotIn('href="/lists/loops/"', body)
        self.assertIn('href="/lists/national-scenic-trails/"', body)
        recs[4]["hike"] = {"shape": "loop"}
        self.assertIn("loops", [lst.key for lst, _ in browse.shown(recs)])

    def test_rules_name_no_trail(self):
        ids = [d for d in os.listdir(os.path.dirname(WEB)) if os.path.isfile(os.path.join(os.path.dirname(WEB), d, "trail.toml"))]
        for name in ("browse.py",):
            with open(os.path.join(WEB, "olt", name), encoding="utf-8") as f:
                source = f.read()
            for tid in ids:
                self.assertNotIn(f'"{tid}"', source, f"{name}: {tid}")


class ListRowTest(unittest.TestCase):
    def test_row_words_and_description(self):
        rec = fake(1)
        rec["wave"] = "held"
        rec["tier"] = "deferred"
        row = home.entry(rec)
        t = text(row)
        for word in DATASET_WORDS:
            self.assertNotRegex(t, rf"\b{word}", word)
        self.assertIn("See the official site", t)
        rec["hike"] = {"summary": "A fine walk. Long too.", "days": [4, 6]}
        t = text(home.entry(rec))
        self.assertIn("A fine walk.", t)
        self.assertNotIn("Long too.", t)
        self.assertIn("4 to 6 days", t)

    def test_route_rows_say_how_to_get_the_track(self):
        rec = fake(1)
        rec["derived"]["kind"] = "route"
        rec["kind"] = "route"
        rec["route"] = {"creator": "A Person", "line_policy": "sold"}
        rec["guide"] = []
        self.assertIn("Sold by its author", text(home.entry(rec)))
        self.assertIn("Route by A Person", text(home.entry(rec)))
        self.assertIn('<a class="tag tag--route" href="/routes/">Route</a>', home.entry(rec))
        self.assertNotRegex(text(home.entry(rec)), r"\b(creator|maker|person-defined)\b")


if __name__ == "__main__":
    unittest.main()
