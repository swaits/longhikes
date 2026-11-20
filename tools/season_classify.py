#!/usr/bin/env python3
"""Propose a season_basis for every record that already has a season.

Python 3 standard library only. Run from the repository root:

    python3 tools/season_classify.py table [--dir DIR]

The suggestion is a starting point for a person's review, never written to a
record by this tool. See docs/superpowers/plans/2026-11-20-season-on-every-trail.md.
"""
import sys

sys.dont_write_bytecode = True

import argparse
import csv
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_table = sub.add_parser("table", help="write the classification table")
    p_table.add_argument("--dir", default=None, help="staging directory")
    args = parser.parse_args(argv)
    root = os.path.dirname(HERE)
    if args.cmd == "table":
        path, n = write_table(root, args.dir)
        print(f"{n} rows written to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
