#!/usr/bin/env python3
"""Propose a season_basis for every record that already has a season.

Python 3 standard library only. Run from the repository root:

    python3 tools/season_classify.py table [--dir DIR]
    python3 tools/season_classify.py proposals --reviewed PATH [--dir DIR]

The suggestion is a starting point for a person's review, never written to a
record by this tool. See docs/superpowers/plans/2026-11-20-season-on-every-trail.md.
"""
import sys

sys.dont_write_bytecode = True

import argparse
import csv
import datetime
import os
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import refresh  # noqa: E402

COLUMNS = ("id", "season", "months", "publishers", "urls",
           "n_sources", "n_publishers", "suggested", "reason")


def _host(url):
    if not isinstance(url, str) or not url:
        return ""
    host = urlparse(url).hostname or ""
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


def _naming_sources(rec):
    sources = (rec.get("hike") or {}).get("source") or []
    return [s for s in sources if isinstance(s, dict) and "season" in (s.get("facts") or [])]


def _primary_signals(rec):
    """Yield (host, reason) for each page that would make a source primary."""
    hike = rec.get("hike") or {}
    if _host(hike.get("official_url")):
        yield _host(hike["official_url"]), "source host matches hike.official_url"
    source_table = rec.get("source") or {}
    if _host(source_table.get("publisher_url")):
        yield _host(source_table["publisher_url"]), "source host matches source.publisher_url"
    if rec.get("kind") == "route":
        for guide in rec.get("guide") or []:
            if isinstance(guide, dict) and guide.get("link_is") in ("author", "publisher"):
                if _host(guide.get("url")):
                    yield _host(guide["url"]), "route author guide host (route author counts as primary)"
        route = rec.get("route") or {}
        if _host(route.get("creator_words_url")):
            yield _host(route["creator_words_url"]), \
                "route author creator_words_url host (route author counts as primary)"


def suggest_basis(rec):
    """Return (basis, reason) for a record that has a season."""
    naming = _naming_sources(rec)
    naming_hosts = {_host(s.get("url")) for s in naming} - {""}
    for host, reason in _primary_signals(rec):
        if host in naming_hosts:
            return "primary", reason
    publishers = {str(s.get("publisher", "")).strip().casefold()
                  for s in naming if str(s.get("publisher", "")).strip()}
    if len(publishers) >= 2:
        return "sources", f"{len(publishers)} different publishers name season, none primary"
    if naming:
        return "source", "one non-primary publisher names season"
    return "source", "no source names season"


def table(root):
    rows = []
    for tid in refresh.trail_ids(root):
        rec = refresh.load_toml(os.path.join(root, tid, "trail.toml"))
        hike = rec.get("hike") or {}
        if not hike.get("season"):
            continue
        naming = _naming_sources(rec)
        publishers = [str(s.get("publisher", "")) for s in naming]
        distinct = {p.strip().casefold() for p in publishers if p.strip()}
        suggested, reason = suggest_basis(rec)
        rows.append({
            "id": tid,
            "season": hike["season"],
            "months": hike.get("months"),
            "publishers": publishers,
            "urls": [s.get("url", "") for s in naming],
            "n_sources": len(naming),
            "n_publishers": len(distinct),
            "suggested": suggested,
            "reason": reason,
        })
    return rows


def _cell(value):
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    return value


def write_table(root, given_dir=None):
    staging = refresh.staging_dir(root, given_dir, create=True)
    out_dir = os.path.join(staging, "season")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "classification.csv")
    rows = table(root)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        for row in rows:
            writer.writerow([_cell(row[c]) for c in COLUMNS])
    return path, len(rows)


BASIS_WORDS = {
    "primary": "the page of the body that manages the trail or, for a route, its author",
    "sources": "two or more pages from different publishers that agree",
    "source": "one page that is not the trail's own",
}


def read_reviewed(path):
    """The reviewed file: {id: basis}. Only the three sourced bases are allowed."""
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tid, basis = (row.get("id") or "").strip(), (row.get("basis") or "").strip()
            if basis not in BASIS_WORDS:
                raise ValueError(f"{tid}: basis {basis!r} must be one of {', '.join(BASIS_WORDS)}")
            out[tid] = basis
    return out


def _toml_str(text):
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


def proposals(root, reviewed_csv, given_dir=None):
    """Stage one change proposal per reviewed row; return how many."""
    bases = read_reviewed(reviewed_csv)
    staging = refresh.staging_dir(root, given_dir, create=True)
    out = os.path.join(staging, "staged", "season-classify")
    today = datetime.date.today().isoformat()
    report = []
    for tid in refresh.trail_ids(root):
        if tid not in bases:
            continue
        rec = refresh.load_toml(os.path.join(root, tid, "trail.toml"))
        hike = rec.get("hike") or {}
        naming = _naming_sources(rec)
        if not hike.get("season") or not naming:
            raise ValueError(f"{tid}: no season or no source naming it")
        src = naming[0]
        basis = bases[tid]
        publishers = "; ".join(sorted({str(s.get("publisher", "")).strip()
                                       for s in naming if str(s.get("publisher", "")).strip()}))
        lines = [
            "[[proposal]]", 'kind = "change"', f"id = {_toml_str(tid)}", f"date = {_toml_str(today)}",
            f"summary = {_toml_str('Record where the season came from.')}", "",
            "[[proposal.edit]]", 'field = "hike.season_basis"', f"new = {_toml_str(basis)}",
            f"page = {_toml_str(src['url'])}", f"quote = {_toml_str(hike['season'])}", "",
            "[proposal.history]",
            f"change = {_toml_str('The season is recorded as coming from ' + BASIS_WORDS[basis] + '.')}",
            f"basis = {_toml_str('The season is stated by ' + publishers + ' as: ' + hike['season'] + '.')}",
            f"basis_url = {_toml_str(src['url'])}",
            'asked_by = "the dataset\'s own check"', 'fields = ["hike.season_basis"]', "",
        ]
        d = os.path.join(out, tid)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "proposal.toml"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        report.append((tid, "changed", src["url"], f"season_basis {basis}"))
    with open(os.path.join(out, "report.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "outcome", "pages", "remark"])
        w.writerows(report)
    return len(report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_table = sub.add_parser("table", help="write the classification table")
    p_table.add_argument("--dir", default=None, help="staging directory")
    p_prop = sub.add_parser("proposals", help="stage a proposal per reviewed row")
    p_prop.add_argument("--reviewed", required=True)
    p_prop.add_argument("--dir", default=None, help="staging directory")
    args = parser.parse_args(argv)
    root = os.path.dirname(HERE)
    if args.cmd == "proposals":
        print(f"{proposals(root, args.reviewed, args.dir)} proposals staged")
        return 0
    if args.cmd == "table":
        path, n = write_table(root, args.dir)
        print(f"{n} rows written to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
