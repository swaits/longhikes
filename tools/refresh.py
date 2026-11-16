#!/usr/bin/env python3
"""The mechanical parts of the monthly refresh. Python 3 standard library only.

The process is described in .claude/skills/refresh-trails/SKILL.md; the staged proposal
format is in .claude/skills/refresh-trails/proposal-format.md. This tool does the parts
that need no judgement:

    python3 tools/refresh.py preflight             clean tree, validator, tests, staging directory
    python3 tools/refresh.py slices --n 6          split the trails and the left-out entries into slices
    python3 tools/refresh.py slices --n 6 --since 30
    python3 tools/refresh.py links                 fetch every address once, politely, into links.csv
    python3 tools/refresh.py collect               gather the staged work into collected.toml and summary.md
    python3 tools/refresh.py apply --dry-run       apply the accepted proposals by targeted edits
    python3 tools/refresh.py apply

Staging lives in refresh/<YYYY-MM-DD>/ at the top of the checkout, which .gitignore lists, so
nothing staged can reach a commit. Every command takes --dir to name another directory; by
default it uses the newest one under refresh/.

`slices --since DAYS` takes only trails whose last check is older than DAYS days. The last
check is `hike.checked` (the date the hiker facts were read, which every record with a
[hike] table carries). A record without [hike] falls back to `source.source_checked`.

Records are never re-serialised. `apply` finds the line of the named field and replaces that
one line, adds a line at the end of its table, or adds a block at the end of the matching
array of tables, so hand formatting and comments stay as they are.
"""
import sys

sys.dont_write_bytecode = True

import argparse
import concurrent.futures
import csv
import datetime
import hashlib
import json
import os
import re
import shutil
import ssl
import subprocess
import threading
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import trail_history as H  # noqa: E402

ROOT = os.path.dirname(HERE)
STAGING = "refresh"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
URL_RE = re.compile(r"^https?://[^\s/]+\S*$")
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
URL_IN_TEXT = re.compile(r"https?://[^\s\"'<>\]\[]+")
USER_AGENT = "Mozilla/5.0 (compatible; link-checker/1.0)"

KINDS = ("verified", "change", "declined", "new-record", "left-out-add", "left-out-remove",
         "candidate", "could-not-check")
APPLIED_KINDS = ("verified", "change", "declined", "new-record", "left-out-add",
                 "left-out-remove")
OUTCOMES = ("verified", "changed", "declined", "could-not-check", "refused", "not-reached",
            "found", "not-found", "none-exists", "kept", "replaced", "cropped", "new",
            "not-found-emblem", "accepted", "rejected")
NEEDS_PAGES = ("verified", "not-found", "refused", "none-exists", "could-not-check")
REPORT_COLUMNS = ("id", "outcome", "pages", "remark")
DECISIONS = ("accept", "reject", "hold")
FILE_NAME_RE = re.compile(r"^(line\.geojson|alternates\.geojson|line-[a-z0-9-]+\.geojson|"
                          r"release\.txt|elevation\.json|shield\.svg|shield\.png)$")
APPEND_TABLES = ("hike.source", "guide", "link")
LEFT_OUT_FILE = "left-out.toml"


class RefreshError(Exception):
    """A message for the person running the tool; no traceback."""


# ----------------------------------------------------------------------------- helpers

def today_str(args=None):
    given = getattr(args, "today", None) if args else None
    return given or datetime.date.today().isoformat()


def load_toml(path):
    with open(path, "rb") as f:
        return tomllib.load(f)


def trail_ids(root):
    return sorted(d for d in os.listdir(root)
                  if os.path.isfile(os.path.join(root, d, "trail.toml")))


def left_out_entries(root):
    path = os.path.join(root, LEFT_OUT_FILE)
    if not os.path.isfile(path):
        return []
    return load_toml(path).get("trail", [])


def staging_dir(root, given=None, create=False, today=None, fresh=False):
    """The staging directory: the one named, else the newest under refresh/. With `fresh`
    (preflight), a run starts a new directory for today unless one is named."""
    if fresh and not given:
        given = os.path.join(STAGING, today or datetime.date.today().isoformat())
    if given:
        path = given if os.path.isabs(given) else os.path.join(root, given)
    else:
        base = os.path.join(root, STAGING)
        dated = sorted(d for d in os.listdir(base)
                       if DATE_RE.match(d) and os.path.isdir(os.path.join(base, d))) \
            if os.path.isdir(base) else []
        path = os.path.join(base, dated[-1]) if dated else os.path.join(
            base, today or datetime.date.today().isoformat())
    if not os.path.isdir(path):
        if not create:
            raise RefreshError(f"no staging directory at {path}; run `python3 tools/refresh.py "
                               "preflight` (or `slices`) first")
        os.makedirs(path)
    return path


def walk_strings(obj, path=""):
    """Yield (field path, string) for every string in a parsed record."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{path}[{i}]")


def clean_url(url):
    url = url.rstrip(".,;:'\"")
    while url.endswith(")") and url.count("(") < url.count(")"):
        url = url[:-1].rstrip(".,;:'\"")
    return url


def urls_in(rec):
    """Every http(s) address in a parsed record or entry, with the field it sits in."""
    found = []
    for path, text in walk_strings(rec):
        for m in URL_IN_TEXT.finditer(text):
            url = clean_url(m.group(0))
            if URL_RE.match(url):
                found.append((url, path))
    return found


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


# ----------------------------------------------------------------------------- toml output

def _scalar(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_scalar(v) for v in value) + "]"
    raise RefreshError(f"cannot write {value!r} as a TOML value")


def dump_toml(obj, prefix=""):
    """Write a parsed TOML document back out (used for collected.toml and appended blocks).

    Scalars and arrays of scalars first, then sub-tables, then arrays of tables.
    """
    lines = []
    tables, arrays = [], []
    for key, value in obj.items():
        if isinstance(value, dict):
            tables.append((key, value))
        elif isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
            arrays.append((key, value))
        else:
            lines.append(f"{key} = {_scalar(value)}")
    out = "\n".join(lines) + ("\n" if lines else "")
    for key, value in tables:
        name = f"{prefix}.{key}" if prefix else key
        out += f"\n[{name}]\n" + dump_toml(value, name)
    for key, items in arrays:
        name = f"{prefix}.{key}" if prefix else key
        for item in items:
            out += f"\n[[{name}]]\n" + dump_toml(item, name)
    return out


def digest(obj):
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:10]


# ----------------------------------------------------------------------------- slices

def effective_check(rec):
    """The date a record was last checked, and which field it came from."""
    hike = rec.get("hike") or {}
    if hike.get("checked"):
        return str(hike["checked"]), "hike.checked"
    src = rec.get("source") or {}
    if src.get("source_checked"):
        return str(src["source_checked"]), "source.source_checked"
    return None, None


def balance(items, n):
    """items: [(name, weight)]. Greedy: heaviest first into the lightest slice."""
    n = max(1, min(n, len(items))) if items else 0
    slices = [[] for _ in range(n)]
    loads = [0] * n
    for name, weight in sorted(items, key=lambda x: (-x[1], x[0])):
        i = loads.index(min(loads))
        slices[i].append(name)
        loads[i] += weight
    return [sorted(s) for s in slices]


def cmd_slices(args):
    root = args.root
    today = today_str(args)
    d = staging_dir(root, args.dir, create=True, today=today)
    sdir = os.path.join(d, "slices")
    os.makedirs(sdir, exist_ok=True)
    for old in os.listdir(sdir):
        os.remove(os.path.join(sdir, old))
    cutoff = None
    if args.since is not None:
        cutoff = (datetime.date.fromisoformat(today) - datetime.timedelta(days=args.since)).isoformat()
    items, skipped = [], []
    for tid in trail_ids(root):
        rec = load_toml(os.path.join(root, tid, "trail.toml"))
        when, _field = effective_check(rec)
        if cutoff and when and when >= cutoff:
            skipped.append(tid)
            continue
        items.append((tid, 1 + len({u for u, _ in urls_in(rec)})))
    trail_slices = balance(items, args.n)
    entries = left_out_entries(root)
    lo_items = [(e["id"], 3 if e.get("reason") == "waiting" else 1) for e in entries if e.get("id")]
    lo_slices = balance(lo_items, args.left_out_n)
    manifest = []
    for kind, parts in (("trails", trail_slices), ("left-out", lo_slices)):
        for i, ids in enumerate(parts, 1):
            name = f"{kind}-{i:02d}"
            with open(os.path.join(sdir, name + ".txt"), "w", encoding="utf-8") as f:
                f.write("".join(x + "\n" for x in ids))
            manifest.append((name, kind, len(ids)))
    with open(os.path.join(sdir, "manifest.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(("slice", "kind", "count"))
        w.writerows(manifest)
    print(f"staging directory: {d}")
    if cutoff:
        print(f"--since {args.since}: last check is hike.checked (source.source_checked where a "
              f"record has no [hike]); records checked on or after {cutoff} are left out: "
              f"{len(skipped)} skipped, {len(items)} taken")
    for name, kind, count in manifest:
        print(f"  slices/{name}.txt  {count} {'trails' if kind == 'trails' else 'left-out entries'}")
    return 0


# ----------------------------------------------------------------------------- preflight

def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def cmd_preflight(args):
    root = args.root
    problems = []
    status = run(["git", "status", "--porcelain"], root)
    if status.returncode != 0:
        problems.append("git status failed: " + status.stderr.strip())
    else:
        dirty = [line for line in status.stdout.splitlines()
                 if not line[3:].startswith(STAGING + "/")]
        if dirty:
            problems.append("the working tree is not clean; commit or stash first:\n    "
                            + "\n    ".join(dirty[:10]))
    d = staging_dir(root, args.dir, create=True, today=today_str(args), fresh=True)
    ignored = run(["git", "check-ignore", "-q", os.path.relpath(d, root) + "/x"], root)
    if ignored.returncode != 0:
        problems.append(f"{os.path.relpath(d, root)} is not ignored by git; add /{STAGING}/ to .gitignore")
    if not args.no_validate:
        v = run([sys.executable, os.path.join(root, "tools", "validate.py")], root)
        last = (v.stdout.strip().splitlines() or [""])[-1]
        print("validate:", last)
        if v.returncode != 0:
            problems.append("tools/validate.py fails")
    if not args.no_tests:
        t = run([sys.executable, "-m", "unittest", "discover", "tools/tests"], root)
        print("tests:", (t.stderr.strip().splitlines() or [""])[-1])
        if t.returncode != 0:
            problems.append("tools tests fail")
    print(f"staging directory: {d}")
    if problems:
        for p in problems:
            print("PROBLEM:", p)
        return 1
    print("preflight OK")
    return 0


# ----------------------------------------------------------------------------- links

REFUSAL_STATUS = (401, 403, 429, 451)
CHALLENGE_MARKERS = ("just a moment", "attention required", "verify you are human",
                     "enable javascript and cookies", "captcha")


class Prober:
    """Fetches addresses one at a time per host, with a delay, and never retries a refusal."""

    def __init__(self, delay=2.0, timeout=20.0, user_agent=USER_AGENT):
        self.delay, self.timeout, self.ua = delay, timeout, user_agent
        self.robots = {}
        self.blocked_hosts = {}
        self.last = {}
        self.lock = threading.Lock()

    def _request(self, url, method, size=4096):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": self.ua})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = r.read(size) if method == "GET" else b""
                return r.status, r.geturl(), dict(r.headers), body, None
        except urllib.error.HTTPError as e:
            body = b""
            try:
                body = e.read(size) if method == "GET" else b""
            except Exception:
                pass
            e.close()
            return e.code, e.geturl() or url, dict(e.headers or {}), body, None
        except Exception as e:  # network, dns, timeout, certificate
            return None, url, {}, b"", e

    def _wait(self, host):
        with self.lock:
            last = self.last.get(host, 0.0)
        gap = self.delay - (time.monotonic() - last)
        if gap > 0:
            time.sleep(gap)

    def _stamp(self, host):
        with self.lock:
            self.last[host] = time.monotonic()

    def _robots_allows(self, url, host):
        parts = urllib.parse.urlsplit(url)
        key = f"{parts.scheme}://{parts.netloc}"
        if key not in self.robots:
            self._wait(host)
            status, _final, _h, rbody, err = self._request(key + "/robots.txt", "GET", 200000)
            self._stamp(host)
            rp = urllib.robotparser.RobotFileParser()
            if err is not None or status is None or status == 404 or status >= 500:
                rp = None
            elif status in (401, 403, 429):
                rp = "refused"
            elif status == 200:
                rp.parse(rbody.decode("utf-8", "replace").splitlines())
            else:
                rp = None
            self.robots[key] = rp
        rp = self.robots[key]
        if rp == "refused":
            return False, "robots.txt itself was refused"
        if rp is None:
            return True, ""
        if rp.can_fetch(self.ua, url):
            return True, ""
        return False, "robots.txt disallows this path"

    @staticmethod
    def is_challenge(headers, body):
        low = {k.lower(): str(v).lower() for k, v in headers.items()}
        if "cf-mitigated" in low:
            return True
        text = body.decode("utf-8", "replace").lower()
        return any(m in text for m in CHALLENGE_MARKERS)

    def probe(self, url):
        """Returns a dict with status, final_url, refused, note, error, method."""
        host = urllib.parse.urlsplit(url).netloc.lower()
        row = {"url": url, "host": host, "status": "", "final_url": "", "refused": "",
               "note": "", "error": "", "method": ""}
        if host in self.blocked_hosts:
            row.update(refused="host", note=f"not fetched: {self.blocked_hosts[host]}")
            return row
        allowed, why = self._robots_allows(url, host)
        if not allowed:
            row.update(refused="robots", note="not fetched: " + why)
            return row
        for method in ("HEAD", "GET"):
            self._wait(host)
            status, final, headers, body, err = self._request(url, method)
            self._stamp(host)
            row["method"] = method
            if err is not None and isinstance(getattr(err, "reason", err), ssl.SSLError) \
                    and url.startswith("https://"):
                http_url = "http://" + url[len("https://"):]
                self._wait(host)
                status, final, headers, body, err2 = self._request(http_url, "GET")
                self._stamp(host)
                if err2 is None:
                    row["note"] = "https certificate error; read over http"
                    err = None
                    row["method"] = "GET"
            if err is not None:
                row["error"] = f"{type(err).__name__}: {err}"[:200]
                if method == "HEAD":
                    continue
                return row
            row["status"] = status
            row["final_url"] = final
            if status in REFUSAL_STATUS or (method == "GET" and self.is_challenge(headers, body)):
                row["refused"] = "yes"
                if status == 429 or self.is_challenge(headers, body):
                    self.blocked_hosts[host] = "the host answered 429 or a challenge page"
                    row["note"] = (row["note"] + " " if row["note"] else "") + \
                        "refused; host skipped from here on"
                return row  # never retry a refusal, with another method or otherwise
            if method == "HEAD" and not (200 <= status < 400):
                continue  # some servers answer HEAD badly: ask once with GET
            return row
        return row


def redirect_kind(url, final):
    if not final or final == url:
        return ""
    a, b = urllib.parse.urlsplit(url), urllib.parse.urlsplit(final)
    if a.netloc.lower() != b.netloc.lower():
        if a.netloc.lower().removeprefix("www.") == b.netloc.lower().removeprefix("www."):
            return "www"
        return "host"
    if a.scheme != b.scheme and a.path == b.path:
        return "scheme"
    if a.path.rstrip("/") == b.path.rstrip("/") and a.query == b.query:
        return "slash"
    return "path"


def collect_addresses(root):
    """{url: [(owner, field path)]} for every record and every left-out entry."""
    found = {}
    for tid in trail_ids(root):
        rec = load_toml(os.path.join(root, tid, "trail.toml"))
        for url, path in urls_in(rec):
            found.setdefault(url, []).append((tid, path))
    for e in left_out_entries(root):
        for url, path in urls_in(e):
            found.setdefault(url, []).append(("left-out:" + str(e.get("id")), path))
    return found


def cmd_links(args):
    root = args.root
    d = staging_dir(root, args.dir, create=True, today=today_str(args))
    found = collect_addresses(root)
    urls = sorted(found)
    if args.only_prefix:
        urls = [u for u in urls if u.startswith(args.only_prefix)]
    if args.limit:
        urls = urls[: args.limit]
    by_host = {}
    for u in urls:
        by_host.setdefault(urllib.parse.urlsplit(u).netloc.lower(), []).append(u)
    prober = Prober(delay=args.delay, timeout=args.timeout, user_agent=args.user_agent)

    def work(host):
        return [prober.probe(u) for u in by_host[host]]

    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.hosts)) as pool:
        for part in pool.map(work, sorted(by_host)):
            rows.extend(part)
    rows.sort(key=lambda r: r["url"])
    path = os.path.join(d, "links.csv")
    cols = ("url", "host", "status", "final_url", "redirect", "refused", "note", "error",
            "method", "used_by")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            owners = sorted({o for o, _ in found[r["url"]]})
            w.writerow([r["url"], r["host"], r["status"], r["final_url"],
                        redirect_kind(r["url"], r["final_url"]), r["refused"], r["note"],
                        r["error"], r["method"], ";".join(owners[:12]) + ("…" if len(owners) > 12 else "")])
    ok = sum(1 for r in rows if isinstance(r["status"], int) and 200 <= r["status"] < 300)
    refused = sum(1 for r in rows if r["refused"])
    bad = sum(1 for r in rows if isinstance(r["status"], int) and r["status"] >= 400 and not r["refused"])
    err = sum(1 for r in rows if r["error"] and not r["status"])
    print(f"{len(rows)} addresses on {len(by_host)} hosts: {ok} ok, {bad} error status, "
          f"{refused} refused, {err} no answer. Written to {path}")
    return 0


# ----------------------------------------------------------------------------- proposals

def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def slice_ids(d, name):
    p = os.path.join(d, "slices", name + ".txt")
    if not os.path.isfile(p):
        return None
    return [x.strip() for x in open(p, encoding="utf-8") if x.strip()]


def split_path(field):
    """'hike.source[1].facts' -> ('hike.source', 1, 'facts'); 'source.url' -> ('source', None, 'url');
    'length_km' -> ('', None, 'length_km')."""
    m = re.match(r"^((?:[a-z_]+\.)*[a-z_]+)(?:\[(\d+)\])?\.([a-z_]+)$", field)
    if m:
        return m.group(1), (int(m.group(2)) if m.group(2) is not None else None), m.group(3)
    if re.match(r"^[a-z_]+$", field):
        return "", None, field
    return None


def schema_path(field):
    """The field as docs/schema.md names it: indexes removed."""
    return re.sub(r"\[\d+\]", "", field)


def validate_proposal(p, ctx):
    """Return a list of problems with one staged proposal (a parsed [[proposal]])."""
    errs = []
    kind = p.get("kind")
    if kind not in KINDS:
        return [f"kind must be one of {', '.join(KINDS)}, not {kind!r}"]
    pid = p.get("id")
    if not isinstance(pid, str) or not ID_RE.match(pid):
        errs.append("id must be a lower case id with hyphens")
    target = p.get("target", "record")
    if target not in ("record", "left-out"):
        errs.append("target must be \"record\" or \"left-out\"")
    if kind in ("left-out-add", "left-out-remove"):
        target = "left-out"
    if not isinstance(p.get("date"), str) or not DATE_RE.match(p.get("date", "")):
        errs.append("date must be YYYY-MM-DD (the day the pages were read)")
    if not isinstance(p.get("summary"), str) or not p.get("summary", "").strip():
        errs.append("summary is required: one plain sentence")
    known = {"kind", "id", "target", "date", "summary", "edit", "append", "file", "history",
             "pages", "remark", "entry", "name", "country", "regions", "length_mi",
             "source_url", "recommendation", "reason", "what", "why", "tried", "quote",
             "basis_url", "borderline", "sources_md"}
    for k in p:
        if k not in known:
            errs.append(f"unknown field {k}")

    def need_url(obj, key, where):
        v = obj.get(key)
        if not isinstance(v, str) or not URL_RE.match(v):
            errs.append(f"{where}: {key} must be an http(s) address")

    def need_text(obj, key, where):
        v = obj.get(key)
        if not isinstance(v, str) or not v.strip():
            errs.append(f"{where}: {key} is required")

    if kind == "verified":
        pages = p.get("pages")
        if not isinstance(pages, list) or not pages or not all(
                isinstance(x, str) and URL_RE.match(x) for x in pages):
            errs.append("verified needs pages: the http(s) addresses that were opened")
    elif kind in ("change", "declined"):
        edits, appends, files = p.get("edit", []), p.get("append", []), p.get("file", [])
        if kind == "change" and not (edits or appends or files):
            errs.append("a change needs at least one edit, append or file")
        if kind == "declined" and (edits or appends or files):
            errs.append("a declined proposal changes nothing: no edit, append or file")
        seen = set()
        for i, e in enumerate(edits, 1):
            where = f"edit {i}"
            for k in e:
                if k not in ("field", "old", "new", "page", "quote"):
                    errs.append(f"{where}: unknown field {k}")
            f = e.get("field")
            if not isinstance(f, str):
                errs.append(f"{where}: field is required")
                continue
            if f in seen:
                errs.append(f"{where}: {f} is edited twice")
            seen.add(f)
            if f == "id" or f == "history" or f.startswith("history"):
                errs.append(f"{where}: {f} is never edited")
            if target == "record":
                if split_path(f) is None or (schema_path(f) not in H.SCHEMA_FIELDS):
                    errs.append(f"{where}: {f!r} is not a field of the record (docs/schema.md)")
            if "old" not in e and "new" not in e:
                errs.append(f"{where}: give old, new or both")
            if "old" in e and "new" in e and e["old"] == e["new"]:
                errs.append(f"{where}: old and new are the same")
            need_url(e, "page", where)
            need_text(e, "quote", where)
        for i, a in enumerate(appends, 1):
            where = f"append {i}"
            if a.get("table") not in APPEND_TABLES:
                errs.append(f"{where}: table must be one of {', '.join(APPEND_TABLES)}")
            if not isinstance(a.get("entry"), dict) or not a.get("entry"):
                errs.append(f"{where}: entry (the new table's fields) is required")
            need_url(a, "page", where)
            need_text(a, "quote", where)
        for i, fl in enumerate(files, 1):
            where = f"file {i}"
            to = fl.get("to")
            if not isinstance(to, str) or not FILE_NAME_RE.match(to):
                errs.append(f"{where}: to must be a track, release, elevation or shield file name")
            if fl.get("remove") is True:
                if "from" in fl:
                    errs.append(f"{where}: remove and from together")
            else:
                src = fl.get("from")
                if not isinstance(src, str) or src.startswith("/") or ".." in src.split("/"):
                    errs.append(f"{where}: from must be a path inside the proposal's own directory")
                elif ctx.get("pdir") and not os.path.isfile(os.path.join(ctx["pdir"], src)):
                    errs.append(f"{where}: staged file {src} does not exist")
            need_url(fl, "source_url", where)
        facts_touched = any(
            target == "record" and isinstance(e.get("field"), str)
            and H.is_fact(schema_path(e["field"])) for e in edits)
        facts_touched = facts_touched or bool(appends and any(
            a.get("table") in ("guide",) for a in appends)) or bool(files)
        hist = p.get("history")
        if target == "record" and (kind == "declined" or facts_touched):
            if not isinstance(hist, dict):
                errs.append("a change to a fact needs [proposal.history]: change, basis, "
                            "basis_url, asked_by (docs/schema.md, section [[history]])")
        if isinstance(hist, dict):
            for k in hist:
                if k not in ("change", "basis", "basis_url", "asked_by", "fields"):
                    errs.append(f"history: unknown field {k}")
            for k in ("change", "basis", "asked_by"):
                need_text(hist, k, "history")
            need_url(hist, "basis_url", "history")
            for f in hist.get("fields", []):
                if f not in H.SCHEMA_FIELDS:
                    errs.append(f"history: fields names {f!r}, which is not a field of the record")
            if kind == "declined" and not hist.get("fields"):
                errs.append("a declined proposal names the fields in history.fields")
    elif kind == "new-record":
        pdir = ctx.get("pdir")
        rec_path = os.path.join(pdir, "trail.toml") if pdir else None
        if rec_path is None or not os.path.isfile(rec_path):
            errs.append("new-record needs the staged record, trail.toml, beside proposal.toml")
        else:
            try:
                rec = load_toml(rec_path)
            except tomllib.TOMLDecodeError as e:
                errs.append(f"staged trail.toml does not parse: {e}")
            else:
                if rec.get("id") != pid:
                    errs.append(f"staged trail.toml has id {rec.get('id')!r}, not {pid!r}")
                hist = rec.get("history")
                if not hist or hist[0].get("fields") != ["record"]:
                    errs.append("staged trail.toml needs a first [[history]] entry with "
                                'fields = ["record"]')
        if ctx.get("trail_ids") is not None and pid in ctx["trail_ids"]:
            errs.append(f"{pid} already exists in the repository")
        need_url(p, "basis_url", "new-record")
    elif kind == "left-out-add":
        entry = p.get("entry")
        if not isinstance(entry, dict):
            errs.append("left-out-add needs [proposal.entry]: the new [[trail]] entry")
        else:
            for k in ("id", "name", "country", "regions", "reason", "note", "decided", "was_listed"):
                if k not in entry:
                    errs.append(f"entry is missing {k}")
            if entry.get("id") != pid:
                errs.append("entry.id must equal the proposal id")
        need_url(p, "basis_url", "left-out-add")
    elif kind == "left-out-remove":
        need_url(p, "basis_url", "left-out-remove")
        need_text(p, "why", "left-out-remove")
    elif kind == "candidate":
        for k in ("name", "country", "source_url", "recommendation"):
            if k not in p:
                errs.append(f"candidate is missing {k}")
        if p.get("recommendation") not in ("add", "owner", "decline"):
            errs.append("recommendation must be add, owner or decline")
        if "source_url" in p:
            need_url(p, "source_url", "candidate")
    elif kind == "could-not-check":
        for k in ("what", "why"):
            need_text(p, k, "could-not-check")
    return errs


def read_staged(d, trail_set):
    """Walk staged/<worker>/<id>/proposal.toml. Returns (proposals, problems)."""
    proposals, problems = [], []
    base = os.path.join(d, "staged")
    if not os.path.isdir(base):
        return proposals, problems
    for worker in sorted(os.listdir(base)):
        wdir = os.path.join(base, worker)
        if not os.path.isdir(wdir):
            continue
        for pidname in sorted(os.listdir(wdir)):
            pdir = os.path.join(wdir, pidname)
            ppath = os.path.join(pdir, "proposal.toml")
            if not os.path.isfile(ppath):
                continue
            where = f"staged/{worker}/{pidname}/proposal.toml"
            try:
                doc = load_toml(ppath)
            except tomllib.TOMLDecodeError as e:
                problems.append(f"{where}: does not parse: {e}")
                continue
            for k in doc:
                if k != "proposal":
                    problems.append(f"{where}: unknown top-level key {k}; proposals are [[proposal]] tables")
            for n, p in enumerate(doc.get("proposal", []), 1):
                ctx = {"pdir": pdir, "trail_ids": trail_set}
                errs = validate_proposal(p, ctx)
                if p.get("id") and p.get("id") != pidname and p.get("kind") != "candidate":
                    errs.append(f"id {p.get('id')!r} does not match its directory {pidname!r}")
                for e in errs:
                    problems.append(f"{where} proposal {n}: {e}")
                item = dict(p)
                item["pid"] = f"{worker}:{pidname}:{n}"
                item["worker"] = worker
                item["source_file"] = f"staged/{worker}/{pidname}/proposal.toml"
                item["valid"] = not errs
                item["digest"] = digest(p)
                proposals.append(item)
    return proposals, problems


def read_decisions(d):
    """Review decisions: review/*.csv then owner.csv. Returns {pid: [(source, row)]}."""
    out = {}
    files = []
    rdir = os.path.join(d, "review")
    if os.path.isdir(rdir):
        files += [(f"review/{n}", os.path.join(rdir, n)) for n in sorted(os.listdir(rdir)) if n.endswith(".csv")]
    owner = os.path.join(d, "owner.csv")
    if os.path.isfile(owner):
        files.append(("owner.csv", owner))
    for label, path in files:
        for row in read_csv(path):
            out.setdefault((row.get("pid") or "").strip(), []).append((label, row))
    return out


def decide(p, decisions, warnings):
    """The proposal's status from its decisions: owner wins; else any reject or hold; else accept."""
    rows = decisions.get(p["pid"], [])
    valid = []
    for label, row in rows:
        dec = (row.get("decision") or "").strip().lower()
        if dec not in DECISIONS:
            warnings.append(f"{label}: {p['pid']}: decision {dec!r} is not one of {', '.join(DECISIONS)}")
            continue
        if dec == "accept" and (row.get("digest") or "").strip() != p["digest"]:
            warnings.append(f"{label}: {p['pid']}: accepted a different version "
                            f"({(row.get('digest') or '').strip() or 'no digest'}, now {p['digest']}); "
                            "the proposal changed after review, so it needs review again")
            continue
        valid.append((label, dec))
    if not valid:
        return "proposed"
    owner = [dec for label, dec in valid if label == "owner.csv"]
    if owner:
        return {"accept": "accepted", "reject": "rejected", "hold": "held"}[owner[-1]]
    decs = [dec for _label, dec in valid]
    if "reject" in decs:
        return "rejected"
    if "hold" in decs:
        return "held"
    return "accepted"


def norm_url(u):
    parts = urllib.parse.urlsplit(u.strip())
    return (parts.netloc.lower().removeprefix("www.") + parts.path.rstrip("/")
            + ("?" + parts.query if parts.query else ""))


def trunc(s, n=110):
    s = str(s).replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def cmd_collect(args):
    root = args.root
    d = staging_dir(root, args.dir, create=False)
    trail_set = set(trail_ids(root))
    left_ids = {e.get("id") for e in left_out_entries(root)}
    proposals, problems = read_staged(d, trail_set)
    warnings = []
    decisions = read_decisions(d)
    known_pids = {p["pid"] for p in proposals}
    for pid in decisions:
        if pid and pid not in known_pids:
            warnings.append(f"a decision names {pid}, which is not a staged proposal")
    for p in proposals:
        p["status"] = decide(p, decisions, warnings) if p["valid"] and p["kind"] in APPLIED_KINDS \
            else ("invalid" if not p["valid"] else "info")

    # reports
    reports, report_rows = {}, []
    base = os.path.join(d, "staged")
    if os.path.isdir(base):
        for worker in sorted(os.listdir(base)):
            rp = os.path.join(base, worker, "report.csv")
            if not os.path.isfile(rp):
                continue
            rows = read_csv(rp)
            if rows and set(REPORT_COLUMNS) - set(rows[0]):
                problems.append(f"staged/{worker}/report.csv: columns must be {', '.join(REPORT_COLUMNS)}")
                continue
            reports[worker] = rows
            for r in rows:
                oc = (r.get("outcome") or "").strip()
                r["worker"] = worker
                if oc not in OUTCOMES:
                    problems.append(f"staged/{worker}/report.csv: {r.get('id')}: outcome {oc!r} is not "
                                    f"one of {', '.join(OUTCOMES)}")
                if oc in NEEDS_PAGES and not (r.get("pages") or "").strip():
                    problems.append(f"staged/{worker}/report.csv: {r.get('id')}: outcome {oc} needs "
                                    "pages (where it looked)")
                if oc in ("could-not-check", "refused", "not-found") and not (r.get("remark") or "").strip():
                    problems.append(f"staged/{worker}/report.csv: {r.get('id')}: outcome {oc} needs a remark")
                report_rows.append(r)
    sdir = os.path.join(d, "slices")
    missing = []
    if os.path.isdir(sdir):
        started = set(os.listdir(base)) if os.path.isdir(base) else set()
        for fn in sorted(os.listdir(sdir)):
            if not fn.endswith(".txt"):
                continue
            name = fn[:-4]
            ids = slice_ids(d, name)
            if name in reports:
                got = {(r.get("id") or "").strip() for r in reports[name]}
                lost = [i for i in ids if i not in got]
                if lost:
                    missing.append((name, lost))
            elif name in started:  # a worker staged something but wrote no report
                missing.append((name, ids))
    verified_ids = {p["id"] for p in proposals if p["kind"] == "verified"}
    for r in report_rows:
        if (r.get("outcome") or "").strip() == "verified" and r["worker"].startswith(("trails", "verify")) \
                and r.get("id") and r["id"] not in verified_ids and r["id"] in trail_set:
            warnings.append(f"{r['worker']}: {r['id']} is reported verified but has no `verified` proposal")

    # a record is verified against the pages it cites: say which cited pages were not opened
    opened = {}
    for r in report_rows:
        if (r.get("outcome") or "").strip() in ("verified", "changed"):
            opened.setdefault((r.get("id") or "").strip(), set()).update(
                norm_url(u) for u in re.split(r"[;\s]+", r.get("pages") or "") if u)
    for p in proposals:
        if p["kind"] == "verified" and p["valid"]:
            opened.setdefault(p["id"], set()).update(norm_url(u) for u in p.get("pages", []))
    for tid in sorted(opened):
        if tid not in trail_set:
            continue
        rec = load_toml(os.path.join(root, tid, "trail.toml"))
        hike = rec.get("hike") or {}
        cited = {norm_url(x["url"]) for x in hike.get("source", []) if x.get("url")}
        if hike.get("official_url"):
            cited.add(norm_url(hike["official_url"]))
        short = sorted(cited - opened[tid])
        if short:
            warnings.append(f"{tid}: {len(short)} of {len(cited)} cited pages are not listed as opened "
                            f"(first: {short[0]})")

    # cross-checks between proposals
    seen_fields = {}
    for p in proposals:
        if p["kind"] == "change" and p["valid"]:
            for e in p.get("edit", []):
                seen_fields.setdefault((p.get("target", "record"), p["id"], e["field"]), []).append(p["pid"])
    for key, pids in seen_fields.items():
        if len(pids) > 1:
            warnings.append(f"{key[1]} {key[2]} is edited by more than one proposal: {', '.join(pids)}")
    new_ids = {}
    for p in proposals:
        if p["kind"] == "new-record":
            new_ids.setdefault(p["id"], []).append(p["pid"])
    for tid, pids in new_ids.items():
        if len(pids) > 1:
            warnings.append(f"{tid} is proposed as a new record more than once: {', '.join(pids)}")
        if tid in left_ids and not any(q["kind"] == "left-out-remove" and q["id"] == tid for q in proposals):
            warnings.append(f"{tid} is a new record but is still in left-out.toml; it needs a "
                            "left-out-remove proposal")
    for p in proposals:
        if p["kind"] == "candidate" and p.get("id") in left_ids:
            warnings.append(f"candidate {p['id']} is in left-out.toml; say what changed since it was decided")

    # write collected.toml
    out = {"collected": {"date": today_str(args), "directory": os.path.relpath(d, root),
                         "proposals": len(proposals)},
           "proposal": []}
    for p in proposals:
        q = {k: v for k, v in p.items() if k not in ("valid",)}
        out["proposal"].append(q)
    with open(os.path.join(d, "collected.toml"), "w", encoding="utf-8") as f:
        f.write("# Written by `python3 tools/refresh.py collect`. Do not edit: record decisions in\n"
                "# review/*.csv and owner.csv (pid, digest, decision, note) and collect again.\n\n")
        f.write(dump_toml(out))
    summary = render_summary(d, proposals, problems, warnings, reports, report_rows, missing)
    with open(os.path.join(d, "summary.md"), "w", encoding="utf-8") as f:
        f.write(summary)
    counts = {}
    for p in proposals:
        counts[p["kind"]] = counts.get(p["kind"], 0) + 1
    print(f"{len(proposals)} proposals ({', '.join(f'{v} {k}' for k, v in sorted(counts.items())) or 'none'}), "
          f"{len(problems)} problems, {len(warnings)} warnings, "
          f"{sum(len(v) for _, v in missing)} ids not reported")
    print(f"written: {os.path.join(d, 'collected.toml')} and {os.path.join(d, 'summary.md')}")
    for pr in problems[:20]:
        print("PROBLEM:", pr)
    return 1 if problems else 0


def render_summary(d, proposals, problems, warnings, reports, report_rows, missing):
    L = [f"# Refresh summary, {os.path.basename(d)}", ""]
    kinds = {}
    for p in proposals:
        kinds.setdefault(p["kind"], {}).setdefault(p["status"], 0)
        kinds[p["kind"]][p["status"]] += 1
    L += ["## Counts", ""]
    if proposals:
        L += ["| Kind | Proposals | By status |", "| --- | ---: | --- |"]
        for k in KINDS:
            if k in kinds:
                L.append(f"| {k} | {sum(kinds[k].values())} | "
                         + ", ".join(f"{n} {s}" for s, n in sorted(kinds[k].items())) + " |")
    else:
        L.append("No proposals are staged.")
    outcomes = {}
    for r in report_rows:
        oc = (r.get("outcome") or "").strip()
        outcomes[oc] = outcomes.get(oc, 0) + 1
    if outcomes:
        L += ["", "Report rows by outcome: " + ", ".join(f"{n} {o}" for o, n in sorted(outcomes.items())) + "."]
    L += ["", f"Reports read: {len(reports)}."]
    if problems:
        L += ["", "## Problems (fix before review)", ""] + [f"- {x}" for x in problems]
    if warnings:
        L += ["", "## Warnings", ""] + [f"- {x}" for x in warnings]
    if missing:
        L += ["", "## Ids not reported", ""]
        for name, ids in missing:
            L.append(f"- {name}: {len(ids)} not in the report: {', '.join(ids[:15])}{'…' if len(ids) > 15 else ''}")
    chg = [p for p in proposals if p["kind"] in ("change", "declined") and p["valid"]]
    if chg:
        L += ["", "## Proposed changes", ""]
        for p in chg:
            L.append(f"### {p['id']}{' (left-out)' if p.get('target') == 'left-out' else ''}"
                     f" `{p['pid']}` {p['digest']} [{p['status']}]")
            L.append(p["summary"])
            for e in p.get("edit", []):
                old = trunc(json.dumps(e["old"], ensure_ascii=False)) if "old" in e else "(absent)"
                new = trunc(json.dumps(e["new"], ensure_ascii=False)) if "new" in e else "(removed)"
                L.append(f"- `{e['field']}`: {old} → {new}")
                L.append(f"  - page {e.get('page')}: \"{trunc(e.get('quote', ''), 160)}\"")
            for a in p.get("append", []):
                L.append(f"- add to `{a.get('table')}`: {trunc(json.dumps(a.get('entry'), ensure_ascii=False), 140)}")
                L.append(f"  - page {a.get('page')}: \"{trunc(a.get('quote', ''), 160)}\"")
            for fl in p.get("file", []):
                L.append(f"- file {'removed' if fl.get('remove') else 'set'}: {fl.get('to')} (source {fl.get('source_url')})")
            h = p.get("history")
            if h:
                L.append(f"- history: {trunc(h.get('change', ''), 160)} Basis: {h.get('basis_url')}")
            L.append("")
    for kind, title in (("new-record", "New records"), ("left-out-add", "Entries to add to left-out.toml"),
                        ("left-out-remove", "Entries to remove from left-out.toml")):
        sel = [p for p in proposals if p["kind"] == kind and p["valid"]]
        if sel:
            L += ["", f"## {title}", ""]
            for p in sel:
                L.append(f"- `{p['id']}` `{p['pid']}` {p['digest']} [{p['status']}]: {trunc(p['summary'], 160)}")
    ver = [p for p in proposals if p["kind"] == "verified" and p["valid"]]
    if ver:
        L += ["", f"## Verified, nothing changed ({len(ver)})", ""]
        L.append(", ".join(sorted(p["id"] for p in ver)))
    cand = [p for p in proposals if p["kind"] == "candidate" and p["valid"]]
    if cand:
        L += ["", "## Candidates (for the owner where marked)", "",
              "| Name | Where | Length | Recommendation | Borderline | Page |", "| --- | --- | --- | --- | --- | --- |"]
        for p in cand:
            L.append(f"| {p.get('name')} | {', '.join(p.get('regions', []))} {p.get('country', '')} | "
                     f"{p.get('length_mi', '')} | {p.get('recommendation')} | "
                     f"{'yes' if p.get('borderline') else ''} | {p.get('source_url')} |")
    cnc = [p for p in proposals if p["kind"] == "could-not-check" and p["valid"]]
    cnc_rows = [r for r in report_rows if (r.get("outcome") or "").strip() in ("could-not-check", "refused")]
    if cnc or cnc_rows:
        L += ["", "## Could not check", ""]
        for p in cnc:
            L.append(f"- {p['id']}: {p.get('what')}. {p.get('why')}"
                     + (f" Tried: {p['tried']}" if p.get("tried") else ""))
        for r in cnc_rows:
            L.append(f"- {r.get('id')} ({r['worker']}, {r.get('outcome')}): {trunc(r.get('remark', ''), 200)}")
    srows = [p for p in proposals if p.get("sources_md") and p["valid"]]
    if srows:
        L += ["", "## SOURCES.md rows to change when these are applied", ""]
        for p in srows:
            L.append(f"- `{p['id']}` [{p['status']}]: {p['sources_md']}")
    nf = [r for r in report_rows if (r.get("outcome") or "").strip() == "not-found"]
    if nf:
        L += ["", "## Searches that found nothing, and where they looked", ""]
        for r in nf:
            L.append(f"- {r.get('id')} ({r['worker']}): {trunc(r.get('pages', ''), 300)}")
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------------------- apply

class Doc:
    """A TOML file as lines, edited by targeted replacement. The file is never re-serialised."""

    def __init__(self, text):
        self.lines = text.split("\n")
        if self.lines and self.lines[-1] == "":
            self.lines.pop()

    def text(self):
        return "\n".join(self.lines) + "\n"

    def data(self):
        return tomllib.loads(self.text())

    def _headers(self):
        out = []
        for i, line in enumerate(self.lines):
            m = re.match(r"^\s*(\[\[?)\s*([A-Za-z0-9_.\- ]+?)\s*\]\]?\s*(#.*)?$", line)
            if m:
                out.append((i, m.group(1) == "[[", m.group(2).replace(" ", "")))
        return out

    def span(self, table, index=None):
        """(first line after the header, end) of a table. table '' is the top level.
        For an array of tables, index picks the nth block."""
        heads = self._headers()
        if table == "":
            end = heads[0][0] if heads else len(self.lines)
            return 0, end
        matches = [(i, k) for k, (i, is_arr, name) in enumerate(heads)
                   if name == table and is_arr == (index is not None)]
        if index is None:
            if not matches:
                raise RefreshError(f"the record has no [{table}] table")
            i, k = matches[0]
        else:
            if index >= len(matches):
                raise RefreshError(f"the record has no [[{table}]] number {index}")
            i, k = matches[index]
        end = heads[k + 1][0] if k + 1 < len(heads) else len(self.lines)
        return i + 1, end

    def key_line(self, span, key):
        start, end = span
        for i in range(start, end):
            m = re.match(r"^\s*" + re.escape(key) + r"\s*=(.*)$", self.lines[i])
            if m:
                return i
        return None

    @staticmethod
    def _split_comment(rest, want):
        """Split the text after '=' into (value text, trailing comment). The value must parse
        to `want`; a '#' inside a string is not a comment."""
        for pos in [m.start() for m in re.finditer("#", rest)] + [len(rest)]:
            candidate = rest[:pos]
            try:
                got = tomllib.loads("x = " + candidate)["x"]
            except tomllib.TOMLDecodeError:
                continue
            if got == want and type(got) is type(want):
                return candidate, rest[pos:]
        return None, None

    def get_line(self, span, key, want):
        i = self.key_line(span, key)
        if i is None:
            return None, None, None
        rest = self.lines[i].split("=", 1)[1]
        value, comment = self._split_comment(rest, want)
        if value is None:
            raise RefreshError(f"{key}: the line cannot be matched to the current value for a "
                               "targeted edit (a multi-line value?); change it by hand")
        return i, value, comment

    def set_value(self, span, key, new, old, has_old):
        if has_old:
            i, _v, comment = self.get_line(span, key, old)
            if i is None:
                raise RefreshError(f"{key} is absent, but the proposal expects {trunc(json.dumps(old, ensure_ascii=False), 60)}")
            self.lines[i] = f"{key} = {_scalar(new)}" + (" " + comment if comment else "")
        else:
            if self.key_line(span, key) is not None:
                raise RefreshError(f"{key} is already present, but the proposal expects it absent")
            start, end = span
            last = start - 1
            for i in range(start, end):
                if re.match(r"^\s*[A-Za-z0-9_\-\"]+\s*=", self.lines[i]):
                    last = i
            self.lines.insert(last + 1, f"{key} = {_scalar(new)}")

    def remove_value(self, span, key, old):
        i, _v, _c = self.get_line(span, key, old)
        if i is None:
            raise RefreshError(f"{key} is absent, but the proposal expects {trunc(json.dumps(old, ensure_ascii=False), 60)}")
        del self.lines[i]

    def append_block(self, table, entry):
        block = [f"[[{table}]]"] + [f"{k} = {_scalar(v)}" for k, v in entry.items()]
        heads = self._headers()
        same = [k for k, (i, is_arr, name) in enumerate(heads) if is_arr and name == table]
        if same:
            k = same[-1]
            end = heads[k + 1][0] if k + 1 < len(heads) else len(self.lines)
            # back up over blank lines and the comment lines that belong to the next block
            pos = end
            while pos > heads[k][0] + 1 and (self.lines[pos - 1].strip() == ""
                                             or self.lines[pos - 1].lstrip().startswith("#")):
                pos -= 1
            self.lines[pos:pos] = [""] + block
            return
        pos = len(self.lines)
        for i, line in enumerate(self.lines):
            if line.startswith("# History of this record") or re.match(r"^\[\[history\]\]", line):
                pos = i
                break
        # sit before the comment lines that lead into the history
        while pos > 0 and self.lines[pos - 1].lstrip().startswith("#"):
            pos -= 1
        while pos > 0 and self.lines[pos - 1].strip() == "":
            pos -= 1
        self.lines[pos:pos] = [""] + block

    def append_history(self, entry):
        if self.lines and self.lines[-1].strip() != "":
            self.lines.append("")
        self.lines += ["[[history]]"] + [f"{k} = {_scalar(v)}" for k, v in entry.items()]


def navigate(data, table, index):
    node = data
    if table:
        for part in table.split("."):
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
    if index is not None:
        if not isinstance(node, list) or index >= len(node):
            return None
        node = node[index]
    return node


def history_fields(p):
    h = p.get("history", {})
    if h.get("fields"):
        return list(h["fields"])
    out = []
    for e in p.get("edit", []):
        out.append(schema_path(e["field"]))
    for a in p.get("append", []):
        out.append(a["table"])
    for fl in p.get("file", []):
        out.append("shield.logo_file" if fl["to"].startswith("shield.") else "source.line_file")
    seen = []
    for f in out:
        if f not in seen:
            seen.append(f)
    return seen


def apply_record_edits(doc, p):
    """Apply the edits and appends of one proposal to a Doc. Raises RefreshError."""
    skipped = 0
    for e in p.get("edit", []):
        field = e["field"]
        table, index, key = split_path(field)
        data = doc.data()
        node = navigate(data, table, index)
        has_old, has_new = "old" in e, "new" in e
        current_has = isinstance(node, dict) and key in node
        if node is None:
            raise RefreshError(f"{field}: the record has no {table or 'top level'}"
                               + (f" number {index}" if index is not None else ""))
        if has_new and current_has and node[key] == e["new"] and type(node[key]) is type(e["new"]):
            skipped += 1
            continue
        if has_old and not current_has:
            raise RefreshError(f"{field}: the record has no such field now, but the proposal expects "
                               f"{trunc(json.dumps(e['old'], ensure_ascii=False), 70)}")
        if has_old and node[key] != e["old"]:
            raise RefreshError(f"{field}: the current value is {trunc(json.dumps(node[key], ensure_ascii=False), 70)}, "
                               f"not the proposal's old value {trunc(json.dumps(e['old'], ensure_ascii=False), 70)}")
        if not has_old and current_has:
            raise RefreshError(f"{field}: is already set to {trunc(json.dumps(node[key], ensure_ascii=False), 70)}, "
                               "but the proposal expects it absent")
        span = doc.span(table, index)
        if has_new:
            doc.set_value(span, key, e["new"], e.get("old"), has_old)
        else:
            doc.remove_value(span, key, e["old"])
    for a in p.get("append", []):
        data = doc.data()
        existing = data
        for part in a["table"].split("."):
            existing = existing.get(part, {}) if isinstance(existing, dict) else {}
        urls = {x.get("url") for x in existing} if isinstance(existing, list) else set()
        if a["entry"].get("url") and a["entry"]["url"] in urls:
            raise RefreshError(f"{a['table']}: an entry with {a['entry']['url']} is already there")
        doc.append_block(a["table"], a["entry"])
    if skipped and skipped == len(p.get("edit", [])) and not p.get("append"):
        raise AlreadyApplied(p["id"])


class AlreadyApplied(RefreshError):
    pass


def check_files(root, d, p):
    """Check the file operations of a proposal before anything is written."""
    tdir = os.path.join(root, p["id"])
    pdir = os.path.join(d, os.path.dirname(p["source_file"]))
    plan = []
    for fl in p.get("file", []):
        dest = os.path.join(tdir, fl["to"])
        exists = os.path.isfile(dest)
        if exists:
            want = fl.get("old_sha256")
            if not want:
                raise RefreshError(f"{fl['to']} exists; the proposal must give its old_sha256")
            if sha256_file(dest) != want:
                raise RefreshError(f"{fl['to']} has changed since the proposal was written (sha256 differs)")
        elif fl.get("old_sha256"):
            raise RefreshError(f"{fl['to']} is absent, but the proposal expects it to exist")
        if fl.get("remove"):
            if not exists:
                raise RefreshError(f"{fl['to']} is absent; nothing to remove")
            plan.append(("remove", dest, None))
        else:
            src = os.path.normpath(os.path.join(pdir, fl["from"]))
            if not src.startswith(os.path.normpath(pdir) + os.sep) or not os.path.isfile(src):
                raise RefreshError(f"staged file {fl['from']} is missing")
            plan.append(("copy", dest, src))
    return plan


def do_files(plan):
    for op, dest, src in plan:
        if op == "remove":
            os.remove(dest)
        else:
            shutil.copyfile(src, dest)


def sort_key_name(name):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(name).lower()).split())


def left_out_blocks(doc):
    """[(start, end)] line ranges of each [[trail]] block in left-out.toml (end exclusive,
    trailing blank lines excluded)."""
    heads = [i for i, l in enumerate(doc.lines) if l.strip() == "[[trail]]"]
    blocks = []
    for k, i in enumerate(heads):
        end = heads[k + 1] if k + 1 < len(heads) else len(doc.lines)
        while end > i + 1 and doc.lines[end - 1].strip() == "":
            end -= 1
        blocks.append((i, end))
    return blocks


def left_out_block_for(doc, lid):
    for i, end in left_out_blocks(doc):
        for j in range(i + 1, end):
            m = re.match(r'^id\s*=\s*"(.*)"\s*$', doc.lines[j])
            if m and m.group(1) == lid:
                return i, end
    return None


def apply_left_out(doc, p, today):
    kind = p["kind"]
    if kind == "left-out-add":
        entry = p["entry"]
        if left_out_block_for(doc, entry["id"]):
            raise RefreshError(f"{entry['id']} is already in left-out.toml")
        block = ["[[trail]]"] + [f"{k} = {_scalar(v)}" for k, v in entry.items()]
        blocks = left_out_blocks(doc)
        names = []
        for i, end in blocks:
            nm = ""
            for j in range(i + 1, end):
                m = re.match(r'^name\s*=\s*"(.*)"\s*$', doc.lines[j])
                if m:
                    nm = m.group(1)
            names.append(nm)
        want = sort_key_name(entry["name"])
        pos = None
        for (i, end), nm in zip(blocks, names):
            if sort_key_name(nm) > want:
                pos = i
                break
        if pos is None:
            doc.lines += [""] + block
        else:
            doc.lines[pos:pos] = block + [""]
        return
    blk = left_out_block_for(doc, p["id"])
    if blk is None:
        raise RefreshError(f"{p['id']} is not in left-out.toml")
    i, end = blk
    if kind == "left-out-remove":
        start = i
        # drop one blank line with it, and any comment lines directly above the block
        stop = end
        while stop < len(doc.lines) and doc.lines[stop].strip() == "":
            stop += 1
        del doc.lines[start:stop]
        if not doc.lines or doc.lines[-1].strip() != "":
            pass
        return
    # change: edits inside the block, using the same line logic with a block span
    for e in p.get("edit", []):
        key = e["field"]
        if not re.match(r"^[a-z_]+$", key):
            raise RefreshError(f"{key}: a left-out edit names a plain field")
        i, end = left_out_block_for(doc, p["id"])
        span = (i + 1, end)
        node = tomllib.loads("\n".join(doc.lines[i:end]).replace("[[trail]]", "[t]", 1)).get("t", {})
        has_old, has_new = "old" in e, "new" in e
        if has_old and node.get(key) != e["old"]:
            raise RefreshError(f"{key}: the current value is {trunc(json.dumps(node.get(key), ensure_ascii=False), 70)}, "
                               f"not the proposal's old value")
        if not has_old and key in node:
            raise RefreshError(f"{key} is already set, but the proposal expects it absent")
        if has_new:
            doc.set_value(span, key, e["new"], e.get("old"), has_old)
        else:
            doc.remove_value(span, key, e["old"])


def target_of(p):
    if p["kind"] in ("left-out-add", "left-out-remove") or p.get("target") == "left-out":
        return ("left-out", LEFT_OUT_FILE)
    return ("record", p["id"])


def cmd_apply(args):
    root = args.root
    d = staging_dir(root, args.dir, create=False)
    cpath = os.path.join(d, "collected.toml")
    if not os.path.isfile(cpath):
        raise RefreshError("no collected.toml; run `python3 tools/refresh.py collect` first")
    today = today_str(args)
    coll = load_toml(cpath)
    todo = [p for p in coll.get("proposal", []) if p.get("status") == "accepted"
            and (not args.only or p["pid"] in args.only)]
    log = []
    by_record = {}
    for p in todo:
        by_record.setdefault(target_of(p), []).append(p)
    failures = 0

    def refuse(p, why):
        nonlocal failures
        failures += 1
        log.append((p["pid"], "refused", why))
        print(f"REFUSED {p['pid']}: {why}")

    # left-out.toml first (one file, all its proposals), then records
    for (target, name), props in sorted(by_record.items(), key=lambda kv: (kv[0][0] != "left-out", kv[0][1])):
        if target == "left-out":
            path = os.path.join(root, LEFT_OUT_FILE)
            doc = Doc(open(path, encoding="utf-8").read())
            changed = False
            for p in props:
                if not verify_digest(d, p, refuse):
                    continue
                trial = Doc(doc.text())
                try:
                    apply_left_out(trial, p, today)
                    trial.data()
                except AlreadyApplied:
                    log.append((p["pid"], "already-applied", ""))
                    continue
                except (RefreshError, tomllib.TOMLDecodeError) as e:
                    refuse(p, str(e))
                    continue
                doc, changed = trial, True
                log.append((p["pid"], "applied" if not args.dry_run else "would-apply", ""))
                print(("would apply " if args.dry_run else "applied ") + p["pid"])
            if changed and not args.dry_run:
                write_text(path, doc.text())
            continue
        tdir = os.path.join(root, name)
        for p in props:
            if p["kind"] == "new-record":
                if not verify_digest(d, p, refuse):
                    continue
                if os.path.exists(tdir):
                    refuse(p, f"{name}/ already exists")
                    continue
                src = os.path.join(d, os.path.dirname(p["source_file"]))
                if not os.path.isfile(os.path.join(src, "trail.toml")):
                    refuse(p, "the staged trail.toml is missing")
                    continue
                if args.dry_run:
                    log.append((p["pid"], "would-apply", ""))
                    print("would apply " + p["pid"])
                    continue
                shutil.copytree(src, tdir, ignore=shutil.ignore_patterns("proposal.toml"))
                log.append((p["pid"], "applied", ""))
                print("applied " + p["pid"])
        rec_props = [p for p in props if p["kind"] != "new-record"]
        if not rec_props:
            continue
        path = os.path.join(tdir, "trail.toml")
        if not os.path.isfile(path):
            for p in rec_props:
                refuse(p, f"{name}/trail.toml does not exist")
            continue
        doc = Doc(open(path, encoding="utf-8").read())
        changed, pending_files = False, []
        for p in rec_props:
            if not verify_digest(d, p, refuse):
                continue
            trial = Doc(doc.text())
            try:
                plan = check_files(root, d, p) if p["kind"] == "change" else []
                if p["kind"] == "verified":
                    data = trial.data()
                    hike = data.get("hike")
                    field = "hike.checked" if hike is not None else "source.source_checked"
                    table, _i, key = split_path(field)
                    cur = navigate(data, table, None)
                    if cur is None or key not in cur:
                        raise RefreshError(f"{field} is absent; the record cannot take a verified date")
                    if str(cur[key]) >= p["date"]:
                        raise AlreadyApplied(field)
                    trial.set_value(trial.span(table), key, p["date"], str(cur[key]), True)
                elif p["kind"] in ("change", "declined"):
                    apply_record_edits(trial, p)
                    if p["kind"] == "change" or p.get("history"):
                        pass
                if p["kind"] in ("change", "declined") and p.get("history"):
                    h = p["history"]
                    last = (trial.data().get("history") or [{}])[-1].get("date", "")
                    entry = {"date": max(today, last), "change": h["change"],
                             "fields": history_fields(p), "basis": h["basis"],
                             "basis_url": h["basis_url"], "asked_by": h["asked_by"],
                             "outcome": "declined" if p["kind"] == "declined" else "applied"}
                    trial.append_history(entry)
                trial.data()
            except AlreadyApplied:
                log.append((p["pid"], "already-applied", ""))
                print(f"already applied {p['pid']}")
                continue
            except (RefreshError, tomllib.TOMLDecodeError) as e:
                refuse(p, str(e))
                continue
            doc, changed = trial, True
            pending_files += plan
            log.append((p["pid"], "applied" if not args.dry_run else "would-apply", ""))
            print(("would apply " if args.dry_run else "applied ") + p["pid"])
        if changed and not args.dry_run:
            write_text(path, doc.text())
            do_files(pending_files)
    if not args.dry_run:
        with open(os.path.join(d, "apply-log.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(("pid", "result", "reason"))
            w.writerows(log)
        applied = sum(1 for _p, r, _w in log if r == "applied")
        print(f"{applied} applied, {failures} refused. Next: tools/build_index.py, tools/validate.py, "
              "tools/check_history.py, the test suites, CHANGELOG.md.")
    else:
        print(f"dry run: {sum(1 for _p, r, _w in log if r == 'would-apply')} would apply, {failures} refused")
    return 1 if failures else 0


def verify_digest(d, p, refuse):
    """The staged proposal must still be the one that was collected and reviewed."""
    path = os.path.join(d, p["source_file"])
    if not os.path.isfile(path):
        refuse(p, "the staged proposal file is missing")
        return False
    try:
        doc = load_toml(path)
        n = int(p["pid"].rsplit(":", 1)[1])
        now = digest(doc["proposal"][n - 1])
    except Exception as e:
        refuse(p, f"the staged proposal cannot be read again: {e}")
        return False
    if now != p["digest"]:
        refuse(p, "the staged proposal changed after it was collected; collect and review again")
        return False
    return True


def write_text(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)


# ----------------------------------------------------------------------------- main

def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=ROOT, help="the repository checkout (default: this one)")
    ap.add_argument("--dir", help="the staging directory (default: the newest under refresh/)")
    ap.add_argument("--today", help="today's date, YYYY-MM-DD (for tests)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("preflight", help="clean tree, validator, tests, staging directory")
    p.add_argument("--no-tests", action="store_true")
    p.add_argument("--no-validate", action="store_true")
    p.set_defaults(fn=cmd_preflight)
    p = sub.add_parser("slices", help="split trail ids and left-out entries into balanced slices")
    p.add_argument("--n", type=int, required=True, help="number of trail slices")
    p.add_argument("--left-out-n", type=int, default=2, help="number of left-out slices (default 2)")
    p.add_argument("--since", type=int, metavar="DAYS",
                   help="only trails whose last check (hike.checked, else source.source_checked) is "
                        "older than DAYS days")
    p.set_defaults(fn=cmd_slices)
    p = sub.add_parser("links", help="fetch every address once, politely, into links.csv")
    p.add_argument("--delay", type=float, default=2.0, help="seconds between requests to one host")
    p.add_argument("--timeout", type=float, default=20.0)
    p.add_argument("--hosts", type=int, default=6, help="hosts fetched at the same time")
    p.add_argument("--user-agent", default=USER_AGENT)
    p.add_argument("--limit", type=int, help="only the first N addresses (a trial run)")
    p.add_argument("--only-prefix", help="only addresses that start with this text")
    p.set_defaults(fn=cmd_links)
    p = sub.add_parser("collect", help="gather staged proposals and reports")
    p.set_defaults(fn=cmd_collect)
    p = sub.add_parser("apply", help="apply the proposals marked accepted in collected.toml")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--only", nargs="+", metavar="PID")
    p.set_defaults(fn=cmd_apply)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except RefreshError as e:
        print(f"refresh: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
