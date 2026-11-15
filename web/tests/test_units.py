"""Miles and feet come first, everywhere, until a reader chooses kilometres and metres.

These read the markup writers, the stylesheet and prefs.js; they do not need the built site.
"""
import os
import re
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from olt import browse, home, words  # noqa: E402
from test_hike import fake, render, top_part  # noqa: E402


def read(*parts):
    with open(os.path.join(WEB, *parts), encoding="utf-8") as f:
        return f.read()


class DefaultOrderTest(unittest.TestCase):
    def test_lengths_and_elevations_are_written_miles_and_feet_first(self):
        for html_ in (words.length(1287), words.length(1287, "stack"), words.length(2.0, measured=True),
                      words.elevation(2025)):
            self.assertLess(html_.index("len__mi"), html_.index("len__km"))

    def test_trail_page_at_a_glance_reads_miles_first(self):
        top = top_part(render(fake(1, km=100)))
        self.assertLess(top.index('<span class="len__mi">62 mi</span>'),
                        top.index('<span class="len__km">100 km</span>'))

    def test_list_row_reads_miles_first(self):
        row = home.entry(fake(1, km=100))
        self.assertLess(row.index('<span class="len__mi">62 mi</span>'),
                        row.index('<span class="len__km">100 km</span>'))
        self.assertIn('data-km="100"', row)  # sorting and filtering stay in kilometres

    def test_footer_switch_lists_miles_first_and_selects_it(self):
        src = read("olt", "layout.py")
        self.assertIn('value="mi" checked><span>mi and ft first</span>', src)
        self.assertLess(src.index("mi and ft first"), src.index("km and m first"))
        self.assertIn('value="mi" checked><span>mi</span>', home.UNITS_TOGGLE)
        self.assertLess(home.UNITS_TOGGLE.index(">mi<"), home.UNITS_TOGGLE.index(">km<"))


class StoredChoiceTest(unittest.TestCase):
    def test_prefs_js_knows_only_km_as_the_opt_in(self):
        js = read("assets", "prefs.js")
        self.assertIn("units === 'km'", js)
        self.assertIn("root.dataset.units = 'km'", js)
        self.assertNotIn("=== 'mi'", js)  # an old stored "mi" is simply miles

    def test_app_js_treats_no_value_as_miles(self):
        js = read("assets", "app.js")
        self.assertIn("root.dataset.units !== 'km'", js)
        self.assertIn("writePref('lh-units', value === 'km' ? 'km' : null)", js)

    def test_css_flips_on_km_and_never_on_mi(self):
        css = read("assets", "style.css")
        self.assertNotIn('data-units="mi"', css)
        self.assertIn(':root[data-units="km"] .len__km { order: -1; }', css)
        self.assertIn(':root[data-units="km"] .len--short .len__km { display: inline; }', css)
        self.assertIn(".len--short .len__km { display: none; }", css)
        self.assertIn(':root[data-units="km"] .list-head__scale .len__km { display: inline; }', css)
        self.assertIn(':root[data-units="km"] .loglen {', css)
        # the length strip's ticks sit at 100, 1,000 and 10,000 miles by default, kilometres when chosen
        self.assertIn("log(100 * 1.609344 / 50)", css)
        self.assertIn(':root[data-units="km"] .list-head__scale > span:nth-child(1) { inset-inline-start: 10.8%; }', css)

    def test_tick_positions_match_the_strip_scale(self):
        import math
        css = read("assets", "style.css")
        pos = lambda km: math.log(km / 50) / math.log(600) * 100
        for nth, mi in enumerate(home.SCALE_TICKS, 1):
            m = re.search(r'\.list-head__scale > span:nth-child\(%d\) \{ inset-inline-start: ([\d.]+)%%' % nth, css)
            self.assertAlmostEqual(float(m.group(1)), pos(mi * words.KM_PER_MI), delta=0.1)
            m = re.search(r':root\[data-units="km"\] \.list-head__scale > span:nth-child\(%d\) \{ inset-inline-start: ([\d.]+)%%' % nth, css)
            self.assertAlmostEqual(float(m.group(1)), pos(mi), delta=0.1)


class LengthListsTest(unittest.TestCase):
    def test_renamed_lists(self):
        under = browse.by_key("under-100-miles")
        self.assertEqual(under.title, "Under 100 miles")
        self.assertEqual(browse.path(under), "/lists/under-100-miles/")
        self.assertNotIn("under-100-km", [lst.key for lst in browse.LISTS])
        self.assertIn("100 miles (161 km)", under.blurb)
        longest = browse.by_key("longest")
        self.assertIn("1,000 miles (1,609 km) or more", longest.blurb)

    def test_membership_is_by_the_mile_figure(self):
        under, longest = browse.by_key("under-100-miles"), browse.by_key("longest")
        edge = 100 * words.KM_PER_MI
        self.assertTrue(under.test(fake(1, km=edge - 0.01)))
        self.assertFalse(under.test(fake(1, km=edge)))
        self.assertTrue(under.test(fake(1, km=120)))  # 75 miles: under 100 miles, though over 100 km
        edge = 1000 * words.KM_PER_MI
        self.assertTrue(longest.test(fake(1, km=edge)))
        self.assertFalse(longest.test(fake(1, km=edge - 0.01)))
        self.assertFalse(longest.test(fake(1, km=1500)))  # 932 miles

    def test_the_hide_rule_is_kept(self):
        self.assertFalse(browse.is_shown(3, 100))
        self.assertFalse(browse.is_shown(80, 100))
        self.assertTrue(browse.is_shown(4, 100))


class RoundStepsTest(unittest.TestCase):
    def test_steps_are_round_in_their_own_unit(self):
        for unit, steps in (("mi", home.LENGTH_STEPS_MI), ("km", home.LENGTH_STEPS_KM)):
            self.assertEqual(list(steps), sorted(steps))
            for n in steps:
                self.assertEqual(n % 5, 0, (unit, n))
        recs = [fake(1, km=60), fake(2, km=10945)]
        self.assertEqual(home.length_steps(recs, "mi")[-1], 8000)       # 6,801 miles
        self.assertEqual(home.length_steps(recs, "km")[-1], 20000)      # above 10,945 km
        self.assertEqual(home.step_value(100, "mi"), "100mi")
        self.assertEqual(home.step_label(100, "mi"), "100 mi &middot; 161 km")
        self.assertEqual(home.step_label(100, "km"), "100 km &middot; 62 mi")

    def test_filter_script_reads_steps_in_both_units(self):
        js = read("assets", "app.js")
        self.assertIn("(mi|km)", js)
        self.assertIn("data-steps-' + unit", js)
        self.assertIn("dataset.km", js)  # rows are still compared in kilometres


if __name__ == "__main__":
    unittest.main()
