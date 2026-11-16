"""Every <img> in the built site states its size, so the page does not shift as pictures arrive,
and the logos of the first screen are not lazy-loaded while the rest are."""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)

from olt import home, thumbs  # noqa: E402

OUT = os.path.join(WEB, ".cache", "test-site")


class Imgs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.imgs = []
        self.in_entries = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "li" and "entry" in (a.get("class") or "").split():
            self.in_entries += 1
        if tag == "img":
            a["_row"] = self.in_entries  # the number (1-based) of the last list row opened: 0 before the first
            self.imgs.append(a)


def page_imgs(path):
    p = Imgs()
    with open(path, encoding="utf-8") as f:
        p.feed(f.read())
    return p.imgs


class SvgSizeTest(unittest.TestCase):
    def size(self, svg):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "x.svg")
            with open(path, "w", encoding="utf-8") as f:
                f.write(svg)
            return thumbs.svg_size(path)

    def test_the_shape_comes_from_the_view_box_and_fits_within_the_thumbnail_size(self):
        self.assertEqual(self.size('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 170 92"><g/></svg>'), (256, 139))
        self.assertEqual(self.size('<svg viewBox="17.1 25 82.1 82.1"></svg>'), (256, 256))
        self.assertEqual(self.size('<svg viewBox="0,0,100,400"></svg>'), (64, 256))

    def test_without_a_view_box_the_width_and_height_are_used(self):
        self.assertEqual(self.size('<svg width="75.258mm" height="73.228mm"></svg>'), (256, 249))

    def test_an_svg_with_no_size_is_an_error_not_a_guess(self):
        with self.assertRaises(ValueError):
            self.size("<svg></svg>")


class BuiltSiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        subprocess.run([sys.executable, os.path.join(WEB, "build.py"), "--out", OUT],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.pages = []
        for base, _, names in os.walk(OUT):
            for n in names:
                if n.endswith(".html"):
                    cls.pages.append(os.path.join(base, n))

    def test_every_img_has_a_width_and_height(self):
        seen = 0
        for page in self.pages:
            for img in page_imgs(page):
                seen += 1
                for dim in ("width", "height"):
                    self.assertRegex(img.get(dim, ""), r"^[1-9][0-9]*$", f"{page}: {img}")
        self.assertGreater(seen, 1000)

    def test_logos_are_thumbnails_never_the_full_size_file(self):
        for page in self.pages:
            for img in page_imgs(page):
                self.assertNotRegex(img.get("src", ""), r"/shield\.(svg|png)$", page)

    def test_an_svg_logo_has_a_thumbnail_the_size_of_the_file(self):
        found = 0
        for tid in ("bartram", "appalachian", "long-trail"):
            img = [i for i in page_imgs(os.path.join(OUT, "trails", tid, "index.html"))
                   if i.get("src") == f"/trails/{tid}/{thumbs.THUMB_NAME}"]
            self.assertEqual(len(img), 1, tid)
            w, h = thumbs.png_size(os.path.join(OUT, "trails", tid, thumbs.THUMB_NAME))
            self.assertEqual((img[0]["width"], img[0]["height"]), (str(w), str(h)), tid)
            found += 1
        self.assertEqual(found, 3)

    def test_the_first_rows_of_a_list_are_eager_and_the_rest_are_lazy(self):
        for rel in ("index.html", os.path.join("lists", "under-100-miles", "index.html")):
            logos = [i for i in page_imgs(os.path.join(OUT, rel))
                     if i["_row"] and i.get("src", "").endswith(thumbs.THUMB_NAME)]
            self.assertGreater(len(logos), home.EAGER_ROWS + 2, rel)
            for img in logos:
                if img["_row"] <= home.EAGER_ROWS:
                    self.assertNotIn("loading", img, f"{rel} row {img['_row']}")
                else:
                    self.assertEqual(img.get("loading"), "lazy", f"{rel} row {img['_row']}")

    def test_the_saved_page_loads_no_logo_for_its_hidden_rows_and_the_record_logo_is_eager(self):
        for img in page_imgs(os.path.join(OUT, "saved", "index.html")):
            if img["_row"] and img.get("src", "").endswith(thumbs.THUMB_NAME):
                self.assertEqual(img.get("loading"), "lazy")
        header = [i for i in page_imgs(os.path.join(OUT, "trails", "appalachian", "index.html"))
                  if i.get("src", "").endswith(thumbs.THUMB_NAME)]
        self.assertTrue(header)
        self.assertNotIn("loading", header[0])
        self.assertTrue(re.match(r"^/trails/appalachian/", header[0]["src"]))


if __name__ == "__main__":
    unittest.main()
