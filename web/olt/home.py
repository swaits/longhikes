"""The home page: the catalogue. Search, the filters, and the trails as a list and on a map.

The list (results(), entry()) is shared with the place pages and the lists, so
every list of trails on the site looks and reads the same. The filters are the
attributes in olt/facets.py, under the same names the trail pages use.
"""
import collections
import math

from . import browse, common, datafiles, facets, hike, sketch, words
from .markup import Markup, esc

# Length range choices for the filters, round in the unit they are written in.
# Miles come first (the shortest trails are about 40 miles, the longest over
# 6,000); a reader who chose kilometres gets round kilometre steps. length_steps()
# adds a top step above the longest trail, so a chosen upper bound can always
# reach every trail.
LENGTH_STEPS_MI = (50, 75, 100, 150, 200, 300, 500, 1000, 2000, 4000, 8000)
LENGTH_STEPS_KM = (60, 80, 100, 150, 200, 300, 500, 1000, 2000, 4000, 8000)
LENGTH_STEPS = LENGTH_STEPS_MI


def length_steps(records, unit="mi"):
    """The round steps for the unit, plus a round step at or above the longest trail, when that is longer."""
    longest = max((r["length_km"] for r in records), default=0)
    if unit == "mi":
        longest = words.km_to_mi(longest)
    steps = list(LENGTH_STEPS_MI if unit == "mi" else LENGTH_STEPS_KM)
    if longest > steps[-1]:
        magnitude = 10 ** int(math.floor(math.log10(longest)))
        steps.append(int(math.ceil(longest / magnitude) * magnitude))
    return steps


def step_value(n, unit):
    """The option value of a length step: "100mi" or "160km". app.js reads it the same way."""
    return f"{n}{unit}"


def step_label(n, unit):
    """"100 mi · 161 km": the step in its own unit first."""
    if unit == "mi":
        return f"{n:,} mi &middot; {words.fmt_int(n * words.KM_PER_MI)} km"
    return f"{n:,} km &middot; {words.fmt_int(words.km_to_mi(n))} mi"


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


def overview_box(records):
    """[west, south, east, north] of every track and sketch of these trails, or None."""
    boxes = [r["derived"]["bbox"] for r in records if r["derived"].get("bbox")]
    for r in records:
        box = hike.sketch_bbox(hike.sketch_points(r))
        if box:
            boxes.append(box)
    if not boxes:
        return None
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def overview_bbox(records, box=None):
    """data-bbox attribute: the extent of every track and sketch, so the map opens on it before the data loads.
    box: the ground to open on instead (a place page's, olt/bounds.py)."""
    box = box or overview_box(records)
    return f' data-bbox="{",".join(f"{v:.4f}" for v in box)}"' if box else ""


sort_name = facets.sort_name


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
        partial = (f'<p class="entry__partial">{common.partial_short_text(rec)}</p>'
                   if common.line_differs(rec) else "")
        return (f'<span class="line__status">{swatch}{esc(facets.GPX_SHORT[status])}</span>'
                f'<span class="line__detail">GPX and GeoJSON</span>{partial}')
    return f'<span class="line__status">{common.SWATCH_NONE}{esc(facets.GPX_SHORT[status])}</span>'


# The first rows of a list are on the first screen: their logos are not lazy-loaded.
EAGER_ROWS = 4


# {credit: [(author name, page path)]} for the authors who have a page (olt/authors.py link_map),
# set by pages.render_site: a route's "Route by" line links each named author who has one.
AUTHOR_LINKS = {}


def use_authors(links):
    AUTHOR_LINKS.clear()
    AUTHOR_LINKS.update(links or {})


def route_by_html(rec):
    """facets.route_by(rec) as HTML, each author's name in it a link to their page."""
    text = str(esc(facets.route_by(rec)))
    for name, href in AUTHOR_LINKS.get(facets.author(rec), []):
        n = str(esc(name))
        if n in text:
            text = text.replace(n, f'<a href="{esc(href)}">{n}</a>', 1)
    return Markup(text)


def entry(rec, *, level=3, extra="", routes_list=False, hidden=False, eager=False, lead=None, rank=None, more=(), by=None, here=None):
    """One trail in a list. Its data-* attributes drive the filters in app.js.

    level: the heading level of the trail's name. extra: HTML placed last in the row.
    routes_list: the Routes list, whose "By <author>" headings already say what the
    row's Route badge and "Route by" line would repeat; both are left out there.
    hidden: written hidden, for app.js to show (the Saved page).
    eager: the logo is not lazy-loaded (a row of the first screen).
    lead: (label, HTML) of a figure that leads the line of facts, set as the length is (a ranked
    figure, or a figure a page compares). rank: the row's place in a ranking (data-rank, and
    "No. 3" before the figure). more: [(label, HTML)] of further facts, each with its label,
    after the others on the line of facts (a page that compares a few trails).
    by(rec) -> HTML: the row's author line in place of "Route by" (an author's page, where it
    names only the others a route is credited to); "" for none.
    here: 0 for a trail wholly in the place a place page is about, 1 for one that lies elsewhere too
    (data-here, the order that page opens in; see results()).

    The Save star follows the name in the markup (so it is the next stop for the
    keyboard) but is drawn under the logo, out of the row's flow (style.css
    .save--row): it never makes a row taller or moves its columns.
    """
    route = facets.kind(rec) == "route"
    lo, hi, est = facets.time_days(rec)
    search = " ".join([rec["name"], rec.get("common_name", ""), rec.get("short_name", ""), rec["id"],
                       facets.author(rec)]).lower()
    abbr = rec.get("short_name", "")
    abbr_cls = "entry__abbr" if common.shield_url(rec) else "entry__abbr vh"
    abbr_html = f' <span class="{abbr_cls}">{esc(abbr)}</span>' if abbr else ""
    # The climb a row may show and sort by (facets.row_climb_m): none when the
    # track covers too little or too much of the trail, so data-climb is empty
    # in exactly the cases where the row hides its climb.
    climb_m = facets.row_climb_m(rec)
    data = {
        "id": rec["id"], "where": " ".join(facets.where_tokens(rec)), "km": rec["length_km"],
        "climb": climb_m if climb_m is not None else "",
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
    by_line = by(rec) if by is not None else route_by_html(rec) if route and not routes_list else ""
    by = f'\n    <p class="entry__by">{by_line}</p>' if by_line else ""
    desc = entry_desc(rec)
    desc_html = f'\n    <p class="entry__desc">{esc(desc)}</p>' if desc else ""
    time_html = esc(facets.time_text(rec)) + (' <small class="entry__est">estimate</small>' if est else "")
    climb_html = (f'\n    <div class="entry__climb"><dt>Climb</dt><dd>{words.elevation(climb_m, "stack")}'
                  f'<small class="entry__est">computed</small></dd></div>') if climb_m is not None else ""
    if hidden:
        attrs += " hidden"
    lead_html = ""
    if rank is not None:
        attrs += f' data-rank="{rank}"'
    if here is not None:
        attrs += f' data-here="{here}"'
    if lead:
        no = f'<span class="entry__rank">No. {rank}</span> ' if rank is not None else ""
        lead_html = (f'\n    <div class="entry__lead"><dt>{esc(lead[0])}</dt><dd>{no}'
                     f'<span class="entry__figure">{lead[1]}</span></dd></div>')
    more_html = "".join(f'\n    <div class="entry__more"><dt>{esc(label)}</dt><dd>{value}</dd></div>' for label, value in more)
    return f"""<li class="entry"{attrs}>
  {common.plate(rec, eager=eager)}
  <div class="entry__body">{kicker}
    <{h} class="entry__name"><a href="{esc(common.trail_path(rec))}">{common.name(rec)}</a>{abbr_html}</{h}>
    {common.save_button(rec)}{by}{desc_html}
    <p class="entry__where">{where_html(rec)}</p>
  </div>
  <dl class="entry__facts">{lead_html}
    <div class="entry__length"><dt>Length</dt><dd>{words.length(rec["length_km"], "stack", rec["derived"]["length_mi"])}<span class="loglen" style="--km: {rec["length_km"]}" aria-hidden="true"></span></dd></div>
    <div class="entry__time"><dt>Time</dt><dd>{time_html}</dd></div>
    <div class="entry__line"><dt>GPX</dt><dd class="line line--{"yes" if facets.gpx_here(rec) else "no"}">{gpx_cell(rec)}</dd></div>{climb_html}{more_html}
  </dl>{extra}
</li>"""


# The filters ------------------------------------------------------------------
# One bar and one set of panels, on the home page and on every other page that shows a set of at
# least FILTER_MIN trails (listing()). Everything is built from the page's own trails: a facet that
# cannot narrow them is left out, and an option none of them has is not written. The numbers written
# here are for the whole set; app.js counts again from the rows on the page every time anything
# changes, and hides an option that would show nothing (its counting is facetCounts(), which
# web/tests/test_filter_counts.py runs under node against counts made here from the records).

FILTER_MIN = 10


def _length_options(steps, selected_any_last, unit="mi"):
    opts = [f'<option value="{step_value(n, unit)}">{step_label(n, unit)}</option>' for n in steps]
    if selected_any_last:
        return "".join(opts[1:]) + '<option value="" selected>Any</option>'
    return '<option value="">Any</option>' + "".join(opts[:-1])


def _opt(value, label, n):
    """A counted option: its name in data-label, for app.js to write each new count after it."""
    return f'<option value="{esc(value)}" data-label="{esc(label)}">{esc(label)} ({n})</option>'


def where_options(c, scope="all"):
    """The Where filter. scope "all": the two countries, then each place group with its states and
    provinces. scope "g:<group>": the page of one group: all of it first (the page's whole set),
    then only the places inside it. An option that would show every trail of the page is the same as
    the first one, and one that would show none is not written."""
    total = c["total"]

    def useful(key):
        return 0 < c["where:" + key] < total

    if scope.startswith("g:"):
        g = scope[2:]
        keys = next(k for x, _, k in facets.PLACE_GROUPS if x == g)
        opts = [_opt("", f"All of {facets.GROUP_NAME[g]}", total)]
        opts += [_opt(k, facets.place_name(k), c["where:" + k]) for k in sorted(keys, key=facets.place_name) if useful(k)]
        if g in {facets.GROUP_OF[k] for k in facets.GROUP_OF if k.startswith("CA-")} and useful(facets.ACROSS_CANADA):
            opts.append(_opt(facets.ACROSS_CANADA, facets.ACROSS_CANADA_NAME, c["where:" + facets.ACROSS_CANADA]))
        return "".join(opts)
    opts = [_opt("", "Anywhere", total)]
    for code in ("US", "CA"):
        if useful(code):
            opts.append(_opt(code, words.COUNTRIES[code], c["where:" + code]))
    for g, name, keys in facets.PLACE_GROUPS:
        inner = [_opt("g:" + g, f"All of {name}", c["where:g:" + g])] if useful("g:" + g) else []
        inner += [_opt(k, facets.place_name(k), c["where:" + k]) for k in sorted(keys, key=facets.place_name) if useful(k)]
        if inner:
            opts.append(f'<optgroup label="{esc(name)}">{"".join(inner)}</optgroup>')
    if useful(facets.ACROSS_CANADA):
        opts.append(_opt(facets.ACROSS_CANADA, facets.ACROSS_CANADA_NAME, c["where:" + facets.ACROSS_CANADA]))
    return "".join(opts)


def _narrows(c, prefix, values):
    """True when choosing some value of the facet would show some of the trails but not all."""
    return any(0 < c[f"{prefix}:{v}"] < c["total"] for v in values)


def _checks(name, items, c, prefix, hints=None):
    """Checkboxes for a multi-choice facet: (value, label) items with their counts."""
    out = []
    for value, label in items:
        n = c[f"{prefix}:{value}"]
        if not n:
            continue
        # A hint is a tooltip, not a second line: the row stays one line.
        title = f' title="{esc(hints[value])}"' if hints and hints.get(value) else ""
        out.append(f'<label class="check"{title}><input type="checkbox" name="{name}" value="{esc(value)}">'
                   f'<span class="check__text">{esc(label)} <span class="check__count">{n}</span></span></label>')
    return "".join(out)


def _missing(records, key):
    """The note under an optional facet: how many trails it leaves out while it is in use."""
    _, without = facets.coverage(records, key)
    if not without:
        return ""
    return (f'<p class="field__hint filter-missing" data-missing="{key}" hidden>'
            f'{esc(facets.missing_text(without, key))} They are left out while this filter is on.</p>')


def finder_form(records, c=None, steps=None, where="all"):
    """The bar (search, Filters, Clear) and the panels: the first-rank filters, then Walking, Shape and
    GPX behind "More". records: the page's own trails. where: the Where filter's scope ("all",
    "g:<group>" on a group's page, "" for none: a state's page). A facet is written only when it can
    narrow these trails; each field carries data-facet, for app.js to hide it when it no longer can."""
    c = c or counts(records)
    steps = steps or length_steps(records)
    km_steps = length_steps(records, "km")
    first, more = [], []
    if where:
        opts = where_options(c, where)
        if opts.count("<option") > 1:
            first.append(f"""<div class="field" data-facet="where">
    <label class="field__label" for="where">{facets.WHERE}</label>
    <select class="select" id="where" name="where">{opts}</select>
  </div>""")
    kms = [r["length_km"] for r in records]
    if any(min(kms) < n * words.KM_PER_MI <= max(kms) for n in steps):
        first.append(f"""<fieldset class="field" data-facet="length">
    <legend>{facets.LENGTH}</legend>
    <div class="range">
      <label class="vh" for="min">Shortest length</label>
      <select class="select" id="min" name="min" data-length-options="min" data-steps-mi="{",".join(map(str, steps))}" data-steps-km="{",".join(map(str, km_steps))}">{_length_options(steps, False)}</select>
      <span class="range__to" aria-hidden="true">to</span>
      <label class="vh" for="max">Longest length</label>
      <select class="select" id="max" name="max" data-length-options="max" data-steps-mi="{",".join(map(str, steps))}" data-steps-km="{",".join(map(str, km_steps))}">{_length_options(steps, True)}</select>
    </div>
    <p class="field__hint" id="len-hint" aria-live="polite">Any length.</p>
  </fieldset>""")
    if _narrows(c, "time", [k for k, _, _ in facets.TIME_BANDS]):
        first.append(f"""<fieldset class="field field--wide" data-facet="time">
    <legend>{facets.TIME}</legend>
    <div class="pills">{_checks("time", [(k, label) for k, label, _ in facets.TIME_BANDS], c, "time")}</div>
    <p class="field__hint">To walk it all. Where no source says, it is estimated from the length.</p>
  </fieldset>""")
    if facets.offered(records, "season") and _narrows(c, "month", range(1, 13)):
        month_opts = "".join(_opt(str(i), m, c[f"month:{i}"]) for i, m in enumerate(facets.MONTHS, 1) if c[f"month:{i}"])
        first.append(f"""<div class="field" data-facet="month">
    <label class="field__label" for="month">{facets.SEASON}</label>
    <select class="select" id="month" name="month"><option value="">Any month</option>{month_opts}</select>
    <p class="field__hint">Trails usually walked in that month.</p>
    {_missing(records, "season")}
  </div>""")
    if _narrows(c, "kind", facets.KINDS):
        first.append(f"""<fieldset class="field" data-facet="kind">
    <legend>{facets.KIND}</legend>
    <div class="seg">
      <label><input type="radio" name="kind" value="" checked><span>Any</span></label>
      <label><input type="radio" name="kind" value="trail"><span data-label="Official">Official ({c["kind:trail"]})</span></label>
      <label><input type="radio" name="kind" value="route"><span data-label="Routes">Routes ({c["kind:route"]})</span></label>
    </div>
    <p class="field__hint"><a href="/routes/">What is a route?</a></p>
  </fieldset>""")
    if facets.offered(records, "terrain") and _narrows(c, "terrain", facets.TERRAIN_VALUES):
        first.append(f"""<fieldset class="field field--wide" data-facet="terrain">
    <legend>{facets.TERRAIN}</legend>
    <div class="pills">{_checks("terrain", facets.TERRAIN_VALUES.items(), c, "terrain")}</div>
    {_missing(records, "terrain")}
  </fieldset>""")
    if facets.offered(records, "walking") and _narrows(c, "walking", facets.WALKING_VALUES):
        more.append(f"""<fieldset class="field" data-facet="walking">
        <legend>{facets.WALKING}</legend>
        {_checks("walking", facets.WALKING_VALUES.items(), c, "walking", facets.WALKING_HINT)}
        {_missing(records, "walking")}
      </fieldset>""")
    if facets.offered(records, "shape") and _narrows(c, "shape", facets.SHAPES):
        more.append(f"""<fieldset class="field" data-facet="shape">
        <legend>{facets.SHAPE}</legend>
        {_checks("shape", facets.SHAPES.items(), c, "shape")}
        {_missing(records, "shape")}
      </fieldset>""")
    if _narrows(c, "gpx", facets.GPX_FILTER):
        more.append(f"""<fieldset class="field" data-facet="gpx">
        <legend>{facets.GPX}</legend>
        {_checks("gpx", facets.GPX_FILTER.items(), c, "gpx")}
      </fieldset>""")
    more_html = f"""
    <details class="filters__more">
      <summary>More filters <span class="filters__active"></span></summary>
      <div class="filters__form">
        {"".join(more)}
      </div>
    </details>""" if more else ""
    return f"""<form class="filters" id="finder-form" role="search" aria-label="Find a trail">
  <div class="filters__bar">
    <div class="filters__search field">
      <label class="vh" for="q">Search</label>
      <input class="input" id="q" name="q" type="search" placeholder="Search by name, abbreviation or author" autocomplete="off" spellcheck="false">
    </div>
    <button class="button filters__toggle js-only" type="button" aria-expanded="false" aria-controls="filters-panels">Filters <span class="filters__count"></span></button>
    <button class="button button--quiet filters__clear" type="reset" hidden>Clear</button>
  </div>
  <div class="filters__panels" id="filters-panels">
    <details class="filters__panel" open>
      <summary>Filters</summary>
      <div class="filters__first">
      {"".join(first)}
      </div>
    </details>{more_html}
    <p class="filters__none" hidden>Nothing here narrows these trails further.</p>
    <p class="filters__end js-only"><button class="button filters__done" type="button">Show the trails</button></p>
  </div>
</form>"""


def listing(recs=None, *, where="all", groups=None, **kw):
    """The rows of a page that shows a set of trails, with the filter bar over them when the set
    has at least FILTER_MIN trails (else results() alone). where: the Where filter's scope
    (finder_form). The other arguments are results()'s."""
    trails = [r for g in groups for r in g[1]] if groups is not None else list(recs)
    if len(trails) < FILTER_MIN:
        return results(recs, groups=groups, **kw)
    return Markup(f"""<div class="finder__bar">{finder_form(trails, where=where)}</div>
  {results(recs, groups=groups, finder=True, **kw)}""")


# The list ---------------------------------------------------------------------

# The length strip's ticks (style.css .loglen): 100, 1,000 and 10,000 miles, or
# kilometres for a reader who chose them. Positions are in style.css.
SCALE_TICKS = (100, 1000, 10000)


# Sort column of each sort key, and the arrow for its direction in the head.
_SORT_COLUMN = {"name": "name", "name-desc": "name", "length-desc": "length",
                "length-asc": "length", "time-asc": "time", "time-desc": "time",
                "climb-desc": "climb", "climb-asc": "climb"}
_SORT_ARROW = {"name": "↑", "name-desc": "↓", "length-desc": "↓", "length-asc": "↑",
               "time-asc": "↑", "time-desc": "↓", "climb-desc": "↓", "climb-asc": "↑"}


def _head_button(col, label, sort_key, extra=""):
    active = _SORT_COLUMN[sort_key] == col
    arrow = _SORT_ARROW[sort_key] if active else "↕"
    cls = "list-head__sort is-active" if active else "list-head__sort"
    return (f'<span><button type="button" class="{cls}" data-sort-col="{col}" tabindex="-1">'
            f'{esc(label)} <span class="list-head__arrow" data-arrow aria-hidden="true">{arrow}</span>'
            f'</button>{extra}</span>')


def list_head(sort_key="name"):
    """The column head over a list: Trail, Length, Time and Climb are sort
    buttons; GPX is not sortable. The scale ticks follow the reader's unit
    preference with the same len__km / len__mi pair the lengths use.

    The head stays aria-hidden with its buttons out of the tab order on
    purpose: the "Sort by" select in the results head is the one sort
    control for keyboard and screen-reader users, and app.js announces
    each new order beside it. The buttons are a pointer shortcut that
    always agrees with the select.
    """
    sort_key = facets.normalize_sort(sort_key)
    ticks = []
    for i, n in enumerate(SCALE_TICKS):
        last = i == len(SCALE_TICKS) - 1
        ticks.append(f'<span><span class="len__mi">{n:,}{" mi" if last else ""}</span>'
                     f'<span class="len__km">{n:,}{" km" if last else ""}</span></span>')
    scale = f'<span class="list-head__scale">{"".join(ticks)}</span>'
    return f"""<div class="list-head" aria-hidden="true">
        {_head_button("name", "Trail", sort_key)}
        {_head_button("length", facets.LENGTH, sort_key, scale)}
        {_head_button("time", facets.TIME, sort_key)}
        <span class="list-head__plain">{facets.GPX}</span>
        {_head_button("climb", "Climb", sort_key)}
      </div>"""


# The order a saved list was made in: offered first on the Saved page only,
# where app.js numbers the rows (data-order) in the order they were saved.
SAVED_ORDER = ("saved", "Order saved")


HERE_ORDER = "here"


def sort_select(default_sort="name", saved=False, ranked="", wholly=None):
    """The one sort control of every list of trails, with the page's
    default order selected. Hidden without JavaScript (style.css):
    it cannot work then, and the HTML is already in the default order.
    saved: the Saved page's list, which opens in the order saved.
    wholly: a place page's list, which opens with the trails wholly in the place first (results())."""
    sorts = facets.SORTS
    if saved:
        sorts = (SAVED_ORDER,) + tuple(sorts)
        default_sort = SAVED_ORDER[0]
    elif ranked:
        sorts = (("rank", f"Rank: {ranked}"),) + tuple(sorts)
        default_sort = "rank"
    elif wholly:
        sorts = ((HERE_ORDER, "Wholly here first, then A to Z"),) + tuple(sorts)
        default_sort = HERE_ORDER
    else:
        default_sort = facets.normalize_sort(default_sort)
    options = "".join(
        f'\n              <option value="{esc(k)}"{" selected" if k == default_sort else ""}>{esc(label)}</option>'
        for k, label in sorts)
    return f"""<label class="results-sort"><span class="results-sort__label">Sort by</span>
            <select class="select" id="sort" name="sort" data-sort-select>{options}
            </select>
          </label>
          <span class="vh" data-sort-status aria-live="polite"></span>"""


SORT_SELECT = sort_select()


def key(official=True):
    """official: False on a list of routes only, which has no official trail to explain."""
    first = f"<li>{common.SWATCH_LINE}Official trail with a GPX here</li>\n        " if official else ""
    return f"""<ul class="key" aria-label="Key to the list">
        {first}<li>{common.SWATCH_ROUTE}Route with a GPX here</li>
        <li>{common.SWATCH_NONE}No GPX here: its page says where to get one</li>
      </ul>"""


def results(recs=None, *, finder=False, groups=None, routes_list=False, default_sort="name", saved=False, top=3,
            ranked="", lead=None, more=None, tools=True, by=None, every=False, wholly=None):
    """The list of trails, as every page shows it: div.results > head, key, list head, ol.entries.

    Every list carries the same "Sort by" control. The rows are written in
    default_sort order (a key of facets.SORTS), so the page is right with
    JavaScript off; app.js reorders in place and keeps ?sort= in the address.

    finder: a list driven by the filter bar over it (listing(): live count, empty state).
    every: the list holds every trail (the home page's).
    groups: [(heading, trails, extra_fn)] to list the trails under headings (level `top`);
    sorting is within each group and the groups keep their order. A heading may be a pair
    (heading HTML, intro HTML): the intro is a sentence under the heading (an author's summary).
    top: the heading level of a trail's name where the trails are not in groups (and of a
    group's heading where they are; the names then sit one level lower). 3 under a page's
    own h2 (the home page); 2 on a page whose h1 is followed directly by the list.
    extra_fn(rec) gives HTML placed last in each row.
    routes_list: passed to entry() for the Routes list (see there).
    saved: the Saved page's list. Every trail's row is written hidden, and
    app.js shows the saved ones (or a link's) and writes the count; the sort
    control opens on the order saved.

    A list that holds every trail (the home page's, the Saved page's) is marked
    data-every-trail: there app.js knows every trail id, and drops the saved
    ids that match no trail.

    ranked: the label of a ranking (a /numbers/ page): the rows keep the order given, each
    numbered, and "Rank" is the list's first order. lead(rec) -> (label, HTML) or None: a figure
    that leads each row's line of facts (the ranked figure, or one a page compares). more(rec) ->
    [(label, HTML)]: further facts for each row (entry()). tools: False for a short list inside a
    page that has its own (no count and no sort control).

    wholly(rec) -> bool: a place page's test for a trail that lies wholly in the place. The page opens
    with those first, then the trails that lie elsewhere too, each group A to Z (data-here, and a first
    sort option that app.js and this agree on); the other orders stay as everywhere.
    """
    default_sort = facets.normalize_sort(default_sort)
    if groups is None:
        groups = [(None, recs, None)]
    if wholly:
        default_sort = "name"
        groups = [(heading, sorted(items, key=lambda r: (not wholly(r), sort_name(r))), extra_fn)
                  for heading, items, extra_fn in groups]
    else:
        groups = [(heading, list(items) if ranked else facets.sort_records(list(items), default_sort), extra_fn)
                  for heading, items, extra_fn in groups]
    total = sum(len(g[1]) for g in groups)
    shown = [r for g in groups for r in g[1]]
    only_routes = bool(shown) and all(facets.kind(r) == "route" for r in shown)
    noun = ("route" if only_routes else "trail") + ("" if total == 1 else "s")
    lists = ""
    every = ' data-every-trail' if every or saved else ""
    seen = 0
    for heading, items, extra_fn in groups:
        level = top + 1 if heading else top
        rows = "\n".join(entry(r, level=level, extra=extra_fn(r) if extra_fn else "",
                                routes_list=routes_list, hidden=saved,
                                eager=not saved and seen + i < EAGER_ROWS,
                                lead=lead(r) if lead else None, more=more(r) if more else (),
                                rank=seen + i + 1 if ranked else None, by=by,
                                here=(0 if wholly(r) else 1) if wholly else None) for i, r in enumerate(items))
        seen += len(items)
        if isinstance(heading, tuple):
            heading, intro = heading
            intro = f'<p class="results__intro">{intro}</p>' if intro else ""
            lists += f'\n      <div class="results__lead"><h{top} class="results__group">{heading}</h{top}>{intro}</div>'
        elif heading:
            lists += f'\n      <h{top} class="results__group">{heading}</h{top}>'
        list_id = ' id="entries"' if finder and len(groups) == 1 else ""
        lists += f'\n      <ol class="entries"{list_id}{every}>\n{rows}\n      </ol>'
    if finder:
        count = (f'<p class="results-count" id="results-count" role="status" data-noun="{noun}">'
                 f'<strong>{total}</strong> {noun}</p>')
        empty = f"""
      <div class="empty-state" id="empty-state" hidden>
        <p><strong>No {noun} match these filters.</strong></p>
        <button class="button button--quiet" type="button" data-reset>Clear search and filters</button>
        <p>Not finding a trail? <a href="/left-out/">Some are left out, with the reason for each.</a></p>
      </div>"""
    elif saved:
        count = '<p class="results-count" data-saved-total><strong>0</strong> trails</p>'
        empty = ""
    else:
        count = f'<p class="results-count"><strong>{total}</strong> {noun}</p>'
        empty = ""
    if not tools:
        return Markup(f'<div class="results results--short">{lists}</div>')
    tools = sort_select(default_sort, saved=saved, ranked=ranked, wholly=wholly)
    dflt = SAVED_ORDER[0] if saved else "rank" if ranked else HERE_ORDER if wholly else default_sort
    finder_attr = " data-finder" if finder else ""
    return Markup(f"""<div class="results"{finder_attr} data-sortable data-default-sort="{esc(dflt)}">
      <div class="results-head">
        {count}
        <div class="results-tools">
          {tools}
        </div>
      </div>
      {key(official=not only_routes)}
      {list_head(default_sort)}{lists}{empty}
    </div>""")


# A map of a selection is drawn only when it has at least this many things
# to draw: a track, or a sketch from a start or end point (hike.sketch_points).
MAP_MIN = 3


def track_ids(recs):
    return [r["id"] for r in recs if "line" in r["derived"]["files"]]


def sketch_records(recs):
    """Trails with no track that a map can sketch from their start or end point."""
    return [r for r in recs if hike.sketch_points(r)]


def drawable_ids(recs):
    """Ids a map of these trails can draw, by track or by sketch, in order."""
    tracks = set(track_ids(recs))
    return [r["id"] for r in recs if r["id"] in tracks or hike.sketch_points(r)]


def overview_map(recs, label, *, wide=False, scope="", saved=False, place=None):
    """The map of the given trails (the overview geometry, limited to their ids
    unless every trail is shown). A note instead when too little can be drawn.

    saved: the Saved page's map. It is given every trail (scope "all") and
    app.js limits it to the trails shown; the figure lists the ids it can draw
    (data-drawable), so app.js leaves the map out when it would be empty, and
    its caption counts nothing, since the list is the visitor's.

    place: [west, south, east, north] of the place a place page is about. The map opens on it, and
    returns to it when the filters are cleared; the tracks are drawn in full, and those that run
    beyond it leave the opening view. Without it the map opens on the extent of the tracks.
    """
    ids = drawable_ids(recs)
    if not ids:
        return Markup('<p class="note">None of these trails has a GPX here or a known start or end, '
                      'so there is nothing to draw. Each trail&rsquo;s page says where to get a GPX.</p>')
    if len(ids) < MAP_MIN and scope != "all":
        names = words.join_names(f'<a href="{esc(common.trail_path(r))}">{common.name(r)}</a>'
                                 for r in recs if r["id"] in ids)
        return Markup(f'<p class="note">Only {names} {"has" if len(ids) == 1 else "have"} a GPX here '
                      'or a known start or end, so no map of them all is drawn. '
                      'Each trail&rsquo;s page says where to get a track.</p>')
    ids_attr = "" if scope == "all" else f' data-ids="{esc(" ".join(ids))}"'
    n = len(track_ids(recs))
    sketches = sketch_records(recs)
    # The legend names only what this map draws; the home page's map, which the
    # filters change, names every kind.
    drawn = [r for r in recs if r["id"] in set(ids)]
    legend = []
    if scope == "all" or any(not common.is_route(r) for r in drawn):
        legend.append(f"<li>{common.SWATCH_LINE}Official trail</li>")
    if scope == "all" or any(common.is_route(r) for r in drawn):
        legend.append(f"<li>{common.SWATCH_ROUTE}Route</li>")
    if sketches:
        legend.append(f"<li>{common.SWATCH_SKETCH}No GPX here: start and end only</li>")
    legend = "\n      ".join(legend)
    sentences = []
    if n:
        sentences.append(f'{n} track{"s" if n != 1 else ""}, simplified for display. Select one for its name.')
    else:
        sentences.append("Select one for its name.")
    if sketches:
        s = len(sketches)
        sentences.append(f'{s} trail{"s" if s != 1 else ""} with no GPX here '
                         f'{"are" if s != 1 else "is"} shown as a dotted straight line between '
                         'their start and end, or a ring for a loop, which starts and ends in one place. '
                         'That is not the trail&rsquo;s path.')
    if saved:
        sentences = ["Tracks are simplified for display. Select one for its name.",
                     "A trail with no GPX here is shown by its start and end only: dots straight from one "
                     "to the other, or a ring for a loop."]
        ids_attr += f' data-drawable="{esc(" ".join(ids))}"'
    sentences.append("Each trail&rsquo;s page names its source, credit and licence. "
                     "Base map: OpenFreeMap, &copy;&nbsp;OpenMapTiles, data &copy;&nbsp;OpenStreetMap contributors.")
    # The tracks are drawn into the page, on the ground the live map opens on (olt/sketch.py). The
    # Saved page has none: which trails it draws is the visitor's own, so app.js draws them.
    frame_attr, drawing = "", ""
    box = place or overview_box(recs)
    if box and not saved:
        fr = sketch.frame(box)
        frame_attr = f' data-frame="{",".join(f"{v:g}" for v in fr)}"'
        drawing = sketch.svg(sketch.overview_features(ids), fr, ident=True)
        # The frame takes the shape of the ground it shows, within calm bounds, so the tracks fill it
        # (style.css .browse__map); the drawing and the live map fit the same ground either way.
        frame_attr += f' style="--frame-n: {frame_ratio(fr):.3f}"'
    place_attr = " data-place" if place and not saved else ""
    return Markup(f"""<figure class="mapfig{" mapfig--wide" if wide else ""}" data-map="overview" data-src="/data/overview.geojson"{ids_attr}{overview_bbox(recs, place)}{frame_attr}{place_attr}>
  <div class="mapfig__frame">
    <span class="mapfig__corner mapfig__corner--nw" aria-hidden="true"></span>
    <div class="map" role="region" aria-label="{esc(label)}">
      <div class="map__fallback">{drawing}</div>
      <div class="map__canvas"></div>
      <p class="map__status" role="status">The map needs JavaScript. The list has every trail.</p>
    </div>
    <span class="mapfig__corner mapfig__corner--se" aria-hidden="true"></span>
  </div>
  <figcaption class="mapfig__caption">
    <ul class="legend" aria-label="Legend">
      {legend}
    </ul>
    <p>{" ".join(sentences)}</p>
  </figcaption>
</figure>""")


# The shape of a browsing page's map frame: the ground's own width over height, held between these.
RATIO_MIN, RATIO_MAX = 0.8, 1.6


def frame_ratio(fr):
    """Width over height of the frame `fr` (Web Mercator), between RATIO_MIN and RATIO_MAX."""
    plane = sketch.Plane(fr)
    return max(RATIO_MIN, min(RATIO_MAX, plane.w / plane.h if plane.h else RATIO_MAX))


def browse_view(listing, map_html, *, about="", about_title="", about_id="about-these"):
    """The body of every page that shows a set of trails: the rows, with their map.

    On a wide screen the rows are on the left and the map on the right, where it stays in view as the
    rows scroll; on a narrow one the map is a short band above the rows. Text about the set (about,
    HTML) follows the rows as a section of its own under about_title. A set too small to map (the
    map is a note) is the rows alone, with the note under them (style.css .browse)."""
    has_map = 'class="mapfig' in str(map_html)
    if has_map:
        grid = f"""<div class="browse">
  <div class="browse__map" id="map">{map_html}</div>
  <div class="browse__list" id="browse-list">{listing}</div>
</div>"""
    else:
        grid = f"""<div class="browse browse--no-map">
  <div class="browse__list" id="browse-list">{listing}{map_html}</div>
</div>"""
    if about:
        grid += about_section(about, about_title or "About these trails", about_id)
    return Markup(grid)


def about_section(html, title, section_id):
    """A section of text after the rows, under its own heading (browse_view's about)."""
    return Markup(f"""
<section class="browse-about" aria-labelledby="{esc(section_id)}">
  <h2 id="{esc(section_id)}">{esc(title)}</h2>
  <div class="prose">{html}</div>
</section>""")


def has_overview_map(recs, scope=""):
    """True when overview_map would draw a map of these trails (needs the map library)."""
    n = len(drawable_ids(recs))
    return n > 0 and (scope == "all" or n >= MAP_MIN)


def time_band_keys(keys, have, records):
    """keys (list keys, in the row's order) with a list added for each of the filter's trip-length bands
    (facets.TIME_BANDS) that none of them covers, so the row offers every band the Time filter does. A list
    covers a band when every trail in the band is in it; the one with the fewest trails is the one that
    stands for the band. The added list goes after the last list that covers an earlier band. A row that
    holds no trip length at all is returned as it is."""
    time_lists = [(lst, recs) for lst, recs in have.values() if lst.group == "time" and lst.key != "weekend"]
    keys = list(keys)
    if not any(k in {lst.key for lst, _ in time_lists} for k in keys):
        return keys  # a row with no trip length in it (a data file that left them out) is left as it is
    last = None
    for band, _, _ in facets.TIME_BANDS:
        members = [r for r in records if facets.time_band(r) == band]
        covering = [(len(recs), lst.key) for lst, recs in time_lists if members and all(lst.test(r) for r in members)]
        if not covering:
            continue
        if any(k in keys for _, k in covering):
            last = max(keys.index(k) for _, k in covering if k in keys)
            continue
        key = min(covering)[1]
        at = last + 1 if last is not None else len(keys)
        keys.insert(at, key)
        last = at
    return keys


def lists_row(records, picks=()):
    """The row of lists under the home page's headline: the lists the data file marks for it (picks,
    from datafiles.home_lists: key and position), in that order, each with its count, then "All
    lists". A marked list that is not shown today (too few trails, or nearly all of them) is left out."""
    have = {lst.key: (lst, recs) for lst, recs in browse.shown(records)}
    keys = time_band_keys([k for k in picks if k in have], have, records)
    items = "".join(
        f'<li><a href="{esc(browse.path(have[key][0]))}">{esc(have[key][0].title)}'
        f'<span class="lists-row__n">{len(have[key][1])}</span></a></li>'
        for key in keys)
    if not items:
        return ""
    return f"""<nav class="lists-row" aria-labelledby="lists-title">
      <h2 id="lists-title" class="vh">Start from a list</h2>
      <ul>{items}<li class="lists-row__all"><a href="/lists/">All lists</a></li></ul>
    </nav>"""


def home_picks(entries):
    """The keys of the lists marked for the home page, in the order of their `home` positions."""
    marked = [e for e in entries if isinstance(e.get("home"), int)]
    return [e["key"] for e in sorted(marked, key=lambda e: e["home"])]


def description(records):
    """The home page's meta description: how many, what each has, and how many have a GPX."""
    n_gpx = sum(1 for r in records if facets.gpx_here(r))
    text = (f"{len(records)} long-distance hiking trails and routes in the US and Canada: length, typical time, "
            f"a source for every fact, and a GPX for {n_gpx}.")
    return common.cut_at_word(text, common.DESCRIPTION_LIMIT)


def render(records, site, repo_root=""):
    """The home page body (HTML). repo_root: where collections.toml names the lists the page shows."""
    c = counts(records)
    recs = sorted(records, key=sort_name)
    total = c["total"]
    lede = (f"{total} trails. Narrow them by where they are, how long they take, when to walk them "
            f"and what the country is like.")
    contribute = ""
    if site.repo_url:
        contribute = (f'<p class="finder__foot">Something wrong, or a trail missing? '
                      f'<a href="{esc(site.correction_url())}">Report a problem</a> or '
                      f'<a href="{esc(site.new_trail_url)}">suggest a trail</a>.</p>')
    picks = home_picks(datafiles.lists(repo_root))
    listing = f"""<div class="finder__bar">{finder_form(records, c, length_steps(records))}</div>
  {results(recs, finder=True, every=True)}"""
    return f"""<section class="intro" aria-labelledby="intro-title">
  <div class="container intro__inner">
    <h1 id="intro-title">{esc(site.tagline.rstrip("."))}</h1>
    <p class="intro__lede">{lede}</p>
    {lists_row(records, picks)}
  </div>
</section>
<div class="container home" id="finder">
  <h2 class="vh" id="finder-title">Every trail</h2>
  {browse_view(listing, overview_map(records, "Map of the trails the filters leave", scope="all"))}
  <div class="finder__notes">
    <p class="finder__foot">Not for navigation: tracks vary in quality and some trails are unfinished. Check each trail&rsquo;s own maps before you go.</p>
    {contribute}
  </div>
</div>"""
