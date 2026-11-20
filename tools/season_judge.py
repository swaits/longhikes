#!/usr/bin/env python3
"""Packets, blind scoring and proposals for seasons set by judgement.

Python 3 standard library only. Where no page states a season, a reviewer
sets it from a packet: the trail's location, elevation, monthly climate
normals (tools/season_climate.py), the machine estimate of
tools/estimate_season.py and the most similar sourced trails. The method
was tested blind: the same reviewers estimated the trails whose season a
page states, from identical packets with the season hidden, and the share
they matched is in tools/season_blind_test.json, which the site reads.
docs/season-judging.md says how a reviewer works.

Commands:
  packets    write one packet per trail, and the three part lists
  score      score reviewers' answer files against the sourced seasons
             (--write records the figures in tools/season_blind_test.json)
  proposals  stage the judged seasons for the trails with no season, for
             python3 tools/refresh.py collect and apply
  inputs     record the machine estimate and the inputs of every estimate,
             so the monthly check can see when they change

An answer file is tab separated, one trail a line, no header: id, months
(comma separated, 1 to 12), season phrase, confidence (high, medium or
low) and one sentence saying what sets the season there.
"""
import sys

sys.dont_write_bytecode = True

import argparse
import datetime
import json
import os
import random
import re
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import estimate_season as E  # noqa: E402
import refresh  # noqa: E402
import season  # noqa: E402
import season_climate as C  # noqa: E402
import season_model as M  # noqa: E402

ROOT = os.path.dirname(HERE)
BLIND_TEST = os.path.join(ROOT, "tools", "season_blind_test.json")
JUDGED = os.path.join(ROOT, "tools", "season_judged.tsv")
PAGES = os.path.join(ROOT, "tools", "season_judged_pages.json")
INPUTS = os.path.join(ROOT, "tools", "season_inputs.json")

SEED = 20261120
PARTS = 3
NCOMP = 10
PLACE_WEIGHT = 0.1  # climate-distance units per 1000 km between sample-point centres
KM_PER_MILE = 1.609344
CONFIDENCES = ("high", "medium", "low")
LEAD = "Judged from the climate at the trail's elevation and from similar trails."
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
ABB = [m[:3] for m in MONTHS]

# ---------------------------------------------------------------------------
# Hiding the season: a packet never carries a sentence that bears on timing.

_MONTH_RE = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|"
    r"December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\b(?!\s+[A-Z])\.?")
_SEASON_RE = re.compile(
    r"\b(?:summer|winter|spring|fall|autumn|seasons?|seasonal|year[- ]?round|all[- ]year|"
    r"snow[- ]?free|snowmelt|snow[- ]melt|snowpack|monsoons?|best time|time of year|when to go|"
    r"(?:warm|warmer|cold|colder|cool|cooler|hot|wet|dry|snowy|shoulder) months?)\b", re.I)
_LEAD_SEASON_RE = re.compile(r"^(?:Summer|Winter|Spring|Fall|Autumn|Seasons?|Seasonal)\b")
_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


def mentions_season(sentence):
    """True when a sentence names a month or a season. A capitalised month
    counts unless it starts a name ("May Lake"); a season word counts in
    lower case or opening the sentence, so "Summer Lake" does not."""
    sentence = re.sub(r"\bhot springs?\b", "", sentence, flags=re.I)
    if _MONTH_RE.search(sentence):
        return True
    for found in _SEASON_RE.finditer(sentence):
        word = found.group(0)
        if word[0].islower() or word.lower().startswith(("year", "all", "snow")):
            return True
    return bool(_LEAD_SEASON_RE.match(sentence))


def clean(text):
    """(text without the sentences that bear on timing, those sentences)."""
    kept, removed = [], []
    for sentence in _SPLIT.split(str(text or "").strip()):
        if not sentence:
            continue
        (removed if mentions_season(sentence) else kept).append(sentence)
    return " ".join(kept), removed


def shown(kept, original):
    if not original:
        return "(not on file)"
    return kept or "(none left after removing sentences that mention a season)"


# ---------------------------------------------------------------------------
# The blind protocol: trails are split into parts, and a trail's comparable
# trails never come from its own part.

def split_parts(sourced, others, n=PARTS, seed=SEED):
    """Deal the sourced and the other trails separately into n parts, in a
    seeded shuffle, so every part holds a share of each."""
    rng = random.Random(seed)
    parts = [[] for _ in range(n)]
    for group in (sourced, others):
        group = list(group)
        rng.shuffle(group)
        for k, tid in enumerate(group):
            parts[k % n].append(tid)
    return [sorted(p) for p in parts]


def comparables(tid, part_of, sourced_ids, meds, centres, k=NCOMP, place_weight=PLACE_WEIGHT):
    """The k sourced trails closest to tid in climate and place, never itself
    and never one dealt to its own part."""
    if tid not in meds:
        return []
    rows = []
    for other in sourced_ids:
        if other == tid or part_of.get(other) == part_of.get(tid) or other not in meds:
            continue
        d = M.distance(meds[tid], meds[other])
        km = C.haversine_km(*centres[tid], *centres[other])
        rows.append((d + place_weight * km / 1000.0, other))
    rows.sort()
    return [other for _score, other in rows[:k]]


# ---------------------------------------------------------------------------
# The packet.

def _ft(metres):
    return int(round(metres * 3.28084))


def _f(celsius):
    return celsius * 9 / 5 + 32


def _ll(lat, lon):
    return (f"{abs(lat):.1f}{'N' if lat >= 0 else 'S'}",
            f"{abs(lon):.1f}{'W' if lon <= 0 else 'E'}")


def packet_text(rec, info, machine, comparables, pages=None, precip=None):
    """The packet for one trail, as text.

    info: {"points": [PointNormals or None], "kind": "track"|"ends"|"place",
    "profile": (highest_m, lowest_m) or None}. machine: the machine
    estimate's months. comparables: rows of (name, regions, high ground
    feet, season phrase, months). pages: what disagreeing pages say, or
    None. precip: millimetres a month at each point, or None. The trail's
    own season is never used."""
    hike = rec.get("hike") or {}
    tid = rec["id"]
    out = [f"# Trail packet: {tid}", "", "## The trail", ""]
    out += [f"- id: {tid}", f"- name: {rec['name']}",
            f"- common name: {rec.get('common_name') or '(none on file)'}",
            f"- country: {rec['country']}",
            f"- states or provinces: {', '.join(rec.get('regions') or []) or '(none on file)'}",
            f"- length: {rec['length_km'] / KM_PER_MILE:.0f} miles",
            f"- kind: {rec.get('kind') or '(not on file)'}",
            f"- shape: {hike.get('shape') or '(not on file)'}",
            f"- terrain: {', '.join(hike.get('terrain') or []) or '(not on file)'}",
            f"- travel: {hike.get('travel') or '(not on file)'}"]
    hp, name = hike.get("high_point_m"), hike.get("high_point")
    out.append("- high point: " + (f"{_ft(hp)} ft" + (f" ({name})" if name else "")
                                   if hp is not None else "(not on file)"))
    days = hike.get("days")
    out.append("- typical days: " + (f"{days[0]} to {days[1]}" if days and len(days) == 2
                                     and days[0] != days[1] else (str(days[0]) if days else "(not on file)")))
    out += ["", "## Summary, start and end", "",
            "(Sentences that bear on timing have been removed.)", ""]
    for label, key in (("Summary", "summary"), ("Start", "start"), ("End", "end")):
        kept, _removed = clean(hike.get(key))
        out.append(f"{label}: {shown(kept, hike.get(key))}")
    points = M.usable(info["points"])
    out += ["", "## Where it is", ""]
    if points:
        lats, lons = [p.lat for p in points], [p.lon for p in points]
        south, _ = _ll(min(lats), 0)
        north, _ = _ll(max(lats), 0)
        _, west = _ll(0, min(lons))
        _, east = _ll(0, max(lons))
        out += [f"- sample points: {len(points)}",
                f"- southernmost: {south}; northernmost: {north}",
                f"- westernmost: {west}; easternmost: {east}",
                f"- rough extent: {south} to {north}, {west} to {east}" if len(points) > 1
                else f"- rough extent: a single point at {south}, {west}"]
    out.append("- location is: " + {
        "track": "a real track (points spaced along it)",
        "ends": "start and end points only (no track)",
        "place": "a region-centre fallback (no track and no end points; the centre of "
                 "the first region's box)"}[info["kind"]])
    out += ["", "## Elevation", ""]
    if points:
        high, low = M.high_low(points)
        out.append(f"- high ground (the upper quarter of the sample points): "
                   f"{_ft(statistics.median(p.elev_m for p in high))} ft")
        out.append(f"- low ground (the lower half of the sample points): "
                   f"{_ft(statistics.median(p.elev_m for p in low))} ft")
    prof = info.get("profile")
    out.append("- track's highest and lowest points: " + (
        f"{_ft(prof[0])} ft and {_ft(prof[1])} ft" if prof else "(no track elevation on file)"))
    out += ["", "## Climate normals (1981 to 2010)", ""]
    if points:
        pr_of = {}
        if precip and len(precip) == len(points) and all(precip):
            pr_of = {id(p): pr for p, pr in zip(points, precip)}

        def by_month(group, get):
            return [statistics.median(get(p)[m] for p in group) for m in range(12)]
        hh = by_month(high, lambda p: p.tmax_c)
        ll = by_month(low, lambda p: p.tmax_c)
        out.append("Mean daily high in degrees F, " + ("and monthly precipitation in inches, "
                                                        if pr_of else "")
                   + "at the high ground and at the low ground.")
        out.append("")
        if pr_of:
            ph = by_month(high, lambda p: pr_of[id(p)])
            pl = by_month(low, lambda p: pr_of[id(p)])
            out += ["| month | high ground F | low ground F | high ground precip in | low ground precip in |",
                    "|---|---|---|---|---|"]
            out += [f"| {ABB[m]} | {_f(hh[m]):.0f} | {_f(ll[m]):.0f} | {ph[m] / 25.4:.1f} | {pl[m] / 25.4:.1f} |"
                    for m in range(12)]
        else:
            out += ["| month | high ground F | low ground F |", "|---|---|---|"]
            out += [f"| {ABB[m]} | {_f(hh[m]):.0f} | {_f(ll[m]):.0f} |" for m in range(12)]
            out += ["", "(Precipitation is not available for this trail.)"]
    else:
        out.append("No climate data is available for this trail's location.")
    out += ["", "## Machine estimate", "",
            "Labelled: machine estimate, right about two times in three.", "",
            "Months: " + (", ".join(map(str, machine)) + " (" + ", ".join(MONTHS[m - 1] for m in machine) + ")"
                          if machine else "none"),
            "", "## Comparable trails", "",
            "The ten trails with a season on record that are most similar in climate and "
            "nearest in place (this trail is never listed).", ""]
    if comparables:
        out += ["| trail | state | high ground elevation | season | months |", "|---|---|---|---|---|"]
        out += [f"| {n} | {', '.join(regions)} | {feet} ft | {phrase} | {', '.join(map(str, months))} |"
                for n, regions, feet, phrase, months in comparables]
    else:
        out.append("(none)")
    if pages:
        out += ["", "## What pages say", "", "Published pages disagree about this trail's season.", "", pages]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Answers and the blind score.

def read_answers(path, known):
    """({id: (months, phrase, confidence, why)}, [(line number, problem)])."""
    answers, problems, known = {}, [], set(known)
    with open(path, encoding="utf-8") as f:
        for n, raw in enumerate(f, 1):
            line = raw.rstrip("\n")
            if not line.strip() or line.startswith("#") or line.lower().startswith("id\t"):
                continue
            c = line.split("\t")
            if len(c) < 4:
                problems.append((n, f"expected at least 4 tab-separated columns, got {len(c)}"))
                continue
            tid, text, phrase, conf = c[0].strip(), c[1].strip(), c[2].strip(), c[3].strip().lower()
            why = c[4].strip() if len(c) > 4 else ""
            if tid not in known:
                problems.append((n, f"unknown id {tid!r}"))
            elif tid in answers:
                problems.append((n, f"duplicate id {tid}"))
            elif conf not in CONFIDENCES:
                problems.append((n, f"{tid}: confidence must be high, medium or low: {conf!r}"))
            else:
                try:
                    months = sorted({int(x) for x in re.split(r"[,\s]+", text) if x})
                except ValueError:
                    problems.append((n, f"{tid}: months are not numbers: {text!r}"))
                    continue
                if not months or months[0] < 1 or months[-1] > 12:
                    problems.append((n, f"{tid}: months empty or outside 1 to 12: {text!r}"))
                    continue
                answers[tid] = (months, phrase, conf, why)
    return answers, problems


def score(answers, truth):
    """The blind result: for every trail whose season a page states (truth,
    {id: months}) whether the reviewer's months match within a month at each
    end, in all and by the reviewer's confidence. A trail with no answer is
    tested and counts as missed; an answer for a trail not in truth is not
    scored."""
    by = {c: {"tested": 0, "matched": 0} for c in CONFIDENCES}
    tested = matched = unanswered = 0
    for tid, months in sorted(truth.items()):
        tested += 1
        if tid not in answers:
            unanswered += 1
            continue
        got, _phrase, conf, _why = answers[tid]
        hit = bool(M.score(got, months)[0])
        matched += hit
        by[conf]["tested"] += 1
        by[conf]["matched"] += hit
    return {"tested": tested, "matched": matched, "unanswered": unanswered, "by_confidence": by}


def _share(matched, tested):
    return round(matched / tested, 2) if tested else 0.0


def write_blind_test(path, figures, date):
    doc = {
        "date": date,
        "measure": "within one month at each end of the season a page states",
        "tested": figures["tested"],
        "matched": figures["matched"],
        "share": _share(figures["matched"], figures["tested"]),
        "by_confidence": {
            c: {"tested": v["tested"], "matched": v["matched"],
                "share": _share(v["matched"], v["tested"])}
            for c, v in figures["by_confidence"].items()},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, sort_keys=False)
        f.write("\n")


def load_blind_test(path=BLIND_TEST):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check_blind_test(doc):
    """Problems with the figure file: the parts must add up to the whole and
    each share must be the matched count over the tested count."""
    problems = []
    by = doc.get("by_confidence") or {}
    if sorted(by) != sorted(CONFIDENCES):
        problems.append("by_confidence must hold high, medium and low")
        return problems
    if sum(v["tested"] for v in by.values()) != doc["tested"]:
        problems.append("the confidence groups do not add up to the trails tested")
    if sum(v["matched"] for v in by.values()) != doc["matched"]:
        problems.append("the confidence groups do not add up to the trails matched")
    for name, v in [("all", doc)] + list(by.items()):
        if v["matched"] > v["tested"]:
            problems.append(f"{name}: more matched than tested")
        elif v["share"] != _share(v["matched"], v["tested"]):
            problems.append(f"{name}: the share is not matched over tested")
    return problems


# ---------------------------------------------------------------------------
# Writing the judged seasons: proposals for refresh.py collect and apply.

def method_text(why, confidence, lead=LEAD):
    """The season_method an estimate carries: how it was set, what sets the
    season there, and the confidence."""
    return f"{lead} {why.strip()} Confidence: {confidence}."


def proposals(root, answers_path, pages_path, given_dir=None):
    """Stage one proposal for every trail with no season that has an answer.
    A trail named in the pages file was set by judgement from pages that
    differ: its season is `sources`, citing those pages, with the sentences
    the file gives as its method. Every other is an `estimate` citing the
    climate data. Returns how many were staged."""
    ids = refresh.trail_ids(root)
    answers, problems = read_answers(answers_path, ids)
    if problems:
        raise ValueError("; ".join(f"line {n}: {t}" for n, t in problems))
    pages = {}
    if pages_path and os.path.exists(pages_path):
        with open(pages_path, encoding="utf-8") as f:
            pages = json.load(f)
    staging = refresh.staging_dir(root, given_dir, create=True)
    out = os.path.join(staging, "staged", "season-judged")
    today = datetime.date.today().isoformat()
    source = C.SOURCE
    report = []
    for tid in ids:
        rec = refresh.load_toml(os.path.join(root, tid, "trail.toml"))
        hike = rec.get("hike") or {}
        if hike.get("season") or tid not in answers:
            continue
        months, _phrase, conf, why = answers[tid]
        phrase = season.phrase_for(months)
        judged_pages = pages.get(tid)
        if judged_pages:
            basis = "sources"
            method = f"{judged_pages['why'].strip()} Confidence: {conf}."
            cites = [(s["url"], s["publisher"], s["quote"]) for s in judged_pages["sources"]]
            note = "the pages differ; set by judgement"
        else:
            basis = "estimate"
            method = method_text(why, conf)
            quote = (f"Monthly climate ({source['period']}) from {source['name']} "
                     f"at the trail elevation, read with the seasons of similar trails.")
            cites = [(source["url"], source["publisher"], quote)]
            note = "estimated from climate"
        page, _publisher, quote = cites[0]
        lines = ["[[proposal]]", 'kind = "change"', f"id = {E._toml_str(tid)}",
                 f"date = {E._toml_str(today)}",
                 f"summary = {E._toml_str('Add a season, ' + note + ': ' + phrase + '.')}", ""]

        def edit(field, new_toml, old_toml=None):
            lines.append("[[proposal.edit]]")
            lines.append(f"field = {E._toml_str(field)}")
            if old_toml is not None:
                lines.append(f"old = {old_toml}")
            lines.append(f"new = {new_toml}")
            lines.append(f"page = {E._toml_str(page)}")
            lines.append(f"quote = {E._toml_str(quote)}")
            lines.append("")

        edit("hike.season", E._toml_str(phrase))
        edit("hike.months", "[" + ", ".join(str(m) for m in months) + "]")
        edit("hike.season_basis", E._toml_str(basis))
        edit("hike.season_method", E._toml_str(method))
        checked_old = hike.get("checked")
        edit("hike.checked", E._toml_str(today), E._toml_str(checked_old) if checked_old else None)
        for url, publisher, q in cites:
            lines += ["[[proposal.append]]", 'table = "hike.source"',
                      f"page = {E._toml_str(url)}", f"quote = {E._toml_str(q)}", "",
                      "[proposal.append.entry]",
                      f"url = {E._toml_str(url)}",
                      f"publisher = {E._toml_str(publisher)}",
                      'facts = ["season", "months"]', ""]
        if basis == "estimate":
            change = f"A season was estimated: {phrase}."
            why_basis = ("No page states a season. It was set by judgement from the climate "
                         "at the trail's elevation and from similar trails.")
        else:
            change = f"A season was set from pages that differ: {phrase}."
            why_basis = ("The pages that state a season differ and none is the managing body, "
                         "association or route author, so it was set by judgement from all of "
                         "them and the climate estimate.")
        lines += ["[proposal.history]", f"change = {E._toml_str(change)}",
                  f"basis = {E._toml_str(why_basis)}",
                  f"basis_url = {E._toml_str(page)}",
                  'asked_by = "the dataset\'s own check"',
                  'fields = ["hike.season", "hike.months", "hike.season_basis", "hike.season_method"]',
                  ""]
        d = os.path.join(out, tid)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "proposal.toml"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        report.append((tid, "changed", page, f"season {phrase}; {note}"))
    os.makedirs(out, exist_ok=True)
    import csv
    with open(os.path.join(out, "report.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "outcome", "pages", "remark"])
        writer.writerows(report)
    return len(report)


# ---------------------------------------------------------------------------
# Command line.

def _truth(root):
    truth = {}
    for tid, rec in E._records(root):
        hike = rec.get("hike") or {}
        if season.read_from_a_page(hike):
            truth[tid] = sorted(int(m) for m in hike.get("months") or [])
    return truth


def build_packets(root, out_dir, fetch, precip_file=None, pages_text=None):
    """Write packets/<id>.md and part-N.txt under out_dir. Reads the climate
    through fetch (the cache); returns the number of packets."""
    recs = {tid: dict(rec, id=tid) for tid, rec in E._records(root)}
    ids = sorted(recs)
    truth = _truth(root)
    precip = {}
    if precip_file:
        with open(precip_file, encoding="utf-8") as f:
            precip = json.load(f)
    params = E.load_params(root)
    refs = E.references(root, fetch)
    info, meds, centres = {}, {}, {}
    for tid in ids:
        pts, kind = E.sample_points(root, recs[tid])
        norms = E.normals_at(pts, fetch)
        profile = None
        if kind == "track":
            try:
                with open(os.path.join(root, tid, "elevation.json"), encoding="utf-8") as f:
                    data = json.load(f)
                profile = (data["highest"]["m"], data["lowest"]["m"])
            except (OSError, KeyError, TypeError, ValueError):
                profile = None
        got = M.usable(norms)
        info[tid] = {"points": got or [], "kind": kind, "profile": profile}
        if got:
            meds[tid] = M.medians(got)
            centres[tid] = (sum(p.lat for p in got) / len(got), sum(p.lon for p in got) / len(got))
    parts = split_parts([t for t in ids if t in truth], [t for t in ids if t not in truth])
    part_of = {t: n for n, p in enumerate(parts) for t in p}
    os.makedirs(os.path.join(out_dir, "packets"), exist_ok=True)
    for n, part in enumerate(parts, 1):
        with open(os.path.join(out_dir, f"part-{n}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(part) + "\n")
    pages = {}
    if os.path.exists(PAGES):
        with open(PAGES, encoding="utf-8") as f:
            pages = json.load(f)
    for tid in ids:
        rec = recs[tid]
        est = E.estimate(root, rec, params, fetch, refs)
        comp = []
        for other in comparables(tid, part_of, sorted(truth), meds, centres):
            o = recs[other]
            high, _low = M.high_low(info[other]["points"])
            comp.append((o["name"], o.get("regions") or [],
                         _ft(statistics.median(p.elev_m for p in high)),
                         str((o.get("hike") or {}).get("season")), truth[other]))
        text = packet_text(rec, info[tid], est["months"] or [], comp,
                           pages=_pages_text(pages.get(tid)),
                           precip=precip.get(tid))
        with open(os.path.join(out_dir, "packets", f"{tid}.md"), "w", encoding="utf-8") as f:
            f.write(text)
    return len(ids)


def _pages_text(entry):
    if not entry:
        return None
    publishers = "; ".join(s["publisher"] for s in entry["sources"])
    return f"Publisher(s): {publishers}\nMonths each gives: {entry.get('months_text', '')}"


def cmd_packets(args):
    fetch = E._fetch_with_cache(args.cache)
    n = build_packets(ROOT, args.out, fetch, args.precip)
    print(f"{n} packets written to {args.out}/packets")
    return 0


def cmd_score(args):
    ids = refresh.trail_ids(ROOT)
    truth = _truth(ROOT)
    answers = {}
    for path in args.answers:
        got, problems = read_answers(path, ids)
        for n, text in problems:
            print(f"{path} line {n}: {text}")
        answers.update(got)
    figures = score(answers, truth)
    t, m = figures["tested"], figures["matched"]
    print(f"owner's measure (within one month at each end): {m} of {t} = {100 * m / t:.1f}%"
          f" ({figures['unanswered']} unanswered)")
    for c in CONFIDENCES:
        v = figures["by_confidence"][c]
        print(f"  {c:<7} {v['matched']:>3} of {v['tested']:<3} = "
              f"{100 * v['matched'] / v['tested'] if v['tested'] else 0:.1f}%")
    if args.write:
        write_blind_test(args.write, figures, args.date or datetime.date.today().isoformat())
        print(f"written to {args.write}")
    return 0


def cmd_proposals(args):
    n = proposals(ROOT, args.answers, args.pages, args.dir)
    print(f"{n} proposals staged")
    return 0


def cmd_inputs(args):
    fetch = E._fetch_with_cache(args.cache)
    params = E.load_params(ROOT)
    refs = E.references(ROOT, fetch)
    doc = {}
    for tid, rec in E._records(ROOT):
        if (rec.get("hike") or {}).get("season_basis") == "estimate":
            doc[tid] = E.inputs_signature(E.estimate(ROOT, dict(rec, id=tid), params, fetch, refs))
    with open(args.write, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"inputs of {len(doc)} estimates written to {args.write}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("packets", help="write the packets and part lists")
    p.add_argument("--out", required=True)
    p.add_argument("--precip", default=None,
                   help="JSON {id: [twelve monthly mm for each sample point]}; optional")
    p.add_argument("--cache", default=None)
    p.set_defaults(func=cmd_packets)
    p = sub.add_parser("score", help="score answer files against the sourced seasons")
    p.add_argument("answers", nargs="+")
    p.add_argument("--write", default=None, help="record the figures in this JSON file")
    p.add_argument("--date", default=None)
    p.set_defaults(func=cmd_score)
    p = sub.add_parser("proposals", help="stage the judged seasons for refresh.py")
    p.add_argument("--answers", default=JUDGED)
    p.add_argument("--pages", default=PAGES)
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_proposals)
    p = sub.add_parser("inputs", help="record the inputs of every estimate")
    p.add_argument("--write", default=INPUTS)
    p.add_argument("--cache", default=None)
    p.set_defaults(func=cmd_inputs)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
