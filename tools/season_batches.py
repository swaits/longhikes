#!/usr/bin/env python3
"""List the trails with no season and split them into batches for researchers.

Python 3 standard library only. Run from the repository root:

    python3 tools/season_batches.py [--n 10] [--dir DIR]

Writes <staging>/season/batches/season-NN.txt, one trail id per line, and prints
the batch count and the number of trails. A batch holds trails of one region
group; a group of more than the batch size is split, and a leftover of fewer
than five joins a neighbouring batch that has room.
See docs/superpowers/plans/2026-11-20-season-on-every-trail.md.
"""
import sys

sys.dont_write_bytecode = True

import argparse
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import refresh  # noqa: E402

# Ordered so that neighbouring groups are neighbours on the map.
REGION_GROUPS = {
    "west coast": ("CA", "OR", "WA", "AK", "HI"),
    "interior west": ("ID", "NV", "UT"),
    "southwest": ("AZ", "NM", "TX"),
    "Rockies": ("CO", "WY", "MT"),
    "plains and midwest": ("ND", "SD", "NE", "KS", "OK", "MN", "IA", "MO", "WI", "IL", "IN", "MI", "OH"),
    "northeast": ("ME", "NH", "VT", "MA", "RI", "CT", "NY", "NJ", "PA", "DE", "MD", "DC", "WV"),
    "southeast": ("VA", "NC", "SC", "GA", "FL", "AL", "MS", "TN", "KY", "LA", "AR"),
    "Canada west": ("BC", "AB", "SK", "MB", "YT"),
    "Canada east and north": ("ON", "QC", "NB", "NS", "PE", "NL", "NT", "NU"),
}
OTHER = "other"
MIN_BATCH = 5


def group_of(rec):
    """The region group of a record's first region code (OTHER when unknown)."""
    for code in rec.get("regions") or []:
        for name, codes in REGION_GROUPS.items():
            if code in codes:
                return name
        break
    return OTHER


def _records(root):
    for tid in refresh.trail_ids(root):
        yield tid, refresh.load_toml(os.path.join(root, tid, "trail.toml"))


def missing_ids(root):
    """Ids of the records with no hike.season, sorted."""
    return sorted(tid for tid, rec in _records(root) if not (rec.get("hike") or {}).get("season"))


def batches(root, size=10):
    by_group = {}
    for tid, rec in _records(root):
        if not (rec.get("hike") or {}).get("season"):
            by_group.setdefault(group_of(rec), []).append(tid)
    chunks = []
    for name in list(REGION_GROUPS) + [OTHER]:
        ids = sorted(by_group.get(name, []))
        chunks += [ids[i:i + size] for i in range(0, len(ids), size)]
    out = []
    carry = None  # a small chunk waiting for the next one to absorb it
    for chunk in chunks:
        if carry is not None:
            if len(carry) + len(chunk) <= size:
                chunk = carry + chunk
            else:
                out.append(carry)
            carry = None
        if len(chunk) < MIN_BATCH:
            if out and len(out[-1]) + len(chunk) <= size:
                out[-1] = out[-1] + chunk
            else:
                carry = chunk
        else:
            out.append(chunk)
    if carry is not None:
        out.append(carry)
    return out


def write_batches(root, size, given_dir=None):
    staging = refresh.staging_dir(root, given_dir, create=True)
    d = os.path.join(staging, "season", "batches")
    os.makedirs(d, exist_ok=True)
    for name in os.listdir(d):
        if name.startswith("season-") and name.endswith(".txt"):
            os.remove(os.path.join(d, name))
    got = batches(root, size)
    for n, ids in enumerate(got, 1):
        with open(os.path.join(d, f"season-{n:02d}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(ids) + "\n")
    return d, got


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=10, help="trails per batch")
    parser.add_argument("--dir", default=None, help="staging directory")
    args = parser.parse_args(argv)
    d, got = write_batches(os.path.dirname(HERE), args.n, args.dir)
    print(f"{len(got)} batches, {sum(len(b) for b in got)} trails, written to {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
