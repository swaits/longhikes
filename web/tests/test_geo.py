import math
import os
import random
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from olt import geo  # noqa: E402

NS = "{http://www.topografix.com/GPX/1/1}"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
M_PER_DEG = math.pi / 180.0 * geo.EARTH_R


def wiggly(n=2000):
    """A noisy west-east line near 45N, about 0.0001 degrees per step."""
    return [[-110.0 + i * 0.0001, 45.0 + 0.00008 * math.sin(i / 7.0)
             + 0.00002 * ((i * 7919) % 13 - 6) / 6.0] for i in range(n)]


def offset(lon, lat, east_m, north_m):
    """Point east_m/north_m metres from (lon, lat), in degrees."""
    return [lon + east_m / (M_PER_DEG * math.cos(math.radians(lat))),
            lat + north_m / M_PER_DEG]


def synthetic_line(lon0, lat0, n=1200, step_m=4.0):
    """A straight-ish line east from (lon0, lat0), wiggling by up to ~15 m."""
    out = []
    for i in range(n):
        north = (9.0 * math.sin(i / 13.0) + 4.0 * math.sin(i / 3.1)
                 + 2.0 * math.sin(i / 0.7))
        out.append(offset(lon0, lat0, i * step_m, north))
    return out


def unit(lon, lat):
    lo, la = math.radians(lon), math.radians(lat)
    return (math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def angle(a, b):
    return math.atan2(math.sqrt(dot(cross(a, b), cross(a, b))), dot(a, b))


def true_dist_to_segment_m(p, a, b):
    """Distance from p to the great-circle arc a-b, independent of any projection.

    Uses 3D unit vectors on the sphere: the perpendicular distance is
    asin(|p . n|) when the foot lies between a and b, otherwise the nearer end.
    """
    P, A, B = unit(p[0], p[1]), unit(a[0], a[1]), unit(b[0], b[1])
    n = cross(A, B)
    nn = math.sqrt(dot(n, n))
    if nn < 1e-15:  # coincident ends: a zero-length segment
        return min(angle(P, A), angle(P, B)) * geo.EARTH_R
    n = (n[0] / nn, n[1] / nn, n[2] / nn)
    s = dot(P, n)
    q = (P[0] - s * n[0], P[1] - s * n[1], P[2] - s * n[2])
    qn = math.sqrt(dot(q, q))
    if qn < 1e-15:
        return 90.0 * M_PER_DEG
    q = (q[0] / qn, q[1] / qn, q[2] / qn)
    if dot(cross(A, q), n) >= -1e-12 and dot(cross(q, B), n) >= -1e-12:
        return abs(math.asin(max(-1.0, min(1.0, s)))) * geo.EARTH_R
    return min(angle(P, A), angle(P, B)) * geo.EARTH_R


class SimplifyTest(unittest.TestCase):
    def assert_dropped_within(self, line, out, limit_m):
        """Every dropped point must lie within limit_m of the kept polyline."""
        positions = []
        j = 0
        for i, c in enumerate(line):
            if j < len(out) and c == out[j]:
                positions.append(i)
                j += 1
        self.assertEqual(j, len(out), "kept points must be a subsequence of the line")
        self.assertEqual(positions[0], 0)
        self.assertEqual(positions[-1], len(line) - 1)
        for k in range(len(positions) - 1):
            a, b = out[k], out[k + 1]
            for i in range(positions[k] + 1, positions[k + 1]):
                d = true_dist_to_segment_m(line[i], a, b)
                self.assertLessEqual(
                    d, limit_m,
                    f"point {i} is {d:.2f} m from the kept segment "
                    f"({out[k]} -> {out[k + 1]}), limit {limit_m} m")

    def test_keeps_end_points_and_only_drops_interior(self):
        line = wiggly()
        out = geo.simplify_part(line, 5.0)
        self.assertEqual(out[0], line[0])
        self.assertEqual(out[-1], line[-1])
        self.assertLess(len(out), len(line))
        it = iter(line)
        self.assertTrue(all(any(c == o for c in it) for o in out))  # subsequence

    def test_dropped_points_within_true_tolerance(self):
        # Checked against spherical ground truth, not the simplification metric.
        # At these longitudes the old Greenwich-centred projection sheared badly.
        tol = 5.0
        for lon0, lat0 in ((-130.0, 63.0), (-70.0, 45.0), (-81.0, 26.0)):
            with self.subTest(lon=lon0, lat=lat0):
                line = synthetic_line(lon0, lat0)
                out = geo.simplify_part(line, tol)
                self.assertLess(len(out), len(line))
                self.assert_dropped_within(line, out, tol * 1.05)

    def test_dropped_points_within_true_tolerance_on_real_line(self):
        parts = geo.read_parts(os.path.join(ROOT, "canol", "line.geojson"))
        line = max(parts, key=len)
        out = geo.simplify_part(line, 5.0)
        self.assertLess(len(out), len(line))
        self.assert_dropped_within(line, out, 5.0 * 1.05)

    def test_short_and_closed_parts(self):
        self.assertEqual(geo.simplify_part([[0, 0], [1, 1]], 100), [[0, 0], [1, 1]])
        loop = [[0, 0], [0, 0.01], [0.01, 0.01], [0.01, 0], [0, 0]]
        out = geo.simplify_part(loop, 5.0)
        self.assertEqual(out[0], out[-1])
        self.assertGreaterEqual(len(out), 4)

    def test_closed_loop_keeps_both_ends(self):
        # First point equals last: the initial segment is degenerate, so the
        # algorithm must split on the farthest point and keep both ends.
        lon0, lat0 = -81.0, 26.0
        loop = [offset(lon0, lat0, 400.0 * math.cos(2 * math.pi * i / 720),
                       400.0 * math.sin(2 * math.pi * i / 720))
                for i in range(721)]
        out = geo.simplify_part(loop, 5.0)
        self.assertEqual(out[0], loop[0])
        self.assertEqual(out[-1], loop[-1])
        self.assertEqual(out[0], out[-1])
        self.assertLess(len(out), len(loop))
        self.assert_dropped_within(loop, out, 5.0 * 1.05)

    def test_huge_part_does_not_recurse(self):
        line = [[-100 + i * 1e-5, 40 + (i % 2) * 1e-6] for i in range(300000)]
        out = geo.simplify_part(line, 5.0)
        self.assertEqual((out[0], out[-1]), (line[0], line[-1]))

    def test_long_north_south_part_keeps_true_tolerance(self):
        # A part spanning ~3 degrees of latitude: a single cosine for the
        # whole part would be wrong at one end.
        line = [offset(-130.0, 61.0, 4.0 * math.sin(i / 5.0), i * 400.0)
                for i in range(900)]
        out = geo.simplify_part(line, 5.0)
        self.assertLess(len(out), len(line))
        self.assert_dropped_within(line, out, 5.0 * 1.05)

    def test_long_north_south_segment_does_not_understate_distance(self):
        # A 780 km segment with the only deviation near its southern end: the
        # cosine at the segment's mean latitude would compute 5.5 m as < 5 m
        # and drop a point that is really too far from the kept line.
        line = [offset(-130.0, 61.0, 0.0, 0.0),
                offset(-130.0, 61.001, 5.5, 0.0),
                offset(-130.0, 68.0, 0.0, 0.0)]
        out = geo.simplify_part(line, 5.0)
        self.assertEqual(len(out), 3, "a point 5.5 m off must not be dropped")
        self.assert_dropped_within(line, out, 5.0 * 1.05)

    def test_elevation_kept(self):
        out = geo.simplify_part([[0, 0, 5], [0.0005, 0.0005, 6], [0.001, 0.001, 7]], 1.0)
        self.assertEqual(out, [[0, 0, 5], [0.001, 0.001, 7]])


class MeasureTest(unittest.TestCase):
    def test_length_one_degree_of_latitude(self):
        self.assertAlmostEqual(geo.length_km([[[0, 0], [0, 1]]]), 111.195, delta=0.01)

    def test_length_known_pair(self):
        # one degree of longitude at 60N is half of one at the equator
        km = geo.length_km([[[10, 60], [11, 60]]])
        self.assertAlmostEqual(km, 55.6, delta=0.1)

    def test_bbox(self):
        self.assertEqual(geo.bbox([[[1, 2], [3, 4]], [[-1, 9], [0, 0]]]), [-1, 0, 3, 9])

    def test_round_coords_drops_repeats_keeps_ele(self):
        out = geo.round_coords([[[1.000001, 2.0, 7], [1.000002, 2.0, 8], [2.0, 3.0, 9]]], 4)
        self.assertEqual(out, [[[1.0, 2.0, 7], [2.0, 3.0, 9]]])

    def test_round_coords_drops_a_part_that_collapses(self):
        collapsing = [[-81.503841, 36.648341], [-81.503849, 36.648349]]
        self.assertEqual(geo.round_coords([collapsing], 4), [])

    def test_round_coords_surviving_part_keeps_its_ends(self):
        collapsing = [[-81.503841, 36.648341], [-81.503849, 36.648349]]
        line = [[1.234561, 2.345678], [1.234562, 2.345679], [3.5, 4.5]]
        out = geo.round_coords([collapsing, line], 4)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0][0], [1.2346, 2.3457])
        self.assertEqual(out[0][-1], [3.5, 4.5])

    def test_round_coords_all_parts_collapse(self):
        collapsing = [[-81.503841, 36.648341], [-81.503849, 36.648349]]
        out = geo.round_coords([collapsing, collapsing], 4)
        self.assertEqual(out, [])
        # Callers in geo.py must cope with no parts left.
        self.assertIsNone(geo.bbox(out))
        self.assertEqual(geo.join_parts(out), [])
        root = ET.fromstring(geo.gpx_text(out, "x"))
        self.assertEqual(root.findall(f".//{NS}trkseg"), [])

    def test_join_parts(self):
        a = [[0, 0], [0, 0.01]]
        b = [[0, 0.02], [0, 0.0100005]]  # reversed, starts far, ends near a's end
        out = geo.join_parts([a, b], 100.0)
        self.assertEqual(len(out), 1)
        self.assertEqual(len(out[0]), 4)


class JoinPartsTest(unittest.TestCase):
    @staticmethod
    def aligned_pair(lat, gap_m, bearing, far_m=300.0):
        """Two parts whose near ends are gap_m apart, their far ends harmless.

        The whole assembly is laid out along one bearing, which exercises the
        bucket grid in every direction (including mostly north-south, where a
        longitude bucket shrunk by cos(lat) is easy to get wrong).
        """
        east, north = math.sin(bearing), math.cos(bearing)
        base = [-110.0, lat]
        near = offset(base[0], base[1], gap_m * east, gap_m * north)
        a = [offset(base[0], base[1], -far_m * east, -far_m * north), base]
        b = [near, offset(base[0], base[1], (gap_m + far_m) * east,
                          (gap_m + far_m) * north)]
        return a, b

    def test_joins_95m_gap_at_all_latitudes(self):
        rnd = random.Random(20261110)
        for lat in (30.0, 49.0, 62.0, 65.25, 68.0):
            for _ in range(200):
                a, b = self.aligned_pair(lat, 95.0, rnd.uniform(0.0, 2.0 * math.pi))
                out = geo.join_parts([a, b], 100.0)
                self.assertEqual(len(out), 1, f"95 m gap not joined at lat {lat}")
                self.assertEqual(len(out[0]), 4)

    def test_does_not_join_150m_gap(self):
        rnd = random.Random(7)
        for lat in (30.0, 49.0, 62.0, 65.25, 68.0):
            for _ in range(50):
                a, b = self.aligned_pair(lat, 150.0, rnd.uniform(0.0, 2.0 * math.pi))
                out = geo.join_parts([a, b], 100.0)
                self.assertEqual(len(out), 2, f"150 m gap joined at lat {lat}")


class GpxTest(unittest.TestCase):
    def test_gpx_segments_and_metadata(self):
        parts = [[[-105.1, 40.1], [-105.2, 40.2]], [[-106.0, 41.0], [-106.1, 41.1], [-106.2, 41.2]]]
        text = geo.gpx_text(parts, "A & B <Trail>", url="https://example.org/?a=1&b=2",
                            attribution='Me "and" you', licence="ODbL-1.0",
                            licence_text="ODbL 1.0 text")
        root = ET.fromstring(text)
        self.assertEqual(root.get("version"), "1.1")
        trks = root.findall(NS + "trk")
        self.assertEqual(len(trks), 1)
        segs = trks[0].findall(NS + "trkseg")
        self.assertEqual([len(s.findall(NS + "trkpt")) for s in segs], [2, 3])
        meta = root.find(NS + "metadata")
        self.assertEqual(meta.find(NS + "name").text, "A & B <Trail>")
        self.assertEqual(meta.find(NS + "link").get("href"), "https://example.org/?a=1&b=2")
        self.assertEqual(meta.find(NS + "copyright").get("author"), 'Me "and" you')
        self.assertIn("ODbL 1.0 text", meta.find(NS + "desc").text)
        self.assertIsNone(root.find(f".//{NS}ele"))

    def test_gpx_elevation_only_when_present(self):
        root = ET.fromstring(geo.gpx_text([[[1, 2, 300.5], [1.000001, 2.000001, 301]]], "x"))
        eles = [e.text for e in root.iter(NS + "ele")]
        self.assertEqual(eles, ["300.5", "301"])

    def test_no_exponent_in_numbers(self):
        root = ET.fromstring(geo.gpx_text([[[0.000001, 0.0], [0.5, 0.5]]], "x"))
        pt = root.find(f".//{NS}trkpt")
        self.assertEqual(pt.get("lon"), "0.000001")


if __name__ == "__main__":
    unittest.main()
