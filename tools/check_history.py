#!/usr/bin/env python3
"""Check that a change to a trail's facts comes with a new [[history]] entry.

Python 3 standard library only, and git. Run it from anywhere inside the clone, before you
send a change:

    python3 tools/check_history.py              # against origin/main (or main)
    python3 tools/check_history.py --base REV   # against another revision
    python3 tools/check_history.py --facts      # print which fields count as facts

For every trail.toml (or track file) that differs from the base, it
  * FAILS when a fact about the trail or its track changed and no new history entry names
    that field with the outcome "applied" (it says which record and which fields);
  * FAILS when an entry that was already in the base history was changed or removed
    (history is only added to; use --allow-history-edits for a typing mistake);
  * PRINTS, for every changed fact, the earlier history entries about the same field, and
    prints "!!" lines when one of them was declined or was asked for by someone other than
    the dataset's own check: that is where two requests may conflict.
The history is compared with the merge base of the revision and HEAD, so the work you are
sending is checked, and not what others have merged meanwhile. Your uncommitted edits count.
Exit status: 0 passes, 1 a check failed, 2 the base revision could not be read.

The fields that count as facts are listed in tools/trail_history.py (NOT_FACTS is the short
list of fields that do not) and in docs/schema.md, section "[[history]]".
"""
import sys

sys.dont_write_bytecode = True

import argparse
import os
import re
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_index  # noqa: E402
import trail_history as H  # noqa: E402

DEFAULT_BASES = ("origin/main", "github/main", "main")
TRACK_FILE_RE = re.compile(r"^([^/]+)/([^/]+\.geojson)$")
TOML_RE = re.compile(r"^([^/]+)/trail\.toml$")


class BaseError(Exception):
    """The base revision could not be used."""


def git(root, *args, check=True):
    done = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    if check and done.returncode != 0:
        raise BaseError(f"git {' '.join(args)}: {done.stderr.strip() or 'failed'}")
    return done


def repo_root():
    here = os.path.dirname(HERE)
    try:
        return git(here, "rev-parse", "--show-toplevel").stdout.strip()
    except (BaseError, FileNotFoundError):
        return here


def merge_base(root, base):
    """The commit where this work left `base`. Says so plainly when a shallow clone hides it."""
    candidates = [base] if base and not re.fullmatch(r"0+", base) else list(DEFAULT_BASES)
    for rev in candidates:
        if git(root, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}", check=False).returncode:
            continue
        done = git(root, "merge-base", rev, "HEAD", check=False)
        if done.returncode == 0 and done.stdout.strip():
            return rev, done.stdout.strip()
        raise BaseError(
            f"no common commit between {rev} and HEAD. In a shallow clone, fetch more: "
            f"git fetch --unshallow (or fetch-depth: 0 in the workflow's checkout).")
    raise BaseError(
        f"cannot find {' or '.join(candidates)}. Fetch it (git fetch origin main) or pass --base REV.")


def changed_files(root, mb):
    """Trail directories whose record or track files differ from commit mb, in the working tree."""
    names = set(git(root, "diff", "--name-only", "--no-renames", mb).stdout.split("\n"))
    names |= set(git(root, "ls-files", "--others", "--exclude-standard").stdout.split("\n"))
    records, tracks = set(), set()
    for name in names:
        m = TOML_RE.match(name)
        if m:
            records.add(m.group(1))
            continue
        m = TRACK_FILE_RE.match(name)
        if m:
            tracks.add(m.group(1))
    return sorted(records | tracks), tracks


def load_text(text):
    with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False, encoding="utf-8") as f:
        f.write(text)
    try:
        return build_index.load_toml(f.name)
    finally:
        os.unlink(f.name)


def base_record(root, mb, tid):
    done = git(root, "show", f"{mb}:{tid}/trail.toml", check=False)
    return load_text(done.stdout) if done.returncode == 0 else None


def current_record(root, tid):
    path = os.path.join(root, tid, "trail.toml")
    return build_index.load_toml(path) if os.path.isfile(path) else None


def entry_text(e):
    """One earlier entry, in a sentence."""
    fields = ", ".join(e.get("fields", []))
    who = e.get("asked_by", "?")
    url = f" ({e['basis_url']})" if e.get("basis_url") else ""
    verb = "A request to change" if e.get("outcome") == "declined" else "Changed"
    return (f"{verb} {fields} on {e.get('date', '?')} at the request of {who}, because "
            f"{str(e.get('basis', '')).rstrip('.')}{url}; outcome {e.get('outcome', '?')}.")


def split_history(base_hist, new_hist):
    """(entries added, whether the earlier ones are untouched)."""
    if new_hist[:len(base_hist)] == base_hist:
        return new_hist[len(base_hist):], True
    rest = list(new_hist)
    for e in base_hist:
        if e in rest:
            rest.remove(e)
    return rest, False


def analyse(tid, old, new, track_changed=False, allow_edits=False):
    """Return (failures, loud, notes) for one trail: lists of lines to print."""
    failures, loud, notes = [], [], []
    if new is None:
        notes.append(f"{tid}: the record was removed; nothing to check.")
        return failures, loud, notes
    new_hist = [e for e in new.get("history", []) if isinstance(e, dict)]
    old_hist = [e for e in (old or {}).get("history", []) if isinstance(e, dict)]
    added, intact = split_history(old_hist, new_hist)
    if not intact and not allow_edits:
        failures.append(f"{tid}: earlier history entries were changed or removed. History is only "
                        "added to. Put the change back, and add a new entry that corrects it "
                        "(or pass --allow-history-edits for a typing mistake).")
    if old is None:
        if not any(e.get("fields") == [H.RECORD] for e in added):
            failures.append(f"{tid}: a new record needs a history entry with fields = [\"record\"].")
        notes.append(f"{tid}: new record, with {len(added)} history entr{'y' if len(added) == 1 else 'ies'}.")
        return failures, loud, notes

    paths = H.changed_paths(old, new)
    if track_changed and H.TRACK_FIELD not in paths:
        paths = sorted(paths + [H.TRACK_FIELD])
    facts = [p for p in paths if H.is_fact(p)]
    others = [p for p in paths if not H.is_fact(p)]
    if others:
        notes.append(f"{tid}: not facts, so no history entry needed: {', '.join(others)}")
    applied = [e for e in added if e.get("outcome") == "applied"]
    uncovered = [p for p in facts if not any(H.entry_covers(e, p) for e in applied)]
    if uncovered:
        if not added:
            failures.append(f"{tid}: facts changed and no new history entry was added. "
                            f"Changed: {', '.join(uncovered)}.")
        else:
            failures.append(f"{tid}: no new history entry with outcome \"applied\" names "
                            f"{', '.join(uncovered)}, which changed.")
        failures.append(f"    Add one to [[history]] in {tid}/trail.toml (docs/schema.md, section "
                        "[[history]]). `python3 tools/check_history.py --facts` lists the facts.")
    for e in applied:
        idle = [f for f in e.get("fields", []) if f != H.RECORD
                and not any(H.covers(f, p) or H.covers(p, f) for p in paths)]
        if idle:
            notes.append(f"{tid}: the entry of {e.get('date')} says {', '.join(idle)} changed, "
                         "but it did not change here.")

    for p in facts:
        earlier = [e for e in old_hist if e.get("fields") != [H.RECORD] and H.entry_covers(e, p)]
        for e in earlier:
            quiet = e.get("outcome") == "applied" and H.is_own(e)
            line = f"{p} of {tid}: " + entry_text(e)
            if e is earlier[-1] and e.get("outcome") == "applied":
                line = (f"{p} of {tid} was last changed on {e.get('date')} at the request of "
                        f"{e.get('asked_by')}, because {str(e.get('basis', '')).rstrip('.')}"
                        f"{' (' + e['basis_url'] + ')' if e.get('basis_url') else ''}; "
                        f"outcome {e.get('outcome')}.")
            if quiet:
                notes.append(line)
            elif e.get("outcome") == "declined":
                loud.append(f"{line} It was DECLINED. Read the reason before asking again.")
            else:
                loud.append(f"{line} It was NOT the dataset's own check who asked: this field "
                            "may be disputed.")
    return failures, loud, notes


def run(root, base=None, allow_edits=False, out=print):
    """Check the work in `root` against `base`. Return the exit status."""
    rev, mb = merge_base(root, base)
    ids, tracks = changed_files(root, mb)
    out(f"Checking the history of records changed since {rev} ({mb[:9]}).")
    failed, count = False, 0
    for tid in ids:
        old, new = base_record(root, mb, tid), current_record(root, tid)
        if old is None and new is None:
            continue
        count += 1
        failures, loud, notes = analyse(tid, old, new, tid in tracks, allow_edits)
        for line in notes:
            out(f"note  {line}")
        for line in loud:
            out(f"!! CONFLICT RISK: {line}")
            if os.environ.get("GITHUB_ACTIONS"):
                out(f"::warning file={tid}/trail.toml::{line}")
        for line in failures:
            out(f"FAIL  {line}" if not line.startswith("    ") else line)
            if os.environ.get("GITHUB_ACTIONS") and not line.startswith("    "):
                out(f"::error file={tid}/trail.toml::{line}")
        failed = failed or bool(failures)
    if failed:
        out("History check FAILED.")
        return 1
    out(f"OK history: {count} changed record{'s' if count != 1 else ''} checked.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base", help="revision to compare with (default origin/main, then main)")
    parser.add_argument("--facts", action="store_true", help="print which fields count as facts and exit")
    parser.add_argument("--allow-history-edits", action="store_true",
                        help="do not fail when an earlier history entry was changed")
    args = parser.parse_args(argv)
    if args.facts:
        print("Facts (a change needs a new history entry):\n  " + H.FACTS_TEXT)
        print("Not facts (no entry needed):\n  " + H.NOT_FACTS_TEXT)
        return 0
    try:
        return run(repo_root(), args.base, args.allow_history_edits)
    except BaseError as e:
        print(f"ERROR {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
