"""Region pages (/regions/, /regions/<slug>/) and the routes page (/routes/).

Both list records with home.results(), the same list the home page shows.
"""
import collections

from . import common, docs, home, words
from .markup import Markup, esc

# The /regions/ anchor and the finder's region key for records that name all of Canada.
CANADA_WIDE_ID = "canada-wide"
CANADA_WIDE_KEY = words.region_key(words.ALL_CANADA, "CA")  # "CA-*"


def region_country(code):
    return words.region_country(code) if code != words.ALL_CANADA else ""


def region_slug(code, fallback_country=""):
    return words.region_key(code, region_country(code) or fallback_country).lower()


def region_path(code, fallback_country=""):
    return f"/regions/{region_slug(code, fallback_country)}/"


def collect_regions(records):
    """slug -> {code, country, name, records}; plus Canada-wide records separately."""
    by_slug = {}
    canada_wide = []
    for r in records:
        for code in r.get("regions", []):
            if code == words.ALL_CANADA:
                canada_wide.append(r)
                continue
            country = region_country(code) or r["country"]
            slug = region_slug(code, r["country"])
            info = by_slug.setdefault(slug, {"code": code, "country": country,
                                             "name": words.region_name(code), "records": []})
            if all(x["id"] != r["id"] for x in info["records"]):
                info["records"].append(r)
    for info in by_slug.values():
        info["records"].sort(key=home.sort_name)
    canada_wide.sort(key=home.sort_name)
    return by_slug, canada_wide


def country_records(records, country):
    """Every record that touches a country: listed on one of its region pages, or Canada-wide."""
    return [r for r in records if country in common.countries(r)]


def _bbox_attr(recs):
    boxes = [r["derived"]["bbox"] for r in recs if r["derived"].get("bbox")]
    if not boxes:
        return ""
    box = [min(b[0] for b in boxes), min(b[1] for b in boxes),
           max(b[2] for b in boxes), max(b[3] for b in boxes)]
    return f' data-bbox="{",".join(f"{v:.4f}" for v in box)}"'


def _region_map(recs, title):
    ids = [r["id"] for r in recs if "line" in r["derived"]["files"]]
    if not ids:
        return ('<p class="note">No downloadable track in this region yet, so there is '
                'nothing to draw. The records below say why.</p>')
    return f"""<figure class="mapfig" data-map="overview" data-src="/data/overview.geojson" data-ids="{esc(" ".join(ids))}"{_bbox_attr(recs)}>
  <div class="mapfig__frame">
    <span class="mapfig__corner mapfig__corner--nw" aria-hidden="true"></span>
    <div class="map" role="region" aria-label="Map of tracks in {esc(title)}">
      <div class="map__fallback"></div><div class="map__canvas"></div>
      <p class="map__status" role="status">The map needs JavaScript. The list below has every record.</p>
    </div>
    <span class="mapfig__corner mapfig__corner--se" aria-hidden="true"></span>
  </div>
  <figcaption class="mapfig__caption">
    <ul class="legend" aria-label="Legend"><li>{common.SWATCH_LINE}Designated trail</li>
    <li>{common.SWATCH_ROUTE}Person-defined route</li></ul>
    <p>{len(ids)} track{"s" if len(ids) != 1 else ""} in this region, simplified for display. Select a trail on the map for its name.</p>
  </figcaption>
</figure>"""


def regions_index_page(records, site):
    by_slug, canada_wide = collect_regions(records)
    blocks = ""
    tally = '<div><dt>Records</dt><dd>' + str(len(records)) + '</dd></div>'
    for country in ("US", "CA"):
        n_country = len(country_records(records, country))
        tally += (f'<div><dt><a href="#{esc(country.lower())}">{esc(words.COUNTRIES[country])}</a></dt>'
                  f'<dd data-country-count="{esc(country)}">{n_country}</dd></div>')
        infos = sorted((i for i in by_slug.values() if i["country"] == country),
                       key=lambda i: i["name"].lower())
        rows = ""
        for info in infos:
            lines = sum(1 for r in info["records"] if common.has_line(r))
            rows += (f'<tr><td><a href="{esc(region_path(info["code"], country))}">{esc(info["name"])}</a> '
                     f'<code class="raw">{esc(info["code"])}</code></td>'
                     f'<td class="num">{len(info["records"])}</td><td class="num">{lines}</td></tr>')
        extra = ""
        if country == "CA" and canada_wide:
            links = ", ".join(f'<a href="{esc(common.trail_path(r))}">{common.name(r)}</a>' for r in canada_wide)
            extra = (f'<div class="doc-block" id="{CANADA_WIDE_ID}"><h3>All provinces and territories</h3>'
                     f'<p class="prose">These records name <em>all provinces and territories</em> rather than '
                     f'one province, so they have no single region page and are not counted under each '
                     f'province: {links}. <a href="/?region={esc(CANADA_WIDE_KEY)}">Open in the trail finder</a>.</p></div>')
        unit = "state" if country == "US" else "province or territory, or all of them"
        blocks += f"""<div class="doc-block"><h2 id="{esc(country.lower())}">{esc(words.COUNTRIES[country])}</h2>
  <p class="prose">{n_country} records name at least one {unit}. Each is counted once, whichever
  country it is filed under.</p>
  <div class="table-wrap"><table><thead><tr><th scope="col">State, province or territory</th><th scope="col">Records</th><th scope="col">With a downloadable track</th></tr></thead>
  <tbody>{rows}</tbody></table></div>{extra}</div>"""
    body = f"""<div class="page-head"><div class="container"><header class="titleblock">
  <div class="titleblock__text"><p class="kicker">Browse</p><h1>Regions</h1>
  <p class="page-head__lede">Every state, province and territory a record names. A record that
  crosses several regions appears on each region's page, under the country that region belongs to.</p>
  </div></header>
  <dl class="tally">{tally}</dl></div></div>
<div class="container section">{blocks}</div>"""
    return "Regions", "Long trails by state, province and territory, with counts of records and tracks.", Markup(body)


def region_page(slug, records, site):
    by_slug, _ = collect_regions(records)
    info = by_slug[slug]
    recs = info["records"]
    lines = sum(1 for r in recs if common.has_line(r))
    key = words.region_key(info["code"], info["country"])
    same = sorted((s for s, i in by_slug.items() if i["country"] == info["country"]),
                  key=lambda s: by_slug[s]["name"].lower())
    idx = same.index(slug)
    neighbours = []
    if idx > 0:
        p = by_slug[same[idx - 1]]
        neighbours.append(f'<a href="{esc(region_path(p["code"], p["country"]))}">← {esc(p["name"])}</a>')
    if idx + 1 < len(same):
        n = by_slug[same[idx + 1]]
        neighbours.append(f'<a href="{esc(region_path(n["code"], n["country"]))}">{esc(n["name"])} →</a>')
    nav = " · ".join(neighbours)
    with_line = (f'<a href="/?region={esc(key)}&amp;line=1">With a track</a>' if lines else "With a track")
    body = f"""<div class="page-head"><div class="container">
  <nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="/regions/">Regions</a></li>
  <li><a href="/regions/#{esc(info["country"].lower())}">{esc(words.COUNTRIES[info["country"]])}</a></li>
  <li aria-current="page">{esc(info["name"])}</li></ol></nav>
  <header class="titleblock"><div class="titleblock__text">
  <p class="kicker">{esc(words.COUNTRIES[info["country"]])} · {esc(info["code"])}</p>
  <h1>{esc(info["name"])}</h1>
  <p class="page-head__lede">{len(recs)} record{"s" if len(recs) != 1 else ""}, {lines} with a downloadable track.</p>
  </div></header>
  <dl class="tally"><div><dt>Records</dt><dd>{len(recs)}</dd></div>
  <div><dt>{common.SWATCH_LINE}{with_line}</dt><dd>{lines}</dd></div>
  <div><dt>{common.SWATCH_NONE}Records only</dt><dd>{len(recs) - lines}</dd></div></dl>
</div></div>
<div class="container section">
  <div class="section-head"><h2>Tracks in {esc(info["name"])}</h2><p>Only tracks in this region are drawn.</p></div>
  {_region_map(recs, info["name"])}
</div>
<div class="container section">
  <div class="section-head"><h2>Trails and routes in {esc(info["name"])}</h2>
  <p><a href="/?region={esc(key)}">Open these in the trail finder</a> to search and filter them.</p></div>
  {home.results(recs)}
  <nav class="region-nav" aria-label="Neighbouring regions"><a href="/regions/">All regions</a>{f' · {nav}' if nav else ""}</nav>
</div>"""
    title = info["name"]
    return title, f"{len(recs)} long trails and routes in {info['name']}, {words.COUNTRIES[info['country']]}.", Markup(body), bool(lines)


def route_guides(rec):
    """A route's guides, placed last in its list row on /routes/."""
    items = ""
    for g in rec.get("guide", []):
        access = g.get("access", "")
        price = ""
        if g.get("price"):
            price = f' · {esc(g["price"])}'
            if g.get("price_checked"):
                price += f' (read {esc(g["price_checked"])})'
        fmt = f' · {esc(g["format"])}' if g.get("format") else ""
        items += (f'<li><a href="{esc(g.get("url", ""))}">{esc(g.get("title", ""))}</a>'
                  f' <span class="access access--{esc(access)}">{esc(words.ACCESS.get(access, access))}</span>'
                  f'{fmt}{price}</li>')
    if not items:
        return ""
    return (f'\n  <div class="entry__guides"><p class="route-item__guides-label">Guides</p>'
            f'<ul class="route-guides">{items}</ul></div>')


def routes_page(records, site, repo_root):
    """(title, description, body) for /routes/."""
    readme = docs.sections_map(docs.read_doc(repo_root, "README.md"))
    inc = readme.get("Inclusion rule", "")
    paras = [p for p in inc.split("\n\n") if "Person-defined rout" in p and "at the same 50-mile floor" in p]
    bullets = [p for p in inc.split("\n\n") if "The creator sells" in p]
    explainer = "\n\n".join(paras + bullets) or readme.get("Person-defined routes", "")
    intro = docs.render_doc("## What a person-defined route is\n\n" + explainer, site)

    policy_items = ""
    for key in ("open", "sold", "withheld", "unclear"):
        lab, short, rule = words.POLICIES[key]
        policy_items += f'<li>{common.policy_chip(key)}<span>{esc(short)}. {esc(rule)}</span></li>'
    policies = Markup(f'<ol class="policy-scale" aria-label="The four track policies">{policy_items}</ol>')

    routes = [r for r in records if common.is_route(r)]
    by_creator = collections.defaultdict(list)
    for r in routes:
        by_creator[r.get("route", {}).get("creator", "") or "Unknown"].append(r)
    groups = [(esc(creator), sorted(by_creator[creator], key=home.sort_name), route_guides)
              for creator in sorted(by_creator, key=str.lower)]

    body = f"""<div class="page-head"><div class="container"><header class="titleblock">
  <div class="titleblock__text"><p class="kicker">Person-defined routes</p><h1>Routes</h1>
  <p class="page-head__lede">{len(routes)} routes worked out and published by a person or a small group.</p>
  </div></header></div></div>
<div class="container section"><div class="prose doc">{intro}</div>
<h2 class="doc-block">The four track policies</h2>{policies}
<p class="prose"><a href="/?kind=route">See the routes in the trail finder</a>, or read a route below.</p></div>
<div class="container section"><div class="section-head"><h2>Routes by creator</h2>
<p>Each route links to its record; its guides link out to the creator's or publisher's page.</p></div>
{home.results(groups=groups)}</div>"""
    return "Routes", f"{len(routes)} person-defined routes by creator, with track policies and guides.", Markup(body)
