"""The outdoor map of the trail pages: the style file, the contour add-on, where
each loads, and the credits. The security policy for the elevation tiles is
tested with the other headers in test_extra.py."""
import ast
import json
import os
import re
import subprocess
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)

from olt import common, layout, records  # noqa: E402

OUT = os.path.join(WEB, ".cache", "test-site")
STYLE = os.path.join(WEB, "assets", "map", "outdoor.json")
VENDOR = os.path.join(WEB, "assets", "vendor")
MAP_FONTS = {"Noto Sans Regular", "Noto Sans Italic", "Noto Sans Bold"}  # served by OpenFreeMap


def setUpModule():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    subprocess.run([sys.executable, os.path.join(WEB, "build.py"), "--out", OUT],
                   check=True, stdout=subprocess.DEVNULL)


def read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def tool_constant(name):
    """A constant of tools/elevation.py, read without importing it (the tool needs numpy)."""
    tree = ast.parse(read(ROOT, "tools", "elevation.py"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


def fonts(value):
    """Every font stack named in a text-font value, expressions included."""
    if isinstance(value, list) and value and all(isinstance(v, str) for v in value) and value[0] != "literal":
        return set(value)
    if isinstance(value, list):
        return set().union(*(fonts(v) for v in value)) if value else set()
    return set()


class OutdoorStyleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(STYLE, encoding="utf-8") as f:
            cls.style = json.load(f)
        cls.layers = cls.style["layers"]

    def test_small_enough_to_read(self):
        self.assertLess(os.path.getsize(STYLE), 40_000)
        self.assertLess(len(self.layers), 60)
        ids = [layer["id"] for layer in self.layers]
        self.assertEqual(len(ids), len(set(ids)))

    def test_no_new_host_for_tiles_fonts_or_icons(self):
        self.assertTrue(self.style["glyphs"].startswith("https://tiles.openfreemap.org/fonts/"))
        self.assertTrue(self.style["sprite"].startswith("https://tiles.openfreemap.org/sprites/"))
        self.assertEqual(self.style["sources"]["openmaptiles"]["url"], "https://tiles.openfreemap.org/planet")
        for layer in self.layers:
            self.assertIn(layer.get("source", "openmaptiles"), self.style["sources"], layer["id"])
            used = fonts(layer.get("layout", {}).get("text-font", []))
            self.assertLessEqual(used, MAP_FONTS, layer["id"])

    def test_elevation_source_is_the_tools_dataset_capped(self):
        dem = self.style["sources"]["olt-dem"]
        self.assertEqual(dem["type"], "raster-dem")
        self.assertEqual(dem["encoding"], "terrarium")
        self.assertEqual(dem["tiles"], [tool_constant("TILE_URL")])
        self.assertLessEqual(dem["maxzoom"], 12)
        self.assertIn("Terrain Tiles", dem["attribution"])
        self.assertIn("https://registry.opendata.aws/terrain-tiles/", dem["attribution"])
        # Bounded to North America, where the credit under the map covers every source drawn.
        west, south, east, north = dem["bounds"]
        self.assertLessEqual(west, -170)
        self.assertGreaterEqual(south, 10)
        self.assertLessEqual(east, -50)
        self.assertEqual(self.style["sources"]["olt-contours"]["bounds"], dem["bounds"])

    def test_contours_only_when_zoomed_in_with_round_steps(self):
        contours = self.style["metadata"]["olt:contours"]
        source = self.style["sources"]["olt-contours"]
        self.assertGreaterEqual(source["minzoom"], 11)
        self.assertEqual(sorted(contours), ["ft", "m"])
        self.assertAlmostEqual(contours["ft"]["multiplier"], 3.28084)
        self.assertEqual(contours["m"]["multiplier"], 1)
        for unit, opts in contours.items():
            zooms = sorted(int(z) for z in opts["thresholds"])
            self.assertEqual(zooms[0], source["minzoom"], unit)
            steps = [opts["thresholds"][str(z)] for z in zooms]
            for minor, major in steps:
                self.assertEqual(major % minor, 0, unit)
                self.assertEqual(minor % 10, 0, unit)
            # Closer lines as the map zooms in, never wider.
            self.assertEqual([s[0] for s in steps], sorted((s[0] for s in steps), reverse=True), unit)

    def test_dark_and_km_values_have_light_and_miles_ones(self):
        dark = km = 0
        for layer in self.layers:
            meta = layer.get("metadata", {})
            for prop in meta.get("olt:dark", {}):
                dark += 1
                self.assertFalse(prop.startswith(("text-field", "visibility")), layer["id"])
                if prop != "icon-opacity":
                    self.assertIn(prop, layer.get("paint", {}), f"{layer['id']} {prop}")
            for prop in meta.get("olt:km", {}):
                km += 1
                self.assertIn(prop, layer.get("layout", {}), f"{layer['id']} {prop}")
        self.assertGreater(dark, 30)
        self.assertEqual(km, 2)  # the peak heights and the contour labels

    def test_peaks_and_contours_name_their_units(self):
        by_id = {layer["id"]: layer for layer in self.layers}
        peak, label = by_id["peak"], by_id["contour-label"]
        self.assertIn('"ele_ft"', json.dumps(peak["layout"]["text-field"]))
        self.assertIn('" ft"', json.dumps(peak["layout"]["text-field"]))
        self.assertIn('" m"', json.dumps(peak["metadata"]["olt:km"]["text-field"]))
        self.assertIn('" ft"', json.dumps(label["layout"]["text-field"]))
        self.assertIn('" m"', json.dumps(label["metadata"]["olt:km"]["text-field"]))

    def test_footpaths_are_thin_dashes(self):
        by_id = {layer["id"]: layer for layer in self.layers}
        for lid in ("road-path", "road-track"):
            paint = by_id[lid]["paint"]
            self.assertIn("line-dasharray", paint, lid)
            widths = paint["line-width"][3:]
            self.assertLessEqual(max(widths[1::2]), 2, lid)

    def test_licence_notices_beside_the_style(self):
        text = read(WEB, "assets", "map", "LICENSE.txt")
        text = " ".join(text.split())
        for words in ("OpenFreeMap", "MIT License", "OSM Liberty", "BSD 3-Clause",
                      "Creative Commons Attribution 4.0", "OpenMapTiles"):
            self.assertIn(words, text)


class ContourAddOnTest(unittest.TestCase):
    def test_vendored_with_its_licence_and_pinned(self):
        script = os.path.join(VENDOR, "maplibre-contour", "maplibre-contour.js")
        self.assertTrue(os.path.isfile(script))
        self.assertIn("BSD 3-Clause License", read(VENDOR, "maplibre-contour", "LICENSE.txt"))
        readme = read(VENDOR, "README.md")
        self.assertIn("| maplibre-contour | 0.1.1 |", readme)
        import hashlib
        with open(script, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        self.assertIn(f"{digest}  maplibre-contour.js", readme)
        self.assertNotIn("sourceMappingURL", read(script))


class OutdoorPagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = records.load_records(ROOT)

    def test_trail_maps_are_outdoor_and_load_the_add_on(self):
        contour = f'<script src="{layout.CONTOUR_JS}" defer></script>'
        maplibre = f'<script src="{layout.MAPLIBRE_JS}" defer></script>'
        with_map = 0
        for rec in self.records:
            page = read(OUT, "trails", rec["id"], "index.html")
            figures = re.findall(r'<figure class="mapfig[^"]*"[^>]*>', page)
            mapped = [f for f in figures if 'data-map="' in f]
            if mapped:
                with_map += 1
                for fig in mapped:
                    self.assertIn(f'data-outdoor="{layout.OUTDOOR_STYLE}"', fig, rec["id"])
                self.assertEqual(page.count(contour), 1, rec["id"])
                self.assertLess(page.index(maplibre), page.index(contour), rec["id"])
            else:
                self.assertNotIn(contour, page, rec["id"])
                self.assertNotIn("data-outdoor", page, rec["id"])
        self.assertGreater(with_map, 100)
        self.assertTrue(os.path.isfile(os.path.join(OUT, *layout.OUTDOOR_STYLE.strip("/").split("/"))))
        self.assertTrue(os.path.isfile(os.path.join(OUT, *layout.CONTOUR_JS.strip("/").split("/"))))

    def test_overview_maps_stay_plain(self):
        paths = ["index.html", os.path.join("routes", "index.html"), os.path.join("lists", "index.html")]
        for base in ("regions", "lists"):
            for name in sorted(os.listdir(os.path.join(OUT, base))):
                if os.path.isfile(os.path.join(OUT, base, name, "index.html")):
                    paths.append(os.path.join(base, name, "index.html"))
        overview = 0
        for path in paths:
            page = read(OUT, path)
            overview += 'data-map="overview"' in page
            self.assertNotIn(layout.CONTOUR_JS, page, path)
            self.assertNotIn("data-outdoor", page, path)
        self.assertGreater(overview, 10)


class CreditsTest(unittest.TestCase):
    def test_elevation_credit_is_the_tools_credit(self):
        self.assertEqual(common.ELEVATION_CREDIT, tool_constant("ATTRIBUTION"))
        self.assertTrue(common.MAP_ELEVATION_CREDIT.startswith(common.ELEVATION_CREDIT))
        self.assertIn("INEGI", common.MAP_ELEVATION_CREDIT)

    def test_every_trail_map_credits_the_base_map_and_the_relief(self):
        credit = str(common.TRAIL_MAP_CREDIT)
        self.assertIn("Relief and contours: Terrain Tiles, accessed from https://registry.opendata.aws/terrain-tiles.", credit)
        for rec in records.load_records(ROOT):
            page = read(OUT, "trails", rec["id"], "index.html")
            if 'data-map="' in page:
                caption = page[page.index('<figcaption class="mapfig__caption'):]
                caption = caption[:caption.index("</figcaption>")]
                self.assertIn(credit, caption, rec["id"])

    def test_footer_credits_the_elevation_data_on_every_page(self):
        for base, _, names in os.walk(OUT):
            for name in names:
                if name.endswith(".html"):
                    page = read(base, name)
                    foot = page[page.index('<div class="site-footer__base">'):]
                    self.assertIn("Terrain Tiles", foot, os.path.join(base, name))
                    self.assertIn("OpenFreeMap", foot, os.path.join(base, name))
