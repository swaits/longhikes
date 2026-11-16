"""The Atom feed of the changelog: /feed.xml.

One entry for each dated heading of CHANGELOG.md ("## 2026-11-16 - What changed"),
newest first, as many as FEED_MAX. An entry's date is its heading's date, never
the build date, so the feed changes only when the changelog does. Each entry links
to its heading on /data/changelog/ and carries the section as HTML.

No author is named: site.toml names none, so the feed's author is the site.
"""
import html
import os
import re

from . import docs, md

FEED_MAX = 30
HEADING = re.compile(r"^(\d{4}-\d{2}-\d{2})\s*[-:–]\s*(.+)$")


def entries(text):
    """[(date, title, slug, markdown body)] for the changelog's dated sections, in file order."""
    slugs = [slug for level, _, slug in md.headings(text) if level == 2]
    out = []
    for (heading, body), slug in zip(md.split_sections(text, level=2), slugs):
        m = HEADING.match(heading)
        if m:
            out.append((m.group(1), m.group(2).strip(), slug, body))
    return out


def newest_date(text):
    """The newest date in the changelog, or ""."""
    return max((e[0] for e in entries(text)), default="")


def atom(text, site):
    """The Atom document for a changelog's text; "" when the site has no base_url."""
    if not site.base_url:
        return ""
    base = site.base_url

    def absolute(href):
        return base + href if href.startswith("/") else href

    rewrite = docs.make_link_rewrite(site)

    def link_rewrite(href):
        target = rewrite(href)
        return absolute(target) if target else target

    found = entries(text)[:FEED_MAX]
    q = lambda s: html.escape(s, quote=True)  # noqa: E731
    rows = []
    for date, title, slug, body in found:
        content = md.render(body, heading_offset=2, link_rewrite=link_rewrite)
        url = f"{base}/data/changelog/#{slug}"
        rows.append(
            f"  <entry>\n    <title>{q(title)}</title>\n    <id>{q(url)}</id>\n"
            f'    <link rel="alternate" type="text/html" href="{q(url)}"/>\n'
            f"    <updated>{date}T00:00:00Z</updated>\n"
            f'    <content type="html">{q(content)}</content>\n  </entry>\n')
    updated = f"{max((e[0] for e in found), default='1970-01-01')}T00:00:00Z"
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en">\n'
            f"  <title>{q(site.name)}: what changed</title>\n"
            f"  <subtitle>{q(site.tagline)}</subtitle>\n"
            f"  <id>{q(base)}/feed.xml</id>\n"
            f'  <link rel="self" type="application/atom+xml" href="{q(base)}/feed.xml"/>\n'
            f'  <link rel="alternate" type="text/html" href="{q(base)}/data/changelog/"/>\n'
            f"  <updated>{updated}</updated>\n"
            f"  <author><name>{q(site.name)}</name></author>\n"
            f"{''.join(rows)}</feed>\n")


def write_feed(out_dir, site, repo_root):
    """Write feed.xml from the changelog. Returns its path, or "" when there is no base_url."""
    text = docs.read_doc(repo_root, "CHANGELOG.md")
    xml = atom(text, site)
    path = os.path.join(out_dir, "feed.xml")
    if not xml:
        if os.path.isfile(path):
            os.remove(path)
        return ""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(xml)
    return path
