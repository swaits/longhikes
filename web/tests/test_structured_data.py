"""Tests for the machine-readable side of the site: JSON-LD, social cards, the sitemap's dates,
robots headers, the 404, the Atom feed, llms.txt and the favicon.

The JSON-LD is checked against the properties schema.org and Google Search Central document
for each type (REQUIRED below, read 2026-11); Google's Rich Results Test itself cannot be run
here. The site is built into web/.cache/test-site, as the other page tests do.
"""
import html
import json
import os
import re
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)

import serve  # noqa: E402
from olt import browse, cards, common, docs, feed, records, regions, seo, site, thumbs  # noqa: E402

OUT = os.path.join(WEB, ".cache", "test-site")
SITE = site.load()
BASE = SITE.base_url

# The properties each type must carry: Google's required ones where it has a feature
# (BreadcrumbList, ListItem, Dataset), and the ones that make the node say what it is otherwise.
REQUIRED = {
    "ItemPage": ("@id", "url", "name", "mainEntity", "dateModified"),
    "CollectionPage": ("@id", "url", "name", "mainEntity", "dateModified"),
    "Place": ("name",),
    "TouristAttraction": ("@id", "name", "url", "additionalProperty"),  # a trail or route
    "ItemList": ("itemListElement", "numberOfItems"),
    "BreadcrumbList": ("itemListElement",),
    "ListItem": ("position", "name"),
    "WebSite": ("name", "url"),
    "Organization": ("name", "url", "logo"),
    "Dataset": ("name", "description", "license", "creator", "distribution", "keywords",
                "spatialCoverage", "temporalCoverage", "dateModified", "version", "isAccessibleForFree",
                "variableMeasured", "measurementTechnique"),
    "DataDownload": ("contentUrl", "encodingFormat"),
    "PropertyValue": ("name",),
}
# Things a page about a trail must not claim: the dataset holds none of them.
FORBIDDEN = {"aggregateRating", "review", "reviews", "openingHours", "openingHoursSpecification",
             "priceRange", "offers", "price", "telephone", "ratingValue", "potentialAction"}


def missing(node):
    """The required properties a node lacks, by its type; ListItem needs item or url as well."""
    types = node.get("@type")
    types = types if isinstance(types, list) else [types]
    out = []
    for t in types:
        out += [k for k in REQUIRED.get(t, ()) if node.get(k) in (None, "", [], {})]
        if t == "ListItem" and not (node.get("item") or node.get("url")):
            out.append("item")
        if t == "Dataset" and "description" in node and not 50 <= len(node["description"]) <= 5000:
            out.append("description (50 to 5000 characters)")
    return out


def read(rel):
    with open(os.path.join(OUT, *rel.split("/")), encoding="utf-8") as f:
        return f.read()


def ld_blocks(doc):
    """The raw text of every JSON-LD script in an HTML document."""
    return re.findall(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S)


def nodes_of(doc):
    """Every JSON-LD node on a page, flattened out of any @graph."""
    out = []
    for raw in ld_blocks(doc):
        obj = json.loads(raw)
        out += obj["@graph"] if "@graph" in obj else [obj]
    return out


def walk(obj):
    """Every dict inside a JSON-LD value."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)


def meta(doc, key, attr="property"):
    m = re.search(rf'<meta {attr}="{re.escape(key)}" content="([^"]*)"', doc)
    return html.unescape(m.group(1)) if m else None


def page_paths():
    out = []
    for base, _, names in os.walk(OUT):
        for n in names:
            if n.endswith(".html"):
                out.append(os.path.relpath(os.path.join(base, n), OUT).replace(os.sep, "/"))
    return sorted(out)


def visible_crumbs(doc):
    """(text, href) from the breadcrumb a page shows, read with a regular expression
    so that it does not share code with the markup under test."""
    m = re.search(r'<nav class="breadcrumb"[^>]*>(.*?)</nav>', doc, re.S)
    if not m:
        return []
    items = []
    for li in re.findall(r"<li[^>]*>(.*?)</li>", m.group(1), re.S):
        href = re.search(r'href="([^"]*)"', li)
        items.append((" ".join(html.unescape(re.sub(r"<[^>]+>", "", li)).split()), href.group(1) if href else ""))
    return items


def setUpModule():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    subprocess.run([sys.executable, os.path.join(WEB, "build.py"), "--out", OUT],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class RequiredPropertiesTest(unittest.TestCase):
    """The checker itself: it must fail on a node that lacks what its type needs."""

    def test_missing_properties_are_found(self):
        self.assertEqual(missing({"@type": ["Place", "TouristAttraction"], "name": "X", "url": "u", "@id": "i"}),
                         ["additionalProperty"])
        self.assertEqual(missing({"@type": "Place"}), ["name"])
        self.assertIn("name", missing({"@type": "BreadcrumbList", "itemListElement": []}) + ["name"])
        self.assertEqual(missing({"@type": "BreadcrumbList"}), ["itemListElement"])
        self.assertEqual(missing({"@type": "ListItem", "position": 1, "name": "A"}), ["item"])
        self.assertEqual(missing({"@type": "ListItem", "position": 1, "name": "A", "item": "https://x/"}), [])
        self.assertIn("contentUrl", missing({"@type": "DataDownload", "encodingFormat": "text/csv"}))
        self.assertTrue(missing({"@type": "Dataset", "name": "n", "description": "too short"}))

    def test_a_trail_without_a_name_would_fail(self):
        rec = records.load_record(ROOT, "long-trail")
        rec["derived"]["downloads"] = []
        node = seo.place_node(rec, SITE)
        self.assertEqual(missing(node), [])
        node.pop("additionalProperty")
        self.assertEqual(missing(node), ["additionalProperty"])


class JsonLdTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = records.load_records(ROOT)
        cls.pages = {p: read(p) for p in page_paths()}

    def test_every_block_parses_and_is_escaped(self):
        seen = 0
        for path, doc in self.pages.items():
            for raw in ld_blocks(doc):
                seen += 1
                obj = json.loads(raw)
                self.assertEqual(obj["@context"], "https://schema.org", path)
                self.assertNotRegex(raw, r"[<>&]", f"{path}: unescaped character inside JSON-LD")
        self.assertGreater(seen, 280)

    def test_blocks_are_data_blocks_the_policy_allows(self):
        """application/ld+json is not script: the browser does not run it, so script-src 'self'
        covers every page and nothing here needs a looser policy."""
        rules = serve.parse_headers(os.path.join(OUT, "_headers"))
        csp = next(v for pat, hs in rules if pat.match("/") for k, v in hs if k.lower() == "content-security-policy")
        script_src = re.search(r"script-src ([^;]*)", csp).group(1).split()
        self.assertEqual(script_src, ["'self'"])
        self.assertNotIn("unsafe-inline", csp.replace("style-src-attr 'unsafe-inline'", ""))
        for path, doc in self.pages.items():
            self.assertNotRegex(doc, r'<script type="application/ld\+json"[^>]*\ssrc=', path)

    def test_every_node_has_what_its_type_requires_and_nothing_forbidden(self):
        for path, doc in self.pages.items():
            for top in nodes_of(doc):
                for node in walk(top):
                    if "@type" in node:
                        self.assertEqual(missing(node), [], f"{path}: {node.get('@type')}")
                    self.assertFalse(FORBIDDEN & set(node), f"{path}: {FORBIDDEN & set(node)}")

    def test_204_trail_pages_carry_a_place(self):
        count = 0
        for rec in self.records:
            path = f"trails/{rec['id']}/index.html"
            nodes = nodes_of(self.pages[path])
            places = [n for n in nodes if "Place" in (n["@type"] if isinstance(n["@type"], list) else [n["@type"]])]
            self.assertEqual(len(places), 1, rec["id"])
            place = places[0]
            self.assertIn("TouristAttraction", place["@type"])
            self.assertEqual(place["name"], rec["name"])
            self.assertEqual(place["url"], f"{BASE}/trails/{rec['id']}/")
            page = next(n for n in nodes if n["@type"] == "ItemPage")
            self.assertEqual(page["mainEntity"]["@id"], place["@id"])
            self.assertEqual(page["dateModified"], seo.checked(rec))
            self.assertRegex(page["dateModified"], r"^\d{4}-\d{2}-\d{2}$")
            count += 1
        self.assertEqual(count, len(self.records))

    def test_a_trail_states_only_what_its_record_holds(self):
        built_derived = {r["id"]: r["derived"] for r in json.loads(read("data/trails.json"))}
        for rec in self.records:
            place = next(n for n in nodes_of(self.pages[f"trails/{rec['id']}/index.html"])
                         if n["@type"] != "ItemPage" and n["@type"] != "BreadcrumbList")
            props = {(p["name"], p.get("unitCode")): p for p in place["additionalProperty"]}
            self.assertEqual(props[("Published length", "SMI")]["value"], rec["derived"]["length_mi"], rec["id"])
            self.assertEqual(props[("Published length", "KMT")]["value"], rec["length_km"], rec["id"])
            h = rec.get("hike", {})
            self.assertEqual(("Start", None) in props, bool(h.get("start")), rec["id"])
            self.assertEqual(("Usual season", None) in props, bool(h.get("season")), rec["id"])
            self.assertEqual(any(k[0] == "Highest point" for k in props),
                             bool(h.get("high_point_m") or h.get("high_point")), rec["id"])
            if h.get("official_url"):
                self.assertIn(h["official_url"], place["sameAs"], rec["id"])
            else:
                self.assertNotIn("sameAs", {k: v for k, v in place.items() if k == "sameAs" and
                                            any(u == h.get("official_url") for u in v)})
            if common.is_route(rec):
                self.assertEqual(props[("Route author", None)]["value"], rec["route"]["creator"], rec["id"])
            tracks = [d for d in place.get("subjectOf", []) if d["@type"] == "DataDownload"]
            self.assertEqual(bool(tracks), common.has_line(rec), rec["id"])
            for d in tracks:
                self.assertTrue(os.path.isfile(os.path.join(OUT, *d["contentUrl"][len(BASE) + 1:].split("/"))),
                                d["contentUrl"])
                self.assertTrue(d.get("license") or d.get("usageInfo"), rec["id"])
            if "geo" in place:
                self.assertIn(place["geo"]["@type"], ("GeoShape", "GeoCoordinates"))
            built = built_derived[rec["id"]]  # the build adds the track's box to the record
            self.assertEqual("geo" in place, bool(built.get("bbox") or h.get("start_lonlat") or h.get("end_lonlat")),
                             rec["id"])

    def test_group_crumbs_go_to_the_group_page(self):
        from olt import facets
        names = {facets.GROUP_NAME[g]: g for g in facets.GROUP_NAME}
        seen_trail = seen_state = 0
        for path, doc in self.pages.items():
            if not (path.startswith(("trails/", "regions/")) and path.endswith("index.html")):
                continue
            crumbs = visible_crumbs(doc)
            for text, href in crumbs[:-1]:
                g = names.get(text)
                if g is None or not href:
                    continue
                self.assertEqual(href, regions.group_path(g), path)
                self.assertIn(regions.group_path(g).strip("/") + "/index.html", self.pages, path)
                seen_trail += path.startswith("trails/")
                seen_state += path.startswith("regions/")
            # ...and the BreadcrumbList item for it is the same address
            lists = [n for n in nodes_of(doc) if n["@type"] == "BreadcrumbList"]
            for i, (text, href) in zip(lists[0]["itemListElement"] if lists else [], crumbs):
                if names.get(i["name"]) and href:
                    self.assertEqual(i["item"], BASE + regions.group_path(names[i["name"]]), path)
        self.assertGreater(seen_trail, 0)
        self.assertGreater(seen_state, 0)

    def test_no_page_links_to_a_group_anchor_that_has_a_page(self):
        from olt import facets
        for path, doc in self.pages.items():
            for g in facets.GROUP_NAME:
                if regions.group_path(g).strip("/") + "/index.html" in self.pages:
                    self.assertNotIn(f'href="/regions/#{g}"', doc, path)

    def test_breadcrumbs_equal_the_visible_ones(self):
        counted = 0
        for path, doc in self.pages.items():
            crumbs = visible_crumbs(doc)
            lists = [n for n in nodes_of(doc) if n["@type"] == "BreadcrumbList"]
            if not crumbs or 'name="robots" content="noindex"' in doc:
                self.assertEqual(lists, [], path)
                continue
            self.assertEqual(len(lists), 1, path)
            items = lists[0]["itemListElement"]
            self.assertEqual([i["name"] for i in items], [t for t, _ in crumbs], path)
            self.assertEqual([i["position"] for i in items], list(range(1, len(crumbs) + 1)), path)
            canonical = meta(doc, "og:url")
            self.assertEqual(items[-1]["item"], canonical, path)
            for item, (_, href) in zip(items[:-1], crumbs):
                self.assertEqual(item["item"], BASE + href, path)
            counted += 1
        self.assertGreater(counted, 280)  # trail, place, list and document pages

    def test_trail_place_and_list_pages_have_breadcrumbs(self):
        for rec in self.records:
            self.assertTrue(any(n["@type"] == "BreadcrumbList" for n in nodes_of(self.pages[f"trails/{rec['id']}/index.html"])))
        for path in self.pages:
            if path.startswith(("regions/", "lists/")) and path.count("/") == 2:
                self.assertTrue(any(n["@type"] == "BreadcrumbList" for n in nodes_of(self.pages[path])), path)

    def test_lists_and_places_carry_a_collection_of_what_they_list(self):
        by_slug, _ = regions.collect_regions(self.records)
        expected = {f"regions/{slug}/index.html": info["records"] for slug, info in by_slug.items()}
        for lst, recs in browse.shown(self.records):
            expected[f"{browse.path(lst).strip('/')}/index.html"] = recs
        self.assertGreater(len(expected), 70)
        for path, recs in expected.items():
            page = next(n for n in nodes_of(self.pages[path]) if n["@type"] == "CollectionPage")
            listing = page["mainEntity"]
            self.assertEqual(listing["@type"], "ItemList", path)
            self.assertEqual(listing["numberOfItems"], len(recs), path)
            self.assertEqual({i["url"] for i in listing["itemListElement"]},
                             {BASE + common.trail_path(r) for r in recs}, path)
            self.assertEqual([i["position"] for i in listing["itemListElement"]], list(range(1, len(recs) + 1)), path)
            self.assertEqual(page["dateModified"], seo.newest(recs), path)

    def test_home_has_website_and_organization_and_the_data_page_has_the_dataset(self):
        home = nodes_of(self.pages["index.html"])
        kinds = sorted(n["@type"] for n in home)
        self.assertEqual(kinds, ["Organization", "WebSite"])
        org = next(n for n in home if n["@type"] == "Organization")
        self.assertEqual(org["name"], SITE.name)
        self.assertEqual(org["url"], BASE + "/")
        self.assertTrue(os.path.isfile(os.path.join(OUT, "assets", "apple-touch-icon.png")))
        # only what site.toml holds: the repository, and a contact when one is set
        self.assertEqual(org.get("sameAs", []), [SITE.repo_url] if SITE.repo_url else [])
        self.assertEqual("email" in org or "contactPoint" in org, bool(SITE.contact))
        web = next(n for n in home if n["@type"] == "WebSite")
        self.assertEqual(web["publisher"], {"@id": org["@id"]})
        data = nodes_of(self.pages["data/index.html"])
        sets = [n for n in data if n["@type"] == "Dataset"]
        self.assertEqual(len(sets), 1)
        ds = sets[0]
        self.assertEqual(missing(ds), [])
        self.assertEqual(ds["license"], "https://creativecommons.org/publicdomain/zero/1.0/")
        self.assertEqual(ds["dateModified"], seo.newest(self.records))
        self.assertTrue(re.fullmatch(r"\d{4}-\d{2}-\d{2}/\d{4}-\d{2}-\d{2}", ds["temporalCoverage"]))
        self.assertEqual({d["contentUrl"].rsplit("/", 1)[1] for d in ds["distribution"]},
                         {n for n, _, _ in docs.BULK_FILES} | set())
        for d in ds["distribution"]:
            path = d["contentUrl"][len(BASE) + 1:]
            self.assertTrue(os.path.isfile(os.path.join(OUT, *path.split("/"))), path)
        self.assertTrue(all("name" in v for v in ds["variableMeasured"]))
        self.assertIn("United States", ds["description"])
        # one maintainer, named by name and profile page: the Person is the creator, the site the publisher
        self.assertEqual(ds["creator"]["name"], SITE.maintainer_name or SITE.name)
        self.assertEqual(ds["publisher"]["name"], SITE.name)

    def test_no_wording_the_house_style_forbids(self):
        for path in ("data/index.html", "index.html", "trails/long-trail/index.html"):
            text = " ".join(json.dumps(n) for n in nodes_of(self.pages[path]))
            self.assertNotRegex(text, r"\bline file\b|\btrack line\b", path)


class CardsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = records.load_records(ROOT)

    def test_every_page_has_complete_open_graph_and_a_card_that_exists(self):
        for path in page_paths():
            doc = read(path)
            for key in ("og:title", "og:description", "og:type", "og:site_name", "og:image", "og:image:alt"):
                self.assertTrue(meta(doc, key), f"{path}: {key}")
            for key in ("twitter:title", "twitter:description", "twitter:image"):
                self.assertTrue(meta(doc, key, "name"), f"{path}: {key}")
            self.assertEqual(meta(doc, "og:image"), meta(doc, "twitter:image", "name"), path)
            image = meta(doc, "og:image")
            self.assertTrue(image.startswith(BASE + "/"), f"{path}: {image}")
            target = os.path.join(OUT, *image[len(BASE) + 1:].split("/"))
            self.assertTrue(os.path.isfile(target), f"{path}: {image}")
            self.assertEqual(thumbs.png_size(target), (1200, 630), image)

    def test_each_trail_has_its_own_card_under_200_kb(self):
        for rec in self.records:
            doc = read(f"trails/{rec['id']}/index.html")
            self.assertEqual(meta(doc, "og:image"), f"{BASE}/trails/{rec['id']}/card.png", rec["id"])
            card = os.path.join(OUT, "trails", rec["id"], "card.png")
            self.assertEqual(thumbs.png_size(card), (1200, 630), rec["id"])
            self.assertLess(os.path.getsize(card), 200_000, rec["id"])
            self.assertIn(rec["name"], meta(doc, "og:image:alt"))
        self.assertEqual(meta(read("regions/index.html"), "og:image"), f"{BASE}/assets/og.png")

    def test_no_card_is_stale(self):
        """A card stores a hash of what it shows (name, length, places). A record that changed
        since its card was drawn fails here: run web/tools/make_cards.py and commit the cards."""
        for rec in self.records:
            stored = cards.stored_fingerprint(os.path.join(WEB, "cards", f"{rec['id']}.png"))
            self.assertEqual(stored, cards.fingerprint(rec), f"{rec['id']}: card is stale")

    def test_site_card_is_not_stale(self):
        """assets/og.png shows the site name and tagline from web/site.toml. A changed setting
        fails here until web/tools/make_cards.py has redrawn it."""
        cfg = site.from_file(os.path.join(WEB, "site.toml"))
        self.assertEqual(cards.stored_fingerprint(os.path.join(WEB, "assets", "og.png")),
                         cards.site_fingerprint(cfg), "assets/og.png is stale")
        self.assertEqual(thumbs.png_size(os.path.join(WEB, "assets", "og.png")), (1200, 630))
        self.assertEqual(meta(read("index.html"), "og:image"), f"{BASE}/assets/og.png")

    def test_no_card_for_a_record_that_is_gone(self):
        ids = {r["id"] for r in self.records}
        cards = {n[:-4] for n in os.listdir(os.path.join(WEB, "cards")) if n.endswith(".png")}
        self.assertEqual(cards, ids)


class SitemapDatesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = records.load_records(ROOT)
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        root = ET.fromstring(read("sitemap.xml"))
        cls.dates = {u.find("s:loc", ns).text: (u.find("s:lastmod", ns).text if u.find("s:lastmod", ns) is not None else "")
                     for u in root.findall("s:url", ns)}

    def test_sitemap_urls_are_the_indexable_pages(self):
        built = set()
        for path in page_paths():
            doc = read(path)
            if 'name="robots" content="noindex"' in doc:
                continue
            built.add(BASE + "/" + re.sub(r"index\.html$", "", path))
        self.assertEqual(set(self.dates), built)

    def test_trail_pages_carry_their_records_date(self):
        for rec in self.records:
            self.assertEqual(self.dates[f"{BASE}/trails/{rec['id']}/"], seo.modified(rec), rec["id"])

    def test_every_lastmod_is_a_date_the_data_holds(self):
        held = {d for r in self.records for d in seo.record_dates(r)}
        held |= {e[0] for e in feed.entries(docs.read_doc(ROOT, "CHANGELOG.md"))}
        held |= {str(e["decided"]) for e in __import__("olt.leftout", fromlist=["x"]).load_entries(ROOT)}
        for url, date in self.dates.items():
            if date:
                self.assertRegex(date, r"^\d{4}-\d{2}-\d{2}$", url)
                self.assertIn(date, held, url)
        self.assertGreaterEqual(sum(1 for d in self.dates.values() if d), 290)

    def test_a_list_or_place_is_as_new_as_its_newest_trail(self):
        by_slug, _ = regions.collect_regions(self.records)
        for slug, info in by_slug.items():
            self.assertEqual(self.dates[f"{BASE}/regions/{slug}/"], seo.newest(info["records"]), slug)
        for lst, recs in browse.shown(self.records):
            if lst.key != "routes":
                self.assertEqual(self.dates[f"{BASE}{browse.path(lst)}"], seo.newest(recs), lst.key)

    def test_modified_is_the_newest_of_check_and_history(self):
        rec = {"verification": {"date": "2026-01-02"}, "hike": {"checked": "2026-03-04"},
               "source": {"source_checked": "2026-02-01"},
               "history": [{"date": "2026-01-01"}, {"date": "2026-05-06"}]}
        self.assertEqual(seo.modified(rec), "2026-05-06")
        rec["history"] = [{"date": "2026-01-01"}]
        self.assertEqual(seo.modified(rec), "2026-03-04")
        self.assertEqual(seo.modified({}), "")

    def test_a_page_with_no_date_gets_no_lastmod(self):
        s = site.Site("N", "T", base_url="https://example.org")
        xml = seo.sitemap_xml(["/a/", "/b/"], s, {"/a/": "2026-01-01"})
        self.assertIn("<loc>https://example.org/a/</loc><lastmod>2026-01-01</lastmod>", xml)
        self.assertIn("<url><loc>https://example.org/b/</loc></url>", xml)

    def test_the_sitemap_does_not_read_the_clock(self):
        with open(os.path.join(WEB, "olt", "seo.py"), encoding="utf-8") as f:
            source = f.read()
        self.assertNotRegex(source, r"import (time|datetime)|from (time|datetime)|\.today\(|\.now\(")


class CrawlerFilesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = serve.parse_headers(os.path.join(OUT, "_headers"))

    def headers(self, path):
        out = {}
        for pattern, hs in self.rules:
            if pattern.match(path):
                for name, value in hs:
                    self.assertNotIn(name.lower(), out, f"{path}: {name} set by two rules")
                    out[name.lower()] = value
        return out

    def test_404_is_noindex_and_not_in_the_sitemap(self):
        doc = read("404.html")
        self.assertIn('<meta name="robots" content="noindex">', doc)
        self.assertNotIn('rel="canonical"', doc)
        self.assertNotIn("/404.html", read("sitemap.xml"))
        self.assertEqual(ld_blocks(doc), [])

    def test_raw_files_under_trails_are_noindex_and_data_downloads_are_not(self):
        raw = {"trail.toml": 0, "release.txt": 0, "map.json": 0, "sketch.json": 0, ".geojson": 0, ".gpx": 0}
        for base, _, names in os.walk(os.path.join(OUT, "trails")):
            for n in names:
                path = "/" + os.path.relpath(os.path.join(base, n), OUT).replace(os.sep, "/")
                h = self.headers(path)
                if n in raw or n.endswith((".geojson", ".gpx")):
                    key = n if n in raw else "." + n.rsplit(".", 1)[1]
                    raw[key] += 1
                    self.assertEqual(h.get("x-robots-tag"), "noindex", path)
                else:
                    self.assertNotIn("x-robots-tag", h, path)  # pages, logos, cards
        self.assertTrue(all(raw.values()), raw)
        for name in ("trails.csv", "trails.json", "index.geojson", "overview.geojson", "all-gpx.zip", "all-geojson.zip"):
            self.assertNotIn("x-robots-tag", self.headers(f"/data/{name}"), name)
        for path in ("/", "/trails/long-trail/", "/feed.xml", "/llms.txt", "/sitemap.xml", "/robots.txt"):
            self.assertNotIn("x-robots-tag", self.headers(path), path)

    def test_no_header_is_set_twice_for_any_built_file(self):
        for base, _, names in os.walk(OUT):
            for n in names:
                self.headers("/" + os.path.relpath(os.path.join(base, n), OUT).replace(os.sep, "/"))


class FeedAndExtrasTest(unittest.TestCase):
    def test_atom_feed_is_well_formed_and_from_the_changelog(self):
        ns = {"a": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(read("feed.xml"))
        self.assertEqual(root.tag, "{http://www.w3.org/2005/Atom}feed")
        for tag in ("title", "id", "updated", "author"):
            self.assertIsNotNone(root.find(f"a:{tag}", ns), tag)
        self.assertEqual(root.find("a:link[@rel='self']", ns).get("href"), f"{BASE}/feed.xml")
        entries = root.findall("a:entry", ns)
        changelog = feed.entries(docs.read_doc(ROOT, "CHANGELOG.md"))
        self.assertEqual(len(entries), min(len(changelog), feed.FEED_MAX))
        ids = [e.find("a:id", ns).text for e in entries]
        self.assertEqual(len(set(ids)), len(ids))
        for e, (date, title, slug, _) in zip(entries, changelog):
            self.assertEqual(e.find("a:title", ns).text, title)
            self.assertEqual(e.find("a:updated", ns).text, f"{date}T00:00:00Z")
            self.assertEqual(e.find("a:link", ns).get("href"), f"{BASE}/data/changelog/#{slug}")
            self.assertIn(f'id="{slug}"', read("data/changelog/index.html"))
            self.assertTrue(e.find("a:content", ns).text.strip())
        self.assertEqual(root.find("a:updated", ns).text, f"{changelog[0][0]}T00:00:00Z")
        for e in entries:  # links in an entry are absolute: a reader has no base
            self.assertNotRegex(e.find("a:content", ns).text, r'href="/')

    def test_head_links_to_the_feed_and_the_data_page_to_its_files(self):
        for path in ("index.html", "trails/long-trail/index.html", "data/index.html"):
            self.assertIn('<link rel="alternate" type="application/atom+xml"', read(path))
            self.assertIn('href="/feed.xml"', read(path))
        data = read("data/index.html")
        self.assertIn('<link rel="alternate" type="application/json" href="/data/trails.json"', data)
        self.assertIn('<link rel="alternate" type="text/csv" href="/data/trails.csv"', data)
        self.assertNotIn('type="text/csv"', read("index.html"))

    def test_favicon_ico_is_a_real_icon_at_the_root(self):
        with open(os.path.join(OUT, "favicon.ico"), "rb") as f:
            head = f.read(6)
        self.assertEqual(head[:4], b"\x00\x00\x01\x00")  # ICO
        self.assertGreaterEqual(int.from_bytes(head[4:6], "little"), 1)

    def test_llms_txt_points_at_files_that_exist(self):
        text = read("llms.txt")
        self.assertTrue(text.startswith(f"# {SITE.name}\n\n> "))
        links = re.findall(r"\]\((https://[^)]+)\)", text)
        self.assertGreater(len(links), 8)
        for url in links:
            if url.startswith(BASE + "/"):
                path = os.path.join(OUT, *url[len(BASE) + 1:].split("/"))
                self.assertTrue(os.path.exists(path) or os.path.isfile(os.path.join(path, "index.html")), url)
        self.assertIn("CC0", text)
        self.assertNotIn("<id>.line", text)


if __name__ == "__main__":
    unittest.main()
