"""Monthly climate normals for a point, downloaded once and cached.

Python 3 standard library only. The estimator (tools/estimate_season.py)
asks this module for the normals at a trail's sample points. Network use
happens only when the cache lacks a point. Every response is cached
outside the repository, requests go one at a time with a short pause, and
the same point is never requested twice (a point with no data is cached
as having no data). Run the trial with:

    python3 tools/estimate_season.py trial

Source chosen
=============
ERA5-Land through the Open-Meteo Historical Weather API: daily maximum
temperature and daily maximum snow depth, averaged by month over
2011-2020, at the elevation asked for (the API adjusts both values to
that elevation). SOURCE below names it for the record entries.

Licences, read on each publisher's own terms page (2026-11-20):

- Open-Meteo licence page, https://open-meteo.com/en/licence:
  "API data are offered under Attribution 4.0 International (CC BY 4.0)".
  Its terms page, https://open-meteo.com/en/terms, adds for the free
  API: "You may only use the free API services for non-commercial
  purposes." and "Less than 10'000 API calls per day, 5'000 per hour
  and 600 per minute." This dataset is a public, non-commercial one, and
  the CC BY 4.0 data licence is met by the attribution in NOTICE.md and
  the source entry on each estimated record. The rate limit is why the
  period is the last ten years of the normals period and not all
  thirty: one point for 1991-2020 costs about 156 of the 600 units
  allowed per minute, so the roughly 900 sample points would need about
  five hours of throttled requests; ten years cost about 52 units a
  point. The rule's thresholds are fitted on the same ten years, so a
  steady offset between the decade and the thirty year normals is
  mostly absorbed by the fit. Widening the period later only refills
  the cache.
- NOAA (US only), https://www.weather.gov/disclaimer: "The information
  on National Weather Service (NWS) Web pages are in the public domain,
  unless specifically noted otherwise, and may be used without charge
  for any lawful purpose". The 1991-2020 monthly normals are station
  values, and the product carries temperature and precipitation only:
  its station files have no snow depth variable, so the snow test
  would be dropped. SNODAS snow depth is a separate daily US grid with
  no point service.
- Environment and Climate Change Canada (Canada only), normals under
  the Open Government Licence, Canada,
  https://open.canada.ca/en/open-government-licence-canada: "The
  Information Provider grants you a worldwide, royalty-free, perpetual,
  non-exclusive licence to use the Information, including for
  commercial purposes", with acknowledgement of the source. The MSC
  GeoMet normals collection trialled here is the 1981-2010 station
  normals. It has mean daily maximum temperature but no snow depth
  (total snowfall is not depth), and its features carry no station
  elevation, so no lapse adjustment to a trail's high ground is
  possible.

Why the others lost: neither station product covers both countries,
neither gives snow depth, and neither gives values at the elevation of
a trail's high ground, which is what decides when an alpine trail
opens. Stations also thin out exactly where trails are wildest (the
trial's far north point has no station in range). Open-Meteo returns
temperature and snow depth at the elevation asked for, for every
trial trail in both countries. Its weakness is the free API's
non-commercial access term, recorded above for the owner.

Trial (twelve sourced trails, 2026-11-20, one coarse default rule
for every candidate: the high point at least 5 C and at most 10 cm of
snow where snow exists, the low point at most 32 C; high and low track
points only, place centres for akshayuk-pass and
desert-winter-thru-hike, which have no track or ends; rerun with the
trial command above once the estimator exists). The akshayuk-pass
place centre falls in water, where the land model has no values, and
no station is in range, so every candidate lacks data there. NOAA
reached west-coast-trail across the border from a US station.

  open-meteo: trail (sourced months) gives estimated months, grade
    akshayuk-pass (7,8): no data
    great-divide-trail (7,8,9): 7,8,9, exact
    west-coast-trail (5,6,7,8,9): all year, worse
    john-muir (7,8,9): 6,7,8,9, within1
    colorado-trail (7,8,9): 7,8,9, exact
    uinta-highline (7,8,9): 7,8,9, exact
    desert-winter-thru-hike (12,1,2): 1,2,3,4,5,8,9,10,11,12, worse
    arizona (2,3,9,10): 3,4,10,11, within1
    florida (10,11,12,1,2,3,4): all year, worse
    washington-coast-trail (5,6,7,8,9): all year, worse
    maah-daah-hey (all year): 3,4,5,6,7,8,9,10,11, worse
    superior-hiking (6,7,8,9): 5,6,7,8,9,10, within1
  Data for 11 of 12, exact or within one month for 6 of the 11.

  noaa: trail (sourced months) gives estimated months, grade
    akshayuk-pass (7,8): no data
    great-divide-trail (7,8,9): no data
    west-coast-trail (5,6,7,8,9): all year, worse
    john-muir (7,8,9): 5,6,7,8,9,10, worse
    colorado-trail (7,8,9): 5,6,7,8,9,10, worse
    uinta-highline (7,8,9): 5,6,7,8,9, worse
    desert-winter-thru-hike (12,1,2): 1,2,3,4,5,9,10,11,12, worse
    arizona (2,3,9,10): 4,10, worse
    florida (10,11,12,1,2,3,4): all year, worse
    washington-coast-trail (5,6,7,8,9): all year, worse
    maah-daah-hey (all year): 3,4,5,6,7,8,9,10,11, worse
    superior-hiking (6,7,8,9): 4,5,6,7,8,9,10, worse
  Data for 10 of 12, exact or within one month for 0 of the 10. With
  no snow measure the alpine seasons all open about two months early.

  eccc: trail (sourced months) gives estimated months, grade
    akshayuk-pass (7,8): no data
    great-divide-trail (7,8,9): 4,5,6,7,8,9,10, worse
    west-coast-trail (5,6,7,8,9): all year, worse
    john-muir (7,8,9): no data
    colorado-trail (7,8,9): no data
    uinta-highline (7,8,9): no data
    desert-winter-thru-hike (12,1,2): no data
    arizona (2,3,9,10): no data
    florida (10,11,12,1,2,3,4): no data
    washington-coast-trail (5,6,7,8,9): partial data
    maah-daah-hey (all year): no data
    superior-hiking (6,7,8,9): partial data
  Data for 2 of 12 (the Canadian trails), exact or within one month
  for 0 of the 2.
"""
import sys

sys.dont_write_bytecode = True

import csv
import io
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

CACHE_DIR = os.environ.get("LONGHIKES_CLIMATE_CACHE") or os.path.join(
    os.path.expanduser("~"), ".cache", "longhikes-climate")

SOURCE = {
    "name": "ERA5-Land via Open-Meteo",
    "publisher": "Open-Meteo.com",
    "url": "https://open-meteo.com/en/docs/historical-weather-api",
    "licence": "CC BY 4.0",
    "period": "2011-2020",
}

USER_AGENT = "Mozilla/5.0"
DELAY_S = 0.15
LAPSE_C_PER_KM = 6.5
ERA5_YEARS = (2011, 2020)
NOAA_MAX_KM = 150.0
ECCC_MAX_KM = 250.0

_LAST_AT = [0.0]
_REMAINING = [None]


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


def _pace():
    """One request at a time, a short pause, and respect for the free
    API's per-minute allowance when it reports one."""
    if _REMAINING[0] is not None and _REMAINING[0] < 60:
        time.sleep(61)
        _REMAINING[0] = None
    wait = DELAY_S - (time.time() - _LAST_AT[0])
    if wait > 0:
        time.sleep(wait)


def _get_bytes(url, opener, timeout=180):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(4):
        _pace()
        try:
            with opener(req, timeout=timeout) as resp:
                raw = resp.read()
                headers = getattr(resp, "headers", None) or {}
                try:
                    _REMAINING[0] = float(headers.get("X-RateLimit-Remaining"))
                except (TypeError, ValueError):
                    pass
            _LAST_AT[0] = time.time()
            return raw
        except urllib.error.HTTPError as exc:
            _LAST_AT[0] = time.time()
            if exc.code == 429 and attempt < 3:
                time.sleep(65)
                continue
            raise


def _cache_path(cache, source, lat, lon, elev_m):
    elev_key = "cell" if elev_m is None else str(int(round(elev_m)))
    return os.path.join(cache, f"{source}_{lat:.3f}_{lon:.3f}_{elev_key}.json")


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
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, sort_keys=True)
        f.write("\n")


def _rounded(lat, lon):
    return round(float(lat), 3), round(float(lon), 3)


# ---------------------------------------------------------------------------
# Open-Meteo (ERA5-Land), the chosen source.

def _open_meteo_url(lat, lon, elev_m):
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": f"{ERA5_YEARS[0]}-01-01", "end_date": f"{ERA5_YEARS[1]}-12-31",
        "daily": "temperature_2m_max,snow_depth_max",
        "timezone": "UTC", "models": "era5_land",
    }
    if elev_m is not None:
        params["elevation"] = int(round(elev_m))
    return ("https://archive-api.open-meteo.com/v1/archive?"
            + urllib.parse.urlencode(params))


def parse_open_meteo(raw, lat, lon, elev_m):
    """Daily ERA5-Land values averaged by month, or None. Snow depths
    arrive in metres and leave in cm. A month with no temperature value
    at all is missing data, never zero; a point whose snow values are
    absent (open water) keeps its temperatures with snow_cm None."""
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    daily = doc.get("daily") or {}
    days = daily.get("time") or []
    tmax = daily.get("temperature_2m_max") or []
    snow = daily.get("snow_depth_max") or []
    if not days or len(tmax) != len(days):
        return None
    by_month_t = [[] for _ in range(12)]
    by_month_s = [[] for _ in range(12)]
    for i, day in enumerate(days):
        try:
            month = int(day[5:7])
        except (TypeError, ValueError, IndexError):
            return None
        if tmax[i] is not None:
            by_month_t[month - 1].append(float(tmax[i]))
        if i < len(snow) and snow[i] is not None:
            by_month_s[month - 1].append(float(snow[i]))
    if any(not values for values in by_month_t):
        return None
    tmax_c = tuple(round(sum(v) / len(v), 1) for v in by_month_t)
    if all(by_month_s):
        snow_cm = tuple(round(sum(v) / len(v) * 100.0, 1) for v in by_month_s)
    else:
        snow_cm = None
    elev = float(elev_m) if elev_m is not None else float(doc.get("elevation") or 0.0)
    return PointNormals(lat=lat, lon=lon, elev_m=elev, tmax_c=tmax_c, snow_cm=snow_cm)


def fetch_open_meteo(lat, lon, elev_m, cache=CACHE_DIR, opener=urllib.request.urlopen):
    lat, lon = _rounded(lat, lon)
    path = _cache_path(cache, "open-meteo", lat, lon, elev_m)
    hit, got = _read_cache(path)
    if hit:
        return got
    raw = _get_bytes(_open_meteo_url(lat, lon, elev_m), opener)
    got = parse_open_meteo(raw, lat, lon, elev_m)
    _write_cache(path, got)
    return got


# ---------------------------------------------------------------------------
# NOAA 1991-2020 monthly station normals (US only, temperature only).

NOAA_STATIONS_URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt"
NOAA_NORMALS_URL = ("https://www.ncei.noaa.gov/data/normals-monthly/"
                    "1991-2020/access/{sid}.csv")


def _noaa_stations(cache, opener):
    path = os.path.join(cache, "noaa_ghcnd-stations.txt")
    if not os.path.exists(path):
        raw = _get_bytes(NOAA_STATIONS_URL, opener)
        os.makedirs(cache, exist_ok=True)
        with open(path, "wb") as f:
            f.write(raw)
    stations = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 4 or not parts[0].startswith("US"):
                continue
            try:
                stations.append((parts[0], float(parts[1]), float(parts[2]),
                                 float(parts[3])))
            except ValueError:
                continue
    return stations


def parse_noaa_csv(raw, lat, lon, elev_m):
    """MLY-TMAX-NORMAL is in degrees F. Temperatures are lapse adjusted
    from the station elevation to the elevation asked for. The product
    has no snow depth, so snow_cm is None."""
    text = raw.decode("utf-8", errors="replace")
    rows = {}
    station_elev = None
    for row in csv.DictReader(io.StringIO(text)):
        try:
            month = int(row.get("month") or 0)
            value = float(row.get("MLY-TMAX-NORMAL") or "")
            station_elev = float(row.get("ELEVATION") or 0.0)
        except ValueError:
            continue
        if 1 <= month <= 12:
            rows[month] = value
    if len(rows) != 12 or station_elev is None:
        return None
    lapse = 0.0
    if elev_m is not None:
        lapse = LAPSE_C_PER_KM * (float(elev_m) - station_elev) / 1000.0
    tmax_c = tuple(round((rows[m] - 32.0) * 5.0 / 9.0 - lapse, 1)
                   for m in range(1, 13))
    elev = float(elev_m) if elev_m is not None else station_elev
    return PointNormals(lat=lat, lon=lon, elev_m=elev, tmax_c=tmax_c, snow_cm=None)


def fetch_noaa(lat, lon, elev_m, cache=CACHE_DIR, opener=urllib.request.urlopen):
    lat, lon = _rounded(lat, lon)
    path = _cache_path(cache, "noaa", lat, lon, elev_m)
    hit, got = _read_cache(path)
    if hit:
        return got
    near = sorted(
        ((haversine_km(lat, lon, slat, slon), sid)
         for sid, slat, slon, _selev in _noaa_stations(cache, opener)),
    )
    got = None
    tried = 0
    # Most GHCN stations have no normals file, so walk past the ones
    # that answer 404; the nearest normals station is rarely the
    # nearest station of any kind.
    for dist, sid in near:
        if dist > NOAA_MAX_KM or tried >= 30:
            break
        tried += 1
        csv_path = os.path.join(cache, f"noaa_{sid}.csv")
        if os.path.exists(csv_path):
            with open(csv_path, "rb") as f:
                raw = f.read()
        else:
            try:
                raw = _get_bytes(NOAA_NORMALS_URL.format(sid=sid), opener)
            except urllib.error.HTTPError:
                continue
            os.makedirs(cache, exist_ok=True)
            with open(csv_path, "wb") as f:
                f.write(raw)
        got = parse_noaa_csv(raw, lat, lon, elev_m)
        if got is not None:
            break
    _write_cache(path, got)
    return got


# ---------------------------------------------------------------------------
# MSC GeoMet climate normals (Canada only, 1981-2010 stations).

ECCC_ELEMENT = "Mean daily max temperature deg C"
ECCC_URL = "https://api.weather.gc.ca/collections/climate-normals/items"


def _eccc_url(lat, lon):
    bbox = f"{lon - 1.5},{lat - 1.0},{lon + 1.5},{lat + 1.0}"
    params = {"bbox": bbox, "limit": 10000, "f": "json",
              "E_NORMAL_ELEMENT_NAME": ECCC_ELEMENT}
    return ECCC_URL + "?" + urllib.parse.urlencode(params)


def parse_eccc(raw, lat, lon, elev_m):
    """The nearest station with all twelve months of mean daily maximum
    temperature. The features carry no station elevation and no snow
    depth, so neither can be given."""
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    stations = {}
    for feat in doc.get("features") or []:
        props = feat.get("properties") or {}
        if props.get("E_NORMAL_ELEMENT_NAME") != ECCC_ELEMENT:
            continue
        try:
            month = int(props.get("MONTH") or 0)
            value = float(props.get("VALUE"))
            slon, slat = (feat.get("geometry") or {}).get("coordinates") or (None, None)
            slat, slon = float(slat), float(slon)
        except (TypeError, ValueError):
            continue
        if not 1 <= month <= 12:
            continue
        entry = stations.setdefault(props.get("STN_ID"), (slat, slon, {}))
        entry[2][month] = value
    best = None
    for slat, slon, months in stations.values():
        if len(months) != 12:
            continue
        dist = haversine_km(lat, lon, slat, slon)
        if best is None or dist < best[0]:
            best = (dist, months)
    if best is None or best[0] > ECCC_MAX_KM:
        return None
    tmax_c = tuple(round(best[1][m], 1) for m in range(1, 13))
    elev = float(elev_m) if elev_m is not None else 0.0
    return PointNormals(lat=lat, lon=lon, elev_m=elev, tmax_c=tmax_c, snow_cm=None)


def fetch_eccc(lat, lon, elev_m, cache=CACHE_DIR, opener=urllib.request.urlopen):
    lat, lon = _rounded(lat, lon)
    path = _cache_path(cache, "eccc", lat, lon, elev_m)
    hit, got = _read_cache(path)
    if hit:
        return got
    raw = _get_bytes(_eccc_url(lat, lon), opener)
    got = parse_eccc(raw, lat, lon, elev_m)
    _write_cache(path, got)
    return got


def fetch_normals(lat, lon, elev_m, cache=CACHE_DIR, opener=urllib.request.urlopen):
    """Normals from the chosen source (see SOURCE), or None when it has
    no data for the point. Never returns invented zeros."""
    return fetch_open_meteo(lat, lon, elev_m, cache=cache, opener=opener)


CANDIDATES = {
    "open-meteo": fetch_open_meteo,
    "noaa": fetch_noaa,
    "eccc": fetch_eccc,
}
