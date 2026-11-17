"""Plain words for the record's coded values, and number formatting.

Every coded value in docs/schema.md that a page shows has a label here, with
a one-line meaning taken from the schema or the README.
"""
from .markup import Markup, esc

KM_PER_MI = 1.609344

COUNTRIES = {"US": "United States", "CA": "Canada"}

US_STATES = {
    "AK": "Alaska", "AL": "Alabama", "AR": "Arkansas", "AZ": "Arizona", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DC": "District of Columbia", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "IA": "Iowa", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "MA": "Massachusetts",
    "MD": "Maryland", "ME": "Maine", "MI": "Michigan", "MN": "Minnesota", "MO": "Missouri",
    "MS": "Mississippi", "MT": "Montana", "NC": "North Carolina", "ND": "North Dakota",
    "NE": "Nebraska", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NV": "Nevada",
    "NY": "New York", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VA": "Virginia", "VT": "Vermont", "WA": "Washington",
    "WI": "Wisconsin", "WV": "West Virginia", "WY": "Wyoming",
}
CA_PROVINCES = {
    "AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba", "NB": "New Brunswick",
    "NL": "Newfoundland and Labrador", "NS": "Nova Scotia", "NT": "Northwest Territories",
    "NU": "Nunavut", "ON": "Ontario", "PE": "Prince Edward Island", "QC": "Quebec",
    "SK": "Saskatchewan", "YT": "Yukon",
}
ALL_CANADA = "all provinces and territories"

# (label, meaning). Meanings follow docs/schema.md and README.md.
TIERS = {
    "national": ("National Scenic Trail", "A United States National Scenic Trail"),
    "regional": ("Regional", "A long trail of 50 miles (80 km) or more"),
    "short": ("Short", "A well-known multi-day trail of 37 to 50 miles (60 to 80 km)"),
    "deferred": ("Deferred", "Listed, but something about it is not settled; the record's note says what"),
    "candidate": ("Candidate", "Listing not yet decided"),
}
WAVES = {
    "1": ("First set", "In the first set of trails"),
    "held": ("Held", "Listed, but something about it is not settled"),
}
INCLUSION = {
    "nst-unconditional": ("Listed as a National Scenic Trail", "A National Scenic Trail is listed unless it cannot be walked from one end to the other"),
    "candidate-decision-pending": ("Candidate", "The decision to list it is pending"),
}
KINDS = {
    "designated": ("Official trail",
                   "Looked after as one trail by a land agency or a trail association"),
    "route": ("Route",
              "A trail that a hiker worked out and published. No agency or association looks after it "
              "as one trail, and there may be no signs for it"),
}
SOURCE_STATUS = {
    "verified": ("Verified", "The track was downloaded from the source and measured"),
    "found": ("Found", "The source was located but not downloaded"),
    "osm-only": ("OpenStreetMap only", "The only source is an OpenStreetMap route relation"),
    "none": ("None", "No source of a track"),
}
LICENCES = {
    "us-gov-public-domain": "US public domain",
    "CC-BY-4.0": "CC BY 4.0",
    "CC-BY": "CC BY",
    "ODbL-1.0": "ODbL 1.0",
    "stated-permission": "Shared with permission",
    "CC-BY-NC-ND-4.0": "CC BY-NC-ND 4.0",
    "none-stated": "None stated",
    "restricted": "Restricted",
    "unknown": "Unknown",
}
LICENCE_NOTES = {
    "stated-permission": ("Shared with permission. The holder has said in writing that this track may be "
                          "shared. It is not public domain and not a Creative Commons licence."),
}
LICENCE_URLS = {
    "us-gov-public-domain": "https://www.usa.gov/government-works",
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "ODbL-1.0": "https://opendatacommons.org/licenses/odbl/1-0/",
    "CC-BY-NC-ND-4.0": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
}
POLICIES = {
    "open": ("Open", "The author publishes the track freely",
             "A track is included only where the author's terms allow passing it on, or where "
             "OpenStreetMap carries the route as a route relation. Otherwise get it from the author."),
    "sold": ("Sold", "The route is got by buying a guide or map set",
             "No track is included from any source, OpenStreetMap included."),
    "withheld": ("Withheld", "The author chooses not to publish a track",
                 "No track is included from any source, OpenStreetMap included."),
    "unclear": ("Unclear", "Whether the author shares the track is not settled",
                "No track is included until it is settled."),
}
SHIELD_STATUS = {
    "use-real-logo": ("Logo in use", "The trail has a logo"),
    "no-logo-exists": ("No emblem of its own", "The trail has no emblem of its own"),
    "logo-not-found": ("Emblem not found", "An emblem exists or may exist, but no usable artwork of it was found"),
}
ACCESS = {"free": "Free", "purchase": "Purchase"}
DECISIONS = {"included-named": "Included with its name"}


def label(table, key):
    """The label for a coded value; the raw value itself when the table has none."""
    entry = table.get(str(key))
    return entry[0] if isinstance(entry, tuple) else (entry or str(key))


def meaning(table, key):
    entry = table.get(str(key))
    return entry[1] if isinstance(entry, tuple) else ""


def region_name(code):
    if code == ALL_CANADA:
        return "All provinces and territories"
    return US_STATES.get(code) or CA_PROVINCES.get(code) or code


def region_country(code):
    """"US" or "CA" for a state, province or territory code; "CA" for all of Canada; "" when unknown."""
    if code == ALL_CANADA or code in CA_PROVINCES:
        return "CA"
    if code in US_STATES:
        return "US"
    return ""


def region_key(code, country):
    """Filter value for a region: "US-AZ", "CA-ON"; "CA-*" for all of Canada."""
    if code == ALL_CANADA:
        return "CA-*"
    if code in CA_PROVINCES:
        return f"CA-{code}"
    if code in US_STATES:
        return f"US-{code}"
    return f"{country}-{code}"


def fmt_int(n):
    return f"{int(round(n)):,}"


def fmt_km(km):
    """1287 -> "1,287"; 1255.1 -> "1,255.1"."""
    if float(km).is_integer():
        return f"{int(km):,}"
    return f"{km:,.1f}"


def fmt_km1(km):
    """A measured length, always with one decimal: 2.0 -> "2.0", 1141 -> "1,141.0"."""
    return f"{float(km):,.1f}"


def km_to_mi(km):
    return km / KM_PER_MI


def m_to_ft(m):
    return m / M_PER_FT


def fmt_percent(p):
    """-2.5 -> "−2.5%" (true minus sign), 0.9 -> "+0.9%", 0 -> "0.0%"."""
    if p == 0:
        return "0.0%"
    sign = "+" if p > 0 else "−"
    return f"{sign}{abs(p):.1f}%"


def fmt_bytes(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} MB"
    if n >= 1_000:
        return f"{round(n / 1_000):,} KB"
    return f"{n} B"


def length(km, style="inline", mi=None, measured=False):
    """A length in both units. Miles come first unless the reader chose kilometres (CSS).

    style "inline": "800 mi (1,287 km)"; "stack": large first unit over small second.
    measured: a measured length, always written with its one decimal ("2.0 km").
    """
    mi = km_to_mi(km) if mi is None else mi
    km_text = f"{fmt_km1(km) if measured else fmt_km(km)} km"
    whole = float(km).is_integer() and not measured
    mi_text = f"{fmt_int(mi)} mi" if whole or mi >= 100 else f"{mi:,.1f} mi"
    return Markup(f'<span class="len len--{style}"><span class="len__mi">{esc(mi_text)}</span>'
                  f'<span class="len__km">{esc(km_text)}</span></span>')


def distances(kms):
    """Several measured distances in both units, as lengths are: "0.0, 12.4 mi" with "0.0, 20.0 km"
    behind it, the reader's order decided by CSS. Markup."""
    kms = list(kms)
    mi = ", ".join(f"{km_to_mi(k):,.1f}" for k in kms) + " mi"
    km = ", ".join(fmt_km1(k) for k in kms) + " km"
    return Markup(f'<span class="len len--inline"><span class="len__mi">{esc(mi)}</span>'
                  f'<span class="len__km">{esc(km)}</span></span>')


# Hiker facts ([hike] table) -------------------------------------------------

M_PER_FT = 0.3048

TERRAIN = {
    "alpine": "Alpine", "forest": "Forest", "desert": "Desert", "coast": "Coast",
    "prairie": "Prairie", "canyon": "Canyon", "tundra": "Tundra", "lakes": "Lakes",
    "farmland": "Farmland",
}
# The [hike] fields a [[hike.source]] may name in `facts`, in plain words.
HIKE_FACTS = {
    "summary": "description", "official_url": "official site", "start": "start", "end": "end",
    "shape": "shape", "days": "time", "season": "season", "months": "season", "travel": "walking", "high_point": "high point",
    "high_point_m": "high point elevation", "terrain": "terrain", "permit": "permits",
    "unfinished": "unfinished sections", "caution": "caution",
}

def _plural(n, unit):
    return f"{n} {unit}" if n == 1 else f"{n} {unit}s"


def fmt_days(days):
    """Usual time to walk a trail in one go, in a unit a person would use.

    [4, 6] -> "4 to 6 days"; [14, 21] -> "2 to 3 weeks"; [150, 210] -> "5 to 7 months".
    Days up to 14, weeks up to 9 weeks (63 days), months beyond. One value, or both
    ends the same after rounding: "5 days", "about 3 weeks". "" for no value.
    """
    if isinstance(days, (int, float)):
        days = [days]
    days = [d for d in (days or []) if isinstance(d, (int, float)) and d > 0]
    if not days:
        return ""
    lo, hi = min(days), max(days)
    if hi <= 14:
        unit, a, b = "day", round(lo), round(hi)
    elif hi <= 63:
        unit, a, b = "week", max(1, round(lo / 7)), max(1, round(hi / 7))
    else:
        unit, a, b = "month", max(1, round(lo / 30.44)), max(1, round(hi / 30.44))
    if a == b:
        return _plural(a, unit) if unit == "day" else "about " + _plural(a, unit)
    return f"{a} to {b} {unit}s"


def elevation(m, style="inline"):
    """An elevation in feet and metres; feet come first unless the reader chose metres,
    with the same len__mi / len__km pair as lengths: "6,644 ft (2,025 m)".
    style "stack" sets the first unit large over the second, as lengths do."""
    ft = m_to_ft(m)
    return Markup(f'<span class="len len--{style}"><span class="len__mi">{esc(fmt_int(ft))} ft</span>'
                  f'<span class="len__km">{esc(fmt_int(m))} m</span></span>')


def join_names(names):
    """["a"] -> "a"; ["a", "b"] -> "a and b"; ["a", "b", "c"] -> "a, b and c"."""
    names = list(names)
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]
