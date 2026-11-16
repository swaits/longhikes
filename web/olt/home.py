"""The home page: the catalogue. Search, the filters, and the trails as a list and on a map.

The list (results(), entry()) is shared with the place pages and the lists, so
every list of trails on the site looks and reads the same. The filters are the
attributes in olt/facets.py, under the same names the trail pages use.
"""
import collections
import math

from . import browse, common, facets, hike, words
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


def overview_bbox(records):
    """data-bbox attribute: the extent of every track and sketch, so the map opens on it before the data loads."""
    boxes = [r["derived"]["bbox"] for r in records if r["derived"].get("bbox")]
    for r in records:
        box = hike.sketch_bbox(hike.sketch_points(r))
        if box:
            boxes.append(box)
    if not boxes:
        return ""
    box = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
    return f' data-bbox="{",".join(f"{v:.4f}" for v in box)}"'


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


def entry(rec, *, level=3, extra="", routes_list=False, hidden=False):
    """One trail in a list. Its data-* attributes drive the filters in app.js.

    level: the heading level of the trail's name. extra: HTML placed last in the row.
    routes_list: the Routes list, whose "By <author>" headings already say what the
    row's Route badge and "Route by" line would repeat; both are left out there.
    hidden: written hidden, for app.js to show (the Saved page).

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
    by = f'\n    <p class="entry__by">{esc(facets.route_by(rec))}</p>' if route and not routes_list else ""
    desc = entry_desc(rec)
    desc_html = f'\n    <p class="entry__desc">{esc(desc)}</p>' if desc else ""
    time_html = esc(facets.time_text(rec)) + (' <small class="entry__est">estimate</small>' if est else "")
    climb_html = (f'\n    <div class="entry__climb"><dt>Climb</dt><dd>{words.elevation(climb_m, "stack")}'
                  f'<small class="entry__est">computed</small></dd></div>') if climb_m is not None else ""
    if hidden:
        attrs += " hidden"
    return f"""<li class="entry"{attrs}>
  {common.plate(rec)}
  <div class="entry__body">{kicker}
    <{h} class="entry__name"><a href="{esc(common.trail_path(rec))}">{common.name(rec)}</a>{abbr_html}</{h}>
    {common.save_button(rec)}{by}{desc_html}
    <p class="entry__where">{where_html(rec)}</p>
  </div>
  <dl class="entry__facts">
    <div class="entry__length"><dt>Length</dt><dd>{words.length(rec["length_km"], "stack", rec["derived"]["length_mi"])}<span class="loglen" style="--km: {rec["length_km"]}" aria-hidden="true"></span></dd></div>
    <div class="entry__time"><dt>Time</dt><dd>{time_html}</dd></div>
    <div class="entry__line"><dt>GPX</dt><dd class="line line--{"yes" if facets.gpx_here(rec) else "no"}">{gpx_cell(rec)}</dd></div>{climb_html}
  </dl>{extra}
</li>"""


# The filters ------------------------------------------------------------------

def _length_options(steps, selected_any_last, unit="mi"):
    opts = [f'<option value="{step_value(n, unit)}">{step_label(n, unit)}</option>' for n in steps]
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


def finder_form(records, c=None, steps=None):
    """Search and the first-rank filters in view; Walking, Shape and GPX behind "More"."""
    c = c or counts(records)
    steps = steps or length_steps(records)
    km_steps = length_steps(records, "km")
    first, more = [], []
    first.append(f"""<div class="field">
    <label class="field__label" for="where">{facets.WHERE}</label>
    <select class="select" id="where" name="where">{where_options(c)}</select>
  </div>""")
    first.append(f"""<fieldset class="field">
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
      <label><input type="radio" name="kind" value="trail"><span>Official ({c["kind:trail"]})</span></label>
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
        {_checks("gpx", facets.GPX_FILTER.items(), c, "gpx")}
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


def sort_select(default_sort="name", saved=False):
    """The one sort control of every list of trails, with the page's
    default order selected. Hidden without JavaScript (style.css):
    it cannot work then, and the HTML is already in the default order.
    saved: the Saved page's list, which opens in the order saved."""
    sorts = facets.SORTS
    if saved:
        sorts = (SAVED_ORDER,) + tuple(sorts)
        default_sort = SAVED_ORDER[0]
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


def results(recs=None, *, finder=False, groups=None, routes_list=False, default_sort="name", saved=False, top=3):
    """The list of trails, as every page shows it: div.results > head, key, list head, ol.entries.

    Every list carries the same "Sort by" control. The rows are written in
    default_sort order (a key of facets.SORTS), so the page is right with
    JavaScript off; app.js reorders in place and keeps ?sort= in the address.

    finder: the home page's list, driven by the filters (live count, empty state).
    groups: [(heading, trails, extra_fn)] to list the trails under headings (level `top`);
    sorting is within each group and the groups keep their order.
    top: the heading level of a trail's name where the trails are not in groups (and of a
    group's heading where they are; the names then sit one level lower). 3 under a page's
    own h2 (the home page); 2 on a page whose h1 is followed directly by the list.
    extra_fn(rec) gives HTML placed last in each row.
    routes_list: passed to entry() for the Routes list (see there).
    saved: the Saved page's list. Every trail's row is written hidden, and
    app.js shows the saved ones (or a link's) and writes the count; the sort
    control opens on the order saved.

    A list that holds every trail (the finder's, the Saved page's) is marked
    data-every-trail: there app.js knows every trail id, and drops the saved
    ids that match no trail.
    """
    default_sort = facets.normalize_sort(default_sort)
    if groups is None:
        groups = [(None, recs, None)]
    groups = [(heading, facets.sort_records(list(items), default_sort), extra_fn)
              for heading, items, extra_fn in groups]
    total = sum(len(g[1]) for g in groups)
    shown = [r for g in groups for r in g[1]]
    only_routes = bool(shown) and all(facets.kind(r) == "route" for r in shown)
    noun = ("route" if only_routes else "trail") + ("" if total == 1 else "s")
    lists = ""
    every = ' data-every-trail' if finder or saved else ""
    for heading, items, extra_fn in groups:
        level = top + 1 if heading else top
        rows = "\n".join(entry(r, level=level, extra=extra_fn(r) if extra_fn else "",
                                routes_list=routes_list, hidden=saved) for r in items)
        if heading:
            lists += f'\n      <h{top} class="results__group">{heading}</h{top}>'
        list_id = ' id="entries"' if finder else ""
        lists += f'\n      <ol class="entries"{list_id}{every}>\n{rows}\n      </ol>'
    if finder:
        count = (f'<p class="results-count" id="results-count" role="status">'
                 f'<strong>{total}</strong> of {total} {noun}</p>')
        empty = """
      <div class="empty-state" id="empty-state" hidden>
        <p><strong>No trails match these filters.</strong></p>
        <button class="button button--quiet" type="button" data-reset>Clear search and filters</button>
      </div>"""
    elif saved:
        count = '<p class="results-count" data-saved-total><strong>0</strong> trails</p>'
        empty = ""
    else:
        count = f'<p class="results-count"><strong>{total}</strong> {noun}</p>'
        empty = ""
    tools = sort_select(default_sort, saved=saved)
    dflt = SAVED_ORDER[0] if saved else default_sort
    return Markup(f"""<div class="results" data-sortable data-default-sort="{esc(dflt)}">
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


def overview_map(recs, label, *, wide=False, scope="", saved=False):
    """The map of the given trails (the overview geometry, limited to their ids
    unless every trail is shown). A note instead when too little can be drawn.

    saved: the Saved page's map. It is given every trail (scope "all") and
    app.js limits it to the trails shown; the figure lists the ids it can draw
    (data-drawable), so app.js leaves the map out when it would be empty, and
    its caption counts nothing, since the list is the visitor's.
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
                         'their start and end, or a ring where only one end is known. '
                         'That is not the trail&rsquo;s path.')
    if saved:
        sentences = ["Tracks are simplified for display. Select one for its name.",
                     "A trail with no GPX here is shown by its start and end only: dots straight from one "
                     "to the other, or a ring where only one end is known."]
        ids_attr += f' data-drawable="{esc(" ".join(ids))}"'
    sentences.append("Each trail&rsquo;s page names its source, credit and licence. "
                     "Base map: OpenFreeMap, &copy;&nbsp;OpenMapTiles, data &copy;&nbsp;OpenStreetMap contributors.")
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
      {legend}
    </ul>
    <p>{" ".join(sentences)}</p>
  </figcaption>
</figure>""")


def has_overview_map(recs, scope=""):
    """True when overview_map would draw a map of these trails (needs the map library)."""
    n = len(drawable_ids(recs))
    return n > 0 and (scope == "all" or n >= MAP_MIN)


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


def description(records):
    """The home page's meta description: how many, what each has, and how many have a GPX."""
    n_gpx = sum(1 for r in records if facets.gpx_here(r))
    text = (f"{len(records)} long-distance hiking trails and routes in the US and Canada: length, typical time, "
            f"a source for every fact, and a GPX for {n_gpx}.")
    return common.cut_at_word(text, common.DESCRIPTION_LIMIT)


def render(records, site):
    """The home page body (HTML)."""
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
    return f"""<section class="hero hero--short hero--home" aria-labelledby="hero-title">
  <div class="container hero__inner">
    <h1 id="hero-title" class="lockup"><img class="lockup__mark" src="/assets/favicon.svg" alt="" width="96" height="96">{esc(site.name)}<span class="vh">: long-distance hiking trails of the United States and Canada</span></h1>
    <p class="hero__tagline">Long-distance hiking trails of the United States and Canada.</p>
    <ul class="hero__tags">
      <li><a href="#finder">Filters</a></li>
      <li><a href="/lists/with-gpx/">GPX</a></li>
      <li><a href="/sources/">A source for every fact</a></li>
      <li><a href="/data/">Open data</a></li>
    </ul>
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
