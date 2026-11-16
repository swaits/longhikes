"""The page's controls, its address, the stored choices and what is drawn must
say the same thing. These pin the script's answers to the faults found by
driving the pages in a browser (the script itself has no unit tests)."""
import os
import re
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(WEB, *parts), encoding="utf-8") as f:
        return f.read()


class ScriptSyncTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = read("assets", "app.js")

    def test_basemap_follows_a_choice_made_while_the_map_loaded(self):
        # Another tab, or Back, may change the base map before the map is ready; the
        # change event is then ignored, so the map catches up once it is ready and
        # the switch (which shows the choice) is added.
        self.assertRegex(self.js, re.compile(r"map\.addControl\(switcher, 'top-left'\);\s*/\*.*?\*/\s*applyBasemap\(\);", re.S))

    def test_lengths_the_wrong_way_round_in_the_address_show_in_order(self):
        # apply() writes the shorter length first; the controls must say the same.
        self.assertIn("if (stepKm(el.min.value) > stepKm(el.max.value) && stepKm(el.max.value)) {", self.js)

    def test_the_header_switch_is_the_only_units_switch(self):
        css = read("assets", "style.css")
        for text in (self.js, css, read("olt", "home.py")):
            self.assertNotIn("units-list", text)
            self.assertNotIn("results-units", text)
        self.assertNotIn("UNITS_TOGGLE", read("olt", "home.py"))


if __name__ == "__main__":
    unittest.main()
