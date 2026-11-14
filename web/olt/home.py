"""The home page: the catalogue. Search, the filters, and the trails as a list and on a map.

The list (results(), entry()) is shared with the place pages and the lists, so
every list of trails on the site looks and reads the same. The filters are the
attributes in olt/facets.py, under the same names the trail pages use.
"""
import collections
import math
import re

from . import browse, common, elevation, facets, hike, words
from .markup import Markup, esc

# Length range choices (km) for the filters. length_steps() adds a top step
# above the longest trail, so a chosen upper bound can always reach every trail.
LENGTH_STEPS = (60, 80, 100, 150, 200, 300, 500, 1000, 2000, 4000, 8000)


def length_steps(records):
    """LENGTH_STEPS plus a round step at or above the longest trail, when that is longer."""
    longest = max((r["length_km"] for r in records), default=0)
    steps = list(LENGTH_STEPS)
    if longest > steps[-1]:
        magnitude = 10 ** int(math.floor(math.log10(longest)))
        steps.append(int(math.ceil(longest / magnitude) * magnitude))
    return steps


def counts(records):
    """Counts for the filter options: each Where value, Time band, month, terrain, Kind,
    Walking, Shape and GPX status, as the filter would find them."""
    c = collections.Counter()
    for r in records:
        c["total"] += 1
        for tok in facets.where_tokens(r):
            c["where:" + tok] += 1
        c["time:" + facets.time_band(r)] += 1
        for m in facets.months(r):
            c[f"month:{m}"] += 1
        for t in facets.terrain(r):
            c["terrain:" + t] += 1
        c["kind:" + facets.kind(r)] += 1
        if facets.walking(r):
            c["walking:" + facets.walking(r)] += 1
        if facets.shape(r):
            c["shape:" + facets.shape(r)] += 1
        c["gpx:" + facets.gpx(r)] += 1
        if facets.gpx_here(r):
            c["gpx_here"] += 1
    return c


def overview_bbox(records):
    """data-bbox attribute: the extent of every track, so the map opens on it before the data loads."""
    boxes = [r["derived"]["bbox"] for r in records if r["derived"].get("bbox")]
    if not boxes:
        return ""
    box = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
    return f' data-bbox="{",".join(f"{v:.4f}" for v in box)}"'


def sort_name(rec):
    return re.sub(r"^The ", "", rec["name"]).lower()


# A row ------------------------------------------------------------------------

def entry_desc(rec):
    """The one-line description of a row: the [hike] summary's first sentence, else
    the trail's designation (an official trail) or nothing (a route says who made it)."""
    one = hike.one_line(rec)
    if one:
        return one
    if facets.kind(rec) == "route":
        return ""
    return rec.get("designation", "")


def where_html(rec):
    """The states and provinces of a row, each linked to its place page, and the country."""
    parts = []
    for key in facets.place_keys(rec):
        name = facets.place_name(key)
        text = esc(name) if key == facets.ACROSS_CANADA else \
            Markup(f'<abbr title="{esc(name)}">{esc(key.split("-", 1)[1])}</abbr>')
        parts.append(f'<a href="{esc(facets.place_path(key))}">{text}</a>')
    country = " and ".join(words.COUNTRIES.get(c, c) for c in common.countries(rec))
    return Markup(" ".join(parts) + f' <span aria-hidden="true">&middot;</span> {esc(country)}')


def gpx_cell(rec):
    status = facets.gpx(rec)
    route = facets.kind(rec) == "route"
    if facets.gpx_here(rec):
        swatch = common.SWATCH_ROUTE if route else common.SWATCH_LINE
        partial = (f'<p class="entry__partial">{esc(common.partial_short_text(rec))}</p>'
                   if common.line_differs(rec) else "")
        return (f'<span class="line__status">{swatch}{esc(facets.GPX_SHORT[status])}</span>'
                f'<span class="line__detail">GPX and GeoJSON</span>{partial}')
    return f'<span class="line__status">{common.SWATCH_NONE}{esc(facets.GPX_SHORT[status])}</span>'


def entry(rec, *, level=3, extra="", routes_list=False):
    """One trail in a list. Its data-* attributes drive the filters in app.js.

    level: the heading level of the trail's name. extra: HTML placed last in the row.
    routes_list: the Routes list, whose "By <author>" headings already say what the
    row's Route badge and "Route by" line would repeat; both are left out there.
    """
    route = facets.kind(rec) == "route"
    lo, hi, est = facets.time_days(rec)
    search = " ".join([rec["name"], rec.get("short_name", ""), rec["id"], facets.author(rec)]).lower()
    abbr_cls = "entry__abbr" if common.shield_url(rec) else "entry__abbr vh"
    elev = elevation.get(rec)
    # A climb worked out from a track that covers only part of the trail, or more
    # than the trail, would mislead in a list; the trail's own page gives it with
    # its caveat.
    if elev and elevation.coverage_kind(elev):
        elev = None
    data = {
        "id": rec["id"], "where": " ".join(facets.where_tokens(rec)), "km": rec["length_km"],
        "climb": elev["ascent_m"] if elev else "",
        "days": hi, "time": facets.time_band(rec), "months": " ".join(map(str, facets.months(rec))),
        "terrain": " ".join(facets.terrain(rec)), "kind": facets.kind(rec), "walking": facets.walking(rec),
        "shape": facets.shape(rec), "gpx": facets.gpx(rec), "name": sort_name(rec), "search": search.strip(),
    }
    attrs = "".join(f' data-{k}="{esc(v)}"' for k, v in data.items())
    if common.line_differs(rec):
        attrs += ' data-partial="yes"'
    h = f"h{level}"
    tag_html = common.badges(rec, route_tag=not routes_list)
    kicker = f'\n    <p class="entry__kicker">{tag_html}</p>' if tag_html else ""
    by = f'\n    <p class="entry__by">{esc(facets.route_by(rec))}</p>' if route and not routes_list else ""
    desc = entry_desc(rec)
    desc_html = f'\n    <p class="entry__desc">{esc(desc)}</p>' if desc else ""
    time_html = esc(facets.time_text(rec)) + (' <small class="entry__est">estimate</small>' if est else "")
    climb_html = (f'\n    <div class="entry__climb"><dt>Climb</dt><dd>{words.elevation(elev["ascent_m"], "stack")}'
                  f'<small class="entry__est">computed</small></dd></div>') if elev else ""
    return f"""<li class="entry"{attrs}>
  {common.plate(rec)}
  <div class="entry__body">{kicker}
    <{h} class="entry__name"><a href="{esc(common.trail_path(rec))}">{common.name(rec)}</a> <span class="{abbr_cls}">{esc(rec.get("short_name", ""))}</span></{h}>{by}{desc_html}
    <p class="entry__where">{where_html(rec)}</p>
  </div>
  <dl class="entry__facts">
    <div class="entry__length"><dt>Length</dt><dd>{words.length(rec["length_km"], "stack", rec["derived"]["length_mi"])}<span class="loglen" style="--km: {rec["length_km"]}" aria-hidden="true"></span></dd></div>
    <div class="entry__time"><dt>Time</dt><dd>{time_html}</dd></div>
    <div class="entry__line"><dt>GPX</dt><dd class="line line--{"yes" if facets.gpx_here(rec) else "no"}">{gpx_cell(rec)}</dd></div>{climb_html}
  </dl>{extra}
</li>"""


# The filters ------------------------------------------------------------------

def _length_options(steps, selected_any_last):
    opts = [f'<option value="{km}">{km:,} km &middot; {words.fmt_int(words.km_to_mi(km))} mi</option>'
            for km in steps]
    if selected_any_last:
        return "".join(opts[1:]) + '<option value="" selected>Any</option>'
    return '<option value="">Any</option>' + "".join(opts[:-1])


def where_options(c):
    """The Where filter: the two countries, then each place group with its states and provinces."""
    opts = [f'<option value="">Anywhere ({c["total"]})</option>']
    for code in ("US", "CA"):
        if c["where:" + code]:
            opts.append(f'<option value="{code}">{esc(words.COUNTRIES[code])} ({c["where:" + code]})</option>')
    for g, name, keys in facets.PLACE_GROUPS:
        if not c["where:g:" + g]:
            continue
        inner = [f'<option value="g:{g}">All of {esc(name)} ({c["where:g:" + g]})</option>']
        for key in sorted(keys, key=facets.place_name):
            if c["where:" + key]:
                inner.append(f'<option value="{key}">{esc(facets.place_name(key))} ({c["where:" + key]})</option>')
        opts.append(f'<optgroup label="{esc(name)}">{"".join(inner)}</optgroup>')
    if c["where:" + facets.ACROSS_CANADA]:
        opts.append(f'<option value="{facets.ACROSS_CANADA}">{facets.ACROSS_CANADA_NAME} '
                    f'({c["where:" + facets.ACROSS_CANADA]})</option>')
    return "".join(opts)


def _checks(name, items, c, prefix, hints=None):
    """Checkboxes for a multi-choice facet: (value, label) items with their counts."""
    out = []
    for value, label in items:
        n = c[f"{prefix}:{value}"]
        if not n:
            continue
        hint = f'<span class="check__hint">{esc(hints[value])}</span>' if hints and hints.get(value) else ""
        out.append(f'<label class="check"><input type="checkbox" name="{name}" value="{esc(value)}">'
                   f'<span class="check__text">{esc(label)} <span class="check__count">{n}</span></span>{hint}</label>')
    return "".join(out)


def _missing(records, key):
    """The note under an optional facet: how many trails it leaves out while it is in use."""
    _, without = facets.coverage(records, key)
    if not without:
        return ""
    return (f'<p class="field__hint filter-missing" data-missing="{key}" hidden>'
            f'{esc(facets.missing_text(without, key))} They are left out while this filter is on.</p>')


def finder_form(records, c=None, steps=None):
    """Search and the first-rank filters in view; Walking, Shape and GPX behind "More"."""
    c = c or counts(records)
    steps = steps or length_steps(records)
    first, more = [], []
    first.append(f"""<div class="field">
    <label class="field__label" for="where">{facets.WHERE}</label>
    <select class="select" id="where" name="where">{where_options(c)}</select>
  </div>""")
    first.append(f"""<fieldset class="field">
    <legend>{facets.LENGTH}</legend>
    <div class="range">
      <label class="vh" for="min">Shortest length</label>
      <select class="select" id="min" name="min" data-length-options>{_length_options(steps, False)}</select>
      <span class="range__to" aria-hidden="true">to</span>
      <label class="vh" for="max">Longest length</label>
      <select class="select" id="max" name="max" data-length-options>{_length_options(steps, True)}</select>
    </div>
    <p class="field__hint" id="len-hint" aria-live="polite">Any length.</p>
  </fieldset>""")
    first.append(f"""<fieldset class="field">
    <legend>{facets.TIME}</legend>
    <div class="pills">{_checks("time", [(k, label) for k, label, _ in facets.TIME_BANDS], c, "time")}</div>
    <p class="field__hint">To walk it all. Where no source says, it is estimated from the length.</p>
  </fieldset>""")
    if facets.offered(records, "season"):
        month_opts = "".join(f'<option value="{i}">{esc(m)} ({c[f"month:{i}"]})</option>'
                             for i, m in enumerate(facets.MONTHS, 1))
        first.append(f"""<div class="field">
    <label class="field__label" for="month">{facets.SEASON}</label>
    <select class="select" id="month" name="month"><option value="">Any month</option>{month_opts}</select>
    <p class="field__hint">Trails usually walked in that month.</p>
    {_missing(records, "season")}
  </div>""")
    if facets.offered(records, "terrain"):
        first.append(f"""<fieldset class="field">
    <legend>{facets.TERRAIN}</legend>
    <div class="pills">{_checks("terrain", facets.TERRAIN_VALUES.items(), c, "terrain")}</div>
    {_missing(records, "terrain")}
  </fieldset>""")
    first.append(f"""<fieldset class="field">
    <legend>{facets.KIND}</legend>
    <div class="seg">
      <label><input type="radio" name="kind" value="" checked><span>Any</span></label>
      <label><input type="radio" name="kind" value="trail"><span>Official trails ({c["kind:trail"]})</span></label>
      <label><input type="radio" name="kind" value="route"><span>Routes ({c["kind:route"]})</span></label>
    </div>
    <p class="field__hint"><a href="/routes/">What is a route?</a></p>
  </fieldset>""")
    if facets.offered(records, "walking"):
        more.append(f"""<fieldset class="field">
        <legend>{facets.WALKING}</legend>
        {_checks("walking", facets.WALKING_VALUES.items(), c, "walking", facets.WALKING_HINT)}
        {_missing(records, "walking")}
      </fieldset>""")
    if facets.offered(records, "shape"):
        more.append(f"""<fieldset class="field">
        <legend>{facets.SHAPE}</legend>
        {_checks("shape", facets.SHAPES.items(), c, "shape")}
        {_missing(records, "shape")}
      </fieldset>""")
    more.append(f"""<fieldset class="field">
        <legend>{facets.GPX}</legend>
        {_checks("gpx", facets.GPX_STATUS.items(), c, "gpx")}
      </fieldset>""")
    return f"""<form class="filters" id="finder-form" role="search" aria-label="Find a trail">
  <div class="filters__search field">
    <label class="field__label" for="q">Search</label>
    <input class="input" id="q" name="q" type="search" placeholder="Name, abbreviation or author of a route" autocomplete="off" spellcheck="false">
  </div>
  <details class="filters__panel" open>
    <summary>Filters <span class="filters__count"></span></summary>
    <div class="filters__first">
    {"".join(first)}
    </div>
  </details>
  <details class="filters__more">
    <summary>More filters <span class="filters__active"></span></summary>
    <div class="filters__form">
      {"".join(more)}
    </div>
  </details>
  <div class="field filters__reset">
    <button class="button button--quiet" type="reset">Clear search and filters</button>
  </div>
</form>"""


# The list ---------------------------------------------------------------------

# The length strip's ticks (style.css .loglen): 100, 1,000 and 10,000 km.
SCALE_KM = (100, 1000, 10000)


def list_head():
    """The column head over a list. The scale ticks follow the reader's unit preference
    with the same len__km / len__mi pair the lengths use."""
    ticks = []
    for i, km in enumerate(SCALE_KM):
        unit = " km" if i == len(SCALE_KM) - 1 else ""
        mi_unit = " mi" if i == len(SCALE_KM) - 1 else ""
        ticks.append(f'<span><span class="len__km">{km:,}{unit}</span>'
                     f'<span class="len__mi">{words.fmt_int(words.km_to_mi(km))}{mi_unit}</span></span>')
    return f"""<div class="list-head" aria-hidden="true">
        <span>Trail</span>
        <span>{facets.LENGTH}<span class="list-head__scale">{"".join(ticks)}</span></span>
        <span>{facets.TIME}</span>
        <span>{facets.GPX}</span>
        <span>Climb</span>
      </div>"""


UNITS_TOGGLE = """<fieldset class="results-units">
            <legend class="vh">Lengths</legend>
            <div class="seg seg--small">
              <label><input type="radio" name="units-list" value="km" checked><span>km</span></label>
              <label><input type="radio" name="units-list" value="mi"><span>mi</span></label>
            </div>
          </fieldset>"""

SORT_SELECT = """<label class="results-sort">Sort
            <select class="select" id="sort" name="sort">
              <option value="name">Name, A to Z</option>
              <option value="long">Longest first</option>
              <option value="short">Shortest first</option>
              <option value="quick">Quickest first</option>
              <option value="climb">Most climb first</option>
            </select>
          </label>"""


def key(official=True):
    """official: False on a list of routes only, which has no official trail to explain."""
    first = f"<li>{common.SWATCH_LINE}Official trail with a GPX here</li>\n        " if official else ""
    return f"""<ul class="key" aria-label="Key to the list">
        {first}<li>{common.SWATCH_ROUTE}Route with a GPX here</li>
        <li>{common.SWATCH_NONE}No GPX here: its page says where to get one</li>
      </ul>"""


def results(recs=None, *, finder=False, groups=None, routes_list=False):
    """The list of trails, as every page shows it: div.results > head, key, list head, ol.entries.

    finder: the home page's list, driven by the filters (live count, sort, empty state).
    groups: [(heading, trails, extra_fn)] to list the trails under level-3 headings;
    extra_fn(rec) gives HTML placed last in each row.
    routes_list: passed to entry() for the Routes list (see there).
    """
    if groups is None:
        groups = [(None, recs, None)]
    total = sum(len(g[1]) for g in groups)
    shown = [r for g in groups for r in g[1]]
    only_routes = bool(shown) and all(facets.kind(r) == "route" for r in shown)
    noun = ("route" if only_routes else "trail") + ("" if total == 1 else "s")
    lists = ""
    for heading, items, extra_fn in groups:
        level = 4 if heading else 3
        rows = "\n".join(entry(r, level=level, extra=extra_fn(r) if extra_fn else "",
                                routes_list=routes_list) for r in items)
        if heading:
            lists += f'\n      <h3 class="results__group">{heading}</h3>'
        list_id = ' id="entries"' if finder else ""
        lists += f'\n      <ol class="entries"{list_id}>\n{rows}\n      </ol>'
    if finder:
        count = (f'<p class="results-count" id="results-count" role="status">'
                 f'<strong>{total}</strong> of {total} {noun}</p>')
        tools = SORT_SELECT + "\n          " + UNITS_TOGGLE
        empty = """
      <div class="empty-state" id="empty-state" hidden>
        <p><strong>No trails match these filters.</strong></p>
        <button class="button button--quiet" type="button" data-reset>Clear search and filters</button>
      </div>"""
    else:
        count = f'<p class="results-count"><strong>{total}</strong> {noun}</p>'
        tools = UNITS_TOGGLE
        empty = ""
    return Markup(f"""<div class="results">
      <div class="results-head">
        {count}
        <div class="results-tools">
          {tools}
        </div>
      </div>
      {key(official=not only_routes)}
      {list_head()}{lists}{empty}
    </div>""")


# A map of a selection is drawn only when it has at least this many tracks.
MAP_MIN = 3


def overview_map(recs, label, *, wide=False, scope=""):
    """The map of the given trails' tracks (the overview geometry, limited to their ids
    unless every trail is shown). "" when none of them has a track."""
    ids = [r["id"] for r in recs if "line" in r["derived"]["files"]]
    if not ids:
        return Markup('<p class="note">None of these trails has a GPX here, so there is no track to draw. '
                      'Each trail&rsquo;s page says where to get one.</p>')
    if len(ids) < MAP_MIN and scope != "all":
        names = words.join_names(f'<a href="{esc(common.trail_path(r))}">{common.name(r)}</a>'
                                 for r in recs if r["id"] in ids)
        return Markup(f'<p class="note">Only {names} {"has" if len(ids) == 1 else "have"} a GPX here, '
                      'so no map of them all is drawn. Each trail&rsquo;s page says where to get a track.</p>')
    ids_attr = "" if scope == "all" else f' data-ids="{esc(" ".join(ids))}"'
    n = len(ids)
    return Markup(f"""<figure class="mapfig{" mapfig--wide" if wide else ""}" data-map="overview" data-src="/data/overview.geojson"{ids_attr}{overview_bbox(recs)}>
  <div class="mapfig__frame">
    <span class="mapfig__corner mapfig__corner--nw" aria-hidden="true"></span>
    <div class="map" role="region" aria-label="{esc(label)}">
      <div class="map__fallback"></div>
      <div class="map__canvas"></div>
      <p class="map__status" role="status">The map needs JavaScript. The list has every trail.</p>
    </div>
    <span class="mapfig__corner mapfig__corner--se" aria-hidden="true"></span>
  </div>
  <figcaption class="mapfig__caption">
    <ul class="legend" aria-label="Legend">
      <li>{common.SWATCH_LINE}Official trail</li>
      <li>{common.SWATCH_ROUTE}Route</li>
    </ul>
    <p>{n} track{"s" if n != 1 else ""}, simplified for display. Select one for its name. Each trail&rsquo;s page names its source, credit and licence. Base map: OpenFreeMap, &copy;&nbsp;OpenMapTiles, data &copy;&nbsp;OpenStreetMap contributors.</p>
  </figcaption>
</figure>""")


def lists_row(records):
    """The ready-made lists, as a row of links with their counts. The terrain lists are
    on /lists/; here the Terrain filter does the same work."""
    items = "".join(
        f'<li><a href="{esc(browse.path(lst))}">{esc(lst.title)} <span class="chips__n">{len(recs)}</span></a></li>'
        for lst, recs in browse.shown(records) if not lst.key.startswith("terrain-"))
    if not items:
        return ""
    return f"""<nav class="lists-row" aria-labelledby="lists-title">
      <h2 id="lists-title" class="lists-row__title">Start from a list</h2>
      <ul class="chips">{items}<li><a href="/lists/">All lists</a></li></ul>
    </nav>"""


def render(records, site):
    """The home page body (HTML)."""
    c = counts(records)
    recs = sorted(records, key=sort_name)
    total = c["total"]
    lede = (f"{total} long-distance trails in the United States and Canada. Narrow them by where they are, "
            f"how long they take, when to walk them and what the country is like. "
            f"{c['gpx_here']} have a GPX to download.")
    contribute = ""
    if site.repo_url:
        contribute = (f'<p class="finder__foot">Something wrong, or a trail missing? '
                      f'<a href="{esc(site.correction_url())}">Report a problem</a> or '
                      f'<a href="{esc(site.new_trail_url)}">suggest a trail</a>.</p>')
    return f"""<section class="hero hero--short" aria-labelledby="hero-title">
  <div class="container hero__inner">
    <h1 id="hero-title">Find a long trail</h1>
    <p class="hero__lede">{lede}</p>
    {lists_row(records)}
  </div>
</section>

<section class="section section--finder" id="finder" aria-labelledby="finder-title">
  <div class="container finder__grid">
    <h2 class="vh" id="finder-title">Every trail</h2>
    {finder_form(records, c, length_steps(records))}
    <div class="finder__main">
      {overview_map(records, "Map of the trails the filters leave", wide=True, scope="all")}
      {results(recs, finder=True)}
    </div>
    <div class="finder__notes">
      <p class="finder__foot">Not for navigation: tracks vary in quality and some trails are unfinished. Check each trail&rsquo;s own maps before you go.</p>
      {contribute}
    </div>
  </div>
</section>"""
