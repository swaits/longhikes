"""Two reference pages: the Glossary (/glossary/) and the Method (/method/).

The glossary is read from glossary.toml. The method page is generated from the definitions in
docs/schema.md and from the records: how many have each figure, and how the measured lengths of the
tracks compare with the published ones.
"""
import collections
import os
import re
import statistics

from . import common, datafiles, elevation, facets, hike, pagekit, words
from .markup import Markup, esc

GLOSSARY = "/glossary/"
METHOD = "/method/"


# Glossary ---------------------------------------------------------------------------

def terms(repo_root):
    return datafiles.glossary(repo_root)


def terms_for(path, repo_root):
    """The glossary terms that point at a page: [(term id, term)]."""
    return [(t["id"], t["term"]) for t in terms(repo_root) if path in t.get("see", [])]


def terms_nav(path, repo_root):
    """A line of links to the glossary entries for a page, or ""."""
    found = terms_for(path, repo_root)
    if not found:
        return ""
    links = " · ".join(f'<a href="{GLOSSARY}#{esc(i)}">{esc(t)}</a>' for i, t in found)
    return f'<nav class="region-nav" aria-label="Terms used on this page">Terms used on this page: {links}</nav>'


def glossary_page(repo_root, labels, site):
    """(title, description, body, terms) for /glossary/. labels: {path: link text} for every page built,
    so that a term links only to a page that exists."""
    ts = terms(repo_root)
    if not ts:
        return None
    entries = ""
    for t in ts:
        see = [(p, labels[p]) for p in t.get("see", []) if p in labels]
        see_html = (" See: " + ", ".join(f'<a href="{esc(p)}">{esc(label)}</a>' for p, label in see) + ".") if see else ""
        src = (f' Source: <a href="{esc(t["source_url"])}">{esc(t["source_url"])}</a>.') if t.get("source_url") else ""
        entries += (f'<div class="gloss"><dt id="{esc(t["id"])}">{esc(t["term"])}</dt>'
                    f'<dd>{esc(t["definition"])}{src}{see_html}</dd></div>\n')
    lede = (f"{len(ts)} words this site uses for long trails, as it uses them. Each entry says what the word means here, "
            f"and links to the list or page where it applies.")
    body = (pagekit.head("Glossary of long trail terms", lede, [("Trails", "/"), ("Lists", "/lists/")])
            + f"""<div class="container section place">
  <dl class="prose glossary">{entries}</dl>
  <nav class="region-nav" aria-label="Related pages"><a href="{METHOD}">How lengths are measured</a> · <a href="/lists/">All lists</a> · <a href="/data/schema/">Record schema</a></nav>
</div>""")
    title = common.fit_title([f"Hiking Trail Glossary: {len(ts)} Terms Used Here", "Hiking Trail Glossary"], site)
    names = words.join_names(t["term"] for t in ts[:5])
    desc = common.cut_at_word(f"{len(ts)} long trail terms as this site uses them, from {names} "
                              f"to {ts[-1]['term'].lower()}, each linked to where it applies.", common.DESCRIPTION_LIMIT)
    return title, desc, Markup(body), ts


# Method -----------------------------------------------------------------------------

def schema_meanings(repo_root):
    """{field: meaning} from the tables of docs/schema.md, with the code marks removed. A field in two
    tables keeps its first meaning."""
    out = {}
    for base in (repo_root, datafiles.REAL_ROOT):
        path = os.path.join(base or datafiles.REAL_ROOT, "docs", "schema.md")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    m = re.match(r"\|\s*`([a-z_.]+)`[^|]*\|[^|]*\|\s*(.*?)\s*\|[^|]*\|?\s*$", line)
                    if m and m.group(1) not in out:
                        out[m.group(1)] = re.sub(r"`", "", m.group(2))
            break
    return out


def _sentence(text):
    return common.sentence(text.strip())


def verified(records):
    """[(record, difference percent)] for the records whose track was measured."""
    out = []
    for r in records:
        v = r.get("verification", {})
        d = v.get("difference_percent")
        if v.get("verified") and isinstance(d, (int, float)) and not isinstance(d, bool):
            out.append((r, d))
    return out


def method_page(records, site, repo_root):
    """(title, description, body) for /method/."""
    meaning = schema_meanings(repo_root)
    ver = verified(records)
    n = len(records)
    within = lambda lo, hi: sum(1 for _, d in ver if lo <= abs(d) < hi)  # noqa: E731
    limit = common.LENGTH_LIMIT
    bands = [("Within 5 percent", within(0, 5)), ("5 to 15 percent", within(5, limit)),
             (f"More than {limit:.0f} percent", sum(1 for _, d in ver if abs(d) >= limit))]
    gaps = sum(1 for r, _ in ver if r.get("source", {}).get("length_gap_note"))
    mid = statistics.median(abs(d) for _, d in ver) if ver else 0
    no_track = sum(1 for r in records if not common.has_line(r))
    n_system = sum(1 for r in records if r.get("system_km"))
    n_built = sum(1 for r in records if r.get("built_km"))
    elev = [(r, elevation.get(r)) for r in records if elevation.get(r)]
    src = collections.Counter((e["source"].get("model", ""), e["source"].get("smoothing", ""),
                              e["source"].get("sample_spacing_m")) for _, e in elev if e.get("source"))
    model, smoothing, spacing = src.most_common(1)[0][0] if src else ("", "", None)
    limits = collections.Counter(e["source"]["limits"] for _, e in elev if e.get("source", {}).get("limits"))
    limits_text = limits.most_common(1)[0][0] if limits else ""
    stated = sum(1 for r in records if not facets.time_days(r)[2])
    (a, b), (c, d_) = facets.PACE_KM, facets.PACE_KM_CROSS
    coverage = []
    for label, fn in (("A usual time stated by a source", lambda r: not facets.time_days(r)[2]),
                      ("A season", lambda r: bool(facets.months(r))), ("A high point", lambda r: bool(hike.table(r).get("high_point_m"))),
                      ("Terrain", lambda r: bool(facets.terrain(r))), ("What the walking is", lambda r: bool(facets.walking(r))),
                      ("A computed climb that covers the whole trail", lambda r: facets.row_climb_m(r) is not None),
                      ("A track included here", common.has_line)):
        have = sum(1 for r in records if fn(r))
        coverage.append([label, str(have), str(n - have)])
    rows = [[label, str(k), f"{k / len(ver) * 100:.0f}%" if ver else ""] for label, k in bands]
    body = (pagekit.head("How the figures are measured", (
        f"What each figure on this site means, and how far to trust it. {len(ver)} of the {n} trails have a track whose "
        f"length was measured and checked against the published length."), [("Trails", "/"), ("About", "/about/")])
        + f"""<div class="container section place"><div class="prose">
  <h2>Length</h2>
  <p>A trail&rsquo;s length here is the end-to-end length of its canonical path: one walk from one end to the other, taking one branch at a split, leaving out side trails and counting no stretch twice. It is the figure the trail&rsquo;s holder or author gives for that walk, and each record says where it comes from. A trail that cannot be walked from end to end today is not listed, but a ferry, shuttle or bus link that the holder or the route&rsquo;s author names as the way through does not rule one out, and the track has a gap there. Every trail or route needs a published length; one with no stated length is not listed. The floor is 50 miles, or, for an author&rsquo;s route that is short on miles, at least five days as its author gives the trip, and the five days never replace a published length; cross-country travel, route finding and hard terrain count in that judgement. Nothing harder than Class&nbsp;3 may be required, apart from a few short Class&nbsp;4 scrambles. A route that needs a rope, a belay or rock-climbing skill is not listed, unless that section is optional and the record says so. The lists and pages show the length in miles with kilometres after.</p>
  <p>Some holders also publish a larger figure for a whole system, or a planned total. A record keeps it apart as the whole system, with what it counts, and no list, length band or time estimate uses it. {n_system} of the {n} records have one. A trail that can be walked through but is partly unbuilt keeps the holder&rsquo;s end-to-end route as its length and gives the built length beside it. {n_built} of the {n} records give one.</p>
  <p>Where a track is included, its length is measured along the track as a geodesic length and compared with the published figure. The difference is the measured length minus the published length, as a percent of the published length. Track ends within 100 metres are joined, and the number of parts left is shown.</p>
  <p>Across the {len(ver)} measured tracks, the middle difference is {mid:.1f} percent.</p>
  {pagekit.table(["Measured against published", "Tracks", "Share"], rows, caption="How the measured tracks compare", numeric=(1, 2))}
  <p>A track that differs by more than {limit:.0f} percent needs a reason in its record, such as a trail that is partly unbuilt, a published length that is a planned one, or side trails counted in the figure. {gaps} of the {len(ver)} measured tracks give one. A track that covers only part of a trail is marked as partial, and its measured length is not its trail&rsquo;s length.</p>
  <p>{no_track} records have no track included. Their length is the published figure alone, and nothing has been measured.</p>
  <h2>Time</h2>
  <p>{esc(_sentence(meaning.get("days", "").replace(" [fewest, most],", "")))} {stated} of the {n} records have a time a source states. For the others the page estimates it from the length, at {round(words.km_to_mi(a))} to {round(words.km_to_mi(b))} miles ({a} to {b} km) a day, or {round(words.km_to_mi(c))} to {round(words.km_to_mi(d_))} miles ({c} to {d_} km) a day where much of the trail is cross-country. An estimate is labelled as one wherever it is shown.</p>
  <h2>Climb</h2>
  <p>Climb is the total ascent along the track.{(" It uses " + esc(model) + ", sampled every " + words.fmt_int(spacing) + " metres, with " + esc(smoothing[:1].lower() + smoothing[1:]) + ".") if model and spacing else ""} {esc(limits_text)}</p>
  <p>A climb is ranked or shown in a list only where its track covers the whole trail: a track that covers part of the trail, or more than the trail, would mislead.</p>
  <h2>Season and high point</h2>
  <p>{esc(_sentence(meaning.get("season", "")))} {esc(_sentence(meaning.get("high_point_m", "").split(" May be given")[0]))} Not every record has them, so a page built from them says how many records it covers.</p>
  <h2>What the records have</h2>
  {pagekit.table(["Figure", "Records with it", "Records without"], coverage, caption="How many records carry each figure", numeric=(1, 2))}
  <p>Every fact is read on a page that the record names. See the <a href="/sources/">sources</a>, the <a href="/data/schema/">record schema</a> and <a href="{GLOSSARY}">the glossary</a>.</p>
</div>
  <nav class="region-nav" aria-label="Related pages"><a href="/numbers/">Trails by the numbers</a> · <a href="/lists/">All lists</a></nav></div>""")
    title = "How Trail Lengths and Climbs Are Measured"
    desc = common.cut_at_word(f"How this site checks published trail lengths against measured tracks, estimates time and computes climb, "
                              f"with how many of the {n} records carry each figure.", common.DESCRIPTION_LIMIT)
    return title, desc, Markup(body)
