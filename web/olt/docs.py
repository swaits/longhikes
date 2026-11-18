"""Document-backed pages: /sources/, /logos/, /about/, /data/ and sub-pages.

Markdown goes through olt.md; relative links are rewritten to site pages.
Repository paths with no site page become repository links when repo_url
is set, and plain text otherwise (never a dead link).
"""
import collections
import os
import re

from . import common, elevation, facets, md, words
from .markup import Markup, esc

REAL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read_doc(repo_root, relpath):
    """Read a repository document, falling back to this checkout's copy."""
    for base in (repo_root, REAL_ROOT):
        path = os.path.join(base, *relpath.split("/"))
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return f.read()
    return ""


_PAGE_MAP = {
    "docs/schema.md": "/data/schema/",
    "schema.md": "/data/schema/",
    "notice.md": "/logos/",
    "sources.md": "/sources/",
    "contributing.md": "/about/",
    "changelog.md": "/data/changelog/",
    "readme.md": "/about/",
    "license": "/licences/LICENSE",
    "trails.csv": "/data/trails.csv",
    "trails.json": "/data/trails.json",
    "index.geojson": "/data/index.geojson",
    "overview.geojson": "/data/overview.geojson",
}


def _classify(href, site):
    """Site href for a Markdown destination, or None to drop the link."""
    if not href or href.startswith(("#", "/", "http://", "https://", "mailto:", "tel:")):
        return href
    path, _, frag = href.partition("#")
    norm = path[2:] if path.startswith("./") else path
    while norm.startswith("../"):
        norm = norm[3:]
    key = norm.lower()
    if key in _PAGE_MAP:
        return _PAGE_MAP[key] + (f"#{frag}" if frag else "")
    if key.startswith("licenses/") and key.endswith(".txt"):
        return "/licences/" + norm.split("/", 1)[1] + (f"#{frag}" if frag else "")
    if site.repo_url:
        return site.blob_url(norm) + (f"#{frag}" if frag else "")
    return None


def make_link_rewrite(site):
    """md.render link_rewrite: the site href, or None (md.py then keeps the link's text only)."""
    return lambda href: _classify(href, site)


def _link_text(html, phrase, url):
    """Link each occurrence of phrase in the text of html (not inside a tag or an existing link)."""
    out, depth = [], 0
    for part in re.split(r"(<[^>]*>)", html):
        if part.startswith("<"):
            if re.match(r"<a[\s>]", part):
                depth += 1
            elif part.startswith("</a"):
                depth = max(0, depth - 1)
        elif depth == 0 and phrase in part:
            part = part.replace(phrase, f'<a href="{esc(url)}">{phrase}</a>')
        out.append(part)
    return "".join(out)


def link_requests(html, site):
    """Link the documents' own words asking readers to open an issue or to write
    to the maintainers, when site.toml says where (repo_url, contact_url).
    The wording is left as the documents have it; with neither set, nothing changes."""
    issue = site.issues_url or site.contact_url
    contact = site.contact or site.repo_url
    if issue:
        for phrase in ("Open an issue", "open an issue", "opening an issue"):
            html = _link_text(html, phrase, issue)
    if contact:
        for phrase in ("writing to the repository maintainers", "write to the repository maintainers"):
            html = _link_text(html, phrase, contact)
    return Markup(html)


def render_doc(text, site, *, heading_offset=0, drop_h1=False):
    """Render Markdown to HTML with rewritten links and scrollable tables."""
    if drop_h1:
        text = re.sub(r"\A# [^\n]*\n+", "", text, count=1)
    html = md.render(text, heading_offset=heading_offset,
                     link_rewrite=make_link_rewrite(site))
    html = html.replace("<table>", '<div class="table-wrap"><table>')
    html = html.replace("</table>", "</table></div>")
    return Markup(html)


def sections_map(text):
    return dict(md.split_sections(text, level=2))


def render_sections(text, site, titles, *, level=2):
    """Render named level-2 sections only, each under its own heading."""
    found = sections_map(text) if level == 2 else {}
    out = []
    for title in titles:
        body = found.get(title)
        if body is None:
            continue
        out.append(md.render(f"## {title}\n\n{body}", link_rewrite=make_link_rewrite(site)))
    html = "\n".join(out)
    html = html.replace("<table>", '<div class="table-wrap"><table>')
    html = html.replace("</table>", "</table></div>")
    return Markup(html)


def _record_links(recs):
    """The records as a link list, one name per line."""
    return Markup('<ul class="linklist">' + "".join(
        f'<li><a href="{esc(common.trail_path(r))}">{common.name(r)}</a></li>' for r in recs) + "</ul>")


def _group_by(records, keyfn):
    groups = collections.defaultdict(list)
    for r in records:
        groups[keyfn(r)].append(r)
    for recs in groups.values():
        recs.sort(key=lambda r: r["name"].lower())
    return groups


def sources_page(records, site, repo_root):
    """(title, description, body) for /sources/."""
    by_licence = _group_by(records, lambda r: r.get("source", {}).get("licence", "") or "unknown")
    by_source = _group_by(records, lambda r: r.get("source", {}).get("line_source", "") or "none (no line included)")
    by_status = _group_by(records, lambda r: r.get("source", {}).get("status", "") or "none")

    def measured(recs):
        return sum(1 for r in recs if r.get("verification", {}).get("verified"))

    n_measured = measured(records)
    status_cells = (f'<div><dt>Track measured</dt><dd>{n_measured}<small>Records whose track was '
                    f'downloaded and measured (verification), whatever its source</small></dd></div>')
    for key in ("verified", "osm-only", "found", "none"):
        recs = by_status.get(key, [])
        k = measured(recs)
        of_these = (f"; {k} of these measured" if k and k < len(recs) else
                    "; all measured" if k and k == len(recs) and key != "verified" else "")
        status_cells += (f'<div><dt>Source status: {esc(words.label(words.SOURCE_STATUS, key))}</dt>'
                         f'<dd>{len(recs)}<small>{esc(words.meaning(words.SOURCE_STATUS, key))}{esc(of_these)}</small></dd></div>')
    other = [k for k in by_status if k not in ("verified", "osm-only", "found", "none")]

    def group_rows(groups, label_of):
        rows = ""
        for key in sorted(groups, key=lambda k: (-len(groups[k]), str(k).lower())):
            recs = groups[key]
            lines = sum(1 for r in recs if common.has_line(r))
            rows += (f'<tr><td>{label_of(key)}</td><td class="num">{len(recs)}</td>'
                     f'<td class="num">{lines}</td><td>{_record_links(recs)}</td></tr>')
        return rows

    def source_label(k):
        # A record with no track holds a value such as "none (no line included)"; say it in words.
        if str(k).strip().lower().startswith(("none (no line", "none (no track")):
            return "None (no track included)"
        return esc(k)

    def lic_label(k):
        return Markup(f'{esc(words.label(words.LICENCES, k))} <code class="raw">{esc(k)}</code>')

    head = ('<thead><tr><th scope="col">{0}</th><th scope="col">Records</th>'
            '<th scope="col">With a track</th><th scope="col">Trails</th></tr></thead>')
    elev_models = {}
    for r in records:
        src = (elevation.get(r) or {}).get("source") or {}
        if src.get("attribution"):
            key = (src.get("model", ""), src.get("url", ""), src["attribution"])
            elev_models[key] = elev_models.get(key, 0) + 1
    elev_credit = ""
    if elev_models:
        items = ""
        for (model, url, attribution), n in sorted(elev_models.items()):
            model_html = (f'<a href="{esc(url)}">{esc(model)}</a>' if url else esc(model)) if model else "The elevation model"
            items += (f'<p>{model_html}, used for {n} trail{"s" if n != 1 else ""}.</p>'
                      f'<p>{esc(attribution)}</p>')
        elev_credit = (f'<div class="doc-block"><h3>Elevation model</h3>'
                       f'<p>The elevation figures and profiles on the trail pages were computed '
                       f'from each track and this model. Its credit, as it gives it:</p>{items}</div>')
    computed = f"""<div class="container section">
  <div class="section-head"><h2 id="sources-at-a-glance">At a glance</h2>
  <p>Counted from the {len(records)} records. Each trail page names its own source, licence and credit.
  The source status says where a track was looked for; whether it was measured is counted separately.</p></div>
  <dl class="tally">{status_cells}</dl>
  {f'<p class="note">Other source status values: {esc(", ".join(map(str, other)))}.</p>' if other else ""}
  <div class="doc-block"><h3>By licence</h3><div class="table-wrap"><table>
  {head.format("Licence")}
  <tbody>{group_rows(by_licence, lic_label)}</tbody></table></div></div>
  <div class="doc-block"><h3>By track source</h3><div class="table-wrap"><table>
  {head.format("Track source")}
  <tbody>{group_rows(by_source, source_label)}</tbody></table></div></div>
  {elev_credit}
</div>"""
    doc_html = render_doc(read_doc(repo_root, "SOURCES.md"), site, drop_h1=True)
    body = (f'<div class="page-head"><div class="container">{BREAD}<li aria-current="page">Sources</li></ol></nav><header class="titleblock">'
            f'<div class="titleblock__text"><h1>Sources</h1>'
            f'<p class="page-head__lede">Where the tracks come from, and the terms each source states.</p>'
            f'</div></header></div></div>{computed}'
            f'<div class="container section"><div class="prose doc">{doc_html}</div></div>')
    n_tracks = sum(1 for r in records if r.get("source", {}).get("line_file"))
    description = (f"Where the tracks and facts for the {len(records)} trails come from: {n_tracks} tracks included, "
                   f"each source's licence and terms, and the credit each asks for.")
    return "Sources and Licences for Trail Tracks and Data", common.cut_at_word(description, common.DESCRIPTION_LIMIT), Markup(body)


def logos_page(records, site, repo_root):
    """(title, description, body) for /logos/."""
    notice_html = link_requests(render_sections(read_doc(repo_root, "NOTICE.md"), site,
                                                ["Logos and marks", "Removal"]), site)
    with_logo = [r for r in sorted(records, key=lambda r: r["name"].lower())
                 if "shield" in r["derived"]["files"]]
    cards = ""
    for r in with_logo:
        sh = r.get("shield", {})
        src = sh.get("logo_source", "")
        if src.startswith(("http://", "https://")):
            src_html = Markup(f'<a href="{esc(src)}">{esc(src)}</a>')
        elif src:
            src_html = esc(src)
        else:
            src_html = Markup("Not recorded")
        cards += f"""<li class="logo-card">
  {common.plate(r, size="lg", link=True, alt="")}
  <div><h3><a href="{esc(common.trail_path(r))}">{common.name(r)}</a></h3>
  <dl class="facts"><div><dt>Holder</dt><dd>{esc(sh.get("logo_owner", "") or "Not recorded")}</dd></div>
  <div><dt>Taken from</dt><dd>{src_html}</dd></div></dl></div>
</li>"""
    counts = collections.Counter(r.get("shield", {}).get("status", "") for r in records)
    body = f"""<div class="page-head"><div class="container">{BREAD}<li aria-current="page">Logos</li></ol></nav><header class="titleblock">
  <div class="titleblock__text"><h1>Logos</h1>
  <p class="page-head__lede">Logos are shown only to identify each trail. They belong to their holders.</p>
  </div></header></div></div>
<div class="container section"><div class="prose doc">{notice_html}{f'<p><a href="{esc(site.removal_url)}">Ask for a track or logo to be removed, or its credit changed</a>.</p>' if site.is_github else ""}</div></div>
<div class="container section"><div class="section-head"><h2>Every logo in the dataset</h2>
<p>{len(with_logo)} records include a logo file.</p></div>
<ul class="logo-grid">{cards}</ul>
<p class="note">No logo file is included for the other records. {counts["no-logo-exists"]} have no emblem of
their own (<code class="raw">no-logo-exists</code>): the pages that would show one were checked and none does.
{counts["logo-not-found"]} have an emblem, or may have one, but no usable artwork of it was found at a source the
dataset allows (<code class="raw">logo-not-found</code>). Each record says in its logo note where an emblem was
looked for.</p></div>"""
    n_logos = sum(1 for r in records if "shield" in r["derived"]["files"])
    description = (f"The {n_logos} trail logos shown on {site.name}, who holds each one, "
                   f"and how a holder can ask for a logo to be removed.")
    return "Trail Logos and Their Holders", common.cut_at_word(description, common.DESCRIPTION_LIMIT), Markup(body)


BREAD = Markup('<nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="/about/">About</a></li>')

ABOUT_PARTS = (
    # (anchor or path, title, what it is)
    ("#what-this-is", "What this is", "A guide to the long trails, built from an open dataset"),
    ("#how-trails-are-chosen", "How trails are chosen", "The rule, and what held, deferred and candidate mean"),
    ("#when-a-gpx-is-included", "When a GPX is included", "Whose tracks may be passed on, and routes' authors' terms"),
    ("/data/", "Data and downloads", "Every trail and track in bulk, the per-trail files and the licences"),
    ("/sources/", "Sources and their terms", "Where each track comes from, and the terms each source states"),
    ("/logos/", "Logos", "Each trail's logo, who holds it, and how to ask for removal"),
    ("/data/schema/", "Record schema", "Every field of a trail's record (trail.toml) and what it means"),
    ("/data/changelog/", "Changelog", "What changed, release by release"),
    ("/left-out/", "Considered and left out", "Trails that were looked at and left out, and why"),
    ("#correct-or-add", "Correct or add a trail", "Report a problem, suggest a trail, or edit the data"),
)


def _count_line(records, key, value):
    return sum(1 for r in records if str(r.get(key, "")) == value)


def maintainer_section(site):
    """The About page's "Who maintains this", from site.toml and facts the repository holds:
    the name and the profile page, the licence, the sources, how a correction is made, and what
    the site does not do. "" when site.toml names no maintainer. No email address, no biography."""
    if not site.maintainer_name:
        return ""
    who = esc(site.maintainer_name)
    if site.maintainer_url:
        who = f'<a href="{esc(site.maintainer_url)}">{who}</a>'
    ask = "open an issue on GitHub"
    if site.contact:
        ask = f'<a href="{esc(site.contact)}">open an issue on GitHub</a>'
    return f"""<section aria-labelledby="who-maintains"><h2 id="who-maintains">Who maintains this</h2>
<p>{esc(site.name)} is maintained by {who}. It is an open project: the data, the code and every change are in a public repository.</p>
<ul>
<li>The records and the compiled index are public domain (CC0 1.0). Each track keeps the licence of its source.</li>
<li>Every fact in a record names the page it was read on, and each record keeps a history of what changed and why.</li>
<li>To correct a fact, suggest a trail or ask for a track or logo to be removed, {ask}. Every trail page has its own &ldquo;Report a problem&rdquo; link.</li>
<li>The site has no ads, no accounts, no tracking and no analytics. Your theme, units and saved trails stay in your own browser. Maps load their tiles from OpenFreeMap.</li>
</ul>
</section>
"""


def about_page(records, site, repo_root):
    """(title, description, body) for /about/: the hub for the project and the dataset."""
    readme = read_doc(repo_root, "README.md")
    found = sections_map(readme)

    def quoted(title, heading):
        body = found.get(title)
        if body is None:
            return ""
        return link_requests(render_doc(f"### {heading}\n\n{body}", site), site)

    what = quoted("What this is, and what it is not", "The dataset’s own words")
    rule = quoted("Inclusion rule", "The rule as the dataset states it")
    rest = link_requests(render_sections(readme, site, ["How to use it", "Other lists of long trails", "Licences", "Report an error"]), site)
    contrib = render_doc(read_doc(repo_root, "CONTRIBUTING.md"), site, heading_offset=1)
    cards = "".join(
        f'<li><a href="{esc(href)}">{esc(title)}</a><small>{esc(what_)}</small></li>'
        for href, title, what_ in ABOUT_PARTS)
    n = len(records)
    routes = sum(1 for r in records if common.is_route(r))
    tiers = collections.Counter(r.get("tier", "") for r in records)
    held = _count_line(records, "wave", "held")
    tier_rows = "".join(
        f'<tr><td>{esc(words.label(words.TIERS, t))} <code class="raw">{esc(t)}</code></td>'
        f'<td>{esc(words.meaning(words.TIERS, t))}.</td><td class="num">{tiers[t]}</td></tr>'
        for t in ("national", "regional", "short", "deferred", "candidate") if tiers[t])
    policies = collections.Counter(common.policy(r) for r in records if common.is_route(r))
    policy_rows = "".join(
        f'<tr><td>{common.policy_chip(p)}</td><td>{esc(words.POLICIES[p][1])}. {esc(words.POLICIES[p][2])}</td>'
        f'<td class="num">{policies[p]}</td></tr>'
        for p in ("open", "sold", "withheld", "unclear") if policies[p])
    lines = sum(1 for r in records if common.has_line(r))
    forms = ""
    if site.repo_url and site.is_github:
        forms = (f'<ul class="linklist">'
                 f'<li><a href="{esc(site.correction_url())}">Report a problem</a><small>A short form, no git needed. '
                 f'Every trail page also has its own link, with the trail filled in.</small></li>'
                 f'<li><a href="{esc(site.new_trail_url)}">Suggest a trail</a><small>A short form for a trail that is missing. '
                 f'First look at <a href="/left-out/">Considered and left out</a>, in case it has been decided already</small></li>'
                 f'<li><a href="{esc(site.removal_url)}">Ask for a track or logo to be removed</a><small>For the holder of a track or a logo</small></li>'
                 f'<li><a href="{esc(site.repo_url)}">Edit the data yourself</a><small>The source repository: one text file per trail</small></li>'
                 f'</ul>')
    elif site.issues_url:
        forms = f'<p><a href="{esc(site.issues_url)}">Open an issue</a> to report an error.</p>'
    body = f"""<div class="page-head"><div class="container"><header class="titleblock">
  <div class="titleblock__text"><h1>About {esc(site.name)}</h1>
  <p class="page-head__lede">{esc(site.tagline)}. Everything about the project and the data behind it is here.</p></div></header>
  <nav class="about-hub" aria-label="About this site"><ul class="linklist about-hub__list">{cards}</ul></nav>
</div></div>
<div class="container section"><div class="prose doc">
<section aria-labelledby="what-this-is"><h2 id="what-this-is">What this is</h2>
<p>{esc(site.name)} lists {n} long-distance trails in the United States and Canada: where each one goes,
how long it is and takes, when to walk it, and where to get its track. It is built, page by page, from an
open dataset of one text file per trail. Everything a page says about a trail comes from that file.
{f'The dataset is kept in a <a href="{esc(site.repo_url)}">public repository</a>, where anyone can propose a change.' if site.repo_url else ""}</p>
<p>The dataset calls each trail a <em>record</em>, and the pages under About use its terms. The rest of the
site calls them trails.</p>
{what}
</section>

{maintainer_section(site)}
<section aria-labelledby="how-trails-are-chosen"><h2 id="how-trails-are-chosen">How trails are chosen</h2>
<p>A trail is listed when it is a named, continuous walk, or a named loop, of at least 50&nbsp;miles (80&nbsp;km)
in the United States or Canada. It is either an official trail, looked after as one trail by a land agency or
a trail association, or a route: {esc(facets.ROUTE_DEFINITION[0].lower() + facets.ROUTE_DEFINITION[1:])}
{routes} of the {n} trails are routes. The length is the end-to-end length of the trail&rsquo;s canonical path, and the
trail must be walkable from one end to the other today, on foot. A ferry, shuttle or bus link that the holder or the route&rsquo;s author names as the way through does not rule a trail out, and the maintainer judges each case. Every trail or route needs a published length; one with no stated length is not listed. The length rule is at least 50&nbsp;miles, or, for an author&rsquo;s route that is short on miles, at least five days as its author gives the trip, and the five days never replace a published length; cross-country travel, route finding and hard terrain count in that judgement. Nothing harder than Class&nbsp;3 may be required: a route with a harder section is listed only where that section is optional, and the record says so. A National Scenic Trail is listed unless it cannot be walked
through, and so are a few well-known multi-day trails between 37 and 50&nbsp;miles (60 and 80&nbsp;km).</p>
<p>Each record has a <em>tier</em>, which says why it is listed. A record can also be <em>held</em>: listed,
but with something about it not yet settled, which its note says.</p>
<p>Trails that were looked at and left out are kept in the open too, with the reason for each one:
<a href="/left-out/">Considered and left out</a>. Look there before suggesting a trail.</p>
<div class="table-wrap"><table><thead><tr><th scope="col">Tier</th><th scope="col">What it means</th><th scope="col">Records</th></tr></thead>
<tbody>{tier_rows}<tr><td>Held <code class="raw">wave = "held"</code></td><td>{esc(words.meaning(words.WAVES, "held"))}. Any tier can be held.</td><td class="num">{held}</td></tr></tbody></table></div>
<p>These states are for keeping the dataset. They are not shown when browsing trails, and they do not change
what a trail page says about walking it. Each trail page shows its own under &ldquo;About this data&rdquo;.</p>
{rule}
</section>

<section aria-labelledby="when-a-gpx-is-included"><h2 id="when-a-gpx-is-included">When a GPX is included</h2>
<p>A track is included, as GPX and GeoJSON, only where its source&rsquo;s terms allow passing it on.
{lines} of the {n} trails have one. Where there is none, the trail&rsquo;s page says why and where to look.
Each track keeps its source&rsquo;s terms; the credit and licence are shown beside every map and download.</p>
<p>A route&rsquo;s track follows its author&rsquo;s choice. The dataset records that choice as the route&rsquo;s
<em>track policy</em>:</p>
<div class="table-wrap"><table><thead><tr><th scope="col">Track policy</th><th scope="col">What it means here</th><th scope="col">Routes</th></tr></thead>
<tbody>{policy_rows}</tbody></table></div>
<p>The author of a route who wants its record changed or removed can ask; see <a href="/logos/">Logos</a> for how,
or use the links below.</p>
</section>

<section aria-labelledby="correct-or-add"><h2 id="correct-or-add">Correct or add a trail</h2>
<p>Every trail page has a &ldquo;Report a problem&rdquo; link. Please say where a correction can be checked:
a source page, a map, or a measured track.</p>
{forms}
{rest}
{contrib}
</section>
</div></div>"""
    description = (f"{n} trails and routes in the United States and Canada: how a trail is chosen, "
                   f"where the data comes from, and how to correct or add one.")
    return "About: How Trails Are Listed and Checked", common.cut_at_word(description, common.DESCRIPTION_LIMIT), Markup(body)


def _size(out_dir, relpath):
    path = os.path.join(out_dir, *relpath.split("/"))
    return words.fmt_bytes(os.path.getsize(path)) if os.path.isfile(path) else "—"


# The bulk files on /data/: (name, what it holds, offered as a download).
# trails.json and overview.geojson are what the pages fetch; a browser shows them.
BULK_FILES = (
    ("trails.csv", "One row per trail: id, name, country, regions, length, kind, track policy and status.", True),
    ("trails.json", "Every record in full, as JSON, with the derived fields the site builds.", False),
    ("index.geojson", "Every included track, simplified to about 100 m, with id and name.", True),
    ("overview.geojson", "Every included track simplified to about 750 m for the overview map, "
                         "with id, name, kind, country and length. A trail with no track but a known "
                         "start or end appears marked as a sketch: a straight line between the two, "
                         "or one point alone. A sketch is not a track.", False),
    ("all-gpx.zip", "Every GPX file (main tracks and alternates, simplified to 5 m), as <id>/<file>, "
                    "with each trail's release.txt, trails.csv, SOURCES.md and a README.", True),
    ("all-geojson.zip", "Every full-resolution GeoJSON main track and alternates file, as <id>/<file>, "
                        "with each trail's release.txt, trails.csv, SOURCES.md and a README.", True),
)


def _licence_text_url(licence, repo_root):
    """Where to read a licence: the copy under /licences/, else the licence's own page, else /sources/."""
    for base in (repo_root, REAL_ROOT):
        if os.path.isfile(os.path.join(base, "LICENSES", f"{licence}.txt")):
            return f"/licences/{licence}.txt"
    return words.LICENCE_URLS.get(licence, "/sources/")


def line_licence_rows(records, repo_root):
    """(what, terms, text URL) for each licence the included tracks carry, from the records."""
    by_licence = _group_by([r for r in records if common.has_line(r)],
                           lambda r: r.get("source", {}).get("licence", "") or "unknown")
    rows = []
    for lic in sorted(by_licence, key=lambda k: (-len(by_licence[k]), k.lower())):
        recs = by_licence[lic]
        label = words.label(words.LICENCES, lic)
        n = len(recs)
        what = (f"Tracks shared with permission: {n} record{'s' if n != 1 else ''}" if lic == "stated-permission"
                else f"Tracks licensed {esc(label)}: {n} record{'s' if n != 1 else ''}")
        if n <= 3:
            links = ", ".join(f'<a href="{esc(common.trail_path(r))}">{common.name(r)}</a>' for r in recs)
            what += f" ({links})"
        what = Markup(what)
        terms = Markup(f'{esc(label)} <code class="raw">{esc(lic)}</code>; credit as named in each record and its release.txt')
        if lic in words.LICENCE_NOTES:
            terms = Markup(f'{esc(words.LICENCE_NOTES[lic])} <code class="raw">{esc(lic)}</code>; credit as named in each record and its release.txt')
        rows.append((what, terms, _licence_text_url(lic, repo_root)))
    return rows


def data_page(records, site, repo_root, out_dir):
    """(title, description, body) for /data/."""
    rows = ""
    for name, what, download in BULK_FILES:
        dl = f' download="{esc(name)}"' if download else ""
        rows += (f'<tr><td><a href="/data/{esc(name)}"{dl}>/data/{esc(name)}</a></td>'
                 f'<td>{esc(what)}</td><td class="num">{esc(_size(out_dir, "data/" + name))}</td></tr>')
    per_trail = [
        ("<id>.geojson", "The main track at full resolution, as published in the dataset."),
        ("<id>.gpx", "The main track simplified to 5 m, for GPS devices. No elevation."),
        ("<id>-alternates.geojson / .gpx", "Alternate and connector tracks, where the source serves them separately."),
        ("<id>-<source>.geojson", "One source's own extract, where a track combines sources."),
        ("map.json", "The track simplified to 30 m for the trail page map (GeoJSON)."),
        ("sketch.json", "Start and end points only, for the trail page map where there is no track (GeoJSON). Not a track."),
        ("trail.toml", "The record itself: source, licence, verification, logo and route details."),
        ("release.txt", "The source, licence and date the track files came from, where a track is included."),
        ("shield.svg / shield.png", "The trail logo, where one is included. Not licensed; see Logos."),
        ("shield-thumb.png", "A copy of a PNG logo no larger than 256 px, for the lists."),
    ]
    prow = "".join(f'<tr><td><code>{esc(n)}</code></td><td>{esc(w)}</td></tr>' for n, w in per_trail)
    lic_rows = [
        ("Records, documents and compiled index", "CC0-1.0 (public domain)", '/licences/LICENSE'),
        ("Tools in tools/", "MIT", '/licences/MIT.txt'),
        ("Each trail track", "Keeps its source's terms, stated in its record; see Sources", '/sources/'),
        ("Tracks from OpenStreetMap", "ODbL-1.0; credit © OpenStreetMap contributors", '/licences/ODbL-1.0.txt'),
        *line_licence_rows(records, repo_root),
        ("Trail logos", "Not licensed; belong to their holders, shown only to identify each trail", '/logos/'),
    ]
    lrow = "".join(f'<tr><td>{esc(a)}</td><td>{esc(b)}</td><td><a href="{esc(c)}">{esc(c)}</a></td></tr>'
                   for a, b, c in lic_rows)
    body = f"""<div class="page-head"><div class="container">{BREAD}<li aria-current="page">Data</li></ol></nav><header class="titleblock">
  <div class="titleblock__text"><h1>Data and downloads</h1>
  <p class="page-head__lede">Bulk files, the stable per-trail URLs, and the licences.</p></div></header></div></div>
<div class="container section">
  <div class="section-head"><h2>Bulk downloads</h2><p>{len(records)} records. Sizes are this build's.</p></div>
  <div class="table-wrap"><table><thead><tr><th scope="col">File</th><th scope="col">What it holds</th><th scope="col">Size</th></tr></thead>
  <tbody>{rows}</tbody></table></div>
  <p class="prose">Each track in the archives keeps its source&rsquo;s terms and needs its source&rsquo;s
  credit, as given in the trail&rsquo;s release.txt; trails.csv gives each record&rsquo;s licence too.</p>
  <div class="doc-block"><h2>Per-trail files</h2>
  <p class="prose">Every record has a stable directory. Replace <code>&lt;id&gt;</code> with a record id
  (for example <code>long-trail</code>): <code>/trails/&lt;id&gt;/&lt;id&gt;.geojson</code>,
  <code>/trails/&lt;id&gt;/&lt;id&gt;.gpx</code>, <code>/trails/&lt;id&gt;/&lt;id&gt;-alternates.geojson</code> (and <code>.gpx</code>),
  <code>/trails/&lt;id&gt;/map.json</code>, <code>/trails/&lt;id&gt;/trail.toml</code> and
  <code>/trails/&lt;id&gt;/release.txt</code>. The trail page is <code>/trails/&lt;id&gt;/</code>.
  Track files exist only where the record includes a track; the record says why when it does not.</p>
  <div class="table-wrap"><table><thead><tr><th scope="col">File under /trails/&lt;id&gt;/</th><th scope="col">What it holds</th></tr></thead>
  <tbody>{prow}</tbody></table></div></div>
  <div class="doc-block"><h2>Licences</h2>
  <div class="table-wrap"><table><thead><tr><th scope="col">What</th><th scope="col">Terms</th><th scope="col">Text</th></tr></thead>
  <tbody>{lrow}</tbody></table></div>
  <p class="prose">Licence texts: <a href="/licences/LICENSE">CC0-1.0 (LICENSE)</a>,
  <a href="/licences/CC0-1.0.txt">CC0-1.0.txt</a>, <a href="/licences/MIT.txt">MIT.txt</a>,
  <a href="/licences/CC-BY-4.0.txt">CC-BY-4.0.txt</a>, <a href="/licences/ODbL-1.0.txt">ODbL-1.0.txt</a>.</p></div>
  <div class="doc-block"><h2>Reference</h2><ul class="linklist doc-links">
  <li><a href="/data/schema/">Record schema</a><small>Every field of trail.toml</small></li>
  <li><a href="/data/changelog/">Changelog</a><small>What changed, release by release</small></li>
  <li><a href="/sources/">Sources</a><small>Each source, its terms and the trails that use it</small></li>
  </ul></div>
</div>"""
    description = (f"Download the records of all {len(records)} trails, and every track that may be shared, "
                   f"as CSV, JSON, GeoJSON and GPX. The records are public domain.")
    return "Trail Data Downloads: CSV, JSON, GeoJSON and GPX", common.cut_at_word(description, common.DESCRIPTION_LIMIT), Markup(body)


def schema_page(site, repo_root):
    doc_html = render_doc(read_doc(repo_root, "docs/schema.md"), site, drop_h1=True)
    body = f"""<div class="page-head"><div class="container">
  {BREAD}<li><a href="/data/">Data</a></li>
  <li aria-current="page">Record schema</li></ol></nav>
  <header class="titleblock"><div class="titleblock__text"><p class="kicker">Reference</p>
  <h1>Record schema</h1></div></header></div></div>
<div class="container section"><div class="prose doc">{doc_html}</div></div>"""
    return ("Trail Record Schema: Every Field of trail.toml",
            "What each field of a trail record means, which fields need a source and a history entry, "
            "and how the elevation figures are computed.", Markup(body))


def changelog_page(site, repo_root):
    doc_html = render_doc(read_doc(repo_root, "CHANGELOG.md"), site, drop_h1=True)
    body = f"""<div class="page-head"><div class="container">
  {BREAD}<li><a href="/data/">Data</a></li>
  <li aria-current="page">Changelog</li></ol></nav>
  <header class="titleblock"><div class="titleblock__text"><p class="kicker">Reference</p>
  <h1>Changelog</h1></div></header></div></div>
<div class="container section"><div class="prose doc">{doc_html}</div></div>"""
    return ("Changelog: What Changed in the Trail Data",
            "Trails added, removed and corrected in the dataset, release by release, newest first.", Markup(body))


def copy_licences(out_dir, repo_root):
    """Copy LICENSE and LICENSES/*.txt to /licences/. Returns file names copied."""
    import shutil
    dest = os.path.join(out_dir, "licences")
    os.makedirs(dest, exist_ok=True)
    copied = []
    for base in (repo_root, REAL_ROOT):
        lic = os.path.join(base, "LICENSE")
        if os.path.isfile(lic):
            shutil.copyfile(lic, os.path.join(dest, "LICENSE"))
            copied.append("LICENSE")
            break
    for base in (repo_root, REAL_ROOT):
        d = os.path.join(base, "LICENSES")
        if os.path.isdir(d):
            for name in sorted(os.listdir(d)):
                if name.endswith(".txt"):
                    shutil.copyfile(os.path.join(d, name), os.path.join(dest, name))
                    copied.append(name)
            break
    return copied
