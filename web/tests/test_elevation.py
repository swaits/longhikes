"""Tests for the computed elevation facts (olt/elevation.py): the At a glance
rows, the profile and its part breaks, the caveats, unit switching, the climb
sort, the model credit, and the Routes list dropping its repetition.

These render fixtures; they do not need the built site.
"""
import copy
import html
import os
import re
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from olt import docs, elevation, home, records, regions, site, trail  # noqa: E402
from test_pages import sample_record  # noqa: E402

GH = site.Site("N", "T", repo_url="https://github.com/o/r")

SOURCE = {
    "model": "Example Model", "url": "https://model.example/",
    "attribution": "Example Model credit, as it gives it.",
    "zoom": 12, "ground_m_per_pixel_at_40n": 29.2, "sample_spacing_m": 30.0,
    "smoothing": "Moving average over 90 m of track; ascent and descent counted with a 5 m reversal threshold",
    "limits": "Computed from a public elevation model, not measured on the ground.",
    "method_version": 1, "computed": "2026-11-13",
}


def elev(**kw):
    """A small elevation.json in memory: one part, full coverage, south to north."""
    data = {
        "highest": {"m": 2000, "lat": 40.0, "lon": -105.0},
        "lowest": {"m": 500, "lat": 39.0, "lon": -105.5},
        "ascent_m": 3000, "descent_m": 2900,
        "track_km": 100.0, "published_km": 100, "coverage": 1.0,
        "parts": 1, "orientation": "south-to-north",
        "profile": [[0, 500], [50, 2000], [100, 800]],
        "source": copy.deepcopy(SOURCE),
    }
    data.update(kw)
    return data


def rec_with(data=None, hike_table=None):
    rec = sample_record("X Trail")
    rec["derived"]["elevation"] = data
    rec["derived"]["has_line"] = data is not None
    if data is not None:
        rec["source"]["line_file"] = "line.geojson"
        rec["derived"]["files"] = {"line": "x/line.geojson"}
    if hike_table:
        rec["hike"] = hike_table
    return rec


def render(rec):
    return trail.render(rec, GH)[2]


def text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment)))


def glance_of(body):
    return body[body.index('<section class="glance'):body.index("</section>", body.index('<section class="glance'))]


def top_part(body):
    return body[:body.index('<details class="about-data"')]


class GlanceTest(unittest.TestCase):
    def test_computed_rows_without_a_sourced_high_point(self):
        t = text(glance_of(render(rec_with(elev()))))
        self.assertIn("High point 2,000 m 6,562 ft Computed from the track.", t)
        self.assertIn("Low point 500 m 1,640 ft Computed from the track.", t)
        # descent within a few percent of the climb is not shown
        self.assertIn("Climb 3,000 m 9,843 ft Computed from the track, walking south to north.", t)
        self.assertNotIn("Descent", t)

    def test_descent_shown_when_it_differs(self):
        t = text(glance_of(render(rec_with(elev(descent_m=1000)))))
        self.assertIn("Descent: 1,000 m 3,281 ft", t)
        self.assertIn("walking south to north", t)
        self.assertFalse(elevation.show_descent(elev(ascent_m=1000, descent_m=951)))
        self.assertTrue(elevation.show_descent(elev(ascent_m=1000, descent_m=949)))

    def test_sourced_high_point_is_kept(self):
        rec = rec_with(elev(), {"high_point": "Example Peak", "high_point_m": 2025, "checked": "2026-11-13"})
        t = text(glance_of(render(rec)))
        self.assertIn("High point Example Peak 2,025 m 6,644 ft", t)
        self.assertNotIn("2,000 m", t)  # the computed highest does not replace it
        # the computed low point and climb still appear, marked as computed
        self.assertIn("Low point 500 m", t)
        self.assertIn("Climb 3,000 m", t)

    def test_sourced_name_without_an_elevation_stays_as_it_was(self):
        rec = rec_with(elev(), {"high_point": "Example Peak", "checked": "2026-11-13"})
        t = text(glance_of(render(rec)))
        self.assertIn("High point Example Peak", t)
        self.assertNotIn("2,000 m", t)

    def test_sea_level_low_point(self):
        data = elev(lowest={"m": 0, "lat": 43.0, "lon": -124.0})
        t = text(glance_of(render(rec_with(data))))
        self.assertIn("Low point 0 m 0 ft Sea level. Computed from the track.", t)
        self.assertIn("low point of sea level", elevation.summary_sentence(data))

    def test_loop_climb_has_no_direction(self):
        rec = rec_with(elev(), {"shape": "loop", "checked": "2026-11-13"})
        t = text(glance_of(render(rec)))
        self.assertIn("Climb 3,000 m 9,843 ft Computed from the track.", t)
        self.assertNotIn("walking south to north", text(top_part(render(rec))))


class CaveatTest(unittest.TestCase):
    def test_partial_coverage(self):
        for cov, shown in ((0.84, True), (0.85, False), (1.0, False)):
            data = elev(coverage=cov, track_km=cov * 100)
            t = text(top_part(render(rec_with(data))))
            if shown:
                self.assertIn("for the track only", t)
                self.assertIn(f"about {round(cov * 100)}% of the published length", t)
            else:
                self.assertNotIn("for the track only", t, cov)
        self.assertEqual(elevation.coverage_percent(elev(coverage=0.002)), "less than 1%")

    def test_over_coverage(self):
        for cov, shown in ((1.16, True), (1.15, False)):
            data = elev(coverage=cov, track_km=cov * 100)
            t = text(top_part(render(rec_with(data))))
            if shown:
                self.assertIn("the climb is overstated", t)
                self.assertIn("side trails or alternates", t)
            else:
                self.assertNotIn("overstated", t, cov)

    def test_many_parts_draw_no_profile(self):
        for parts, drawn in ((elevation.PROFILE_MAX_PARTS, True), (elevation.PROFILE_MAX_PARTS + 1, False)):
            body = render(rec_with(elev(parts=parts)))
            self.assertEqual("elev-profile__line" in body, drawn, parts)
            if not drawn:
                self.assertIn("No profile is drawn", text(body))
                self.assertIn(f"{parts} in the elevation sampling", text(body))
                # the figures are still there
                self.assertIn("Climb 3,000 m", text(glance_of(body)))


class ProfileTest(unittest.TestCase):
    # two parts: the point at 50 km ends the first, the next at 50 km starts the second
    PROFILE = [[0, 500], [25, 900], [50, 700], [50, 1200], [75, 2000], [100, 800]]

    def test_breaks_at_part_boundaries(self):
        segs = elevation.segments(self.PROFILE, [50])
        self.assertEqual([[p[0] for p in s] for s in segs], [[0, 25, 50], [50, 75, 100]])
        data = elev(parts=2, part_starts_km=[50], profile=self.PROFILE)
        svg = str(elevation.profile_svg(data))
        path = re.search(r'<path class="elev-profile__line" d="([^"]*)"', svg).group(1)
        self.assertEqual(path.count("M"), 2)  # one subpath per part, never joined
        self.assertIn("The line breaks where the track does", text(render(rec_with(data))))

    def test_repeated_part_starts_each_break(self):
        profile = [[0, 1], [10, 2], [10, 3], [10, 4], [20, 5]]
        self.assertEqual(len(elevation.segments(profile, [10, 10])), 3)

    def test_axes_in_both_units(self):
        svg = str(elevation.profile_svg(elev()))
        km = svg[svg.index('<g class="len__km">'):svg.index('<g class="len__mi">')]
        mi = svg[svg.index('<g class="len__mi">'):]
        self.assertIn("Distance along the track (km)", km)
        self.assertIn("Elevation (m)", km)
        self.assertIn("2,000", km)  # a metre tick reaches the high point
        self.assertIn("Distance along the track (mi)", mi)
        self.assertIn("Elevation (ft)", mi)
        self.assertNotIn("style=", svg)
        # CSS shows one system, by the same data-units preference as lengths
        with open(os.path.join(WEB, "assets", "style.css"), encoding="utf-8") as f:
            css = f.read()
        self.assertIn(".elev-profile .len__mi { display: none; }", css)
        self.assertIn(':root[data-units="mi"] .elev-profile .len__mi { display: inline; }', css)
        self.assertIn(':root[data-units="mi"] .elev-profile .len__km { display: none; }', css)

    def test_text_alternative_states_the_facts(self):
        svg = str(elevation.profile_svg(elev()))
        label = html.unescape(re.search(r'aria-label="([^"]*)"', svg).group(1))
        for want in ("3,000 m (9,843 ft)", "100.0 km (62 mi)", "500 m (1,640 ft)",
                     "2,000 m (6,562 ft)", "walking south to north"):
            self.assertIn(want, label, want)
        # the same sentence is the visible caption
        self.assertIn(label, text(render(rec_with(elev()))))

    def test_no_elevation_file_shows_nothing(self):
        body = render(rec_with(None))
        for absent in ("Elevation profile", "Low point", "Climb", 'id="elevation-data-title"',
                       'id="elevation-title"', "detail--with-profile"):
            self.assertNotIn(absent, body, absent)
        self.assertIn("At a glance", body)  # and the page is otherwise whole


class AboutTest(unittest.TestCase):
    def test_method_credit_and_every_value(self):
        data = elev(parts=2, part_starts_km=[50], profile=ProfileTest.PROFILE)
        body = render(rec_with(data))
        about = body[body.index('<details class="about-data"'):]
        t = text(about)
        self.assertIn('id="elevation-data-title"', about)
        for want in ("computed from the trail’s track and Example Model",
                     "A point was taken every 30 m along each part of the track",
                     "Example Model credit, as it gives it.",
                     "Highest point on the track 2,000 m", "At 40.00000, -105.00000",
                     "Lowest point on the track 500 m", "Total climb 3,000 m",
                     "Total descent 2,900 m", "Length sampled 100.0 km",
                     "Coverage 1.000", "Parts 2", "Part starts 50.0 km",
                     "Computed 2026-11-13",
                     "Computed from a public elevation model, not measured on the ground."):
            self.assertIn(want, t, want)
        self.assertIn('href="https://model.example/"', about)

    def test_model_credit_on_the_sources_page(self):
        _, _, body = docs.sources_page([rec_with(elev()), rec_with(None)], GH, ROOT)
        self.assertIn("Elevation model", body)
        self.assertIn("Example Model credit, as it gives it.", body)
        self.assertIn('href="https://model.example/"', body)


class CatalogueTest(unittest.TestCase):
    def test_climb_in_the_row_and_the_sort(self):
        row = home.entry(rec_with(elev()))
        self.assertIn('data-climb="3000"', row)
        self.assertIn("<dt>Climb</dt>", row)
        self.assertIn("3,000 m", text(row))
        self.assertIn("computed", text(row))
        row_none = home.entry(rec_with(None))
        self.assertIn('data-climb=""', row_none)
        self.assertNotIn("<dt>Climb</dt>", row_none)
        self.assertIn('<option value="climb">Most climb first</option>', home.SORT_SELECT)
        with open(os.path.join(WEB, "assets", "app.js"), encoding="utf-8") as f:
            js = f.read()
        self.assertIn("key === 'climb'", js)
        # a trail with no computed climb sorts last, not first
        self.assertIn("a.dataset.climb === '' ? -1", js)
        self.assertIn("return bc - ac", js)


class RoutesListTest(unittest.TestCase):
    def _route(self):
        rec = rec_with(None)
        rec["derived"]["kind"] = "route"
        rec["kind"] = "route"
        rec["route"] = {"creator": "A Person", "year": 1970, "line_policy": "sold"}
        rec["guide"] = []
        return rec

    def test_no_repetition_under_by_author_headings(self):
        rec = self._route()
        plain = home.entry(rec)
        self.assertIn("Route by A Person, 1970", text(plain))
        self.assertIn('<a class="tag tag--route" href="/routes/">Route</a>', plain)
        _, _, body, _ = regions.routes_page([rec], GH)
        self.assertIn("By A Person", text(body))
        self.assertNotIn("entry__by", body)
        self.assertNotIn("tag--route", body)


class LoaderTest(unittest.TestCase):
    def test_real_records(self):
        pct = records.load_record(ROOT, "pacific-crest")
        data = pct["derived"]["elevation"]
        self.assertIsNotNone(data)
        self.assertGreater(data["ascent_m"], 0)
        self.assertIn("Terrain Tiles", data["source"]["attribution"])
        none_rec = records.load_record(ROOT, "sierra-high-route")
        self.assertIsNone(none_rec["derived"]["elevation"])
        # elevation facts are derived, so they never appear as record fields
        self.assertNotIn("ascent_m", text(trail.raw_record(pct)))


if __name__ == "__main__":
    unittest.main()
