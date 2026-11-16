"""Logo thumbnails: the committed web/thumbs, what the built pages show, and the fallback."""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)

from olt import records, thumbs  # noqa: E402

OUT = os.path.join(WEB, ".cache", "test-site")
MAX_SIDE = 256


class Imgs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.imgs = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.imgs.append(dict(attrs))


def page_imgs(path):
    p = Imgs()
    with open(path, encoding="utf-8") as f:
        p.feed(f.read())
    return p.imgs


def html_files(out):
    for base, _, names in os.walk(out):
        for n in names:
            if n.endswith(".html"):
                yield os.path.join(base, n)


def repository_png_logos():
    """{id: path} for each <id>/shield.png directly under the repository root."""
    found = {}
    for name in os.listdir(ROOT):
        path = os.path.join(ROOT, name, "shield.png")
        if not name.startswith((".", "_")) and os.path.isfile(path):
            found[name] = path
    return found


def repository_logos():
    """{id: path} for each logo with a thumbnail: <id>/shield.png, or <id>/shield.svg where there is no PNG."""
    found = dict(repository_png_logos())
    for name in os.listdir(ROOT):
        path = os.path.join(ROOT, name, "shield.svg")
        if not name.startswith((".", "_")) and name not in found and os.path.isfile(path):
            found[name] = path
    return found


def build():
    subprocess.run([sys.executable, os.path.join(WEB, "build.py"), "--out", OUT],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class ThumbFilesTest(unittest.TestCase):
    def test_every_repository_logo_has_a_thumbnail_no_larger_than_256(self):
        logos = repository_logos()
        self.assertTrue(logos)
        for tid in logos:
            thumb = os.path.join(WEB, "thumbs", f"{tid}.png")
            self.assertTrue(os.path.isfile(thumb), f"{tid}: no {thumb}")
            w, h = thumbs.png_size(thumb)
            self.assertLessEqual(w, MAX_SIDE, tid)
            self.assertLessEqual(h, MAX_SIDE, tid)
            self.assertGreater(min(w, h), 0, tid)

    def test_no_thumbnail_without_a_source(self):
        logos = repository_logos()
        thumbs_dir = os.path.join(WEB, "thumbs")
        for name in os.listdir(thumbs_dir):
            self.assertIn(name[:-len(".png")], logos, f"orphan thumbnail {name}")

    def test_fallback_to_full_size_when_no_thumbnail(self):
        tid = "x"
        with tempfile.TemporaryDirectory() as tmp:
            repo, out, empty = (os.path.join(tmp, n) for n in ("repo", "out", "thumbs"))
            os.makedirs(os.path.join(repo, tid))
            os.makedirs(empty)
            src = repository_png_logos()["cohos"]
            shutil.copyfile(src, os.path.join(repo, tid, "shield.png"))
            os.makedirs(os.path.join(out, "trails", tid))
            rec = {"id": tid, "derived": {"files": {"shield": f"{tid}/shield.png"}}}
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                thumbs.prepare(rec, out, repo, thumb_dir=empty)
            self.assertIn(f"{tid}:", err.getvalue())
            self.assertEqual(err.getvalue().count("warning"), 1)
            logo = rec["derived"]["logo_img"]
            self.assertEqual(logo["src"], f"/trails/{tid}/shield.png")
            self.assertEqual((logo["width"], logo["height"]), thumbs.png_size(src))
            self.assertFalse(os.path.exists(os.path.join(out, "trails", tid, thumbs.THUMB_NAME)))

    def test_svg_logo_gets_a_thumbnail_like_a_png_one(self):
        tid = "x"
        with tempfile.TemporaryDirectory() as tmp:
            repo, out, made = (os.path.join(tmp, n) for n in ("repo", "out", "thumbs"))
            for d in (os.path.join(repo, tid), os.path.join(out, "trails", tid), made):
                os.makedirs(d)
            with open(os.path.join(repo, tid, "shield.svg"), "w", encoding="utf-8") as f:
                f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 170 92"></svg>')
            shutil.copyfile(repository_png_logos()["cohos"], os.path.join(made, f"{tid}.png"))
            rec = {"id": tid, "derived": {"files": {"shield": f"{tid}/shield.svg"}, "logo_img": {"src": "stale"}}}
            thumbs.prepare(rec, out, repo, thumb_dir=made)
            logo = rec["derived"]["logo_img"]
            self.assertEqual(logo["src"], f"/trails/{tid}/{thumbs.THUMB_NAME}")
            self.assertEqual((logo["width"], logo["height"]), thumbs.png_size(os.path.join(made, f"{tid}.png")))
            self.assertTrue(os.path.isfile(os.path.join(out, "trails", tid, thumbs.THUMB_NAME)))

    def test_svg_logo_with_no_thumbnail_falls_back_to_the_svg_with_its_own_shape(self):
        tid = "x"
        with tempfile.TemporaryDirectory() as tmp:
            repo, out, empty = (os.path.join(tmp, n) for n in ("repo", "out", "thumbs"))
            for d in (os.path.join(repo, tid), os.path.join(out, "trails", tid), empty):
                os.makedirs(d)
            with open(os.path.join(repo, tid, "shield.svg"), "w", encoding="utf-8") as f:
                f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 170 92"></svg>')
            rec = {"id": tid, "derived": {"files": {"shield": f"{tid}/shield.svg"}}}
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                thumbs.prepare(rec, out, repo, thumb_dir=empty)
            self.assertEqual(err.getvalue().count("warning"), 1)
            self.assertEqual(rec["derived"]["logo_img"], {"src": f"/trails/{tid}/shield.svg", "width": 256, "height": 139})

    def test_a_logo_of_another_type_gets_no_thumbnail(self):
        rec = {"id": "x", "derived": {"files": {"shield": "x/shield.gif"}, "logo_img": {"src": "stale"}}}
        with tempfile.TemporaryDirectory() as tmp:
            thumbs.prepare(rec, tmp, tmp, thumb_dir=tmp)
        self.assertNotIn("logo_img", rec["derived"])


class BuiltPagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        build()
        cls.records = records.load_records(ROOT)
        cls.png = [r["id"] for r in cls.records
                   if r["derived"]["files"].get("shield", "").endswith(".png")]
        cls.all_imgs = [(path, img) for path in html_files(OUT) for img in page_imgs(path)]

    def test_list_pages_show_thumbnails_not_full_size_pngs(self):
        for path, img in self.all_imgs:
            self.assertFalse(img.get("src", "").endswith("/shield.png"), f"{path} shows {img.get('src')}")
        for page in ("index.html", os.path.join("logos", "index.html")):
            with open(os.path.join(OUT, page), encoding="utf-8") as f:
                doc = f.read()
            for tid in self.png:
                self.assertIn(f'src="/trails/{tid}/shield-thumb.png"', doc, f"{page} for {tid}")

    def test_thumbnail_width_and_height_match_the_file(self):
        seen = 0
        for path, img in self.all_imgs:
            src = img.get("src", "")
            if not src.endswith("/" + thumbs.THUMB_NAME):
                continue
            seen += 1
            w, h = thumbs.png_size(os.path.join(OUT, src.lstrip("/")))
            self.assertEqual((img.get("width"), img.get("height")), (str(w), str(h)), path)
            self.assertEqual(img.get("decoding"), "async", path)
        self.assertGreaterEqual(seen, len(self.png) * 2)

    def test_record_header_logo_is_eager_and_links_full_size(self):
        for tid in self.png:
            with open(os.path.join(OUT, "trails", tid, "index.html"), encoding="utf-8") as f:
                doc = f.read()
            self.assertIn(f'<a href="/trails/{tid}/shield.png"><img src="/trails/{tid}/shield-thumb.png"', doc, tid)
            header = [i for i in page_imgs(os.path.join(OUT, "trails", tid, "index.html"))
                      if i.get("src") == f"/trails/{tid}/shield-thumb.png"]
            self.assertEqual(len(header), 1, tid)
            self.assertNotIn("loading", header[0], tid)

    def test_logos_page_links_full_size_and_is_lazy(self):
        for tid in self.png:
            with open(os.path.join(OUT, "logos", "index.html"), encoding="utf-8") as f:
                doc = f.read()
            self.assertIn(f'<a href="/trails/{tid}/shield.png"><img src="/trails/{tid}/shield-thumb.png"', doc, tid)
        for img in page_imgs(os.path.join(OUT, "logos", "index.html")):
            if img.get("src", "").endswith(thumbs.THUMB_NAME):
                self.assertEqual(img.get("loading"), "lazy")

    def test_thumbnails_survive_a_second_build(self):
        build()
        for tid in self.png:
            self.assertTrue(os.path.isfile(os.path.join(OUT, "trails", tid, thumbs.THUMB_NAME)), tid)


if __name__ == "__main__":
    unittest.main()
