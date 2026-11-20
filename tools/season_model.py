"""The season estimator: a pure function over monthly climate normals.

Python 3 standard library only, no network. tools/estimate_season.py
finds a trail's sample points and their normals (tools/season_climate.py
downloads them, cached outside the repository) and hands them to this
module. See docs/superpowers/specs/2026-11-20-season-on-every-trail-design.md.

The method, in three parts:

1. Thresholds. A month is in season when the high ground (points at or
   above the upper quartile of the track's elevations) has a median mean
   daily high of at least cold_c_min, and the low ground (points at or
   below the median elevation) has one of at most heat_c_max.
2. Comparable trails. Each trail is described by twelve monthly
   high-ground highs and twelve low-ground highs. The k most similar
   sourced trails (a season some page states) vote, each weighted by
   1 / (distance + 0.05) ** power, on every month.
3. The blend. Each month scores mix * (share of the comparable trails'
   weight that has the month in season) + (1 - mix) * (1 if the
   thresholds pass it else 0), and the month is in season when the score
   reaches cut. The thresholds propose and the comparable trails confirm
   or add, so a desert trail inherits a cool-season pattern and an arctic
   trail a short summer from trails like it.

A month set is never empty: when no month reaches the cut the three
highest scoring months are used and the result says so.

The measure (match, score) is the owner's: a trail's estimated season
matches a sourced one when each end is within one month, a two-window
season is compared window by window, and a year-round season matches
only an estimate of ten or more months. fit_model scores the method by
leave-one-out over the sourced trails: every trail is predicted by a
model that never saw it, including the choice of the numbers above.
"""
import sys

sys.dont_write_bytecode = True

import math
import statistics

import season

EPS = 0.05
FALLBACK_MONTHS = 3
GRID_COLD = list(range(-10, 26))
GRID_HEAT = list(range(15, 46))
GRID_K = (3, 5, 8, 12, 20)
GRID_POWER = (1, 2)
GRID_CUT = (0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7)
GRID_MIX = (0.5, 0.6, 0.7, 0.8, 0.9)
GRID_BLEND_CUT = (0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8)
FULL = 0xFFF


class Params:
    """cold_c_min, heat_c_max (the thresholds), k and power (the comparable
    trails), mix and cut (the blend)."""

    __slots__ = ("cold_c_min", "heat_c_max", "k", "power", "mix", "cut")

    def __init__(self, cold_c_min, heat_c_max, k=20, power=1, mix=0.7, cut=0.65):
        self.cold_c_min = float(cold_c_min)
        self.heat_c_max = float(heat_c_max)
        self.k = int(k)
        self.power = int(power)
        self.mix = float(mix)
        self.cut = float(cut)

    def as_dict(self):
        return {name: getattr(self, name) for name in self.__slots__}

    @classmethod
    def from_dict(cls, doc):
        return cls(**{name: doc[name] for name in cls.__slots__})

    def __eq__(self, other):
        return isinstance(other, Params) and self.as_dict() == other.as_dict()

    def __repr__(self):
        return "Params(%s)" % ", ".join(f"{k}={v!r}" for k, v in self.as_dict().items())


# ---------------------------------------------------------------------------
# Months as 12-bit masks (bit 0 is January) inside; lists of 1..12 outside.

def to_mask(months):
    mask = 0
    for m in months:
        mask |= 1 << (int(m) - 1)
    return mask


def to_months(mask):
    return [m + 1 for m in range(12) if mask >> m & 1]


def _runs(mask):
    """Circular runs of months as (first, last) pairs; December to
    January joins into one run."""
    runs = []
    for m in to_months(mask):
        if runs and m == runs[-1][1] + 1:
            runs[-1][1] = m
        else:
            runs.append([m, m])
    if len(runs) > 1 and runs[0][0] == 1 and runs[-1][1] == 12:
        runs[0][0] = runs.pop()[0]
    return [tuple(r) for r in runs]


def _near(a, b):
    d = abs(a - b)
    return min(d, 12 - d) <= 1


def match(estimated, sourced):
    """The owner's measure, on month lists or masks. A sourced season of
    eleven or twelve months matches an estimate of ten or more. A sourced
    season in two or more windows matches when every window has an
    estimated window within a month at both ends and the estimate has no
    window of its own left over. Any other sourced season matches when
    the estimate's span (season.span) is within a month at each end."""
    est = estimated if isinstance(estimated, int) else to_mask(estimated)
    src = sourced if isinstance(sourced, int) else to_mask(sourced)
    if not est or not src:
        return False
    if bin(src).count("1") >= 11:
        return bin(est).count("1") >= 10
    src_runs = _runs(src)
    if len(src_runs) >= 2:
        est_runs = _runs(est)
        return (all(any(_near(a, c) and _near(b, d) for c, d in est_runs)
                    for a, b in src_runs)
                and all(any(_near(a, c) and _near(b, d) for c, d in src_runs)
                        for a, b in est_runs))
    return season.grade(to_months(est), to_months(src)) != "worse"


def match_strict(estimated, sourced):
    """The stricter measure: match() and, besides, every window of the
    estimate and of the sourced season must have a partner within a month at
    both ends in the other. An estimate with a gap in the middle that the
    sourced season does not have (or the other way round) is a miss, which
    match() does not see when the sourced season is a single window. A
    sourced season of eleven or twelve months is judged as match() judges
    it."""
    est = estimated if isinstance(estimated, int) else to_mask(estimated)
    src = sourced if isinstance(sourced, int) else to_mask(sourced)
    if not match(est, src):
        return False
    if bin(src).count("1") >= 11:
        return True
    est_runs, src_runs = _runs(est), _runs(src)
    return (all(any(_near(a, c) and _near(b, d) for c, d in est_runs) for a, b in src_runs)
            and all(any(_near(a, c) and _near(b, d) for c, d in src_runs) for a, b in est_runs))


def score(estimated, sourced):
    """(match 1 or 0, share of the twelve months classified correctly,
    Jaccard overlap of the month sets)."""
    est = estimated if isinstance(estimated, int) else to_mask(estimated)
    src = sourced if isinstance(sourced, int) else to_mask(sourced)
    union = bin(est | src).count("1")
    return (1.0 if match(est, src) else 0.0,
            bin(~(est ^ src) & FULL).count("1") / 12,
            bin(est & src).count("1") / union if union else 0.0)


# ---------------------------------------------------------------------------
# Climate summary of a trail.

def usable(points):
    """The points as a list, or None when any point lacks data. A trail
    with a gap in its climate data is unestimable, never filled in."""
    if not points:
        return None
    got = list(points)
    for point in got:
        if point is None or len(getattr(point, "tmax_c", ()) or ()) != 12:
            return None
    return got


def high_low(points):
    """Split points into high ground (at or above the upper quartile of
    the elevations, at least one point) and low ground (at or below
    the median). A single point is both."""
    elevs = sorted(p.elev_m for p in points)
    if len(elevs) == 1:
        return points, points
    upper = statistics.quantiles(elevs, n=4, method="inclusive")[2]
    median = statistics.median(elevs)
    high = [p for p in points if p.elev_m >= upper]
    low = [p for p in points if p.elev_m <= median]
    if not high:
        high = [max(points, key=lambda p: p.elev_m)]
    if not low:
        low = [min(points, key=lambda p: p.elev_m)]
    return high, low


def medians(points):
    """(high-ground, low-ground): each twelve median mean daily highs
    rounded to a tenth. None when a point lacks data."""
    got = usable(points)
    if got is None:
        return None
    high, low = high_low(got)

    def med(group):
        return tuple(round(statistics.median(p.tmax_c[m] for p in group), 1)
                     for m in range(12))
    return med(high), med(low)


def threshold_mask(med, params):
    high, low = med
    mask = 0
    for m in range(12):
        if high[m] >= params.cold_c_min and low[m] <= params.heat_c_max:
            mask |= 1 << m
    return mask


def _margins(med, params):
    high, low = med
    return [min(high[m] - params.cold_c_min, params.heat_c_max - low[m])
            for m in range(12)]


def _top(scores, n=FALLBACK_MONTHS):
    order = sorted(range(12), key=lambda m: (-scores[m], m))[:n]
    return sum(1 << m for m in order)


# ---------------------------------------------------------------------------
# Comparable trails.

class Reference:
    """A sourced trail the estimate may compare with."""

    __slots__ = ("id", "med", "mask")

    def __init__(self, tid, med, months):
        self.id = tid
        self.med = med
        self.mask = to_mask(months)


def distance(a, b):
    """Root mean square difference, in tens of degrees, over the
    twenty-four high-ground and low-ground monthly highs."""
    total = 0.0
    for ga, gb in zip(a, b):
        for m in range(12):
            total += ((ga[m] - gb[m]) / 10) ** 2
    return math.sqrt(total / 24)


def nearest(med, refs, k, exclude=None):
    """The k closest references as (distance, reference), nearest first,
    leaving out the reference whose id is exclude."""
    found = sorted(((distance(med, r.med), r.id, r) for r in refs
                    if r.id != exclude))
    return [(d, r) for d, _id, r in found[:k]]


def vote(near, power):
    """Weighted share of the comparable trails that have each month."""
    total = 0.0
    acc = [0.0] * 12
    for d, r in near:
        w = 1.0 / (d + EPS) ** power
        total += w
        for m in range(12):
            if r.mask >> m & 1:
                acc[m] += w
    return [a / total for a in acc] if total else [0.0] * 12


def blend(med, near, params):
    """(mask, scores, fell_back). Without comparable trails the
    thresholds stand alone."""
    thr = threshold_mask(med, params)
    if not near:
        if thr:
            return thr, [float(thr >> m & 1) for m in range(12)], False
        margins = _margins(med, params)
        return _top(margins), margins, True
    votes = vote(near, params.power)
    scores = [params.mix * votes[m] + (1 - params.mix) * (thr >> m & 1)
              for m in range(12)]
    mask = sum(1 << m for m in range(12) if scores[m] >= params.cut)
    if mask:
        return mask, scores, False
    return _top(scores), scores, True


def months_in_season(points, params, refs=(), exclude=None):
    """Sorted month numbers in season, or None when some point has no
    data. Never an empty list."""
    med = medians(points)
    if med is None:
        return None
    near = nearest(med, list(refs), params.k, exclude) if refs else []
    return to_months(blend(med, near, params)[0])


def confidence(med, near, scores, fell_back, close=0.12, decisive=0.7):
    """("high" or "low", reason). High when the comparable trails are
    close (mean distance at most `close`) and agree (at least `decisive`
    of the twelve months have a weighted vote of 0.2 or less or 0.8 or
    more) and the empty-set fallback was not needed. These two numbers
    were chosen from the leave-one-out predictions: see
    tools/season_fit.json, confidence."""
    if not near:
        return "low", "no comparable trails"
    mean_d = sum(d for d, _ in near) / len(near)
    shares = vote(near, 1)
    sure = sum(1 for s in shares if s <= 0.2 or s >= 0.8) / 12
    if fell_back:
        return "low", "no month reached the cut"
    if mean_d > close:
        return "low", f"comparable trails are far (mean distance {mean_d:.2f})"
    if sure < decisive:
        return "low", f"comparable trails disagree ({sure:.0%} of months settled)"
    return "high", f"comparable trails are close ({mean_d:.2f}) and agree"


# ---------------------------------------------------------------------------
# Fitting by leave-one-out.

def _obj(s):
    return s[0] + 1e-3 * s[2]


def fit_model(trails, params_grid=None):
    """Fit the method on sourced trails and score it leave-one-out.

    trails: list of (id, medians, sourced months). Returns (params,
    loo) where params is fitted on all of them and loo maps id to
    (estimated mask, score) from a model that never saw that trail.
    Each of the three parts is chosen by the same objective (matches,
    then Jaccard overlap): thresholds over the cold and heat grids,
    comparable trails over k, power and a month cut (nested: when
    trail i is held out, every other trail's score is recomputed
    without i among its neighbours), and the blend over mix and cut
    from the other trails' leave-one-out predictions."""
    ids = [t[0] for t in trails]
    index = {tid: n for n, tid in enumerate(ids)}
    meds = [t[1] for t in trails]
    truth = [to_mask(t[2]) for t in trails]
    n = len(trails)

    # -- thresholds
    combos = [(c, h) for c in GRID_COLD for h in GRID_HEAT]
    thr_masks, thr_obj = [], []
    for c, h in combos:
        p = Params(c, h)
        row = []
        for j in range(n):
            mk = threshold_mask(meds[j], p) or _top(_margins(meds[j], p))
            row.append(mk)
        thr_masks.append(row)
        thr_obj.append([_obj(score(row[j], truth[j])) for j in range(n)])
    totals = [sum(row) for row in thr_obj]
    full_t = max(range(len(combos)), key=lambda ci: totals[ci])
    thr_loo = []
    for i in range(n):
        ci = max(range(len(combos)), key=lambda ci: totals[ci] - thr_obj[ci][i])
        thr_loo.append(thr_masks[ci][i])

    # -- comparable trails
    refs = [Reference(ids[j], meds[j], t[2]) for j, t in enumerate(trails)]
    order = [sorted(((distance(meds[j], meds[r]), r) for r in range(n) if r != j))
             for j in range(n)]
    pos = [{r: p for p, (_d, r) in enumerate(order[j])} for j in range(n)]
    bits = [[(truth[r] >> m) & 1 for m in range(12)] for r in range(n)]

    def shares(j, k, power, skip=None):
        total, acc, got = 0.0, [0.0] * 12, 0
        for d, r in order[j]:
            if r == skip:
                continue
            w = 1.0 / (d + EPS) ** power
            total += w
            for m in range(12):
                if bits[r][m]:
                    acc[m] += w
            got += 1
            if got == k:
                break
        return [a / total for a in acc] if total else [0.0] * 12

    def mask_of(v, cut):
        mk = sum(1 << m for m in range(12) if v[m] >= cut)
        return mk or _top(v)

    knn = [(k, p, c) for k in GRID_K for p in GRID_POWER for c in GRID_CUT]
    base = {}
    for k in GRID_K:
        for p in GRID_POWER:
            for j in range(n):
                v = shares(j, k, p)
                base[k, p, j] = [_obj(score(mask_of(v, c), truth[j])) for c in GRID_CUT]
    knn_totals = {}
    for k in GRID_K:
        for p in GRID_POWER:
            for ci, c in enumerate(GRID_CUT):
                knn_totals[k, p, ci] = sum(base[k, p, j][ci] for j in range(n))
    full_k = max(knn_totals, key=lambda key: knn_totals[key])
    knn_choice = []
    for i in range(n):
        best, best_total = None, None
        for k in GRID_K:
            for p in GRID_POWER:
                row = [knn_totals[k, p, ci] - base[k, p, i][ci]
                       for ci in range(len(GRID_CUT))]
                # trails that had i among their k neighbours are rescored without it
                for j in range(n):
                    if j != i and pos[j][i] < k:
                        v = shares(j, k, p, skip=i)
                        for ci, c in enumerate(GRID_CUT):
                            row[ci] += (_obj(score(mask_of(v, c), truth[j]))
                                        - base[k, p, j][ci])
                for ci in range(len(GRID_CUT)):
                    if best_total is None or row[ci] > best_total:
                        best, best_total = (k, p, ci), row[ci]
        knn_choice.append(best)
    knn_votes = [shares(i, knn_choice[i][0], knn_choice[i][1]) for i in range(n)]

    # -- the blend
    blends = [(mix, cut) for mix in GRID_MIX for cut in GRID_BLEND_CUT]
    b_masks, b_obj = [], []
    for mix, cut in blends:
        row = []
        for j in range(n):
            v = [mix * knn_votes[j][m] + (1 - mix) * (thr_loo[j] >> m & 1)
                 for m in range(12)]
            row.append(mask_of(v, cut))
        b_masks.append(row)
        b_obj.append([_obj(score(row[j], truth[j])) for j in range(n)])
    b_totals = [sum(row) for row in b_obj]
    full_b = max(range(len(blends)), key=lambda bi: b_totals[bi])
    loo = {}
    for i in range(n):
        bi = max(range(len(blends)), key=lambda bi: b_totals[bi] - b_obj[bi][i])
        mk = b_masks[bi][i]
        loo[ids[i]] = (mk, score(mk, truth[i]))
    cold, heat = combos[full_t]
    k, p, _ci = full_k
    mix, cut = blends[full_b]
    return Params(cold, heat, k, p, mix, cut), loo
