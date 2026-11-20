#!/usr/bin/env python3
"""Regenerate web/tests/golden/state-pages.json from the fixtures in
test_state_pages_unchanged.py. Run only deliberately, and read the diff:
    python3 web/tests/make_golden.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from test_state_pages_unchanged import GOLDEN, build_map  # noqa: E402

if __name__ == "__main__":
    data = build_map()
    os.makedirs(os.path.dirname(GOLDEN), exist_ok=True)
    with open(GOLDEN, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"wrote {GOLDEN}: {len(data)} pages")
    for path in sorted(data):
        print(" ", path)
