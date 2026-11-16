"""The social cards' layout, measured: no two text boxes overlap, nothing leaves the safe area,
and the text column and the track never meet, for every record's card and the site card.

The boxes come from the same layout code that draws the cards (web/tools/make_cards.py), so a
card cannot pass here and be drawn differently. Needs Pillow and fontTools (with brotli); the
test is skipped where they are not installed."""
import os
import sys
import tempfile
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.join(WEB, "tools"))

try:
    import make_cards  # noqa: E402
    from fontTools.ttLib import TTFont  # noqa: E402
    HAVE = True
except Exception:  # Pillow, fontTools or brotli missing
    HAVE = False

from olt import cards, records, site  # noqa: E402

SITE = os.path.join(WEB, ".cache", "test-site")
GAP = 6          # px of clear space between two lines of text
TRACK_GAP = 24   # px between the text column and the track
EDGE = 40        # px between the track and the card's edges
FOOT_CLEAR = 20  # px between the track and the footer line


def overlap(a, b, gap=0):
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap


def track_parts(tid):
    """The track as the card tool draws it: the site's map.json where one is built, else the
    record's own line (the box depends only on the track's extent)."""
    for path in (os.path.join(SITE, "trails", tid, "map.json"), os.path.join(ROOT, tid, "line.geojson")):
        if os.path.isfile(path):
            return make_cards.parts_of(path)
    return []


@unittest.skipUnless(HAVE, "needs Pillow and fontTools")
class CardLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.fonts = make_cards.load_fonts(cls.tmp.name)
        cls.measure = make_cards.Measure(cls.fonts)
        cls.recs = records.load_records(ROOT)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def check(self, lay, label):
        boxes = make_cards.boxes_of(lay)
        text = [(k, b) for k, b in boxes if k in ("name", "length", "places", "header", "footer")]
        W, H = make_cards.W, make_cards.H
        self.assertTrue(lay.get("fits", True), f"{label}: the text does not fit at the smallest name size")
        self.assertGreaterEqual(lay["name_size"], make_cards.NAME_MIN, label)
        for (ka, a), (kb, b) in ((x, y) for i, x in enumerate(text) for y in text[i + 1:]):
            self.assertFalse(overlap(a, b, GAP), f"{label}: {ka} {a} and {kb} {b} overlap or touch")
        top, bottom = make_cards.SAFE_TOP, make_cards.SAFE_BOTTOM
        for kind, box in text:
            self.assertGreaterEqual(box[0], make_cards.MARGIN - 8, f"{label}: {kind} {box}")  # 8: a J or f overhangs its origin
            self.assertLessEqual(box[2], make_cards.MARGIN + lay["width"] + 8, f"{label}: {kind} {box} is wider than its column")
            if kind in ("name", "length", "places"):
                self.assertGreaterEqual(box[1], top, f"{label}: {kind} {box} is above the safe area")
                self.assertLessEqual(box[3], bottom, f"{label}: {kind} {box} is below the safe area")
        for kind, box in text:
            self.assertTrue(0 <= box[0] and box[2] <= W and 0 <= box[1] and box[3] <= H - 14, f"{label}: {kind} {box} leaves the card")
        mark = dict(boxes)["mark"]
        for kind, box in text:
            if kind in ("name", "length", "places"):
                self.assertFalse(overlap(box, mark, GAP), f"{label}: {kind} meets the mark")
        for kind, box in boxes:
            if kind == "track":
                self.assertGreaterEqual(box[0], make_cards.MARGIN + lay["width"] + TRACK_GAP - 1, f"{label}: track {box} meets the text column")
                self.assertGreaterEqual(box[1], EDGE, f"{label}: track {box}")
                self.assertLessEqual(box[2], W - EDGE, f"{label}: track {box}")
                self.assertLessEqual(box[3], make_cards.FOOT_Y - FOOT_CLEAR, f"{label}: track {box} reaches the footer")
                for k, b in text:
                    self.assertFalse(overlap(box, b, TRACK_GAP), f"{label}: track {box} and {k} {b}")

    def test_every_trail_card_is_laid_out_cleanly(self):
        for rec in self.recs:
            parts = track_parts(rec["id"])
            self.check(make_cards.layout(self.measure, rec, parts), rec["id"])

    def test_site_card_is_laid_out_cleanly(self):
        cfg = site.from_file(os.path.join(WEB, "site.toml"))
        self.check(make_cards.site_layout(self.measure, cfg), "site card")

    def test_every_character_is_in_the_fonts(self):
        have = {}
        for key, path in self.fonts.items():
            have[key] = set(TTFont(path).getBestCmap())
        cfg = site.from_file(os.path.join(WEB, "site.toml"))
        texts = [(r["id"], t) for r in self.recs for t in cards.lines(r)]
        texts += [("site", t) for t in cards.site_lines(cfg)] + [("mark", "Long Hikes longhikes.org")]
        for who, t in texts:
            for ch in t:
                self.assertTrue(ord(ch) in have["serif"] or ch.isspace(), f"{who}: {ch!r} (U+{ord(ch):04X}) is not in the serif font")
        for r in self.recs:
            for ch in cards.where(r):
                self.assertIn(ord(ch), have["sans"], f"{r['id']}: places {ch!r} is not in the sans font")

    def test_a_place_list_is_cut_to_two_lines(self):
        m = self.measure
        f = m.font("sans", 30)
        names = "Newfoundland and Labrador, British Columbia, Northwest Territories, Saskatchewan, Nova Scotia"
        lines = make_cards.short_places(names, m, f, make_cards.COL_TRACK)
        self.assertLessEqual(len(lines), 2)
        self.assertIn("more", " ".join(lines))

    def test_a_long_name_is_never_cut(self):
        name = "Sentier international des Appalaches (International Appalachian Trail, Quebec and New Brunswick)"
        items, size, fits = make_cards.flow(self.measure, name, "731 miles · 1,177 km", "Quebec", 660)
        got = " ".join(t for k, t, *_ in items if k == "name")
        self.assertEqual(got.split(), name.split())


if __name__ == "__main__":
    unittest.main()
