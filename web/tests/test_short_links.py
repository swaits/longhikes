"""The Saved page's short links: the code app.js writes and reads (SavedCode, run under node, no
browser) and the numbers the built page carries. The page's behaviour in a browser was checked by hand.

The format: ?s=<version char "1"><base64url of the bit set over trail numbers>, bit N set when trail N
is in the list, bit 0 the least significant bit of byte 0, trailing zero bytes dropped, no padding.
Up to SAVED_READABLE_MAX trails the link stays ?t=id,id,... (docs/schema.md).
"""
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build_index  # noqa: E402
import trail_numbers  # noqa: E402
from olt import records, saved  # noqa: E402

NODE = shutil.which("node")
import builtsite  # noqa: E402

OUT = builtsite.OUT

# The owner's own list of 49 trails, in the order saved: a real fixture.
OWNER = ("eastern-sierra-high-route,sierra-high-route,southern-sierra-high-route,uinta-highline,grand-moab-route,"
         "beartooth-high-route,chinese-wall-circuit,bitterroots-80-mile-route,pfiffner-traverse,"
         "sawtooth-wilderness-high-route,teton-crest,teton-range-traverse,toiyabe-crest,wasatch-traverse,"
         "wind-river-high-route-dixon-wilson,wind-river-high-route-skurka,yosemite-high-route,"
         "kings-canyon-high-basin-route,prescott-circle,big-seki-loop,high-sierra,john-muir,pacific-crest,"
         "sierra-grand-traverse,great-western-divide-loop,tahoe-rim,tahoe-yosemite-trail,continental-divide,"
         "great-divide-trail,timberline,wonderland,great-basin-trail,lowest-to-highest-route,mogollon-rim-trail,"
         "wyoming-range,teton-crest-route,central-wind-rivers-loop,gospel-hump-loop,grand-sawtooth-loop,"
         "grand-teton-loop,green-river-lakes-titcomb-basin-loop,hayduke-trail,heart-lake-two-ocean-plateau-loop,"
         "middle-fork-trail,teton-wilderness-loop,thorofare-and-south-boundary-trail,alpine-trail-7,"
         "solitude-loop,circle-of-solitude").split(",")


def code_source():
    with open(os.path.join(WEB, "assets", "app.js"), encoding="utf-8") as f:
        js = f.read()
    return js[js.index("/* short-codes:begin */"):js.index("/* short-codes:end */")]


def node(expr, data=None):
    """Evaluate a JS expression with SavedCode in scope; `data` is bound to the JSON given."""
    prog = code_source() + "\nvar data = JSON.parse(require('fs').readFileSync(0, 'utf8'));\n" + \
        "process.stdout.write(JSON.stringify(" + expr + "));"
    done = subprocess.run([NODE, "-e", prog], input=json.dumps(data), capture_output=True, text=True, check=True)
    return json.loads(done.stdout)


def encode(numbers):
    return node("SavedCode.encode(data)", numbers)


def decode(code):
    return node("SavedCode.decode(data)", code)


def reference(numbers):
    """The code, written independently in Python from the format's description."""
    if not numbers:
        return "1"
    raw = bytearray(max(numbers) // 8 + 1)
    for n in numbers:
        raw[n // 8] |= 1 << (n % 8)
    return "1" + base64.urlsafe_b64encode(bytes(raw)).decode().rstrip("=")


@unittest.skipUnless(NODE, "node is not installed")
class CodeTest(unittest.TestCase):
    def test_a_small_known_set(self):
        # bits 0, 1 and 9: byte 0 = 0b00000011, byte 1 = 0b00000010 -> bytes 03 02 -> base64url "AwI"
        self.assertEqual(encode([0, 1, 9]), "1AwI")
        self.assertEqual(decode("1AwI"), [0, 1, 9])

    def test_bit_zero_is_the_least_significant_bit_of_byte_zero(self):
        self.assertEqual(encode([0]), "1AQ")      # byte 0x01
        self.assertEqual(encode([7]), "1gA")      # byte 0x80
        self.assertEqual(encode([8]), "1AAE")     # bytes 00 01

    def test_trailing_zero_bytes_are_dropped_and_leading_ones_kept(self):
        self.assertEqual(encode([0, 8, 16]), "1AQEB")   # three bytes, none dropped
        self.assertEqual(encode([16]), "1AAAB")         # zero bytes before the last set bit stay
        self.assertEqual(decode("1AQAAAA"), [0])   # extra zero bytes on the way in are harmless
        self.assertEqual(encode([]), "1")

    def test_matches_the_reference_for_many_sets(self):
        import random
        rng = random.Random(7)
        for size in (1, 2, 10, 11, 49, 220):
            for _ in range(5):
                nums = sorted(rng.sample(range(240), size))
                code = encode(nums)
                self.assertEqual(code, reference(nums))
                self.assertEqual(decode(code), nums)

    def test_round_trips_for_0_1_10_11_49_and_all_trails(self):
        ids, _ = trail_numbers.read(ROOT)
        for size in (0, 1, 10, 11, 49, len(ids)):
            nums = list(range(size))
            self.assertEqual(decode(encode(nums)), nums)

    def test_order_and_repeats_in_the_input_do_not_matter(self):
        self.assertEqual(encode([9, 1, 0, 9]), "1AwI")

    def test_malformed_codes_give_null_and_never_throw(self):
        for bad in ("", "2AwI", "AwI", "1Aw$", "1A", "1AwIAA", "1 AwI", "1AwI=", "1AwI==", "1+/", "x" * 10, "1" + "A" * 3000):
            self.assertIsNone(decode(bad), repr(bad[:20]))
        for odd in (None, 5, ["1AwI"], {}):
            self.assertIsNone(decode(odd))

    def test_the_threshold_is_one_named_constant(self):
        self.assertEqual(node("SAVED_READABLE_MAX"), 10)

    def test_the_owners_forty_nine_is_short(self):
        ids, _ = trail_numbers.read(ROOT)
        self.assertEqual(len(OWNER), 49)
        nums = sorted(ids.index(i) for i in OWNER)
        code = encode(nums)
        self.assertEqual(decode(code), nums)
        self.assertLess(len("https://longhikes.org/saved/?s=" + code), 80)


class NumbersOnThePageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        builtsite.ensure()
        with open(os.path.join(OUT, "saved", "index.html"), encoding="utf-8") as f:
            cls.page = f.read()

    def numbers(self):
        m = re.search(r'data-saved-numbers="([^"]*)"', self.page)
        self.assertTrue(m, "the Saved page carries no numbers")
        return m.group(1).split(" ")

    def test_every_record_has_its_number_on_the_page(self):
        ids = build_index.trail_dirs(ROOT)
        registry, problems = trail_numbers.read(ROOT)
        self.assertEqual(problems, [])
        carried = self.numbers()
        for tid in ids:
            self.assertEqual(carried[registry.index(tid)], tid, tid)

    def test_a_retired_number_is_a_hyphen_and_the_list_has_no_trailing_hyphens(self):
        ids = ["a", "b", "c"]
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, saved.NUMBERS_FILE), "w", encoding="utf-8") as f:
                f.write("# c\na\ngone\nb\nc\nalso-gone\n")
            self.assertEqual(saved.trail_numbers(ids, d), ["a", "-", "b", "c"])

    def test_the_page_stays_small(self):
        # 220 ids once in number order; the same words are in the rows, so they compress away.
        self.assertLess(len(re.search(r'data-saved-numbers="([^"]*)"', self.page).group(1)), 8000)

    def test_the_owners_list_is_on_the_page(self):
        carried = set(self.numbers())
        for tid in OWNER:
            self.assertIn(tid, carried)


if __name__ == "__main__":
    unittest.main()
