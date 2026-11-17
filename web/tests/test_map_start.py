"""The maps start a moment after the page has loaded, every one of them, by itself. Nothing for a
map (MapLibre, its style, the contour add-on, the track data) loads with the page, and nothing
waits for a scroll, a tap, a key or focus. These pin the script's promises (the script has no unit
tests; the behaviour was checked by driving the pages in a browser)."""
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
        self.assertEqual(self.js.count("fetchData()"), 3)  # its definition, begin(), and a frame with no drawing
        self.assertEqual(self.js.count("loadLibraries()"), 2)
        begin = re.search(r"function begin\(\) \{(.*?)\n    \}\n", self.js, re.S)
        self.assertIsNotNone(begin)
        self.assertIn("dataReady = dataReady || fetchData();", begin.group(1))
        self.assertIn("loadLibraries().then(startMapLibre);", begin.group(1))
        self.assertIn("if (outdoorUrl) fetchOutdoor(outdoorUrl);", begin.group(1))
        self.assertEqual(self.js.count("fetchOutdoor(outdoorUrl)"), 2)  # begin() and startMapLibre(), once started

    def start_code(self):
        code = re.search(r"function begin\(\) \{.*?\n  function entryFor", self.js, re.S).group(0)
        return re.sub(r"/\*.*?\*/", "", code, flags=re.S)  # the code, not the comments

    def test_every_map_starts_by_itself_after_the_load_event_and_nothing_else_starts_it(self):
        code = self.start_code()
        self.assertIn("window.addEventListener('load', fn, { once: true })", code)
        self.assertIn("requestIdleCallback(begin, { timeout: 500 })", code)
        self.assertIn("setTimeout(begin, 100)", code)
        self.assertEqual(len(re.findall(r"\bbegin\b", code)), 3)  # its definition and those two calls, no other trigger

    def test_no_map_waits_for_visibility_or_for_the_visitor(self):
        # the whole script: no observer of any kind, and no scroll listener
        for word in ("IntersectionObserver", "ResizeObserver", "MAP_AHEAD", "isIntersecting", "'scroll'", "'touchstart'"):
            self.assertNotIn(word, self.js)
        code = self.start_code()
        for event in ("pointerdown", "pointerup", "focusin", "focus", "keydown", "keyup", "click", "mouseover", "touch", "wheel"):
            self.assertNotIn(event, code)
        self.assertNotIn("addEventListener('" , code.replace("window.addEventListener('load'", ""))
        self.assertNotIn("startMaps", self.js)
        self.assertNotRegex(self.js, r"initMap\(fig\)[^}]*\n\s*(fetch|loadLibraries)")

    def test_a_frame_with_no_drawing_of_its_own_is_drawn_from_the_data_at_once(self):
        # the saved trails are known only to the browser: no drawing is made when the site is built
        self.assertIn("if (!hasSketch()) dataReady = fetchData();", self.js)

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

    def test_until_it_starts_the_frame_holds_its_drawing_and_says_nothing_with_a_script(self):
        # the page's own drawing fills the frame (test_first_screen.py); the no-script text is shown
        # only without JavaScript, or when a failure sets data-say
        self.assertNotIn("The map loads when you scroll to it.", self.js)
        self.assertIn("function say(text) {", self.js)


if __name__ == "__main__":
    unittest.main()
