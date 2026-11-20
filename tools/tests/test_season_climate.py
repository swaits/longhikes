"""Tests for tools/season_climate.py. All offline: an injected range
getter serves small synthetic GeoTIFFs laid out like CHELSA's (LZW with
a horizontal predictor, 16 bit) and ETOPO's (deflate with the floating
point predictor).

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import os
import struct
import sys
import tempfile
import unittest
import zlib

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import season_climate as C  # noqa: E402
import validate as V  # noqa: E402

W = H = 8
TW = TH = 4
X0, Y0, RES = -120.0, 40.0, 0.5


def lzw_encode(data):
    """A plain TIFF LZW encoder for short inputs (9 bit codes only)."""
    table = {bytes([i]): i for i in range(256)}
    nxt = 258
    codes = [256]
    cur = b""
    for byte in data:
        nb = cur + bytes([byte])
        if nb in table:
            cur = nb
        else:
            codes.append(table[cur])
            table[nb] = nxt
            nxt += 1
            cur = bytes([byte])
    if cur:
        codes.append(table[cur])
    codes.append(257)
    assert nxt < 500
    bits = "".join(format(c, "09b") for c in codes)
    bits += "0" * (-len(bits) % 8)
    return bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))


def build_tiff(tiles, compression, predictor, bits, sampleformat, meta="", nodata=None):
    """Classic little-endian TIFF, W x H in TW x TH tiles."""
    entries = []
    extra = bytearray()
    base = 8 + 2 + 20 * 12 + 4  # room for up to 20 entries

    def short(tag, v):
        entries.append((tag, 3, 1, struct.pack("<HH", v, 0)))

    def blob(tag, typ, count, payload):
        off = base + len(extra)
        extra.extend(payload)
        entries.append((tag, typ, count, struct.pack("<I", off)))

    short(256, W)
    short(257, H)
    short(258, bits)
    short(259, compression)
    short(277, 1)
    if predictor != 1:
        short(317, predictor)
    short(322, TW)
    short(323, TH)
    short(339, sampleformat)
    blob(33550, 12, 3, struct.pack("<3d", RES, RES, 0.0))
    blob(33922, 12, 6, struct.pack("<6d", 0, 0, 0, X0, Y0, 0))
    if meta:
        text = meta.encode() + b"\x00"
        blob(42112, 2, len(text), text)
    if nodata is not None:
        text = str(nodata).encode() + b"\x00"
        blob(42113, 2, len(text), text)
    # tile offsets and byte counts come after everything else
    n = len(tiles)
    tile_base = base + len(extra) + 8 * n
    offs, pos = [], tile_base
    for t in tiles:
        offs.append(pos)
        pos += len(t)
    blob(324, 4, n, struct.pack("<%dI" % n, *offs))
    blob(325, 4, n, struct.pack("<%dI" % n, *[len(t) for t in tiles]))
    entries.sort()
    ifd = struct.pack("<H", len(entries))
    for tag, typ, count, val in entries:
        ifd += struct.pack("<HHI", tag, typ, count) + val
    ifd += struct.pack("<I", 0)
    head = b"II*\x00" + struct.pack("<I", 8) + ifd
    head += b"\x00" * (base - len(head))
    return head + bytes(extra) + b"".join(tiles)


def tiles_of(values, encode):
    """Cut a W x H grid into tiles (row-major tile order) and encode."""
    out = []
    for ty in range(H // TH):
        for tx in range(W // TW):
            rows = [values[(ty * TH + r) * W + tx * TW: (ty * TH + r) * W + tx * TW + TW]
                    for r in range(TH)]
            out.append(encode(rows))
    return out


def encode_u16(rows):
    """Horizontal predictor, then LZW."""
    raw = b""
    for row in rows:
        prev = 0
        for v in row:
            raw += struct.pack("<H", (v - prev) & 0xFFFF)
            prev = v
    return lzw_encode(raw)


def encode_float(rows):
    """Floating point predictor, then deflate."""
    raw = b""
    for row in rows:
        be = b"".join(struct.pack(">f", v) for v in row)
        planar = bytes(be[j * 4 + k] for k in range(4) for j in range(len(row)))
        diff = bytearray(len(planar))
        prev = 0
        for i, b in enumerate(planar):
            diff[i] = (b - prev) & 255
            prev = b
        raw += bytes(diff)
    return zlib.compress(raw)


def month_file(month, nodata_at=None):
    """Kelvin times ten, one value per cell: 280 K plus the month plus
    the column, so every cell and month is distinguishable."""
    vals = [int((280.0 + month + (i % W) * 0.1) * 10) for i in range(W * H)]
    if nodata_at is not None:
        vals[nodata_at] = 65535
    meta = ('<GDALMetadata><Item name="OFFSET" sample="0" role="offset">0</Item>'
            '<Item name="SCALE" sample="0" role="scale">0.1</Item></GDALMetadata>')
    return build_tiff(tiles_of(vals, encode_u16), 5, 2, 16, 1, meta,
                      nodata=65535 if nodata_at is not None else None)


def dem_file(elev=1000.0):
    vals = [elev] * (W * H)
    return build_tiff(tiles_of(vals, encode_float), 8, 3, 32, 3, nodata=-99999)


class Getter:
    def __init__(self, nodata_at=None, elev=1000.0):
        self.calls = []
        self.files = {}
        for m in range(1, 13):
            self.files[C.CHELSA_URL.format(month=m)] = month_file(
                m, nodata_at if m == 1 else nodata_at)
        self.files[C.ETOPO_URL] = dem_file(elev)

    def __call__(self, url, start, end):
        self.calls.append((url, start, end))
        return self.files[url][start:end + 1]


class ReaderTest(unittest.TestCase):
    def test_lzw_round_trips_repeats(self):
        data = b"ABABABABCCCCCCDDDDABAB" * 5
        self.assertEqual(C.lzw_decode(lzw_encode(data)), data)

    def test_a_chelsa_style_tile_is_read_with_its_predictor_and_scale(self):
        with tempfile.TemporaryDirectory() as cache:
            src = C.Source(C.CHELSA_URL.format(month=3), cache, Getter())
            raw = src.pixel(2, 2)
            self.assertEqual(raw, int((283.0 + 0.2) * 10))
            self.assertAlmostEqual(src.value_nearest(-119.0, 39.0), 283.2, places=1)

    def test_an_etopo_style_float_tile_is_read(self):
        with tempfile.TemporaryDirectory() as cache:
            src = C.Source(C.ETOPO_URL, cache, Getter(elev=1234.5))
            self.assertAlmostEqual(src.value_bilinear(-119.1, 39.2), 1234.5, places=1)


class NormalsTest(unittest.TestCase):
    def test_a_point_becomes_twelve_celsius_values_at_the_cell_elevation(self):
        with tempfile.TemporaryDirectory() as cache:
            n = C.fetch_normals(39.0, -119.0, None, cache=cache, getter=Getter())
            self.assertEqual(len(n.tmax_c), 12)
            self.assertEqual(n.elev_m, 1000.0)
            self.assertIsNone(n.snow_cm)
            self.assertAlmostEqual(n.tmax_c[0], 281.0 + 0.2 - 273.15, places=1)

    def test_values_are_corrected_by_the_lapse_rate_to_the_asked_elevation(self):
        with tempfile.TemporaryDirectory() as cache:
            g = Getter()
            cell = C.fetch_normals(39.0, -119.0, None, cache=cache, getter=g)
            up = C.fetch_normals(39.0, -119.0, 2000, cache=cache, getter=g)
            self.assertEqual(up.elev_m, 2000.0)
            self.assertAlmostEqual(cell.tmax_c[6] - up.tmax_c[6], 6.5, places=1)

    def test_a_second_call_reads_the_cache_not_the_network(self):
        with tempfile.TemporaryDirectory() as cache:
            g = Getter()
            C.fetch_normals(39.0, -119.0, 1500, cache=cache, getter=g)
            first = len(g.calls)
            self.assertGreater(first, 0)
            C.fetch_normals(39.0, -119.0, 1500, cache=cache, getter=g)
            self.assertEqual(len(g.calls), first)

    def test_a_new_getter_still_reads_cached_tiles(self):
        with tempfile.TemporaryDirectory() as cache:
            C.fetch_normals(39.0, -119.0, 1500, cache=cache, getter=Getter())
            g2 = Getter()
            C.fetch_normals(39.2, -119.0, 1500, cache=cache, getter=g2)
            # a different point in the same tiles: no tile range is asked again
            tile_asks = [c for c in g2.calls if c[1] != 0]
            self.assertEqual(tile_asks, [])

    def test_a_point_with_no_data_returns_none_not_zeros(self):
        with tempfile.TemporaryDirectory() as cache:
            # every cell of every month file is nodata
            g = Getter()
            for m in range(1, 13):
                url = C.CHELSA_URL.format(month=m)
                vals = [65535] * (W * H)
                meta = ('<GDALMetadata><Item name="SCALE" role="scale">0.1</Item>'
                        '</GDALMetadata>')
                g.files[url] = build_tiff(tiles_of(vals, encode_u16), 5, 2, 16, 1,
                                          meta, nodata=65535)
            self.assertIsNone(C.fetch_normals(39.0, -119.0, 1500, cache=cache, getter=g))

    def test_a_sea_cell_borrows_the_nearest_land_cell(self):
        with tempfile.TemporaryDirectory() as cache:
            # cell (2, 2) is sea in every month; (3, 2) is land
            g = Getter(nodata_at=2 * W + 2)
            n = C.fetch_normals(39.0, -119.0, None, cache=cache, getter=g)
            self.assertIsNotNone(n)

    def test_a_point_outside_the_grid_has_no_data(self):
        with tempfile.TemporaryDirectory() as cache:
            self.assertIsNone(C.fetch_normals(80.0, -119.0, 100, cache=cache, getter=Getter()))


class SourceTest(unittest.TestCase):
    def test_the_cache_is_outside_the_repository(self):
        self.assertFalse(os.path.abspath(C.CACHE_DIR).startswith(os.path.abspath(V.ROOT)))

    def test_the_source_says_its_licence_and_period(self):
        for key in ("name", "publisher", "url", "licence", "period"):
            self.assertIn(key, C.SOURCE)
            self.assertTrue(str(C.SOURCE[key]).strip())
        self.assertIn("CC0", C.SOURCE["licence"])
        self.assertEqual(C.SOURCE["period"], "1981-2010")


if __name__ == "__main__":
    unittest.main()
