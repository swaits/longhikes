"""The trail-number registry, trail-numbers.txt: a permanent number for every trail.

Python 3 standard library only. Used by tools/validate.py (every record has a line; no id twice;
no malformed line), by tools/build_index.py (appends the records that have none), and by
tools/check_history.py (an earlier line is never changed, removed or reordered). The file is
documented in docs/schema.md, section "trail-numbers.txt".

The file is one trail id per line. A trail's number is the zero-based index of its line among the
id lines. Lines starting with # are comments and may come only before the first id. Lines are only
ever appended: a trail that leaves the catalogue keeps its line, so its number is retired and is
never given to another trail. The Saved page's short links are bit sets over these numbers
(web/assets/app.js, "SavedCode").
"""
import os
import re

FILE = "trail-numbers.txt"
ID_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")

HEADER = """\
# Trail numbers. One trail id per line; a trail's number is the zero-based index of its line
# among the id lines (comments are not counted). The Saved page's short links use these numbers,
# so a line is never changed, moved or removed, and a number is never reused: a trail that
# leaves the catalogue keeps its line. Only append. python3 tools/build_index.py appends the
# records that have no line yet, in sorted order. Seeded alphabetically by id.
"""


def parse(text):
    """(ids, problems) from the file's text. ids is the list of id lines, in order."""
    ids, problems = [], []
    seen = {}
    if text and not text.endswith("\n"):
        problems.append(f"{FILE}: the last line has no newline at its end")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for n, line in enumerate(lines, 1):
        if line.startswith("#"):
            if ids:
                problems.append(f"{FILE}:{n}: a comment after the first id")
            continue
        if not ID_RE.fullmatch(line):
            problems.append(f"{FILE}:{n}: not a trail id (lower-case words joined by hyphens, "
                            f"nothing else on the line): {line!r}")
            continue
        if line in seen:
            problems.append(f"{FILE}:{n}: {line} is already on line {seen[line]}")
            continue
        seen[line] = n
        ids.append(line)
    return ids, problems


def read(root):
    """(ids, problems) from the registry in root; a missing file is one problem."""
    path = os.path.join(root, FILE)
    if not os.path.isfile(path):
        return [], [f"{FILE} is missing: run python3 tools/build_index.py"]
    with open(path, encoding="utf-8") as f:
        return parse(f.read())


def check(root, trail_ids, errors):
    """Append one message per problem: a malformed line, an id twice, a record with no number.
    An id with no record is a retired number and is fine."""
    ids, problems = read(root)
    errors.extend(problems)
    have = set(ids)
    for tid in sorted(trail_ids):
        if tid not in have:
            errors.append(f"{tid}: has no line in {FILE}: run python3 tools/build_index.py")


def missing(root, trail_ids):
    """The record ids with no line, sorted."""
    ids, _ = read(root)
    have = set(ids)
    return sorted(t for t in trail_ids if t not in have)


def seed_text(trail_ids):
    return HEADER + "".join(f"{t}\n" for t in sorted(trail_ids))


def append(root, trail_ids):
    """Append the records with no line, in sorted order, never touching an existing line.
    Creates the file (seeded alphabetically, with its header) when there is none.
    Returns the ids appended."""
    path = os.path.join(root, FILE)
    if not os.path.isfile(path):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(seed_text(trail_ids))
        return sorted(trail_ids)
    new = missing(root, trail_ids)
    if new:
        with open(path, "r+", encoding="utf-8", newline="\n") as f:
            text = f.read()
            f.seek(0, 2)
            if text and not text.endswith("\n"):
                f.write("\n")
            f.write("".join(f"{t}\n" for t in new))
    return new


def only_appended(old_text, new_text):
    """Problems (a list of sentences) when new_text changes, removes or reorders an id line of
    old_text. Appending is the only change allowed; the comment header is free."""
    old, _ = parse(old_text)
    new, _ = parse(new_text)
    problems = []
    for i, tid in enumerate(old):
        if i >= len(new):
            problems.append(f"{FILE}: line {i} ({tid}) was removed; a retired trail keeps its line")
            break
        if new[i] != tid:
            problems.append(f"{FILE}: id line {i} was {tid} and is now {new[i]}; "
                            f"lines are never changed, moved or removed, only appended")
    return problems
