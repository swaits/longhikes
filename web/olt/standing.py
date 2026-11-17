"""Tables built from the records: key figures for a set of trails, a collection set side by side
(the Triple Crown), and the rankings under /numbers/.

Nothing here names a trail. A collection is read from collections.toml; a ranking takes the
records that carry the figure and says how many that is. Every figure comes from a record field,
and the climb and the high point carry the caveats the records themselves state.
"""
import collections
import statistics

from . import browse, common, datafiles, elevation, facets, hike, pagekit, regions, seo, summary, words
from .markup import Markup, esc

NUMBERS = "/numbers/"
RANKING_ROWS = 25          # rows in a ranking table (the page says how many records have the figure)
HUB_ROWS = 10


def _places(rec):
    return ", ".join(words.region_name(c) for c in rec.get("regions", []))


def high_point(rec):
    """(name, metres) as the record states them; either may be missing."""
    h = hike.table(rec)
    m = h.get("high_point_m")
    return h.get("high_point", ""), (m if isinstance(m, (int, float)) and not isinstance(m, bool) else None)


def high_point_cell(rec):
    name, m = high_point(rec)
    if m is None and not name:
        return "Not on file"
    if m is None:
        return name
    return Markup(f"{esc(name + ', ') if name else ''}{words.elevation(m)}")


def climb_cell(rec):
    m = facets.row_climb_m(rec)
    return "Not computed" if m is None else words.elevation(m)


def time_cell(rec):
    return facets.time_text(rec)


def season_cell(rec):
    return facets.season_text(rec) or "Not on file"


# One figure: (label, function of a record). The order is the order of columns and rows.
FIGURES = (
    ("Length", lambda r: words.length(r["length_km"], mi=r["derived"]["length_mi"])),
    ("States and provinces", _places),
    ("Typical time", time_cell),
    ("High point", high_point_cell),
    ("Climb", climb_cell),
    ("Season", season_cell),
    ("Publisher", lambda r: r.get("source", {}).get("publisher", "") or "Not on file"),
)


def key_figures_table(recs, caption="Key figures"):
    """One row per trail: length, places, time, high point, climb, season and publisher."""
    rows = [[pagekit.trail_link(r)] + [fn(r) for _, fn in FIGURES] for r in recs]
    return pagekit.table(["Trail"] + [label for label, _ in FIGURES], rows, caption=caption, row_heads=True)


def figures_note(recs):
    """What the figures in key_figures_table mean, with the caveats the records state."""
    est = sum(1 for r in recs if facets.time_days(r)[2])
    parts = [f"Times that start with “About” are estimated from the length ({est} of these). "
             "Otherwise a source states the time.",
             climb_caveat(recs)]
    return " ".join(p for p in parts if p)


def climb_caveat(recs):
    """The caveat the elevation files give for their climb figures: the most common one among recs."""
    limits = collections.Counter(
        e["source"]["limits"] for e in (elevation.get(r) for r in recs) if e and e.get("source", {}).get("limits"))
    text = limits.most_common(1)[0][0] if limits else ""
    return ("Climb: " + text) if text else ""


def figures_section(recs, intro=""):
    return (f'<div class="prose"><p>{intro}</p></div>' if intro else "") + str(key_figures_table(recs)) + \
        f'<p class="finder__foot">{esc(figures_note(recs))}</p>'


# Collections ----------------------------------------------------------------------

def collection_members(collection, records):
    by_id = {r["id"]: r for r in records}
    return [by_id[i] for i in collection.get("members", []) if i in by_id]


def collection_path(collection):
    return f"/{collection['id']}/"


def collection_page(collection, records, site):
    """(title, description, body, recs) for a collection set side by side, or None when a member is missing.

    The members are set in the order collections.toml gives, with every figure in a row of its own. The
    page ranks and recommends nothing."""
    recs = collection_members(collection, records)
    if not recs or len(recs) != len(collection["members"]):
        return None
    name = collection["name"]
    abbrs = words.join_names(r.get("short_name") or common.plain_name(r) for r in recs)
    title = common.fit_title([f"{name} Trails Compared: {abbrs}", f"{name} Trails Compared"], site)
    total_mi = sum(r["derived"]["length_mi"] for r in recs)
    total_km = sum(r["length_km"] for r in recs)
    places = {c for r in recs for c in r.get("regions", [])}
    lede = (f"{esc(collection['definition'])} Here are the {len(recs)} trails side by side, in the order the "
            f"definition names them, from what each trail's page says. Their published lengths add up to {words.fmt_int(total_mi)} "
            f"miles ({words.fmt_int(total_km)} km), across {len(places)} states and provinces.")
    headers = ["Figure"] + [common.plain_name(r) for r in recs]
    rows = [[label] + [fn(r) for r in recs] for label, fn in FIGURES]
    rows.insert(0, ["Full name"] + [pagekit.trail_link(r) for r in recs])
    rows.append(["Designated"] + [common.designated_year(r) or "Not on file" for r in recs])
    source = (f'<p class="finder__foot">The award is described by {esc(collection.get("source_publisher", "its holder"))} at '
              f'<a href="{esc(collection["source_url"])}">{esc(collection["source_url"])}</a>. '
              f'{esc(figures_note(recs))} Lengths are the published figures. '
              f'See the <a href="/method/">method</a> for how they are checked.</p>')
    from . import home
    body = (pagekit.head(f"{name} trails compared", lede, [("Trails", "/"), ("Lists", "/lists/")])
            + '<div class="container section place">'
              f'{pagekit.table(headers, rows, caption=f"The {name} trails side by side", row_heads=True, compare=True)}'
              f'{source}'
              f'<div class="prose place-summary">{summary.facts(recs, records)}</div>'
              f'{home.results(recs, top=2)}'
              '<nav class="region-nav" aria-label="Related pages"><a href="/lists/national-scenic-trails/">National Scenic Trails</a> · '
              f'<a href="/glossary/#{esc(collection["id"])}">What the {esc(name)} is</a> · <a href="/lists/">All lists</a></nav></div>')
    desc = common.cut_at_word(
        f"{name} trails side by side: published length, states, typical time, high point, climb and season for "
        f"{abbrs}. Figures from each trail's page, not ranked.", common.DESCRIPTION_LIMIT)
    return title, desc, Markup(body), recs


# Numbers ----------------------------------------------------------------------------

def _rank_rows(recs, value_of, cell_of, extra=None):
    rows = []
    for i, r in enumerate(recs, 1):
        row = [str(i), pagekit.trail_link(r), cell_of(r)]
        if extra:
            row.append(extra(r))
        rows.append(row)
    return rows


def _climb(rec):
    return facets.row_climb_m(rec)


def _climb_rate(rec):
    c = _climb(rec)
    return None if c is None else c / rec["length_km"]


# key, path tail, title head, table heading, test value
RANKINGS = (
    ("highest-points", "Hiking Trails Ranked by High Point",
     lambda r: high_point(r)[1], "High point",
     "ranked by the highest point a source states",
     lambda r: high_point_cell(r)),
    ("most-climbing", "Hiking Trails Ranked by Climbing",
     _climb, "Climb",
     "ranked by total climbing along the track",
     lambda r: climb_cell(r)),
    ("climb-per-mile", "Hiking Trails Ranked by Climb per Mile",
     _climb_rate, "Climb per mile",
     "ranked by total climbing for each mile of the trail",
     lambda r: pagekit.ft_per_mile(_climb_rate(r))),
)


def ranking_paths():
    return [f"{NUMBERS}{key}/" for key, *_ in RANKINGS]


def _climb_coverage_note(records):
    withheld = sum(1 for r in records if elevation.get(r) and facets.row_climb_m(r) is None)
    have = sum(1 for r in records if facets.row_climb_m(r) is not None)
    return (f"{have} of the {len(records)} trails have a climb that can be ranked: it comes from a track that covers the whole "
            f"trail. {withheld} more have a track that covers only part of the trail, or more than the trail, and are left out.")


def ranking_page(spec, records, site):
    """(title, description, body, recs) for one ranking, or None when fewer than MIN_SIZE records have the figure."""
    key, head, value_of, label, how, cell_of = spec
    have = [r for r in records if value_of(r) is not None]
    if len(have) < browse.MIN_SIZE:
        return None
    ranked = sorted(have, key=lambda r: (-value_of(r), r["id"]))
    shown = ranked[:RANKING_ROWS]
    title = common.fit_title([f"{head}: {len(have)} Trails", head], site)
    if key == "highest-points":
        caveat = (f"{len(have)} of the {len(records)} trails have a high point stated in metres, as a source gives it. The rest "
                  "give none, so they are not ranked.")
    else:
        caveat = _climb_coverage_note(records) + " " + climb_caveat(have)
    rows = _rank_rows(shown, value_of, cell_of, extra=lambda r: words.length(r["length_km"], mi=r["derived"]["length_mi"]))
    lede = (f"The {len(have)} trails and routes that have the figure, {how}. "
            f"The table shows the first {len(shown)}. {esc(caveat)}")
    from . import home
    body = (pagekit.head(head, lede, [("Trails", "/"), ("Lists", "/lists/"), ("By the numbers", NUMBERS)])
            + '<div class="container section place">'
              f'{pagekit.table(["#", "Trail", label, "Length"], rows, caption=head, numeric=(0,))}'
              f'<p class="finder__foot">Where two trails share a figure, they are in name order. '
              f'The same figures are on each trail&rsquo;s page. See the <a href="/method/">method</a> for what the caveats mean.</p>'
              f'<div class="prose place-summary">{summary.facts(have, records)}</div>'
              f'{home.results(have, default_sort="climb-desc" if key != "highest-points" else "length-desc", top=2)}'
              f'<nav class="region-nav" aria-label="Related pages"><a href="{NUMBERS}">By the numbers</a> · '
              f'<a href="/lists/">All lists</a></nav></div>')
    desc = common.cut_at_word(f"{len(have)} long hiking trails {how}, with the caveats that go with the figure.",
                              common.DESCRIPTION_LIMIT)
    return title, desc, Markup(body), have


def numbers_page(records, site, ranked_pages):
    """(title, description, body) for /numbers/: lengths, places and links to the rankings.

    ranked_pages: [(path, heading, how many)] for the rankings that were built."""
    from . import home
    by_length = sorted(records, key=lambda r: (-r["length_km"], r["id"]))
    miles = [r["derived"]["length_mi"] for r in records]
    mid = statistics.median(miles)
    lede = (f"The {len(records)} trails by length, climb and place. The middle length is {words.fmt_int(mid)} miles "
            f"({words.fmt_int(mid * words.KM_PER_MI)} km). Lengths are the published figures; the other pages here rank "
            "figures that only some trails have, and say how many.")
    longest = by_length[:HUB_ROWS]
    shortest = list(reversed(by_length[-HUB_ROWS:]))

    def length_rows(rs):
        return [[str(i), pagekit.trail_link(r), words.length(r["length_km"], mi=r["derived"]["length_mi"]), time_cell(r)]
                for i, r in enumerate(rs, 1)]
    by_slug, _ = regions.collect_regions(records)
    place_rows = []
    for slug in sorted(by_slug, key=lambda s: (-len(by_slug[s]["records"]), by_slug[s]["name"])):
        info = by_slug[slug]
        rs = info["records"]
        top = max(rs, key=lambda r: (r["length_km"], r["id"]))
        place_rows.append([Markup(f'<a href="{esc(facets.place_path(info["key"]))}">{esc(info["name"])}</a>'),
                           str(len(rs)), str(sum(1 for r in rs if facets.kind(r) == "route")),
                           str(sum(1 for r in rs if facets.shape(r) == "loop")),
                           str(sum(1 for r in rs if facets.gpx_here(r))),
                           Markup(f'{pagekit.trail_link(top)}, {words.length(top["length_km"], mi=top["derived"]["length_mi"])}')])
    links = "".join(f'<li><a href="{esc(path)}">{esc(head)}</a> ({n} trails)</li>' for path, head, n in ranked_pages)
    body = (pagekit.head("Long trails by the numbers", lede, [("Trails", "/"), ("Lists", "/lists/")])
            + f"""<div class="container section place">
  <section><h2>Rankings</h2><ul>{links}</ul></section>
  <section><h2>The {HUB_ROWS} longest by published length</h2>
  {pagekit.table(["#", "Trail", "Length", "Typical time"], length_rows(longest), caption="The longest trails", numeric=(0,))}</section>
  <section><h2>The {HUB_ROWS} shortest by published length</h2>
  {pagekit.table(["#", "Trail", "Length", "Typical time"], length_rows(shortest), caption="The shortest trails", numeric=(0,))}</section>
  <section><h2>Trails by state and province</h2>
  <p>A trail that crosses several states is counted in each, so the counts add up to more than {len(records)}.</p>
  {pagekit.table(["Place", "Trails", "Routes", "Loops", "With a GPX", "Longest"], place_rows, caption="Trails by state and province", numeric=(1, 2, 3, 4))}</section>
  <p class="finder__foot">Lengths are the published figures, which are check values, not measured from a track. See the
  <a href="/method/">method</a>. <a href="/lists/longest/">The longest trails</a> and
  <a href="/lists/under-100-miles/">the shortest</a> have their own lists.</p>
</div>""")
    desc = common.cut_at_word(
        f"The {len(records)} long hiking trails by length, climb and place: the longest and shortest, rankings by high point and "
        f"climbing, and trails by state and province.", common.DESCRIPTION_LIMIT)
    return "Long Hiking Trails by the Numbers", desc, Markup(body)
