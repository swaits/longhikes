"""Guard: the built state, group and state-list pages must not change while place pages are added.

Later ships may add a place-links nav to a state page and place names to its search text;
normalise() strips exactly those two things, and nothing else. Regenerate the golden only
deliberately: python3 web/tests/make_golden.py.
"""
import hashlib
import json
import os
import re
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, WEB)
sys.path.insert(0, HERE)

from olt import bounds, facets, home, placefacets, regions, searchtext, site  # noqa: E402
from test_hike import fake  # noqa: E402

GOLDEN = os.path.join(HERE, "golden", "state-pages.json")


def normalise(html):
    """Remove the two things later ships are allowed to change on a state page: the
    data-search attributes (they gain place names) and the place-links nav block."""
    html = re.sub(r'\s*data-search="[^"]*"', "", html)
    html = re.sub(r'<nav class="region-nav" aria-label="Parks, ranges and wilderness in [^"]*">.*?</nav>',
                  "", html, flags=re.S)
    return html


def fixtures():
    """12 fake records over Colorado, Utah and Ontario, plus one across all of Canada:
    mixed trails and routes, loops, and tracks with a bbox as test_place_view sets."""
    specs = [
        # (regions, country, km, hike, route, line)
        (["CO"], "US", 120, {"shape": "loop", "terrain": ["alpine"]}, False, True),
        (["CO"], "US", 180, {"shape": "loop", "terrain": ["forest"]}, False, True),
        (["CO", "UT"], "US", 260, {"shape": "loop", "terrain": ["desert"]}, False, False),
        (["CO"], "US", 340, {"shape": "loop", "terrain": ["alpine"]}, True, True),
        (["CO"], "US", 90, {"shape": "loop", "terrain": ["forest"]}, False, False),
        (["CO"], "US", 800, {"shape": "point-to-point", "terrain": ["alpine"]}, False, True),
        (["CO", "UT"], "US", 1500, {"shape": "point-to-point", "terrain": ["desert"]}, False, True),
        (["UT"], "US", 210, {"shape": "point-to-point", "terrain": ["canyon"]}, True, False),
        (["UT"], "US", 130, {"shape": "point-to-point", "terrain": ["desert"]}, False, True),
        (["ON"], "CA", 420, {"shape": "point-to-point", "terrain": ["forest", "lakes"]}, False, True),
        (["ON"], "CA", 110, {"shape": "point-to-point", "terrain": ["forest"]}, False, False),
        (["all provinces and territories"], "CA", 3000, {"shape": "point-to-point", "terrain": ["forest"]}, False, True),
    ]
    records = []
    for i, (regs, country, km, hike, route, line) in enumerate(specs, 1):
        rec = fake(i, km=km, hike=dict(hike, summary=f"A walk number {i}.", days=[7, 14]),
                   regions=regs, country=country, line=line)
        if route:
            rec["derived"]["kind"] = "route"
            rec["route"] = {"creator": "A Walker", "year": 2010}
        key = facets.place_keys(rec)[0] if facets.place_keys(rec) else None
        box = bounds.place_box(key) if key and key != facets.ACROSS_CANADA else None
        cx, cy = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2) if box else (-100.0, 45.0)
        rec["derived"]["bbox"] = [cx - 0.3, cy - 0.2, cx + 0.3, cy + 0.2]
        if line:
            rec["derived"]["files"] = dict(rec["derived"].get("files", {}), line="x.gpx")
        records.append(rec)
    return records


def build_map():
    """{path: sha256(normalise(page))} for every state, group, hub, empty-place and
    state-list page the fixtures produce."""
    records = fixtures()
    s = site.Site("Long Hikes", "T", repo_url="https://github.com/o/r")
    out = {}

    def add(path, page):
        text = "\n".join(str(p) for p in page if isinstance(p, str) or hasattr(p, "__html__"))
        out[path] = hashlib.sha256(normalise(text).encode()).hexdigest()

    by_slug, _ = regions.collect_regions(records)
    pages = placefacets.plan(records)
    by_place = placefacets.pages_by_place(pages)
    for slug in sorted(by_slug):
        facet_pages = [(placefacets.label(p["lst"]), p["path"], len(p["recs"]))
                       for p in by_place.get(slug, [])]
        add(f"/regions/{slug}/", regions.region_page(slug, records, s, facet_pages))
    for g, _, _ in facets.PLACE_GROUPS:
        page = regions.group_page(g, records, s)
        if page:
            add(regions.group_path(g), page)
    add("/regions/", regions.regions_index_page(records, s))
    add("/regions/us-hi/", regions.empty_place_page("US-HI", records, s, []))
    for p in pages:
        add(p["path"], placefacets.page(p, records, s, pages))
    return out


class AllowedDifferencesTest(unittest.TestCase):
    def test_state_pages_differ_only_in_data_search_and_the_new_block(self):
        # data-search gains the place names, and nothing else about a row changes
        rec = fixtures()[0]
        plain = home.entry(rec)
        searchtext.use_place_names({rec["id"]: ["Wind River Range"]})
        try:
            with_place = home.entry(rec)
        finally:
            searchtext.use_place_names({})
        self.assertIn("wind river range", with_place)
        self.assertNotEqual(plain, with_place)
        self.assertEqual(normalise(plain), normalise(with_place))
        # the place-links nav is the other allowed addition to a state page
        records = fixtures()
        s = site.Site("Long Hikes", "T", repo_url="https://github.com/o/r")
        block = ('<nav class="region-nav" aria-label="Parks, ranges and wilderness in Colorado">'
                 'Parks, ranges and wilderness in Colorado: <a href="/ranges/front-range/">Front Range</a> (3)</nav>')
        plain_page = regions.region_page("us-co", records, s)
        linked_page = regions.region_page("us-co", records, s, place_links=block)
        self.assertNotEqual(str(plain_page[2]), str(linked_page[2]))
        self.assertEqual(normalise(str(plain_page[2])), normalise(str(linked_page[2])))
        self.assertEqual(plain_page[0], linked_page[0])
        self.assertEqual(plain_page[1], linked_page[1])


class StatePagesUnchangedTest(unittest.TestCase):
    def test_every_state_group_and_state_list_page_is_byte_identical_after_normalising(self):
        with open(GOLDEN, encoding="utf-8") as f:
            want = json.load(f)
        got = build_map()
        differ = sorted(p for p in set(want) | set(got) if want.get(p) != got.get(p))
        self.assertEqual(differ, [], "pages that differ from the golden: " + ", ".join(differ))
        self.assertEqual(got, want)


if __name__ == "__main__":
    unittest.main()
