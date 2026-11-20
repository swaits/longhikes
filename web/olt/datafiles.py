"""The small editorial data files at the top of the repository, read for the pages built from them.

    glossary.toml     [[term]]        the Glossary page (olt/reference.py)
    collections.toml  [[collection]]  named sets of trails set side by side (olt/standing.py)
                      [[list]]        which lists the home page shows, and in what order (olt/home.py)
    authors.toml      [[author]]      route authors, and the words about the people among them (olt/authors.py)
    tools/season_blind_test.json      how the judged seasons did against the seasons pages state (olt/reference.py)

Each is checked by tools/validate.py and described in docs/schema.md. Like left-out.toml, a file
is looked for in the repository being built and then in this one, so a test repository without
one still builds.
"""
import json
import os
import tomllib

REAL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load(repo_root, name, table):
    """The array of tables `table` in file `name`, or []."""
    for base in (repo_root, REAL_ROOT):
        path = os.path.join(base or REAL_ROOT, name)
        if os.path.isfile(path):
            with open(path, "rb") as f:
                return tomllib.load(f).get(table) or []
    return []


def glossary(repo_root):
    return load(repo_root, "glossary.toml", "term")


def collections(repo_root):
    return load(repo_root, "collections.toml", "collection")


def authors(repo_root):
    return load(repo_root, "authors.toml", "author")


def lists(repo_root):
    """The [[list]] entries of collections.toml: a list's key, and `home`, its place in the home page's row."""
    return load(repo_root, "collections.toml", "list")


def blind_test(repo_root):
    """The blind test of the judged seasons (tools/season_blind_test.json, written by
    tools/season_judge.py score), or None when there is none."""
    for base in (repo_root, REAL_ROOT):
        path = os.path.join(base or REAL_ROOT, "tools", "season_blind_test.json")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    return None
