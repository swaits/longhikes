"""The maps start late: nothing for a map (MapLibre, its style, the contour add-on, the track
data) loads with the page. These pin the script's promises (the script has no unit tests; the
behaviour was checked by driving the pages in a browser)."""
import os
import re
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(WEB, *parts), encoding="utf-8") as f:
        return f.read()


class MapStartTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = read("assets", "app.js")

    def test_one_function_starts_a_map_and_it_is_the_only_caller_of_the_fetch_and_the_loader(self):
        self.assertEqual(self.js.count("fetchData()"), 2)  # its definition and the one call
        self.assertEqual(self.js.count("loadLibraries()"), 2)
        begin = re.search(r"function begin\(\) \{(.*?)\n    \}\n", self.js, re.S)
        self.assertIsNotNone(begin)
        self.assertIn("dataReady = fetchData();", begin.group(1))
        self.assertIn("loadLibraries().then(startMapLibre);", begin.group(1))
        self.assertIn("if (outdoorUrl) fetchOutdoor(outdoorUrl);", begin.group(1))
        self.assertEqual(self.js.count("fetchOutdoor(outdoorUrl)"), 2)  # begin() and startMapLibre(), once started

    def test_a_map_starts_when_near_the_screen_or_touched_never_at_once(self):
        self.assertIn("new IntersectionObserver(", self.js)
        self.assertIn("afterLoad(begin);", self.js)  # near the screen, and the page has loaded
        for event in ("pointerdown", "focusin", "keydown"):
            self.assertIn(f"'{event}'", self.js)
        self.assertNotIn("startMaps", self.js)
        self.assertNotRegex(self.js, r"initMap\(fig\)[^}]*\n\s*(fetch|loadLibraries)")

    def test_the_libraries_come_from_the_addresses_on_the_scripts_own_tag(self):
        self.assertIn("var SCRIPT = document.currentScript;", self.js)
        for attr in ("maplibreCss", "maplibreJs", "contourJs"):
            self.assertIn(f"d.{attr}", self.js)

    def test_maplibres_stylesheet_goes_before_the_sites_so_the_sites_frame_rules_win(self):
        # MapLibre's .maplibregl-map sets position: relative; the site's .map__canvas needs absolute.
        self.assertIn("document.head.querySelector('link[rel=\"stylesheet\"]')", self.js)
        self.assertIn("document.head.insertBefore(el, before || null);", self.js)
        # the page runs the scripts in order: the add-on needs MapLibre first
        self.assertIn("script.async = false;", self.js)

    def test_until_it_starts_the_frame_says_what_happens_and_the_page_text_stays_for_no_script(self):
        self.assertIn("'The map loads when you scroll to it.'", self.js)


if __name__ == "__main__":
    unittest.main()
