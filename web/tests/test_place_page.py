"""Park, range and wilderness pages (olt/placepages.py, through regions.place_page),
and their place in the built site: sitemap, structured data, navigation.

Fixtures only: small records with [[place]] entries and a small places.toml in a
temporary directory, never sample data in the real records."""
import html
import json
import os
import re
import sys
import tempfile
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WEB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from olt import layout, pages, placepages, places, regions, seo, site  # noqa: E402
from test_facets import BANNED, site_words  # noqa: E402
from test_hike import fake  # noqa: E402

S = site.Site("Long Hikes", "T", base_url="https://example.org", repo_url="https://github.com/o/r")
BOX = [-110.0, 42.5, -108.5, 43.5]

REGISTRY = [
    {"kind": "range", "slug": "wind-river-range", "name": "Wind River Range", "where": ["WY"],
     "source": "gmba-v2", "source_id": "1", "source_version": "2026-11-20", "box": BOX},
    {"kind": "park", "slug": "yosemite", "name": "Yosemite National Park", "where": ["CA"],
     "source": "nps", "source_id": "YOSE", "source_version": "2026-11-20",
     "box": [-119.9, 37.5, -119.2, 38.2]},
    {"kind": "park", "slug": "small", "name": "Small Park", "where": ["WY"],
     "source": "nps", "source_id": "SMAL", "source_version": "2026-11-20", "box": BOX},
]


def write_registry(root, entries=REGISTRY):
    lines = []
    for e in entries:
        box = ", ".join(str(v) for v in e["box"])
        where = ", ".join(f'"{c}"' for c in e["where"])
        within = f'\nwithin = [{", ".join(chr(34) + s + chr(34) for s in e["within"])}]' if e.get("within") else ""
        extra = "".join(f'{k} = "{e[k]}"\n' for k in ("label", "prep") if e.get(k))
        lines.append(f'[[place]]\nslug = "{e["slug"]}"\nkind = "{e["kind"]}"\nname = "{e["name"]}"\n{extra}'
                     f'where = [{where}]{within}\nsource = "{e["source"]}"\nsource_id = "{e["source_id"]}"\n'
                     f'source_version = "{e["source_version"]}"\nbox = [{box}]\n')
    with open(os.path.join(root, "places.toml"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def rec(i, name, pls, *, km=120, regs=("WY",), country="US", line=True, inside_km=123.456, date=""):
    r = fake(i, km=km, regions=list(regs), country=country, line=line,
             hike={"shape": "point-to-point", "terrain": ["alpine"],
                   "summary": f"A walk called {name}.", "days": [7, 14]})
    r["name"] = name
    r["place"] = [{"kind": k, "slug": s, "basis": "track", "km": inside_km} for k, s in pls]
    r["derived"]["bbox"] = [-109.5, 42.8, -109.0, 43.2]
    if line:
        r["derived"]["files"] = dict(r["derived"].get("files", {}), line="x.gpx")
    if date:
        r["history"] = [{"date": date}]
    return r


def wind_records(n=10):
    """n trails in the Wind River Range, names out of order, half over the state line."""
    out = []
    for i in range(n, 0, -1):
        out.append(rec(100 + i, f"Wind Trail {chr(64 + i)}", [("range", "wind-river-range")],
                       km=90 + i * 10, regs=("WY",) if i % 2 else ("CO",),
                       date="2026-11-18" if i == 3 else ""))
    return out


def yosemite_records(n=5):
    return [rec(200 + i, f"Yosemite Trail {chr(64 + i)}", [("park", "yosemite")],
                km=80 + i * 15, regs=("CA",)) for i in range(n, 0, -1)]


def build(records):
    with tempfile.TemporaryDirectory() as d:
        write_registry(d)
        return {b.path: b for b in placepages.build(records, S, d)}


def text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(fragment))))


def entry_of(kind, slug, name, where, **kw):
    return dict({"kind": kind, "slug": slug, "name": name, "where": where, "source": "gmba-v2",
                 "source_id": "1", "source_version": "2026-11-20", "box": BOX}, **kw)


def built_with(entries, n=3, regs=("WY",)):
    records = [rec(300 + i, f"Place Trail {chr(64 + i)}", [(e["kind"], e["slug"]) for e in entries],
                   regs=regs) for i in range(1, n + 1)]
    with tempfile.TemporaryDirectory() as d:
        write_registry(d, entries)
        return {b.path: b for b in placepages.build(records, S, d)}


class LabelPrepositionAndTitleTest(unittest.TestCase):
    def test_a_plateau_is_not_a_mountain_range_and_is_on_not_in(self):
        built = built_with([entry_of("range", "colorado-plateau", "Colorado Plateau", ["UT"],
                                     label="Plateau", prep="on the")], regs=("UT",))
        b = built["/ranges/colorado-plateau/"]
        body = str(b.body)
        self.assertEqual(b.title, "Long Hikes on the Colorado Plateau, Utah: 3 Trails")
        self.assertIn('<p class="kicker">Plateau · Utah</p>', body)
        self.assertNotIn("Mountain range", body)
        self.assertIn("3 trails on the Colorado Plateau", text(body))
        self.assertIn("on the Colorado Plateau", b.description)
        self.assertNotIn("in the Colorado Plateau", body)

    def test_the_rim_is_along_and_a_range_with_no_label_keeps_the_defaults(self):
        built = built_with([entry_of("range", "mogollon-rim", "Mogollon Rim", ["AZ"],
                                     label="Escarpment", prep="along the"),
                            entry_of("range", "wind-river-range", "Wind River Range", ["WY"])],
                           regs=("AZ", "WY"))
        self.assertIn("3 trails along the Mogollon Rim", text(built["/ranges/mogollon-rim/"].body))
        wind = built["/ranges/wind-river-range/"]
        self.assertIn('<p class="kicker">Mountain range · Wyoming</p>', str(wind.body))
        self.assertIn("3 trails in the Wind River Range", text(wind.body))

    def test_a_park_has_its_own_label_and_no_the(self):
        built = built_with([entry_of("park", "blue-ridge-parkway", "Blue Ridge Parkway", ["NC", "VA"],
                                     label="Parkway", prep="along the")], regs=("NC",))
        b = built["/parks/blue-ridge-parkway/"]
        self.assertIn('<p class="kicker">Parkway · North Carolina and Virginia</p>', str(b.body))
        self.assertEqual(b.title, "Long Hikes along the Blue Ridge Parkway: 3 Trails")

    def test_a_state_already_in_the_name_is_not_repeated(self):
        built = built_with([entry_of("range", "oregon-cascades", "Oregon Cascades", ["OR"]),
                            entry_of("range", "california-coast-ranges", "California Coast Ranges", ["CA"])],
                           regs=("OR", "CA"))
        self.assertEqual(built["/ranges/oregon-cascades/"].title, "Long Hikes in the Oregon Cascades: 3 Trails")
        self.assertEqual(built["/ranges/california-coast-ranges/"].title,
                         "Long Hikes in the California Coast Ranges: 3 Trails")

    def test_every_place_title_keeps_its_count_even_with_a_long_name(self):
        built = built_with([entry_of("range", "vancouver-island-ranges", "Vancouver Island Ranges", ["BC"]),
                            entry_of("park", "sequoia", "Sequoia and Kings Canyon National Parks", ["CA"]),
                            entry_of("wilderness", "sk", "Sequoia-Kings Canyon Wilderness", ["CA"])],
                           n=18, regs=("BC", "CA"))
        for b in built.values():
            self.assertTrue(b.title.endswith(": 18 Trails"), b.title)
            self.assertTrue(b.title.startswith("Long Hikes in "), b.title)
        # the state goes first, then nothing else: no "Long Hikes in" is shortened
        self.assertEqual(built["/ranges/vancouver-island-ranges/"].title,
                         "Long Hikes in the Vancouver Island Ranges: 18 Trails")


class SmallPlaceHasTheBarTest(unittest.TestCase):
    """The owner's rule: every set of trails gets the search box and the filters, at any size."""

    def test_a_place_with_three_trails_has_the_search_box_and_the_finder(self):
        built = built_with([entry_of("range", "wind-river-range", "Wind River Range", ["WY"])], n=3)
        body = str(built["/ranges/wind-river-range/"].body)
        self.assertIn('class="finder__bar"', body)
        self.assertIn('id="q"', body)
        self.assertIn("data-finder", body)
        self.assertLess(body.index('class="finder__bar"'), body.index('<li class="entry"'))

    def test_only_filters_that_have_something_to_offer_are_written(self):
        # three identical trails: nothing narrows them, so the bar is the search box alone
        built = built_with([entry_of("range", "wind-river-range", "Wind River Range", ["WY"])], n=3)
        body = str(built["/ranges/wind-river-range/"].body)
        form = body[body.index('<form class="filters"'):body.index("</form>")]
        self.assertNotIn("data-facet", form)
        self.assertNotIn("filters__toggle", form)
        self.assertNotIn("Nothing here narrows", form)

    def test_a_place_whose_trails_differ_offers_those_filters_with_a_button(self):
        entries = [entry_of("range", "wind-river-range", "Wind River Range", ["WY", "CO"])]
        records = [rec(400 + i, f"Differ {i}", [("range", "wind-river-range")], km=50 + i * 120,
                       regs=("WY",) if i % 2 else ("CO",)) for i in range(1, 4)]
        with tempfile.TemporaryDirectory() as d:
            write_registry(d, entries)
            body = str(placepages.build(records, S, d)[0].body)
        form = body[body.index('<form class="filters"'):body.index("</form>")]
        self.assertIn('data-facet="where"', form)
        self.assertIn("filters__toggle", form)


class PlacePageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = wind_records() + yosemite_records()
        cls.built = build(cls.records)

    def test_a_place_with_three_trails_gets_a_page_and_one_with_two_does_not(self):
        two = [rec(1, "One", [("park", "small")]), rec(2, "Two", [("park", "small")])]
        self.assertEqual(build(two), {})
        three = two + [rec(3, "Three", [("park", "small")])]
        self.assertIn("/parks/small/", build(three))
        self.assertIn("/parks/yosemite/", self.built)
        self.assertIn("/ranges/wind-river-range/", self.built)

    def test_the_page_has_the_filter_bar_rows_and_map_before_the_summary(self):
        body = str(self.built["/ranges/wind-river-range/"].body)
        # browse_view wraps the listing (filter bar, then rows) in browse__list
        # beside browse__map, as on a state page; the summary follows both.
        self.assertLess(body.index('class="finder__bar"'), body.index('<li class="entry"'))
        self.assertLess(body.index('<li class="entry"'), body.index('class="browse-about"'))
        self.assertLess(body.index('class="browse__map"'), body.index('class="browse-about"'))
        self.assertIn('id="where"', body)  # the Where filter: states and provinces, as elsewhere

    def test_the_count_in_the_lede_the_title_and_the_rows_agree(self):
        b = self.built["/ranges/wind-river-range/"]
        body = str(b.body)
        self.assertIn("10 Trails", b.title)
        self.assertIn("10 trails in the Wind River Range", text(body))
        self.assertEqual(body.count('<li class="entry"'), 10)
        self.assertEqual(len(b.recs), 10)

    def test_the_map_opens_on_the_registry_box(self):
        body = str(self.built["/ranges/wind-river-range/"].body)
        want = 'data-bbox="' + ",".join(f"{v:.4f}" for v in BOX) + '"'
        self.assertIn(want, body)

    def test_trails_are_in_plain_a_to_z_order(self):
        body = str(self.built["/ranges/wind-river-range/"].body)
        names = re.findall(r'data-name="([^"]*)"', body)
        self.assertEqual(names, sorted(names))
        self.assertEqual(names[0], "wind trail a")
        self.assertNotIn("data-here", body)  # no wholly-in lead, as the state pages have

    def test_no_banned_word_and_no_internal_km(self):
        for path_, b in self.built.items():
            doc = layout.layout(b.title, b.body, path=path_, description=b.description, site=S,
                                jsonld=seo.collection_jsonld(path_, S, title=b.title,
                                                             description=b.description, recs=b.recs))
            for bad in ("123.456", "123.4", "123.5", "76.7", "76.8"):
                self.assertNotIn(bad, doc, (path_, bad))
            words_ = site_words(doc)
            for pattern in BANNED:
                self.assertIsNone(re.search(pattern, words_, re.I), (path_, pattern))

    def test_the_title_follows_the_search_phrasing(self):
        self.assertEqual(self.built["/ranges/wind-river-range/"].title,
                         "Long Hikes in the Wind River Range, Wyoming: 10 Trails")
        self.assertEqual(self.built["/parks/yosemite/"].title,
                         "Long Hikes in Yosemite National Park: 5 Trails")
        body = str(self.built["/ranges/wind-river-range/"].body)
        self.assertIn("<h1>Wind River Range</h1>", body)
        self.assertIn('<p class="kicker">Mountain range · Wyoming</p>', body)
        park = str(self.built["/parks/yosemite/"].body)
        self.assertIn("<h1>Yosemite National Park</h1>", park)
        self.assertIn("5 trails in Yosemite National Park", text(park))

    def test_the_breadcrumb_is_trails_places_name(self):
        body = str(self.built["/ranges/wind-river-range/"].body)
        crumbs = body[body.index('class="breadcrumb"'):body.index("</ol>")]
        self.assertEqual(re.findall(r">([^<]+)</a>", crumbs), ["Trails", "Places"])
        self.assertIn('<li aria-current="page">Wind River Range</li>', crumbs)
        self.assertEqual(seo.visible_breadcrumbs(body),
                         [("Trails", "/"), ("Places", "/regions/"), ("Wind River Range", "")])

    def test_the_structured_data_is_a_collection_of_the_trails(self):
        b = self.built["/parks/yosemite/"]
        nodes = seo.collection_jsonld(b.path, S, title=b.title, description=b.description, recs=b.recs)
        page = nodes[0]
        self.assertEqual(page["@type"], "CollectionPage")
        listing = page["mainEntity"]
        self.assertEqual(listing["@type"], "ItemList")
        self.assertEqual(listing["numberOfItems"], 5)
        self.assertEqual([i["url"] for i in listing["itemListElement"]],
                         [f"https://example.org/trails/{r['id']}/" for r in b.recs])


class BuiltPlacePagesTest(unittest.TestCase):
    """One synthetic render_site: the pages written, in the sitemap, Places current."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        repo, out = os.path.join(cls.tmp.name, "repo"), os.path.join(cls.tmp.name, "out")
        cls.out = out
        cls.records = wind_records() + yosemite_records()
        for r in cls.records:
            os.makedirs(os.path.join(repo, r["id"]))
            with open(os.path.join(repo, r["id"], "trail.toml"), "w", encoding="utf-8") as f:
                f.write(f'id = "{r["id"]}"\n')
        write_registry(repo)
        pages.render_site(cls.records, out, repo, site=S)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def read(self, *parts):
        with open(os.path.join(self.out, *parts), encoding="utf-8") as f:
            return f.read()

    def test_the_pages_are_written(self):
        self.assertIn("Wind River Range", self.read("ranges", "wind-river-range", "index.html"))
        self.assertIn("Yosemite National Park", self.read("parks", "yosemite", "index.html"))
        self.assertFalse(os.path.exists(os.path.join(self.out, "parks", "small")))

    def test_the_page_is_in_the_sitemap_with_the_newest_trail_date(self):
        xml = self.read("sitemap.xml")
        for p in ("/ranges/wind-river-range/", "/parks/yosemite/"):
            self.assertIn(f"<loc>https://example.org{p}</loc>", xml, p)
        row = next(ln for ln in xml.splitlines() if "/ranges/wind-river-range/" in ln)
        self.assertIn("<lastmod>2026-11-18</lastmod>", row)  # the newest of its trails
        self.assertNotIn("/parks/small/", xml)

    def test_places_is_the_current_nav_item_on_a_place_page(self):
        doc = self.read("parks", "yosemite", "index.html")
        nav = re.search(r'<nav class="site-nav"[^>]*>(.*?)</nav>', doc, re.S).group(1)
        self.assertIn('<a href="/regions/" aria-current="true">Places</a>', nav)

    def test_the_built_page_carries_the_collection_structured_data(self):
        doc = self.read("ranges", "wind-river-range", "index.html")
        m = re.search(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S)
        data = json.loads(m.group(1))
        nodes = data.get("@graph", [data])
        coll = next(n for n in nodes if n.get("@type") == "CollectionPage")
        self.assertEqual(coll["mainEntity"]["numberOfItems"], 10)
        crumbs = next(n for n in nodes if n.get("@type") == "BreadcrumbList")
        self.assertEqual([i["name"] for i in crumbs["itemListElement"]],
                         ["Trails", "Places", "Wind River Range"])

    def test_the_hub_state_and_trail_pages_of_the_same_build_link_here(self):
        hub = self.read("regions", "index.html")
        self.assertIn('<a href="/ranges/wind-river-range/">Wind River Range</a>', hub)
        wyoming = self.read("regions", "us-wy", "index.html")
        self.assertIn('aria-label="Parks, ranges and wilderness in Wyoming"', wyoming)
        trail_page = self.read("trails", "t101", "index.html")
        self.assertIn('<a href="/ranges/wind-river-range/">Wind River Range</a>', trail_page)
        home_page = self.read("index.html")
        self.assertIn("river range", home_page)  # the rows' search words

    def test_the_state_pages_of_the_same_build_are_unchanged_in_shape(self):
        # the golden test pins the exact bytes; here the same render still has them
        doc = self.read("regions", "us-wy", "index.html")
        self.assertIn("<h1>Wyoming</h1>", doc)


if __name__ == "__main__":
    unittest.main()
