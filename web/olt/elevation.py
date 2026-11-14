"""Elevation facts and the profile, from a trail's elevation.json (docs/schema.md).

The file beside each record holds figures computed from its track and a public
elevation model. This module loads it, states the rules that decide what a page
may honestly show, and draws the profile as SVG at build time.

Rules, all on the file's own fields:
    coverage below LOW_COVERAGE: the figures describe the track only.
    coverage above HIGH_COVERAGE: the track includes more than the trail, so
        the climb is overstated.
    parts above PROFILE_MAX_PARTS: the parts are not in walking order, so no
        profile is drawn; the figures are still shown.
    descent is shown beside the climb only when it differs by more than
        DESCENT_DIFF of the larger figure.
"""
import json
import math
import os
from collections import Counter

from . import words
from .markup import Markup, esc

LOW_COVERAGE = 0.85
HIGH_COVERAGE = 1.15
PROFILE_MAX_PARTS = 10
DESCENT_DIFF = 0.05

COMPUTED_NOTE = "Computed from the track."

_REQUIRED = ("highest", "lowest", "ascent_m", "descent_m", "track_km",
             "published_km", "coverage", "parts", "orientation", "profile", "source")


def load_file(root, tid):
    """The parsed elevation.json of one trail, or None when it has none or it
    does not hold the fields a page needs."""
    path = os.path.join(root, tid, "elevation.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or any(k not in data for k in _REQUIRED):
        return None
    if not all(isinstance(data[k], dict) and "m" in data[k] for k in ("highest", "lowest")):
        return None
    if not isinstance(data.get("source"), dict) or not isinstance(data.get("profile"), list):
        return None
    return data


def get(rec):
    """A record's elevation facts (derived.elevation), or None."""
    value = rec.get("derived", {}).get("elevation")
    return value if isinstance(value, dict) else None


def direction_words(elev):
    """"walking south to north", from the file's orientation."""
    text = str(elev.get("orientation", "")).replace("-", " ")
    return f"walking {text}" if text else ""


def coverage_kind(elev):
    """"partial" well under 1, "over" well over 1, else ""."""
    cov = elev.get("coverage")
    if not isinstance(cov, (int, float)):
        return ""
    if cov < LOW_COVERAGE:
        return "partial"
    if cov > HIGH_COVERAGE:
        return "over"
    return ""


def coverage_percent(elev):
    """"about 59%", or "less than 1%" for a track that barely exists."""
    pct = (elev.get("coverage") or 0) * 100
    if pct < 1:
        return "less than 1%"
    return f"about {round(pct):,}%"


def coverage_caveat(elev):
    """What the coverage means for the figures, or "" when it is near 1."""
    kind = coverage_kind(elev)
    if kind == "partial":
        return ("The elevation figures are for the track only. The track covers "
                f"{coverage_percent(elev)} of the published length.")
    if kind == "over":
        return ("The track is longer than the published length "
                f"({coverage_percent(elev)} of it). It includes more than the trail, such as "
                "side trails or alternates, so the climb is overstated.")
    return ""


def show_descent(elev):
    """True when descent differs from ascent by more than a few percent."""
    up, down = elev.get("ascent_m") or 0, elev.get("descent_m") or 0
    bigger = max(up, down)
    return bool(bigger) and abs(up - down) / bigger > DESCENT_DIFF


def show_profile(elev):
    """True when a profile may be drawn: few enough parts to be in walking order."""
    return (elev.get("parts") or 0) <= PROFILE_MAX_PARTS and len(elev.get("profile") or []) >= 2


def parts_caveat(elev):
    """Why no profile is drawn, when the track is in too many parts."""
    if len(elev.get("profile") or []) < 2:
        return "No profile is drawn. The track has too few sampled points to draw one."
    parts = elev.get("parts") or 0
    if parts <= PROFILE_MAX_PARTS:
        return ""
    return (f"No profile is drawn. The track is in many parts ({parts} in the elevation "
            "sampling) and they are not in walking order, so a line through them would not "
            "be the walk. The figures above are still from the whole track, with no climb "
            "counted across a gap.")


def plain_elevation(m):
    """"2,025 m (6,644 ft)", for a sentence or a text alternative."""
    return f"{words.fmt_int(m)} m ({words.fmt_int(m / words.M_PER_FT)} ft)"


def plain_length(km):
    return f"{words.fmt_km1(km)} km ({words.fmt_int(words.km_to_mi(km))} mi)"


def is_sea_level(point):
    return (point or {}).get("m") == 0


def summary_sentence(elev, loop=False):
    """The facts in one sentence: the profile's text alternative."""
    high, low = elev["highest"]["m"], elev["lowest"]["m"]
    direction = "" if loop else f", {direction_words(elev)}"
    low_text = "sea level" if low == 0 else plain_elevation(low)
    text = (f"Computed from the track{direction}, the trail climbs "
            f"{plain_elevation(elev['ascent_m'])} in total over {plain_length(elev['track_km'])} "
            f"of track, between a low point of {low_text} and a high point of {plain_elevation(high)}")
    if show_descent(elev):
        text += f", and descends {plain_elevation(elev['descent_m'])}"
    return text + "."


# The profile ----------------------------------------------------------------

def segments(profile, part_starts=()):
    """The profile split into its parts. A part's first point repeats the
    distance of the point before it (docs/schema.md), and part_starts_km names
    those distances; a new part starts there, never joined to the last."""
    starts = Counter(part_starts or ())
    out, current, prev = [], [], None
    for point in profile or ():
        dist = point[0]
        if current and dist <= prev and (dist < prev or starts.get(dist, 0) or not starts):
            if starts.get(dist, 0):
                starts[dist] -= 1
            out.append(current)
            current = []
        current.append(point)
        prev = dist
    if current:
        out.append(current)
    return out


def _nice_step(span, target=5):
    if span <= 0:
        return 1.0
    raw = span / target
    mag = 10 ** math.floor(math.log10(raw))
    for mult in (1, 2, 5, 10):
        if raw <= mult * mag:
            return float(mult * mag)
    return float(10 * mag)


def _ticks(lo, hi, target=5):
    step = _nice_step(hi - lo, target)
    value = math.ceil(lo / step) * step
    out = []
    while value <= hi + step * 1e-9:
        out.append(round(value, 10))
        value += step
    return out, step


def _fmt_tick(value, step):
    if step >= 1:
        return f"{round(value):,}"
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text


W, H = 680, 270
LEFT, RIGHT, TOP, BOTTOM = 58, 14, 14, 40


def profile_svg(elev, loop=False):
    """The profile as inline SVG, drawn now, not by a script. Both unit systems
    are drawn; CSS shows one, through the same len__km / len__mi pair and the
    reader's unit preference as every length on the site."""
    profile = elev.get("profile") or []
    if len(profile) < 2:
        return Markup("")
    plot_w, plot_h = W - LEFT - RIGHT, H - TOP - BOTTOM
    x_max = max(float(elev.get("track_km") or 0), max(p[0] for p in profile), 0.001)
    low_m = min(float(elev["lowest"]["m"]), min(p[1] for p in profile))
    high_m = max(float(elev["highest"]["m"]), max(p[1] for p in profile))
    span = high_m - low_m
    pad = max(10.0, span * 0.06) if span else 10.0
    y_lo = max(0.0, low_m - pad) if low_m >= 0 else low_m - pad
    y_hi = high_m + pad
    if y_hi <= y_lo:
        y_hi = y_lo + 20

    def x(dist_km):
        return LEFT + dist_km / x_max * plot_w

    def y(elev_m):
        return TOP + (y_hi - elev_m) / (y_hi - y_lo) * plot_h

    paths = []
    for seg in segments(profile, elev.get("part_starts_km")):
        if len(seg) < 2:
            continue
        cmd = "M" + " L".join(f"{x(float(d)):.1f} {y(float(m)):.1f}" for d, m in seg)
        paths.append(cmd)
    line = f'<path class="elev-profile__line" d="{" ".join(paths)}"/>'

    high_pt = max(profile, key=lambda p: p[1])
    low_pt = min(profile, key=lambda p: p[1])
    marks = "".join(
        f'<circle class="elev-profile__mark" cx="{x(float(d)):.1f}" cy="{y(float(m)):.1f}" r="3.5"/>'
        for d, m in (high_pt, low_pt))

    def axis_group(system):
        """Ticks, grid lines and axis titles for one unit system."""
        out = []
        if system == "km":
            yticks, ystep = _ticks(y_lo, y_hi, 4)
            yvals = [(t, t) for t in yticks]
            xticks, xstep = _ticks(0, x_max, 5)
            xvals = [(t, t) for t in xticks]
            ytitle, xtitle = "Elevation (m)", "Distance along the track (km)"
        else:
            yticks, ystep = _ticks(y_lo / words.M_PER_FT, y_hi / words.M_PER_FT, 4)
            yvals = [(t * words.M_PER_FT, t) for t in yticks]
            xticks, xstep = _ticks(0, words.km_to_mi(x_max), 5)
            xvals = [(t * words.KM_PER_MI, t) for t in xticks]
            ytitle, xtitle = "Elevation (ft)", "Distance along the track (mi)"
        for elev_m, label in yvals:
            yy = y(elev_m)
            if TOP - 1 <= yy <= TOP + plot_h + 1:
                out.append(f'<line class="elev-profile__grid" x1="{LEFT}" y1="{yy:.1f}" '
                           f'x2="{LEFT + plot_w}" y2="{yy:.1f}"/>')
                out.append(f'<text class="elev-profile__tick" x="{LEFT - 6}" y="{yy + 4:.1f}" '
                           f'text-anchor="end">{esc(_fmt_tick(label, ystep))}</text>')
        for dist_km, label in xvals:
            xx = x(dist_km)
            if LEFT - 1 <= xx <= LEFT + plot_w + 1:
                anchor = "start" if label == 0 else "middle"
                out.append(f'<text class="elev-profile__tick" x="{xx:.1f}" y="{TOP + plot_h + 18}" '
                           f'text-anchor="{anchor}">{esc(_fmt_tick(label, xstep))}</text>')
        middle_y = TOP + plot_h / 2
        out.append(f'<text class="elev-profile__axis" x="14" y="{middle_y:.1f}" text-anchor="middle" '
                   f'transform="rotate(-90 14 {middle_y:.1f})">{esc(ytitle)}</text>')
        out.append(f'<text class="elev-profile__axis" x="{LEFT + plot_w / 2:.1f}" y="{H - 4}" '
                   f'text-anchor="middle">{esc(xtitle)}</text>')
        cls = "len__km" if system == "km" else "len__mi"
        return f'<g class="{cls}">{"".join(out)}</g>'

    axes = (f'<line class="elev-profile__frame" x1="{LEFT}" y1="{TOP + plot_h}" '
            f'x2="{LEFT + plot_w}" y2="{TOP + plot_h}"/>'
            f'<line class="elev-profile__frame" x1="{LEFT}" y1="{TOP}" '
            f'x2="{LEFT}" y2="{TOP + plot_h}"/>')
    return Markup(
        f'<svg class="elev-profile" viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="{esc(summary_sentence(elev, loop))}" focusable="false">'
        f"{axis_group('km')}{axis_group('mi')}{axes}{line}{marks}</svg>")
