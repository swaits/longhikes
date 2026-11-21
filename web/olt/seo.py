"""Sitemap, robots.txt, and the JSON-LD (schema.org) that describes each page.

Everything here is read from the records and from web/site.toml. No trail is
named in this file: a new record gets its markup from its own fields.

Types, and why (checked against schema.org and Google Search Central, 2026-11):

    Trail page   ItemPage, whose mainEntity is a Place that is also a
                 TouristAttraction. schema.org has no type for a trail
                 (schema.org/Trail is a 404), and Google has no trail or place
                 feature, so this markup is for search and assistants that read
                 entities, not for a rich result. A trail is a place a visitor
                 goes to, so Place is true of it; TouristAttraction is a
                 subtype of Place that "in principle any Thing can be". A route
                 is the same kind of place; the page says it is a route by its
                 author in additionalProperty. A route's author is free text in
                 the record (a person, two people, an association), so it is
                 never typed as Person or Organization.
    Lists, places  CollectionPage whose mainEntity is an ItemList of the trails.
    Every page   BreadcrumbList (a Google feature), read from the breadcrumb
                 the page shows, so the two cannot differ.
    Home         WebSite and Organization. A one-person open data project is
                 not a legal entity, but Organization is the type Google
                 documents for the publisher of a site; it carries only what
                 site.toml holds. No SearchAction: Google retired the sitelinks
                 search box.
    /data/       Dataset (a Google feature), with its downloads.

dateModified is the newest date the record shows for itself (modified()),
never the build date, so a page's date moves only when its content does.
"""
import html
import os
import re
from html.parser import HTMLParser

from . import common, docs, facets, hike, words

CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"

# Media types of the files under /data/, which docs.BULK_FILES describes.
MEDIA_TYPES = {
    "trails.csv": "text/csv",
    "trails.json": "application/json",
    "index.geojson": "application/geo+json",
    "overview.geojson": "application/geo+json",
    "all-gpx.zip": "application/zip",
    "all-geojson.zip": "application/zip",
}


def distribution():
    """[(name, media type, what it holds)] for each bulk file, as the data page lists them."""
    return [(name, MEDIA_TYPES[name], what) for name, what, _ in docs.BULK_FILES]


# What the dataset records for each trail (docs/schema.md), as variableMeasured.
VARIABLES = (
    ("length_km", "End-to-end length of the trail's canonical path, as its holder or author states it", "KMT"),
    ("system_km", "The larger figure the holder publishes for the whole system or a planned total, where there is one", "KMT"),
    ("built_km", "The built length of an unfinished trail, as its holder states it", "KMT"),
    ("measured_km", "Length measured from the track, in kilometres", "KMT"),
    ("difference_percent", "Measured length against the published length, in per cent", "P1"),
    ("ascent_m", "Total climbing along the track, computed from an elevation model", "MTR"),
    ("days", "Usual time to walk the whole trail, as a source states it", "DAY"),
    ("regions", "States and provinces crossed", ""),
    ("terrain", "Main kinds of country", ""),
    ("shape", "End to end, loop or network", ""),
    ("source.licence", "Licence of the track, as its source states it", ""),
    ("verification.date", "Date the track was last checked", ""),
)


# Dates -----------------------------------------------------------------------

def record_dates(rec):
    """Every date a record gives for its own checks and changes, as YYYY-MM-DD strings."""
    found = [rec.get("verification", {}).get("date"), hike.table(rec).get("checked"),
             rec.get("source", {}).get("source_checked")]
    found += [e.get("date") for e in rec.get("history", []) if isinstance(e, dict)]
    return [str(d) for d in found if d and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(d))]


def modified(rec):
    """The newest of the record's check dates and its newest history entry, or ""."""
    return max(record_dates(rec), default="")


def checked(rec):
    """The newest date the record itself was checked on: its verification, its [hike] facts or its
    source read. This is the date a trail page shows as "Last checked" and the page's
    dateModified. A history entry is a change or a request, not a check, so it is left out."""
    found = [rec.get("verification", {}).get("date"), hike.table(rec).get("checked"),
             rec.get("source", {}).get("source_checked")]
    return max((str(d) for d in found if d and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(d))), default="")


def newest(recs):
    """The newest modified() among records: the date of a page that lists them."""
    return max((modified(r) for r in recs), default="")


def earliest(recs):
    """The oldest date any record gives: when the first record was made."""
    return min((d for r in recs for d in record_dates(r)), default="")


# JSON-LD ---------------------------------------------------------------------

def url_of(site, path):
    """Absolute URL of a site path, or the path itself when site.toml has no base_url."""
    return site.canonical(path) or path


def country_names(records):
    """The countries the records cover, the United States first, as a phrase for a sentence:
    "the United States and Canada"."""
    codes = sorted({c for r in records for c in common.countries(r)}, key=lambda c: (c != "US", c))
    return words.join_names(("the " if c == "US" else "") + words.COUNTRIES[c] for c in codes if c in words.COUNTRIES)


def breadcrumb_id(site, path):
    return url_of(site, path) + "#breadcrumb"


def website_ref(site):
    return {"@type": "WebSite", "@id": url_of(site, "/") + "#website", "name": site.name,
            "url": url_of(site, "/")}


def _clean(obj):
    """Drop empty values, so a node holds only what the record has."""
    if isinstance(obj, dict):
        out = {k: _clean(v) for k, v in obj.items()}
        return {k: v for k, v in out.items() if v not in ("", None, [], {})}
    if isinstance(obj, list):
        return [v for v in (_clean(x) for x in obj) if v not in ("", None, [], {})]
    return obj


def _pv(name, value, unit_code="", unit_text="", **extra):
    node = {"@type": "PropertyValue", "name": name, "value": value}
    if unit_code:
        node["unitCode"] = unit_code
    if unit_text:
        node["unitText"] = unit_text
    node.update(extra)
    return node


class _Crumbs(HTMLParser):
    """The (text, href) items of the first <nav class="breadcrumb"> in a page body."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items = []
        self._in_nav = False
        self._done = False
        self._cur = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "nav" and not self._done and "breadcrumb" in (a.get("class") or "").split():
            self._in_nav = True
        elif self._in_nav and tag == "li":
            self._cur = {"text": "", "href": ""}
        elif self._in_nav and tag == "a" and self._cur is not None and not self._cur["href"]:
            self._cur["href"] = a.get("href") or ""

    def handle_endtag(self, tag):
        if not self._in_nav:
            return
        if tag == "li" and self._cur is not None:
            self._cur["text"] = " ".join(self._cur["text"].split())
            self.items.append((self._cur["text"], self._cur["href"]))
            self._cur = None
        elif tag == "nav":
            self._in_nav = False
            self._done = True

    def handle_data(self, data):
        if self._cur is not None:
            self._cur["text"] += data


def visible_breadcrumbs(body):
    """[(text, href)] of the breadcrumb a page body shows; the last item has no href."""
    parser = _Crumbs()
    text = str(body)
    # The breadcrumb is near the top of a body: feed it in pieces and stop once its nav has
    # closed, rather than parsing a whole page of rows.
    for i in range(0, len(text), 8192):
        parser.feed(text[i:i + 8192])
        if parser._done:
            break
    return parser.items


def breadcrumb_node(body, site, path, node_id=""):
    """A BreadcrumbList equal to the breadcrumb the body shows, ending at the page itself.
    None when the page has none (the home page) or fewer than two items."""
    crumbs = visible_breadcrumbs(body)
    if not crumbs:
        return None
    items = []
    for i, (text, href) in enumerate(crumbs, 1):
        href = href or path  # the current page: its own address
        items.append({"@type": "ListItem", "position": i, "name": text,
                      "item": url_of(site, href) if href.startswith("/") else href})
    if len(items) < 2:
        return None
    node = {"@type": "BreadcrumbList", "itemListElement": items}
    if node_id:
        node["@id"] = node_id
    return node


def _extent(rec):
    """geo for a Place: a GeoShape box over the track, else over the two sketch points, else
    the one point on file. Coordinates come from the record or its track, never made up."""
    box = rec.get("derived", {}).get("bbox") or rec.get("derived", {}).get("map_bbox")
    if not box:
        pts = [p for p in (hike.start_point(rec), hike.end_point(rec)) if p]  # the record's own points, map or no map
        if len(pts) == 1:
            return {"@type": "GeoCoordinates", "longitude": pts[0][0], "latitude": pts[0][1]}
        if pts:
            box = hike.sketch_bbox(pts)
    if not box:
        return None
    w, s, e, n = box
    return {"@type": "GeoShape", "box": f"{s} {w} {n} {e}"}


def _same_as(rec):
    urls = []
    official = hike.table(rec).get("official_url")
    if official:
        urls.append(official)
    relation = rec.get("osm", {}).get("relation")
    if relation:
        urls.append(f"https://www.openstreetmap.org/relation/{relation}")
    for link in rec.get("link", []):
        host = re.sub(r"^https?://([^/]+).*$", r"\1", link.get("url", "")).lower()
        if host.endswith(("wikipedia.org", "wikidata.org")):
            urls.append(link["url"])
    return list(dict.fromkeys(urls))


def _contained_in(rec):
    out = []
    for key in facets.place_keys(rec):
        if key == facets.ACROSS_CANADA:
            out.append({"@type": "Country", "name": words.COUNTRIES["CA"]})
        else:
            out.append({"@type": "AdministrativeArea", "name": facets.place_name(key),
                        "containedInPlace": {"@type": "Country",
                                             "name": words.COUNTRIES.get(key.split("-", 1)[0], "")}})
    return out


def _properties(rec):
    h = hike.table(rec)
    mi = rec["derived"]["length_mi"]
    props = [
        _pv("Published length", mi, "SMI", "miles", description=rec.get("length_note", "")),
        _pv("Published length", rec["length_km"], "KMT", "kilometres"),
    ]
    if rec.get("system_km"):
        # The holder's larger figure: its own labelled value, never the trail's length.
        note = str(rec.get("system_note", "")).strip().rstrip(".")
        props.append(_pv("Whole system length", round(words.km_to_mi(rec["system_km"])), "SMI", "miles",
                         description=f"Counting {note}"))
        props.append(_pv("Whole system length", rec["system_km"], "KMT", "kilometres",
                         description=f"Counting {note}"))
    if rec.get("built_km"):
        props.append(_pv("Built length", round(words.km_to_mi(rec["built_km"])), "SMI", "miles"))
        props.append(_pv("Built length", rec["built_km"], "KMT", "kilometres"))
    days = h.get("days")
    if isinstance(days, list) and len(days) == 2:
        props.append(_pv("Usual time to walk it all", f"{days[0]} to {days[1]} days", "DAY", "days",
                         minValue=days[0], maxValue=days[1]))
    elif isinstance(days, int):
        props.append(_pv("Usual time to walk it all", days, "DAY", "days"))
    if h.get("high_point_m"):
        props.append(_pv("Highest point", h["high_point_m"], "MTR", "metres", description=h.get("high_point", "")))
    elif h.get("high_point"):
        props.append(_pv("Highest point", h["high_point"]))
    shape = facets.shape(rec)
    if shape:
        props.append(_pv("Shape", facets.SHAPES[shape]))
    props.append(_pv("Start", h.get("start", "")) if h.get("start") else None)
    props.append(_pv("End", h.get("end", "")) if h.get("end") else None)
    # Only a season a page states: an estimate is not a fact about the trail to hand to a search engine.
    props.append(_pv("Usual season", h["season"]) if h.get("season") and not facets.season_estimated(rec) else None)
    if common.is_route(rec):
        route = rec.get("route", {})
        props.append(_pv("Route author", route["creator"]) if route.get("creator") else None)
        props.append(_pv("First published", route["year"]) if route.get("year") else None)
    elif rec.get("designation"):
        props.append(_pv("Designation", rec["designation"]))
    return [p for p in props if p]


def _downloads(rec, site):
    """The main track files, as DataDownload nodes with the track's own terms."""
    src = rec.get("source", {})
    licence = words.LICENCE_URLS.get(src.get("licence", ""), "")
    types = {"GPX": "application/gpx+xml", "GeoJSON": "application/geo+json"}
    out = []
    for d in rec.get("derived", {}).get("downloads", []):
        if d.get("role") != "main":
            continue
        node = {"@type": "DataDownload", "name": f"{rec['name']}: track as {d['format']}",
                "encodingFormat": types.get(d["format"], ""),
                "contentUrl": url_of(site, f"/trails/{rec['id']}/{d['file']}"),
                "isAccessibleForFree": True, "creditText": src.get("attribution", "")}
        if licence:
            node["license"] = licence
        else:  # a licence with no page of its own: the trail page states the terms
            node["usageInfo"] = url_of(site, f"/trails/{rec['id']}/#download")
        out.append(node)
    return out


def _guides(rec):
    """A route's guides (and any other trail's own guide) as CreativeWork nodes."""
    return [{"@type": "CreativeWork", "name": g.get("title", ""), "url": g.get("url", ""),
             "isAccessibleForFree": g.get("access") == "free" if g.get("access") else None}
            for g in rec.get("guide", [])]


def place_node(rec, site):
    """The trail or route as a Place and TouristAttraction, from the record alone."""
    page = url_of(site, f"/trails/{rec['id']}/")
    names = [n for n in (rec.get("common_name"), rec.get("short_name")) if n and n != rec["name"]]
    node = {
        "@type": ["Place", "TouristAttraction"],
        "@id": page + "#trail",
        "name": rec["name"],
        "alternateName": list(dict.fromkeys(names)),
        "description": hike.summary(rec),
        "url": page,
        "sameAs": _same_as(rec),
        "containedInPlace": _contained_in(rec),
        "geo": _extent(rec),
        "additionalProperty": _properties(rec),
        "subjectOf": _downloads(rec, site) + _guides(rec),
    }
    return _clean(node)


def page_node(kind, path, site, *, name, description="", date="", main=None, breadcrumb_id=""):
    node = {"@type": kind, "@id": url_of(site, path) + "#webpage", "url": url_of(site, path),
            "name": name, "description": description, "inLanguage": "en", "dateModified": date,
            "isPartOf": website_ref(site) if path != "/" else None,
            "breadcrumb": {"@id": breadcrumb_id} if breadcrumb_id else None,
            "mainEntity": main}
    return _clean(node)


def trail_jsonld(rec, site, *, title, description):
    """The nodes for one trail page: its ItemPage and its Place. layout.layout adds the breadcrumb."""
    path = f"/trails/{rec['id']}/"
    place = place_node(rec, site)
    return [page_node("ItemPage", path, site, name=title, description=description, date=checked(rec),
                      main={"@id": place["@id"]}, breadcrumb_id=breadcrumb_id(site, path)), place]


def collection_jsonld(path, site, *, title, description, recs, date=""):
    """CollectionPage and its ItemList for a list or a place: the trails the page lists."""
    items = [{"@type": "ListItem", "position": i, "name": r["name"], "url": url_of(site, common.trail_path(r))}
             for i, r in enumerate(recs, 1)]
    listing = {"@type": "ItemList", "numberOfItems": len(items), "itemListElement": items}
    return [page_node("CollectionPage", path, site, name=title, description=description,
                      date=date or newest(recs), main=listing,
                      breadcrumb_id=breadcrumb_id(site, path))]


def glossary_jsonld(path, site, *, title, description, terms, date=""):
    """The glossary page: a WebPage whose main entity is a DefinedTermSet of the terms it defines."""
    items = [{"@type": "DefinedTerm", "name": t["term"], "description": t["definition"],
              "url": url_of(site, path) + "#" + t["id"], "inDefinedTermSet": {"@id": url_of(site, path) + "#terms"}}
             for t in terms]
    main = {"@type": "DefinedTermSet", "@id": url_of(site, path) + "#terms", "name": title, "hasDefinedTerm": items}
    return [page_node("WebPage", path, site, name=title, description=description, date=date, main=main,
                      breadcrumb_id=breadcrumb_id(site, path))]


def article_jsonld(path, site, *, title, description, date=""):
    """A plain page of text and tables (the method page): a WebPage."""
    return [page_node("WebPage", path, site, name=title, description=description, date=date,
                      breadcrumb_id=breadcrumb_id(site, path))]


def person_node(site):
    """The maintainer, as site.toml names them: a Person with their profile page as `sameAs`.
    {} when site.toml names no maintainer. Name and profile page only."""
    if not site.maintainer_name:
        return {}
    node = {"@type": "Person", "@id": url_of(site, "/") + "#maintainer", "name": site.maintainer_name}
    if site.maintainer_url:
        node["url"] = site.maintainer_url
        node["sameAs"] = [site.maintainer_url]
    return _clean(node)


def organization_node(site):
    """The publisher: name, address, logo, the repository and contact site.toml holds, and
    the maintainer as its founder (schema.org's property for the person behind a small organisation)."""
    node = {"@type": "Organization", "@id": url_of(site, "/") + "#organization", "name": site.name,
            "url": url_of(site, "/"), "description": site.tagline,
            "logo": url_of(site, "/assets/apple-touch-icon.png"),
            "sameAs": [site.repo_url] if site.repo_url else [],
            "founder": person_node(site)}
    contact = site.contact
    if contact.startswith("mailto:"):
        node["email"] = contact[len("mailto:"):]
    elif contact:
        node["contactPoint"] = {"@type": "ContactPoint", "url": contact, "contactType": "customer support"}
    return _clean(node)


def home_jsonld(site):
    """WebSite and Organization for the home page."""
    org = organization_node(site)
    web = {"@type": "WebSite", "@id": url_of(site, "/") + "#website", "name": site.name,
           "url": url_of(site, "/"), "description": site.tagline, "inLanguage": "en",
           "publisher": {"@id": org["@id"]}}
    return [web, org]


def dataset_jsonld(records, site, *, version=""):
    """The Dataset for /data/: what it holds, who made it, its terms, and every download."""
    dist = []
    for name, fmt, what in distribution():
        node = {"@type": "DataDownload", "name": name, "description": what, "encodingFormat": fmt,
                "contentUrl": url_of(site, f"/data/{name}")}
        dist.append(node)
    codes = sorted({c for r in records for c in common.countries(r)}, key=lambda c: (c != "US", c))
    countries = [words.COUNTRIES[c] for c in codes if c in words.COUNTRIES]
    n_tracks = sum(1 for r in records if common.has_line(r))
    boxes = [r["derived"]["bbox"] for r in records if r.get("derived", {}).get("bbox")]
    spatial = {"@type": "Place", "name": words.join_names(countries)}
    if boxes:
        s, w = min(b[1] for b in boxes), min(b[0] for b in boxes)
        n, e = max(b[3] for b in boxes), max(b[2] for b in boxes)
        spatial["geo"] = {"@type": "GeoShape", "box": f"{s} {w} {n} {e}"}
    first, last = earliest(records), newest(records)
    lead = site.tagline.split(",")[0]
    publisher = organization_node(site)
    obj = {
        "@type": "Dataset",
        "@id": url_of(site, "/data/") + "#dataset",
        "name": f"{site.name}: {lead}",
        "description": (
            f"{len(records)} records of long-distance hiking trails and routes in {country_names(records)}. "
            f"Each record gives the trail's length, the places it crosses, where to read more about it and a "
            f"source for every fact; {n_tracks} also have a track, as GPX and GeoJSON. The records and the "
            f"compiled index are public domain (CC0 1.0). Each track keeps the licence of its source, named "
            f"in its record and on its trail page."),
        "url": url_of(site, "/data/"),
        "license": CC0,
        "isAccessibleForFree": True,
        "keywords": ["long-distance hiking trails", "hiking", "backpacking", "thru-hiking", "GPX", "GeoJSON",
                     "trail length", "open data"] + countries,
        "creator": person_node(site) or publisher,
        "maintainer": person_node(site),
        "publisher": publisher,
        "sameAs": site.repo_url,
        "spatialCoverage": spatial,
        "temporalCoverage": f"{first}/{last}" if first and last else "",
        "dateModified": last,
        "datePublished": first,
        "version": version,
        "measurementTechnique": (
            "Each track's length is measured along the track and compared with the length the trail's "
            "holder publishes. Climbing is computed from the track and an open elevation model."),
        "variableMeasured": [{"@type": "PropertyValue", "name": name, "description": what, "unitCode": unit}
                             for name, what, unit in VARIABLES],
        "distribution": dist,
    }
    return _clean(obj)


# llms.txt ---------------------------------------------------------------------

def llms_txt(records, site, version=""):
    """/llms.txt in the llmstxt.org shape: what the site is, its licence, and where the
    bulk files and the per-trail files are. Google says it does not use the file for
    Search, so this is for assistants and tools that fetch the data. It carries what
    /data/ says in tables, as plain links, and lists no trail (trails.json does)."""
    n_tracks = sum(1 for r in records if common.has_line(r))
    u = lambda path: url_of(site, path)  # noqa: E731
    lines = [
        f"# {site.name}", "",
        f"> {site.tagline}. {len(records)} records, {n_tracks} with a track. Every fact in a record "
        f"names the page it was read on.", "",
        "The records and the compiled index are public domain (CC0 1.0). Each track keeps the licence "
        "of its source, named in its record, on its trail page and in its release.txt. Trail logos "
        "belong to their holders. The data is not for navigation.", "",
        "## Bulk data", "",
    ]
    for name, kind, what in distribution():
        lines.append(f"- [{name}]({u('/data/' + name)}): {what} ({kind})")
    lines += ["", "## One trail", "",
              f"- A trail's page is {u('/trails/')}<id>/ . Its files sit beside it, named by the same id.",
              f"- {u('/trails/')}<id>/trail.toml: the record itself, with its sources and licence.",
              f"- {u('/trails/')}<id>/<id>.gpx and <id>.geojson: the main track, where the record includes one.",
              f"- {u('/trails/')}<id>/release.txt: the source, licence and date of the track.",
              "- The ids are the `id` column of trails.csv.", "",
              "## About the data", "",
              f"- [Data and downloads]({u('/data/')}): every file, and every licence.",
              f"- [Record schema]({u('/data/schema/')}): what each field of a record means.",
              f"- [Sources and their terms]({u('/sources/')}): who publishes each track, and on what terms.",
              f"- [Considered and left out]({u('/left-out/')}): trails looked at and not included, with the reason.",
              f"- [Changelog]({u('/data/changelog/')}) and its [Atom feed]({u('/feed.xml')})"
              + (f"; the latest release is dated {version}" if version else "") + ".",
              f"- [Source repository and issue tracker]({site.repo_url})" if site.repo_url else None]
    return "\n".join(x for x in lines if x is not None) + "\n"


# Sitemap and robots -----------------------------------------------------------

def sitemap_xml(paths, site, lastmod=None):
    """sitemap.xml text for site paths; caller checks site.base_url is set.

    lastmod: {path: YYYY-MM-DD}. A path with no date gets no <lastmod>: a date
    that is not the page's own is worse than none."""
    lastmod = lastmod or {}
    rows = []
    for p in paths:
        stamp = f"<lastmod>{lastmod[p]}</lastmod>" if lastmod.get(p) else ""
        rows.append(f"  <url><loc>{html.escape(site.canonical(p), quote=True)}</loc>{stamp}</url>\n")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{''.join(rows)}</urlset>\n")


def robots_txt(site):
    lines = ["User-agent: *", "Allow: /", ""]
    if site.base_url:
        lines.append(f"Sitemap: {site.canonical('/sitemap.xml')}")
    return "\n".join(lines).rstrip() + "\n"


def write_seo_files(out_dir, paths, site, lastmod=None):
    """Write robots.txt always and sitemap.xml only with a base_url."""
    with open(os.path.join(out_dir, "robots.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(robots_txt(site))
    sitemap = os.path.join(out_dir, "sitemap.xml")
    if site.base_url:
        with open(sitemap, "w", encoding="utf-8", newline="\n") as f:
            f.write(sitemap_xml(paths, site, lastmod))
    elif os.path.isfile(sitemap):
        os.remove(sitemap)  # a stale sitemap with wrong URLs is worse than none


def all_paths(records, region_paths, extra_paths=()):
    """Every indexable page path, in nav order then record pages. extra_paths: the view pages
    (tables, authors, glossary and the rest) that pages.render_site builds."""
    paths = ["/", "/regions/"] + list(region_paths) + [
        "/routes/", "/sources/", "/logos/", "/about/", "/data/",
        "/data/schema/", "/data/changelog/", "/left-out/"] + list(extra_paths)
    paths += [common.trail_path(r) for r in sorted(records, key=lambda r: r["id"])]
    return paths
