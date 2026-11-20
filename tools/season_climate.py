"""Monthly climate normals for a point, read from bulk gridded files.

Python 3 standard library only. The estimator (tools/estimate_season.py)
asks this module for the normals at a trail's sample points. The grids
are large public files read in place: only the 512 pixel tiles that
cover a point are fetched (HTTP range requests), each tile is cached
outside the repository once, and the values for a point are cached as
one small file. There is no rate limit to wait out; a tile is never
fetched twice, and an interrupted run resumes from the cache.

Source chosen
=============
CHELSA V2.1 climatologies (monthly mean daily maximum near-surface air
temperature, 1981-2010, about 1 km, global land), from WSL, with the
elevation of the grid cell taken from NOAA's ETOPO 2022 relief model
(60 arc second, unrestricted version). The temperature at a trail's own
elevation is the cell's value plus a lapse rate of 6.5 C per km times
the cell's elevation minus the trail's. The source carries no snow
variable, so snow-free months are derived from the temperature at the
trail's high ground (the rule's cold limit stands in for snow) and the
estimate says so.

Why the first choice was dropped. The previous choice was ERA5-Land
served by the Open-Meteo Historical Weather API. Its free tier
allows 5000 weighted units an hour, and one point-year of daily data
for two variables costs about 5 units, so a thirty year normal for the
roughly 900 sample points needs about 139000 units (some 28 hours) and
ten years about 9 hours; only three years fit in about three hours, and
three years is too short to call a normal. Its terms also limit the
free tier to non-commercial use. A bulk grid read locally has no such
limit.

Why not the other bulk grids. WorldClim 2.1 (monthly 1970-2000, free
download) states at https://www.worldclim.org/about.html: "The data are
freely available for academic use and other non-commercial use.
Redistribution or commercial use is not allowed without prior
permission." That fails the public domain or open licence test. NOAA
and Environment Canada station normals lack the coverage of both
countries and a value at a trail's elevation (see the earlier trial in
the repository history).

Licences, read on each publisher's own page (2026-11-20):

- CHELSA, https://www.chelsa-climate.org/datasets/chelsa_climatologies,
  field License: "Creative Commons Zero - No Rights Reserved (CC0 1.0)".
  The same page asks for the citation: Karger, D. N., Conrad, O.,
  Boehner, J., Kawohl, T., Kreft, H., Soria-Auza, R. W., Zimmermann,
  N. E., Linder, H. P., Kessler, M. (2017). Climatologies at high
  resolution for the earth's land surface areas. Scientific Data 4,
  170122. https://doi.org/10.1038/sdata.2017.122. It is credited in
  NOTICE.md although CC0 does not require it.
- ETOPO 2022, https://www.ncei.noaa.gov/products/etopo-global-relief-model:
  the Unrestricted version is described as "Full global coverage, no
  copyright or security distribution restrictions". NOAA NCEI, DOI
  10.25921/fd45-gt74.

Reading the files. Both are tiled GeoTIFFs. CHELSA's tiles are LZW with a
horizontal predictor, 16 bit unsigned, value times 0.1 in kelvin; ETOPO's
are deflate with the floating point predictor. The small readers below
handle exactly those two layouts and refuse anything else, so no library
is needed in CI or in `web/`.
"""
import sys

sys.dont_write_bytecode = True

import array
import hashlib
import json
import math
import os
import re
import struct
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zlib
from dataclasses import dataclass

CACHE_DIR = os.environ.get("LONGHIKES_CLIMATE_CACHE") or os.path.join(
    os.path.expanduser("~"), ".cache", "longhikes-climate")

SOURCE = {
    "name": "CHELSA V2.1 climatologies, with ETOPO 2022 elevation",
    "publisher": "WSL (CHELSA) and NOAA NCEI (ETOPO)",
    "url": "https://www.chelsa-climate.org/datasets/chelsa_climatologies",
    "licence": "CC0 1.0 (CHELSA); NOAA ETOPO 2022 unrestricted",
    "period": "1981-2010",
}

CHELSA_URL = ("https://os.unil.cloud.switch.ch/chelsa02/chelsa/global/"
              "climatologies/tasmax/1981-2010/"
              "CHELSA_tasmax_{month:02d}_1981-2010_V.2.1.tif")
ETOPO_URL = ("https://www.ngdc.noaa.gov/mgg/global/relief/ETOPO2022/data/"
             "60s/60s_surface_elev_gtif/"
             "ETOPO_2022_v1_60s_N90W180_surface.tif")

USER_AGENT = "Mozilla/5.0"
LAPSE_C_PER_KM = 6.5
HEADER_BYTES = 65536
SEARCH_RADIUS = 3  # cells to look for land when the nearest cell is sea

_LOCK = threading.RLock()


@dataclass(frozen=True)
class PointNormals:
    """Monthly normals at one point: twelve mean daily highs in degrees
    C and, when the source has one, twelve mean snow depths in cm."""

    lat: float
    lon: float
    elev_m: float
    tmax_c: tuple
    snow_cm: tuple = None


def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(h))


# ---------------------------------------------------------------------------
# Range reads, cached on disk.

def default_getter(url, start, end):
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT, "Range": f"bytes={start}-{end}"})
    last = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except (urllib.error.URLError, OSError) as exc:
            last = exc
            if isinstance(exc, urllib.error.HTTPError) and exc.code in (403, 404):
                raise
            time.sleep(2 * (attempt + 1))
    raise last


class Source:
    """One tiled GeoTIFF read by range requests."""

    def __init__(self, url, cache=CACHE_DIR, getter=default_getter):
        self.url = url
        self.cache = os.path.join(cache, "tiles")
        self.getter = getter
        self._tiles = {}
        self._ready = False

    # -- cached ranges
    def _range(self, start, end):
        key = hashlib.sha256(f"{self.url}|{start}|{end}".encode()).hexdigest()[:40]
        path = os.path.join(self.cache, key[:2], key + ".bin")
        if os.path.exists(path):
            with open(path, "rb") as f:
                return f.read()
        raw = self.getter(self.url, start, end)
        if len(raw) != end - start + 1 and start != 0:
            raise OSError(f"short read {len(raw)} of {end - start + 1} at {start}")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
        os.replace(tmp, path)
        return raw

    # -- header
    def _load(self):
        with _LOCK:
            if self._ready:
                return
            head = self._range(0, HEADER_BYTES - 1)
            if head[:4] != b"II*\x00":
                raise ValueError("not a little-endian classic TIFF: " + self.url)
            off = struct.unpack("<I", head[4:8])[0]
            n = struct.unpack("<H", head[off:off + 2])[0]
            sizes = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 12: 8}
            fmts = {1: "B", 3: "H", 4: "I", 12: "d"}
            tags = {}
            for i in range(n):
                e = head[off + 2 + i * 12: off + 14 + i * 12]
                tag, typ, cnt = struct.unpack("<HHI", e[:8])
                if typ not in sizes or typ == 5:
                    continue
                size = sizes[typ] * cnt
                if size <= 4:
                    data = e[8:8 + size]
                else:
                    vo = struct.unpack("<I", e[8:12])[0]
                    data = head[vo:vo + size] if vo + size <= len(head) else \
                        self._range(vo, vo + size - 1)
                if typ == 2:
                    tags[tag] = data.rstrip(b"\x00").decode("latin-1")
                else:
                    tags[tag] = struct.unpack("<%d%s" % (cnt, fmts[typ]), data)
            self.width = tags[256][0]
            self.height = tags[257][0]
            self.bits = tags[258][0]
            self.compression = tags[259][0]
            self.predictor = tags.get(317, (1,))[0]
            self.sampleformat = tags.get(339, (1,))[0]
            self.tw = tags[322][0]
            self.th = tags[323][0]
            self.offsets = tags[324]
            self.counts = tags[325]
            self.xres, self.yres = tags[33550][0], tags[33550][1]
            self.x0, self.y0 = tags[33922][3], tags[33922][4]
            meta = tags.get(42112, "")
            m = re.search(r'name="SCALE"[^>]*>([^<]+)<', meta)
            self.scale = float(m.group(1)) if m else 1.0
            m = re.search(r'name="OFFSET"[^>]*>([^<]+)<', meta)
            self.offset = float(m.group(1)) if m else 0.0
            nd = tags.get(42113)
            self.nodata = float(nd) if nd not in (None, "") else None
            self.tiles_across = (self.width + self.tw - 1) // self.tw
            if self.compression not in (5, 8):
                raise ValueError("unsupported compression %d" % self.compression)
            self._ready = True

    # -- tile decoding
    def _decode(self, idx):
        with _LOCK:
            got = self._tiles.get(idx)
        if got is not None:
            return got
        raw = self._range(self.offsets[idx], self.offsets[idx] + self.counts[idx] - 1)
        data = lzw_decode(raw) if self.compression == 5 else zlib.decompress(raw)
        tile = self._to_values(data)
        with _LOCK:
            if len(self._tiles) > 24:
                self._tiles.clear()
            self._tiles[idx] = tile
        return tile

    def _to_values(self, data):
        w, h = self.tw, self.th
        if self.sampleformat == 3 and self.bits == 32 and self.predictor == 3:
            out = array.array("f")
            for r in range(h):
                row = bytearray(data[r * w * 4:(r + 1) * w * 4])
                acc = 0
                for i in range(len(row)):
                    acc = (acc + row[i]) & 255
                    row[i] = acc
                be = bytearray(w * 4)
                for k in range(4):
                    be[k::4] = row[k * w:(k + 1) * w]
                out.extend(struct.unpack(">%df" % w, bytes(be)))
            return out
        if self.bits == 16 and self.sampleformat in (1, 2):
            code = "H" if self.sampleformat == 1 else "h"
            out = array.array(code)
            out.frombytes(data[: w * h * 2])
            if sys.byteorder != "little":
                out.byteswap()
            if self.predictor == 2:
                for r in range(h):
                    acc = 0
                    base = r * w
                    for i in range(w):
                        acc = (acc + out[base + i]) & 0xFFFF
                        out[base + i] = acc
            elif self.predictor != 1:
                raise ValueError("unsupported predictor")
            return out
        raise ValueError("unsupported sample layout")

    # -- pixels
    def pixel(self, col, row):
        """Raw value at an integer cell, or None for outside or nodata."""
        self._load()
        if row < 0 or row >= self.height:
            return None
        col %= self.width
        idx = (row // self.th) * self.tiles_across + col // self.tw
        tile = self._decode(idx)
        v = tile[(row % self.th) * self.tw + (col % self.tw)]
        if self.nodata is not None and v == self.nodata:
            return None
        return v

    def value_nearest(self, lon, lat):
        """Scaled value of the nearest cell that has data, searching a
        few cells outward when the nearest is sea; None if none."""
        self._load()
        col = int(math.floor((lon - self.x0) / self.xres + 0.5))
        row = int(math.floor((self.y0 - lat) / self.yres + 0.5))
        for radius in range(SEARCH_RADIUS + 1):
            best = None
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    if max(abs(dr), abs(dc)) != radius:
                        continue
                    v = self.pixel(col + dc, row + dr)
                    if v is None:
                        continue
                    d = dr * dr + dc * dc
                    if best is None or d < best[0]:
                        best = (d, v)
            if best is not None:
                return best[1] * self.scale + self.offset
        return None

    def value_bilinear(self, lon, lat):
        self._load()
        fx = (lon - self.x0) / self.xres
        fy = (self.y0 - lat) / self.yres
        c0, r0 = int(math.floor(fx)), int(math.floor(fy))
        tx, ty = fx - c0, fy - r0
        total = weight = 0.0
        for dr, wy in ((0, 1 - ty), (1, ty)):
            for dc, wx in ((0, 1 - tx), (1, tx)):
                v = self.pixel(c0 + dc, r0 + dr)
                if v is None:
                    continue
                total += v * wx * wy
                weight += wx * wy
        if weight <= 0:
            return None
        return (total / weight) * self.scale + self.offset


def lzw_decode(data):
    """TIFF LZW (MSB first, early change)."""
    out = []
    base = [bytes([i]) for i in range(256)] + [b"", b""]
    table = list(base)
    bits = 9
    buf = nb = pos = 0
    n = len(data)
    prev = None
    while True:
        while nb < bits:
            if pos >= n:
                return b"".join(out)
            buf = (buf << 8) | data[pos]
            pos += 1
            nb += 8
        code = (buf >> (nb - bits)) & ((1 << bits) - 1)
        nb -= bits
        buf &= (1 << nb) - 1
        if code == 257:
            break
        if code == 256:
            table = list(base)
            bits = 9
            prev = None
            continue
        if prev is None:
            entry = table[code]
        elif code < len(table):
            entry = table[code]
            table.append(prev + entry[:1])
        else:
            entry = prev + prev[:1]
            table.append(entry)
        out.append(entry)
        prev = entry
        ln = len(table)
        bits = 12 if ln >= 2047 else 11 if ln >= 1023 else 10 if ln >= 511 else 9
    return b"".join(out)


# ---------------------------------------------------------------------------
# Normals for a point.

_SOURCES = {}


def _sources(cache, getter):
    key = (cache, id(getter))
    with _LOCK:
        if key not in _SOURCES:
            _SOURCES[key] = (
                [Source(CHELSA_URL.format(month=m), cache, getter) for m in range(1, 13)],
                Source(ETOPO_URL, cache, getter))
        return _SOURCES[key]


def _cache_path(cache, lat, lon, elev_m):
    elev_key = "cell" if elev_m is None else str(int(round(elev_m)))
    return os.path.join(cache, "points", f"chelsa_{lat:.3f}_{lon:.3f}_{elev_key}.json")


def _read_cache(path):
    """(True, normals or None) when cached, else (False, None). A cached
    None means the source had no data for the point."""
    if not os.path.exists(path):
        return False, None
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    if doc.get("no_data"):
        return True, None
    snow = doc.get("snow_cm")
    return True, PointNormals(
        lat=float(doc["lat"]), lon=float(doc["lon"]), elev_m=float(doc["elev_m"]),
        tmax_c=tuple(float(v) for v in doc["tmax_c"]),
        snow_cm=None if snow is None else tuple(float(v) for v in snow))


def _write_cache(path, normals):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if normals is None:
        doc = {"no_data": True}
    else:
        doc = {"lat": normals.lat, "lon": normals.lon, "elev_m": normals.elev_m,
               "tmax_c": list(normals.tmax_c),
               "snow_cm": None if normals.snow_cm is None else list(normals.snow_cm)}
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(doc, f, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def fetch_normals(lat, lon, elev_m, cache=CACHE_DIR, opener=None, getter=None):
    """Normals at the point, at elev_m (the grid cell's own elevation
    when None), or None when the grid has no land value there. Never
    returns invented zeros. `getter(url, start, end)` replaces the
    network for tests; `opener` is accepted and ignored."""
    lat, lon = round(float(lat), 3), round(float(lon), 3)
    path = _cache_path(cache, lat, lon, elev_m)
    found, normals = _read_cache(path)
    if found:
        return normals
    months, dem = _sources(cache, getter or default_getter)
    cell_elev = dem.value_bilinear(lon, lat)
    values = []
    for src in months:
        v = src.value_nearest(lon, lat)
        if v is None:
            values = None
            break
        values.append(v - 273.15)
    if values is None or cell_elev is None:
        normals = None
    else:
        use = cell_elev if elev_m is None else float(elev_m)
        shift = LAPSE_C_PER_KM * (cell_elev - use) / 1000.0
        normals = PointNormals(
            lat=lat, lon=lon, elev_m=use,
            tmax_c=tuple(round(v + shift, 1) for v in values), snow_cm=None)
    _write_cache(path, normals)
    return normals


CANDIDATES = {"chelsa": fetch_normals}
