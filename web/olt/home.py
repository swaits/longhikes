"""The home page: what the site is, the overview map, and the trail finder with every record.

The list of records (results(), entry()) is shared with the region pages and
the routes page, so every list of records on the site looks and reads the same.
"""
import collections
import math
import re

from . import common, words
from .markup import Markup, esc

# Length range choices (km) for the filters. length_steps() adds a top step
# above the longest record, so a chosen upper bound can always reach every record.
LENGTH_STEPS = (60, 80, 100, 150, 200, 300, 500, 1000, 2000, 4000, 8000)


def length_steps(records):
    """LENGTH_STEPS plus a round step at or above the longest record, when that is longer."""
    longest = max((r["length_km"] for r in records), default=0)
    steps = list(LENGTH_STEPS)
    if longest > steps[-1]:
        magnitude = 10 ** int(math.floor(math.log10(longest)))
        steps.append(int(math.ceil(longest / magnitude) * magnitude))
    return steps


def counts(records):
    """Counts for the filters. A record counts under each country it touches (its own
    country and its regions' countries) and under each of its regions, as on /regions/;
    a Canada-wide record counts under "region:CA-*", not under each province."""
    c = collections.Counter()
    for r in records:
        c["total"] += 1
        c[common.kind(r)] += 1
        c["line" if common.has_line(r) else "record_only"] += 1
        if common.is_route(r):
            c["route_line" if common.has_line(r) else "route_record_only"] += 1
            c["policy:" + common.policy(r)] += 1
        c["tier:" + r.get("tier", "")] += 1
        for country in common.countries(r):
            c["country:" + country] += 1
        for key in set(words.region_key(code, r["country"]) for code in r.get("regions", [])):
            c["region:" + key] += 1
    return c


def overview_bbox(records):
    """data-bbox attribute: the extent of every line, so the map opens on it before the data loads."""
    boxes = [r["derived"]["bbox"] for r in records if r["derived"].get("bbox")]
    if not boxes:
        return ""
    box = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
    return f' data-bbox="{",".join(f"{v:.4f}" for v in box)}"'


def sort_name(rec):
    return re.sub(r"^The ", "", rec["name"]).lower()


def entry(rec, *, level=3, extra=""):
    """One record in a list. Its data-* attributes drive the filters in app.js.

    level: the heading level of the record's name. extra: HTML placed last in the row.
    """
    route = common.is_route(rec)
    if route:
        r = rec["route"]
        desc = "By " + r["creator"] + (f", {r['year']}" if r.get("year") else "")
    elif rec.get("tier") == "national" and common.designated_year(rec):
        desc = "Designated " + common.designated_year(rec)
    else:
        desc = rec.get("designation", "")
    where = Markup(f'{common.regions_html(rec, linked=True)} <span aria-hidden="true">&middot;</span> '
                   f'{esc(words.COUNTRIES.get(rec["country"], rec["country"]))}')
    policy = common.policy_chip(common.policy(rec)) if route else ""
    partial = common.line_differs(rec)
    if common.has_line(rec):
        partial_note = (f'<p class="entry__partial">{esc(common.partial_short_text(rec))}</p>'
                        if partial else "")
        line = (f'<span class="line__status">{common.SWATCH_ROUTE if route else common.SWATCH_LINE}Track{policy}</span>'
                f'{partial_note}'
                f'<span class="line__detail">GeoJSON, GPX</span>'
                f'<span class="line__detail">{esc(common.short_source(rec))} &middot; {esc(common.licence_label(rec))}</span>')
        note = ""
    else:
        line = f'<span class="line__status">{common.SWATCH_NONE}Record only{policy}</span>'
        note = (f'\n  <p class="entry__note"><span class="vh">Why there is no track: </span>'
                f'{esc(common.absent_reason_short(rec))}</p>')
    regions = " ".join(words.region_key(c, rec["country"]) for c in rec.get("regions", []))
    search = " ".join([rec["name"], rec.get("short_name", ""), rec["id"]]
                      + ([rec["route"]["creator"]] if route else [])).lower()
    abbr_cls = "entry__abbr" if common.shield_url(rec) else "entry__abbr vh"
    data = (f' data-id="{esc(rec["id"])}" data-country="{esc(rec["country"])}"'
            f' data-countries="{esc(" ".join(common.countries(rec)))}" data-regions="{esc(regions)}"'
            f' data-km="{rec["length_km"]}" data-kind="{esc(common.kind(rec))}"'
            f' data-line="{"yes" if common.has_line(rec) else "no"}"{' data-partial="yes"' if partial else ""}'
            f' data-tier="{esc(rec.get("tier", ""))}"'
            f' data-policy="{esc(common.policy(rec))}" data-name="{esc(sort_name(rec))}" data-search="{esc(search)}"')
    h = f"h{level}"
    return f"""<li class="entry"{data}>
  {common.plate(rec)}
  <div class="entry__body">
    <p class="entry__kicker">{common.tags(rec, with_policy=False)}</p>
    <{h} class="entry__name"><a href="{esc(common.trail_path(rec))}">{common.name(rec)}</a> <span class="{abbr_cls}">{esc(rec.get("short_name", ""))}</span></{h}>
    <p class="entry__desc">{esc(desc)}</p>
    <p class="entry__where">{where}</p>
  </div>
  <dl class="entry__facts">
    <div class="entry__length"><dt>Length</dt><dd>{words.length(rec["length_km"], "stack", rec["derived"]["length_mi"])}<span class="loglen" style="--km: {rec["length_km"]}" aria-hidden="true"></span></dd></div>
    <div class="entry__line"><dt>Track</dt><dd class="line line--{"yes" if common.has_line(rec) else "no"}">{line}</dd></div>
  </dl>{note}{extra}
</li>"""


def _length_options(steps, selected_any_last):
    opts = [f'<option value="{km}">{km:,} km &middot; {words.fmt_int(words.km_to_mi(km))} mi</option>'
            for km in steps]
    if selected_any_last:
        return "".join(opts[1:]) + '<option value="" selected>Any</option>'
    return '<option value="">Any</option>' + "".join(opts[:-1])


def region_options(c):
    """The region filter: each state, province and territory a record names, with the
    count its /regions/ page shows; the Canada-wide records under their own option."""
    groups = []
    for country, table in (("US", words.US_STATES), ("CA", words.CA_PROVINCES)):
        opts = []
        if country == "CA" and c["region:CA-*"]:
            key = words.region_key(words.ALL_CANADA, "CA")
            opts.append(f'<option value="{esc(key)}">{esc(words.region_name(words.ALL_CANADA))} '
                        f'({c["region:" + key]})</option>')
        for code, name in sorted(table.items(), key=lambda kv: kv[1]):
            n = c[f"region:{country}-{code}"]
            if n:
                opts.append(f'<option value="{country}-{code}">{esc(name)} ({n})</option>')
        groups.append(f'<optgroup label="{esc(words.COUNTRIES[country])}" data-country="{country}">{"".join(opts)}</optgroup>')
    return "".join(groups)


def finder_form(c, steps=LENGTH_STEPS):
    tier_opts = "".join(
        f'<option value="{t}">{esc(words.label(words.TIERS, t))} ({c["tier:" + t]})</option>'
        for t in ("national", "regional", "short", "deferred", "candidate") if c["tier:" + t])
    policy_opts = "".join(
        f'<option value="{p}">{esc(words.label(words.POLICIES, p))}: {esc(words.meaning(words.POLICIES, p).lower())} ({c["policy:" + p]})</option>'
        for p in ("open", "sold", "withheld", "unclear") if c["policy:" + p])
    return f"""<form class="filters" id="finder-form" role="search" aria-label="Find a trail">
  <div class="filters__search field">
    <label class="field__label" for="q">Search</label>
    <input class="input" id="q" name="q" type="search" placeholder="Name, abbreviation or creator" autocomplete="off" spellcheck="false">
  </div>
  <div class="field">
    <label class="check">
      <input type="checkbox" name="line">
      <span class="check__text">Has a downloadable track <span class="check__count">{c["line"]}</span></span>
      <span class="check__hint">GeoJSON and GPX. The other {c["record_only"]} are records only.</span>
    </label>
  </div>
  <details class="filters__more">
    <summary>Filters <span class="filters__active"></span></summary>
    <div class="filters__form">
      <fieldset class="field">
        <legend>Country</legend>
        <div class="seg">
          <label><input type="radio" name="country" value="all" checked><span>Both ({c["total"]})</span></label>
          <label><input type="radio" name="country" value="US"><span>United States ({c["country:US"]})</span></label>
          <label><input type="radio" name="country" value="CA"><span>Canada ({c["country:CA"]})</span></label>
        </div>
        <p class="field__hint">A record that crosses the border counts under both.</p>
      </fieldset>
      <div class="field">
        <label class="field__label" for="region">State, province or territory</label>
        <select class="select" id="region" name="region"><option value="">Any</option>{region_options(c)}</select>
      </div>
      <fieldset class="field field--wide">
        <legend>Length</legend>
        <div class="range">
          <label class="vh" for="min">Shortest length</label>
          <select class="select" id="min" name="min" data-length-options>{_length_options(steps, False)}</select>
          <span class="range__to" aria-hidden="true">to</span>
          <label class="vh" for="max">Longest length</label>
          <select class="select" id="max" name="max" data-length-options>{_length_options(steps, True)}</select>
        </div>
        <p class="field__hint" id="len-hint" aria-live="polite">Any length.</p>
      </fieldset>
      <fieldset class="field">
        <legend>Kind</legend>
        <label class="check">
          <input type="checkbox" name="designated" checked>
          <span class="check__text">Designated trails <span class="check__count">{c["designated"]}</span></span>
          <span class="check__hint">Designated by a land agency or a trail association</span>
        </label>
        <label class="check">
          <input type="checkbox" name="route" checked>
          <span class="check__text">Person-defined routes <span class="check__count">{c["route"]}</span></span>
          <span class="check__hint">Worked out and published by a person or a small group</span>
        </label>
        <label class="field__label field__label--sub" for="policy">Route track policy</label>
        <select class="select" id="policy" name="policy"><option value="">Any</option>{policy_opts}</select>
      </fieldset>
      <div class="field">
        <label class="field__label" for="tier">Tier</label>
        <select class="select" id="tier" name="tier"><option value="">Any</option>{tier_opts}</select>
      </div>
      <div class="field field--wide">
        <button class="button button--quiet" type="reset">Clear search and filters</button>
      </div>
    </div>
  </details>
</form>"""


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
        <span>Length<span class="list-head__scale">{"".join(ticks)}</span></span>
        <span>Track</span>
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
            </select>
          </label>"""


def key():
    return f"""<ul class="key" aria-label="Key to the list">
        <li>{common.SWATCH_LINE}Track in the dataset</li>
        <li>{common.SWATCH_NONE}Record only; the note says why</li>
        <li>Route track policy:
          {common.policy_chip("open")} {common.policy_chip("sold")} {common.policy_chip("withheld")} {common.policy_chip("unclear")}
        </li>
      </ul>"""


def results(recs=None, *, finder=False, groups=None):
    """The list of records, as every page shows it: div.results > head, key, list head, ol.entries.

    finder: the home page's list, driven by the finder form (live count, sort, empty state).
    groups: [(heading, records, extra_fn)] to list the records under level-3 headings
    (the routes page); extra_fn(rec) gives HTML placed last in each row.
    """
    if groups is None:
        groups = [(None, recs, None)]
    total = sum(len(g[1]) for g in groups)
    noun = "record" if total == 1 else "records"
    lists = ""
    for heading, items, extra_fn in groups:
        level = 4 if heading else 3
        rows = "\n".join(entry(r, level=level, extra=extra_fn(r) if extra_fn else "") for r in items)
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
        <p><strong>No records match these filters.</strong></p>
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
      {key()}
      {list_head()}{lists}{empty}
    </div>""")


def render(records, site):
    """The home page body (HTML) for every record."""
    c = counts(records)
    recs = sorted(records, key=sort_name)
    total = c["total"]
    lede = (f"A record for each of {total} long trails and routes, as a rule 50 miles (80&nbsp;km) or more: "
            "what it is, how long it is, who publishes it, and on what terms its track may be passed on. "
            "Where the terms allow, download the track as GPX or GeoJSON.")
    contribute = ""
    if site.repo_url:
        contribute = (f'<p class="hero__caveat">Something wrong, or a trail missing? '
                      f'<a href="{esc(site.correction_url())}">Report a problem</a> or '
                      f'<a href="{esc(site.new_trail_url)}">suggest a trail</a>; '
                      f'the records are text files <a href="{esc(site.repo_url)}">anyone can fix or add to</a>.</p>')
    return f"""<section class="hero" aria-labelledby="hero-title">
  <div class="container hero__inner">
    <p class="kicker">A public dataset &middot; United States and Canada</p>
    <h1 id="hero-title">{esc(site.tagline)}</h1>
    <p class="hero__lede">{lede}</p>
    <p class="hero__caveat">This is a dataset, not a navigation product. Tracks vary in quality, some trails are unfinished, and some records have no track at all; each of those says why.</p>
    {contribute}
    <p><a class="button button--primary hero__cta" href="#q">Find a trail</a></p>
    <div class="hero__counts">
      <dl class="tally">
        <div><dt>Records</dt><dd>{total}</dd></div>
        <div><dt><a href="/?kind=designated">Designated trails</a></dt><dd>{c["designated"]}</dd></div>
        <div><dt><a href="/?kind=route">Person-defined routes</a></dt><dd>{c["route"]}</dd></div>
        <div><dt>{common.SWATCH_LINE}<a href="/?line=1">With a track</a></dt><dd>{c["line"]}</dd></div>
        <div><dt>{common.SWATCH_NONE}Records only</dt><dd>{c["record_only"]}</dd></div>
      </dl>
      <div class="ratio" aria-hidden="true"><span class="ratio__line" style="--n: {c["line"]}"></span><span class="ratio__none" style="--n: {c["record_only"]}"></span></div>
    </div>
  </div>
</section>

<section class="section" aria-labelledby="map-title">
  <div class="container">
    <div class="section-head">
      <h2 id="map-title">Every track in the dataset</h2>
      <p>{c["line"]} tracks, simplified for display. Select a trail on the map for its name.</p>
    </div>
    <figure class="mapfig" data-map="overview" data-src="/data/overview.geojson"{overview_bbox(records)}>
      <div class="mapfig__frame">
        <span class="mapfig__corner mapfig__corner--nw" aria-hidden="true"></span>
        <div class="map" role="region" aria-label="Map of every track in the dataset">
          <div class="map__fallback"></div>
          <div class="map__canvas"></div>
          <p class="map__status" role="status">The map needs JavaScript. The list below has every record.</p>
        </div>
        <span class="mapfig__corner mapfig__corner--se" aria-hidden="true"></span>
      </div>
      <figcaption class="mapfig__caption">
        <ul class="legend" aria-label="Legend">
          <li>{common.SWATCH_LINE}Designated trail</li>
          <li>{common.SWATCH_ROUTE}Person-defined route</li>
        </ul>
        <p>Tracks are simplified to about 750&nbsp;m here; each keeps the credit and licence named on its page. Base map: OpenFreeMap, &copy;&nbsp;OpenMapTiles, data &copy;&nbsp;OpenStreetMap contributors.</p>
      </figcaption>
    </figure>
  </div>
</section>

<section class="section" id="finder" aria-labelledby="finder-title">
  <div class="container finder__grid">
    <div class="finder__head section-head">
      <h2 id="finder-title">Find a trail</h2>
      <p>Search, then narrow by country, region, length, kind and track</p>
    </div>
    {finder_form(c, length_steps(records))}
    {results(recs, finder=True)}
  </div>
</section>"""
