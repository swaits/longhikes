"""Checks for the small editorial data files at the top of the repository.

    glossary.toml     [[term]]        id, term, definition, optional source_url, see
    collections.toml  [[collection]]  id, name, members, definition, source_url, source_publisher
    authors.toml      [[author]]      name, credits, optional kind

Each function appends one message per problem to `errors`. Used by tools/validate.py, which passes
the records it has read. Python 3 standard library only. Fields are in docs/schema.md.
"""
import os
import re
import tomllib

ID_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
DASH_RE = re.compile(r"[–—]| - ")


def _load(root, name, errors):
    path = os.path.join(root, name)
    if not os.path.isfile(path):
        errors.append(f"{name}: missing")
        return None
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:  # noqa: BLE001 - report and continue
        errors.append(f"{name}: does not parse: {e}")
        return None


def _text(table, field, where, errors, required=True):
    value = table.get(field)
    if value is None:
        if required:
            errors.append(f"{where} is missing required field {field}")
        return ""
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{where} {field} must be a non-empty string")
        return ""
    return value


def _url(table, field, where, errors, required=False):
    value = _text(table, field, where, errors, required)
    if value and not value.startswith(("https://", "http://")):
        errors.append(f"{where} {field} must be an http(s) address")


def check_unknown(table, allowed, where, errors):
    for name in sorted(set(table) - set(allowed)):
        errors.append(f"{where} has unknown field {name}")


def check_glossary_entries(entries, errors, where="glossary.toml"):
    if not isinstance(entries, list) or not entries:
        errors.append(f"{where}: must hold at least one [[term]] entry")
        return
    seen_ids, seen_terms = set(), set()
    for i, t in enumerate(entries, 1):
        if not isinstance(t, dict):
            errors.append(f"{where}: entry {i} must be a table ([[term]])")
            continue
        who = f"{where}: {t.get('id') or 'entry ' + str(i)}"
        check_unknown(t, {"id", "term", "definition", "source_url", "see"}, who, errors)
        tid = _text(t, "id", who, errors)
        term = _text(t, "term", who, errors)
        definition = _text(t, "definition", who, errors)
        if tid and not ID_RE.fullmatch(tid):
            errors.append(f"{who} id must be lower case words and hyphens")
        if tid in seen_ids:
            errors.append(f"{who} duplicate id")
        seen_ids.add(tid)
        if term.lower() in seen_terms:
            errors.append(f"{who} duplicate term {term!r}")
        seen_terms.add(term.lower())
        if DASH_RE.search(definition):
            errors.append(f"{who} definition uses a dash as punctuation")
        if definition and not definition.endswith((".", "?")):
            errors.append(f"{who} definition must end with a full stop")
        _url(t, "source_url", who, errors)
        see = t.get("see", [])
        if not isinstance(see, list) or not all(isinstance(p, str) and p.startswith("/") and p.endswith("/") for p in see):
            errors.append(f"{who} see must be a list of site paths, each starting and ending with /")
    terms = [t.get("term", "") for t in entries if isinstance(t, dict)]
    if terms != sorted(terms, key=lambda s: s.lower()) and False:
        errors.append(f"{where}: entries must be sorted by term")


def check_collection_entries(entries, trail_ids, errors, where="collections.toml"):
    if not isinstance(entries, list) or not entries:
        errors.append(f"{where}: must hold at least one [[collection]] entry")
        return
    seen = set()
    for i, c in enumerate(entries, 1):
        if not isinstance(c, dict):
            errors.append(f"{where}: entry {i} must be a table ([[collection]])")
            continue
        who = f"{where}: {c.get('id') or 'entry ' + str(i)}"
        check_unknown(c, {"id", "name", "members", "definition", "source_url", "source_publisher"}, who, errors)
        cid = _text(c, "id", who, errors)
        _text(c, "name", who, errors)
        definition = _text(c, "definition", who, errors)
        _text(c, "source_publisher", who, errors)
        _url(c, "source_url", who, errors, required=True)
        if cid and not ID_RE.fullmatch(cid):
            errors.append(f"{who} id must be lower case words and hyphens")
        if cid in seen:
            errors.append(f"{who} duplicate id")
        seen.add(cid)
        if DASH_RE.search(definition):
            errors.append(f"{who} definition uses a dash as punctuation")
        members = c.get("members")
        if not isinstance(members, list) or len(members) < 2 or not all(isinstance(m, str) for m in members):
            errors.append(f"{who} members must be a list of at least two trail ids")
            continue
        if len(set(members)) != len(members):
            errors.append(f"{who} members repeats an id")
        for m in members:
            if m not in trail_ids:
                errors.append(f"{who} member {m} is not a trail in the dataset")


def check_author_entries(entries, routes, errors, where="authors.toml"):
    """routes: [(trail id, route.creator)] for every route in the dataset."""
    if not isinstance(entries, list) or not entries:
        errors.append(f"{where}: must hold at least one [[author]] entry")
        return
    creators = {c for _, c in routes}
    seen_names, seen_credits = set(), {}
    for i, a in enumerate(entries, 1):
        if not isinstance(a, dict):
            errors.append(f"{where}: entry {i} must be a table ([[author]])")
            continue
        who = f"{where}: {a.get('name') or 'entry ' + str(i)}"
        check_unknown(a, {"name", "credits", "kind"}, who, errors)
        if a.get("kind", "person") not in ("person", "organisation"):
            errors.append(f"{who} kind must be person or organisation")
        name = _text(a, "name", who, errors)
        if name in seen_names:
            errors.append(f"{who} duplicate name")
        seen_names.add(name)
        credits = a.get("credits")
        if not isinstance(credits, list) or len(credits) < 1 or not all(isinstance(c, str) for c in credits):
            errors.append(f"{who} credits must list at least one exact route.creator value")
            continue
        for c in credits:
            if c not in creators:
                errors.append(f"{who} credit {c!r} is not the route.creator of any route")
            if name in seen_credits.setdefault(c, []):
                errors.append(f"{who} credit {c!r} is given twice")
            seen_credits[c].append(name)
            if name and name.lower() not in c.lower():
                errors.append(f"{who} credit {c!r} does not contain the name")


def check_datafiles(root, trails, errors):
    """Check glossary.toml, collections.toml and authors.toml against the records."""
    doc = _load(root, "glossary.toml", errors)
    if doc is not None:
        for name in sorted(set(doc) - {"term"}):
            errors.append(f"glossary.toml: unknown top level field {name}")
        check_glossary_entries(doc.get("term"), errors)
    doc = _load(root, "collections.toml", errors)
    if doc is not None:
        for name in sorted(set(doc) - {"collection"}):
            errors.append(f"collections.toml: unknown top level field {name}")
        check_collection_entries(doc.get("collection"), {r.get("id") for r in trails}, errors)
    doc = _load(root, "authors.toml", errors)
    if doc is not None:
        for name in sorted(set(doc) - {"author"}):
            errors.append(f"authors.toml: unknown top level field {name}")
        routes = [(r.get("id"), r.get("route", {}).get("creator", "")) for r in trails if r.get("kind") == "route"]
        check_author_entries(doc.get("author"), routes, errors)
