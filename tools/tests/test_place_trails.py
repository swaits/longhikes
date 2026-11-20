"""Tests for tools/place_trails.py. Needs the tool's venv (.venv-places); with the system
Python the whole file is skipped, not failed. No network: synthetic outlines and tracks.

    .venv-places/bin/python -m unittest discover tools/tests -p "test_place_trails.py"
"""
import json
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

try:
    import shapely  # noqa: F401
    HAVE = True
except ImportError:
    HAVE = False

if HAVE:
    from shapely.geometry import LineString, MultiLineString, Polygon
    import check_places as C
    import place_trails as P

# At latitude 43, 0.0063 degrees of latitude is about 0.70 km.
BOX = None  # built in setUp when shapely is there


def write_track(d, name, lines):
    feats = [{"type": "Feature", "properties": {},
              "geometry": {"type": "LineString", "coordinates": line}} for line in lines]
    with open(os.path.join(d, name), "w") as f:
        json.dump({"type": "FeatureCollection", "features": feats}, f)


def write_record(d, line_file="line.geojson"):
    with open(os.path.join(d, "trail.toml"), "w") as f:
        f.write(f'id = "x"\n[source]\nline_file = "{line_file}"\n')


@unittest.skipUnless(HAVE, "shapely (the .venv-places venv) is not installed")
class GeometryTest(unittest.TestCase):
    def setUp(self):
        self.box = Polygon([(-110.0, 43.0), (-109.0, 43.0), (-109.0, 44.0), (-110.0, 44.0)])

    def test_pieces_inside_are_summed(self):
        parts = [LineString([(-109.5 + 0.1 * i, 43.5), (-109.5 + 0.1 * i, 43.5063)]) for i in range(3)]
        km = P.km_inside(MultiLineString(parts), self.box)
        self.assertAlmostEqual(km, 2.1, delta=0.15)
        self.assertGreater(km, P.MIN_KM)

    def test_a_skimming_track_is_under_the_threshold(self):
        # about 1.5 km inside
        track = LineString([(-109.5, 43.5), (-109.5, 43.5135)])
        km = P.km_inside(track, self.box)
        self.assertAlmostEqual(km, 1.5, delta=0.1)
        self.assertLess(km, P.MIN_KM)

    def test_a_hole_is_not_inside(self):
        hole = [(-109.6, 43.4), (-109.4, 43.4), (-109.4, 43.6), (-109.6, 43.6)]
        outline = Polygon(self.box.exterior.coords, [hole])
        track = LineString([(-109.5, 43.45), (-109.5, 43.55)])
        self.assertEqual(P.km_inside(track, outline), 0.0)

    def test_alternates_are_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            write_record(d)
            write_track(d, "line.geojson", [[[-108.0, 43.5], [-108.0, 43.51]]])  # outside
            write_track(d, "alternates.geojson", [[[-109.5, 43.1], [-109.5, 43.9]]])  # long, inside
            track = P.main_track(d)
            self.assertIsNotNone(track)
            self.assertEqual(P.km_inside(track, self.box), 0.0)

    def test_a_record_with_no_line_file_has_no_track(self):
        with tempfile.TemporaryDirectory() as d:
            write_record(d, line_file="")
            self.assertIsNone(P.main_track(d))

    def test_box_of_is_west_south_east_north_rounded(self):
        outline = Polygon([(-110.004, 42.501), (-108.499, 42.501), (-108.499, 43.499), (-110.004, 43.499)])
        self.assertEqual(P.box_of(outline), [-110.0, 42.5, -108.5, 43.5])

    def test_track_hash_matches_the_validators(self):
        with tempfile.TemporaryDirectory() as d:
            write_record(d)
            write_track(d, "line.geojson", [[[-109.5, 43.5], [-109.4, 43.5]]])
            self.assertEqual(P.track_hash(d), C.track_hash(os.path.join(d, "line.geojson")))


def outline(kind, source_id, name, geom, slug=None, hint=()):
    return P.Outline(kind=kind, source="nps", source_id=source_id, name=name,
                     state_codes_hint=list(hint), geometry=geom, slug=slug or P.slugify(name))


def rec(rid, regions, track):
    return {"id": rid, "name": rid, "regions": regions, "track": track}


@unittest.skipUnless(HAVE, "shapely (the .venv-places venv) is not installed")
class ProposalTest(unittest.TestCase):
    def setUp(self):
        # Two overlapping places; vertical tracks of about 10 km inside each.
        self.park = outline("park", "P1", "Alpha Park",
                            Polygon([(-110, 43), (-109, 43), (-109, 44), (-110, 44)]), hint=["WY"])
        self.range = outline("range", "R1", "Beta Range",
                             Polygon([(-109.6, 43), (-108.6, 43), (-108.6, 44), (-109.6, 44)]))
        self.inside = LineString([(-109.5, 43.2), (-109.5, 43.29)])   # in both, ~10 km
        self.park_only = LineString([(-109.9, 43.2), (-109.9, 43.29)])
        self.outside = LineString([(-107.0, 43.2), (-107.0, 43.29)])

    def test_a_place_outside_the_trails_regions_does_not_place_it(self):
        p = P.propose([rec("a", ["NH"], self.inside)], [self.park, self.range])
        self.assertEqual(p.per_trail["a"], [])
        p = P.propose([rec("a", ["NH", "WY"], self.inside)], [self.park, self.range])
        self.assertEqual({k for k, _km in p.per_trail["a"]}, {("park", "alpha-park"), ("range", "beta-range")})

    def test_the_registrys_reviewed_where_wins(self):
        p = P.propose([rec("a", ["NH"], self.inside)], [self.park],
                      {("park", "alpha-park"): ["NH"]})
        self.assertEqual([k for k, _km in p.per_trail["a"]], [("park", "alpha-park")])

    def test_propose_lists_per_trail_places_and_per_place_trails(self):
        records = [rec("a", ["WY"], self.inside), rec("b", ["WY"], self.park_only),
                   rec("c", ["WY"], self.inside)]
        p = P.propose(records, [self.park, self.range])
        self.assertEqual({k for k, _ in p.per_trail["a"]}, {("park", "alpha-park"), ("range", "beta-range")})
        self.assertEqual({t for t, _ in p.per_place[("park", "alpha-park")].trails}, {"a", "b", "c"})
        self.assertEqual({t for t, _ in p.per_place[("range", "beta-range")].trails}, {"a", "c"})

    def test_a_trail_under_the_threshold_is_not_in_the_place(self):
        skim = LineString([(-109.5, 43.5), (-109.5, 43.509)])  # ~1.0 km
        p = P.propose([rec("a", ["WY"], skim)], [self.park])
        self.assertEqual(p.per_trail["a"], [])
        self.assertNotIn(("park", "alpha-park"), p.per_place)

    def test_places_with_fewer_than_three_trails_are_marked_no_page(self):
        records = [rec("a", ["WY"], self.inside), rec("b", ["WY"], self.park_only),
                   rec("c", ["WY"], self.inside)]
        p = P.propose(records, [self.park, self.range])
        self.assertTrue(p.per_place[("park", "alpha-park")].page)
        self.assertFalse(p.per_place[("range", "beta-range")].page)

    def test_near_threshold_items_are_listed_first_and_flagged(self):
        near = LineString([(-109.5, 43.5), (-109.5, 43.5153)])  # ~1.7 km: in, but near the line
        p = P.propose([rec("a", ["WY"], near), rec("b", ["WY"], self.inside)], [self.park])
        self.assertEqual(p.near[0].trail, "a")
        self.assertTrue(any(abs(km - P.MIN_KM) <= 0.5 for _, km in p.per_trail["a"]))

    def test_where_is_the_source_states_not_the_visiting_trails_states(self):
        # trails from other states visit the place: where stays the place's own
        records = [rec("a", ["WY"], self.park_only), rec("b", ["WY", "CO"], self.park_only),
                   rec("c", ["OR", "WA"], self.park_only), rec("d", ["UT"], self.park_only)]
        p = P.propose(records, [self.park])
        self.assertEqual(p.per_place[("park", "alpha-park")].where, ["WY"])

    def test_where_of_a_source_with_states_uses_them_and_drops_unknown_codes(self):
        o = outline("park", "P9", "Edge Park", self.park.geometry, hint=["MT", "ID", "PR"])
        self.assertEqual(P.where_of(o), ["ID", "MT"])

    def test_state_codes_reads_the_separators_the_sources_use(self):
        self.assertEqual(P.state_codes("ID-MT-WY"), ["ID", "MT", "WY"])
        self.assertEqual(P.state_codes("AR/OK"), ["AR", "OK"])
        self.assertEqual(P.state_codes("FL 6/"), ["FL"])
        self.assertEqual(P.state_codes("SAMOA"), [])
        self.assertEqual(P.state_codes(None), [])

    def test_where_of_a_range_is_found_from_the_state_boxes(self):
        # wholly inside the Wyoming box, clear of every other state's box
        o = outline("range", "R5", "Wyoming Range", self.park.geometry)
        o.state_codes_hint = []
        self.assertEqual(P.where_of(o), ["WY"])

    def test_where_of_a_place_in_two_states_lists_both(self):
        both = Polygon([(-112.0, 40.0), (-110.0, 40.0), (-110.0, 42.0), (-112.0, 42.0)])
        o = outline("range", "R6", "Border Range", both)
        self.assertEqual(P.where_of(o), ["UT", "WY"])

    def test_a_hand_where_overrides_the_source_and_the_boxes(self):
        o = outline("range", "R7", "Hand Range", self.park.geometry, hint=["WY"])
        o.where_hand = ("WY", "MT")
        self.assertEqual(P.where_of(o), ["MT", "WY"])

    def test_yosemite_like_outline_is_california_only(self):
        yose = Polygon([(-120.0, 37.5), (-119.2, 37.5), (-119.2, 38.2), (-120.0, 38.2)])
        o = outline("park", "YOSE", "Yosemite National Park", yose, hint=["CA"])
        self.assertEqual(P.where_of(o), ["CA"])

    def test_one_name_in_a_kind_and_source_is_one_place_with_both_ids(self):
        a = outline("range", "17222", "Palisades", self.park.geometry)
        b = outline("range", "19588", "Palisades", self.range.geometry)
        c = outline("range", "5", "Other Range", self.range.geometry)
        out = P.merge_same_name([a, b, c])
        self.assertEqual([o.name for o in out], ["Palisades", "Other Range"])
        self.assertEqual(out[0].source_id, ["17222", "19588"])
        self.assertAlmostEqual(out[0].geometry.area,
                               self.park.geometry.union(self.range.geometry).area)
        out = P.assign_slugs(out)
        self.assertEqual(out[0].slug, "palisades")  # no numeric suffix, no state code

    def test_two_ranges_of_one_display_name_with_different_slugs_stay_two_places(self):
        a = outline("range", "12331", "White Mountains", self.park.geometry, slug="white-mountains")
        b = outline("range", "16575", "White Mountains", self.range.geometry,
                    slug="white-mountains-arizona")
        self.assertEqual([o.slug for o in P.merge_same_name([a, b])],
                         ["white-mountains", "white-mountains-arizona"])

    def test_the_same_name_from_two_sources_or_kinds_is_not_merged(self):
        a = outline("park", "1", "Glacier", self.park.geometry, hint=["MT"])
        b = outline("park", "2", "Glacier", self.range.geometry, hint=["BC"])
        b.source = "cpcad"
        w = outline("wilderness", "3", "Glacier", self.range.geometry)
        self.assertEqual(len(P.merge_same_name([a, b, w])), 3)

    def test_two_far_apart_wilderness_areas_of_one_name_stay_two_places(self):
        far = Polygon([(-80, 35), (-79, 35), (-79, 36), (-80, 36)])
        a = outline("wilderness", "1", "Bear Wilderness", self.park.geometry, hint=["WY"])
        b = outline("wilderness", "2", "Bear Wilderness", far, hint=["NC"])
        self.assertEqual(len(P.merge_same_name([a, b])), 2)
        touching = outline("wilderness", "3", "Bear Wilderness", self.range.geometry, hint=["WY"])
        self.assertEqual(len(P.merge_same_name([a, touching])), 1)

    def test_a_wilderness_with_a_parks_exact_trails_and_a_matching_name_is_not_listed(self):
        wild = outline("wilderness", "W1", "Alpha Wilderness", self.park.geometry)
        wild.source = "wilderness-connect"
        records = [rec("a", ["WY"], self.park_only), rec("b", ["WY"], self.park_only),
                   rec("c", ["WY"], self.park_only)]
        p = P.propose(records, [self.park, wild])
        self.assertIn(("park", "alpha-park"), p.per_place)
        self.assertNotIn(("wilderness", "alpha-wilderness"), p.per_place)
        self.assertTrue(all(k[0] != "wilderness" for k, _ in p.per_trail["a"]))
        self.assertEqual([n for n in p.near if n.key[0] == "wilderness"], [])

    def test_the_joined_park_and_its_hyphenated_wilderness_are_one_page(self):
        sets = {("park", "sequoia-and-kings-canyon"): {"a", "b", "c"},
                ("wilderness", "sequoia-kings-canyon-wilderness"): {"a", "b", "c"},
                ("wilderness", "john-muir-wilderness"): {"a", "b", "c"}}
        names = {("park", "sequoia-and-kings-canyon"): "Sequoia and Kings Canyon",
                 ("wilderness", "sequoia-kings-canyon-wilderness"): "Sequoia-Kings Canyon Wilderness",
                 ("wilderness", "john-muir-wilderness"): "John Muir Wilderness"}
        self.assertEqual(P.doubled_places(sets, names), {("wilderness", "sequoia-kings-canyon-wilderness")})

    def test_a_wilderness_with_more_or_fewer_trails_than_the_park_is_kept(self):
        names = {("park", "alpha"): "Alpha National Park", ("wilderness", "alpha-wilderness"): "Alpha Wilderness"}
        sets = {("park", "alpha"): {"a", "b"}, ("wilderness", "alpha-wilderness"): {"a"}}
        self.assertEqual(P.doubled_places(sets, names), set())
        sets[("wilderness", "alpha-wilderness")] = {"a", "b", "c"}
        self.assertEqual(P.doubled_places(sets, names), set())

    def test_a_check_counts_stated_trails_too_when_it_finds_a_doubled_page(self):
        names = {("park", "alpha"): "Alpha National Park", ("wilderness", "alpha-wilderness"): "Alpha Wilderness"}
        tracked = {("park", "alpha"): {"a", "b"}, ("wilderness", "alpha-wilderness"): {"a", "b"}}
        self.assertEqual(len(P.doubled_places(tracked, names)), 1)
        stated = {("park", "alpha"): {"a", "b", "z"}, ("wilderness", "alpha-wilderness"): {"a", "b"}}
        self.assertEqual(P.doubled_places(stated, names), set())

    def test_a_range_with_a_parks_trails_and_name_stem_is_not_a_second_page(self):
        names = {("park", "great-smoky-mountains-national-park"): "Great Smoky Mountains National Park",
                 ("range", "great-smoky-mountains"): "Great Smoky Mountains",
                 ("park", "olympic-national-park"): "Olympic National Park",
                 ("range", "olympic-mountains"): "Olympic Mountains",
                 ("park", "grand-teton-national-park"): "Grand Teton National Park",
                 ("range", "teton-range"): "Teton Range"}
        sets = {k: {"a", "b", "c"} for k in names}
        self.assertEqual(P.doubled_places(sets, names),
                         {("range", "great-smoky-mountains"), ("range", "olympic-mountains")})
        sets[("range", "olympic-mountains")] = {"a", "b", "c", "d"}
        self.assertEqual(P.doubled_places(sets, names), {("range", "great-smoky-mountains")})

    def test_the_deny_list_names_every_place_that_gets_no_page_with_a_reason(self):
        for key in (("range", "gmba-v2", "12330"), ("range", "gmba-v2", "15906"),
                    ("range", "gmba-v2", "11356"), ("range", "gmba-v2", "17612"),
                    ("range", "gmba-v2", "17240"), ("wilderness", "wilderness-connect", "507")):
            self.assertIn(key, P.DENY)
            self.assertGreater(len(P.DENY[key]), 20)

    def test_a_denied_place_is_not_in_the_catalogue(self):
        arch = outline("park", "JEFF", "Gateway Arch National Park", self.park.geometry)
        keep = outline("park", "YOSE", "Yosemite National Park", self.range.geometry)
        self.assertEqual([o.source_id for o in P.apply_denylist([arch, keep])], ["YOSE"])
        self.assertTrue(all(reason.strip() for reason in P.DENY.values()))
        self.assertIn(("park", "nps", "JEFF"), P.DENY)

    def test_the_cpcad_query_asks_for_ontario_and_quebec_parks_and_escapes_quotes(self):
        where = P.cpcad_where()
        self.assertNotIn("LOC IN", where)  # no province is left out by a filter on location
        self.assertIn("'Provincial Park'", where)  # Ontario's type
        self.assertIn("'Quebec''s national park'", where)  # Quebec's type, quote doubled
        self.assertIn("'A - Park'", where)  # British Columbia's

    def test_cpcad_names_are_cleaned_for_a_hiker(self):
        self.assertEqual(P._clean_cpcad_name("Algonquin Provincial Park (Natural Environment Class)"),
                         "Algonquin Provincial Park")
        self.assertEqual(P._clean_cpcad_name("Frontenac National Park (Québec)"),
                         "Frontenac National Park")
        self.assertEqual(P._clean_cpcad_name("Killarney Lakelands And Headwaters Provincial Park"),
                         "Killarney Lakelands and Headwaters Provincial Park")

    def test_a_grown_outline_reaches_a_track_just_outside_it_but_only_inside_its_clip(self):
        # about 20 km east of the park's edge (-109.0): a track the source's outline missed
        east = LineString([(-108.75, 43.2), (-108.75, 43.29)])
        self.assertEqual(P.propose([rec("a", ["WY"], east)], [self.park]).per_trail["a"], [])
        grown = P.grow_outline(self.park.geometry, 25)
        self.assertGreater(grown.area, self.park.geometry.area)
        self.assertTrue(grown.contains(east))
        # a clip keeps the growth off ground the owner did not mean: nothing east of -108.9
        clipped = P.grow_outline(self.park.geometry, 25, clip=[-111.0, 42.0, -108.9, 45.0])
        self.assertFalse(clipped.intersects(east))
        self.assertTrue(clipped.contains(self.park.geometry))

    def test_slugs_drop_accents_and_apostrophes_instead_of_leaving_hyphen_stumps(self):
        self.assertEqual(P.slugify("Gaspésie National Park"), "gaspesie-national-park")
        self.assertEqual(P.slugify("Lion's Head Provincial Park"), "lions-head-provincial-park")
        self.assertEqual(P.slugify("Hautes-Gorges-de-la-Rivière-Malbaie National Park"),
                         "hautes-gorges-de-la-riviere-malbaie-national-park")
        self.assertEqual(P.slugify("Sierra Nevada (USA)"), "sierra-nevada")

    def test_a_small_word_in_a_cpcad_name_is_lower_case_even_after_another(self):
        self.assertEqual(P._clean_cpcad_name("Forks Of The Credit Provincial Park"),
                         "Forks of the Credit Provincial Park")

    def test_a_slug_collision_inside_a_kind_gets_the_state_code(self):
        a = outline("park", "P1", "Glacier", self.park.geometry, slug=None, hint=["MT"])
        b = outline("park", "P2", "Glacier", self.range.geometry, slug=None, hint=["BC"])
        out = P.assign_slugs([a, b])
        self.assertEqual({o.slug for o in out}, {"glacier-mt", "glacier-bc"})

    def test_the_proposal_names_every_trail_with_no_track_as_needing_a_person(self):
        p = P.propose([rec("a", ["WY"], self.inside), rec("z", ["WY"], None)], [self.park])
        self.assertEqual(p.no_track, ["z"])
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "proposal.md")
            P.render_proposal(p, path)
            text = open(path).read()
        self.assertIn("needs a person", text)
        self.assertIn("z", text)

    def test_a_parent_range_is_not_stored_when_a_child_is(self):
        big = outline("range", "R0", "Big Range",
                      Polygon([(-111, 42), (-108, 42), (-108, 45), (-111, 45)]))
        big.path = "Continent > Big Range"
        self.range.path = "Continent > Big Range > Beta Range"
        p = P.propose([rec("a", ["WY"], self.inside)], [big, self.range])
        self.assertEqual({k for k, _ in p.per_trail["a"]}, {("range", "beta-range")})
        # the parent's page count still holds the trail, as measured
        self.assertEqual({t for t, _ in p.per_place[("range", "big-range")].trails}, {"a"})

    def test_one_gmba_id_outside_the_allow_list_is_not_proposed_but_is_listed_by_candidates(self):
        records = [rec(f"t{i}", ["WY"], self.inside) for i in range(3)]
        all_ranges = [dict(gmba_id="R1", name="Beta Range", path="Beta Range",
                           geometry=self.range.geometry)]
        p = P.propose(records, [])  # nothing allow-listed
        self.assertEqual(p.per_place, {})
        found = P.range_candidates(records, all_ranges, allowlisted=set())
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["gmba_id"], "R1")
        self.assertEqual(len(found[0]["trails"]), 3)


import re as _re
import tomllib as _tomllib


@unittest.skipUnless(HAVE, "shapely (the .venv-places venv) is not installed")
class AllowlistTest(unittest.TestCase):
    def setUp(self):
        self.al = P.load_allowlist(P.default_allowlist_path())
        self.by_slug = {}
        for r in self.al["range"]:
            self.by_slug.setdefault(r["slug"], []).append(r)

    def test_the_reviewed_list_has_the_kept_and_the_named_ranges(self):
        slugs = set(self.by_slug)
        for must in ("rocky-mountains", "appalachian-mountains", "palisades", "great-western-divide",
                     "wind-river-range", "teton-range", "uinta-mountains", "wasatch-range",
                     "san-juan-mountains", "sawtooth-range", "beartooth-mountains", "absaroka-range",
                     "bitterroot-range", "great-smoky-mountains", "canadian-rockies",
                     "olympic-mountains", "white-mountains", "bighorn-mountains",
                     "sangre-de-cristo-mountains", "wallowa-mountains", "ruby-mountains", "trinity-alps",
                     "selkirk-mountains", "brooks-range", "alaska-range", "ouachita-mountains",
                     "catskill-mountains"):
            self.assertIn(must, slugs)
        self.assertNotIn("ozark-mountains", slugs)  # the source has only the Ozark Plateau
        self.assertEqual(self.by_slug["white-mountains"][0]["gmba_id"], "12331")

    def test_at_most_two_kept_levels_apply_to_a_trail(self):
        for r in self.al["range"]:
            for parent in r.get("within") or []:
                self.assertIn(parent, self.by_slug, f"{r['slug']} names an unknown parent")
                for grand in self.by_slug[parent][0].get("within") or []:
                    self.fail(f"{r['slug']} > {parent} > {grand} is three levels")

    def test_a_slug_is_on_one_name_and_display_names_carry_no_source_qualifier(self):
        for slug, rows in self.by_slug.items():
            self.assertEqual(len({r["name"] for r in rows}), 1, slug)
        for r in self.al["range"]:
            self.assertNotIn("(", r["name"], r["slug"])

    def test_a_park_entry_carries_no_where_it_was_not_given(self):
        glacier = [p for p in self.al["park"] if p["source_id"] == "GLAC"][0]
        self.assertNotIn("where", glacier)  # the source's own state field says MT
        self.assertEqual(glacier["slug"], "glacier")

    def test_every_range_has_its_states_where_a_hand_value_is_given_and_codes_are_known(self):
        known = set(P.state_boxes())
        for r in self.al["range"]:
            for c in r.get("where") or []:
                self.assertIn(c, known, r["slug"])


def make_repo(root):
    """Three tracked records and one trackless, minimal trail.toml files."""
    for rid, line in (("aa", True), ("bb", True), ("cc", True), ("zz", False)):
        d = os.path.join(root, rid)
        os.makedirs(d)
        with open(os.path.join(d, "trail.toml"), "w") as f:
            f.write(f'id = "{rid}"\nname = "{rid} Trail"\nregions = ["WY"]\n\n'
                    f'[source]\nline_file = "{"line.geojson" if line else ""}"\n\n'
                    '[[history]]\ndate = "2026-01-01"\nchange = "The record was added."\n'
                    'fields = ["record"]\nbasis = "The record\'s own source entry."\n'
                    'asked_by = "the dataset\'s own check"\noutcome = "applied"\n')
        if line:
            write_track(d, "line.geojson", [[[-109.5, 43.2], [-109.5, 43.29]]])
    with open(os.path.join(root, "places.toml"), "w") as f:
        f.write("# The place registry (test).\n")


def read_toml(path):
    with open(path, "rb") as f:
        return _tomllib.load(f)


@unittest.skipUnless(HAVE, "shapely (the .venv-places venv) is not installed")
class HistoryWordsTest(unittest.TestCase):
    def test_a_few_places_are_named_and_many_are_counted(self):
        self.assertEqual(P.place_list(["park", "range"], ["Alpha Park", "Beta Range"]),
                         "Alpha Park and Beta Range")
        kinds = ["park"] * 7 + ["range"] * 4 + ["wilderness"] * 42
        text = P.place_list(kinds, [f"P{i}" for i in range(53)])
        self.assertEqual(text, "53 places (7 parks, 4 ranges and 42 wilderness areas), "
                               "all listed in the record")
        self.assertEqual(P.place_list(["park"] * 9, [f"P{i}" for i in range(9)]),
                         "9 parks, all listed in the record")
        self.assertNotIn("P1,", text)

    def test_the_limit_is_eight_names(self):
        eight = [f"P{i}" for i in range(8)]
        self.assertIn("P7", P.place_list(["park"] * 8, eight))
        self.assertNotIn("P7", P.place_list(["park"] * 9, eight + ["P8"]))

    def test_one_kind_has_no_and(self):
        self.assertEqual(P.count_places(["wilderness"] * 9), "9 wilderness areas")
        self.assertEqual(P.count_places(["park", "range", "range", "range", "range", "range",
                                         "range", "range", "range"]), "1 park and 8 ranges")


@unittest.skipUnless(HAVE, "shapely (the .venv-places venv) is not installed")
class RefreshTest(unittest.TestCase):
    def test_fetch_keeps_a_cached_file_and_clear_cache_makes_the_next_fetch_download(self):
        with tempfile.TemporaryDirectory() as cache:
            src = P.SOURCES["gmba-v2"]
            dest = os.path.join(cache, src.filename)
            with open(dest, "w") as f:
                f.write("old")
            calls = []
            real = P._download
            P._download = lambda url, d: (calls.append(url), open(d, "w").write("new"))
            try:
                P.fetch(src, cache)
                self.assertEqual(calls, [])
                self.assertEqual(P.clear_cache(cache), [src.filename])
                P.fetch(src, cache)
            finally:
                P._download = real
            self.assertEqual(len(calls), 1)
            with open(dest) as f:
                self.assertEqual(f.read(), "new")

    def test_the_monthly_workflow_checks_against_fresh_outlines(self):
        with open(os.path.join(ROOT, ".github", "workflows", "places.yml")) as f:
            text = f.read()
        self.assertIn("place_trails.py --check --refresh", text)
        self.assertNotIn("actions/cache", text)


@unittest.skipUnless(HAVE, "shapely (the .venv-places venv) is not installed")
class ApplyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        make_repo(self.root)
        self.park = outline("park", "P1", "Alpha Park",
                            Polygon([(-110, 43), (-109, 43), (-109, 44), (-110, 44)]), hint=["WY"])
        track = LineString([(-109.5, 43.2), (-109.5, 43.29)])
        records = [rec("aa", ["WY"], track), rec("bb", ["WY"], track),
                   rec("cc", ["WY"], track), rec("zz", ["WY"], None)]
        self.p = P.propose(records, [self.park])
        self.p.versions = {"nps": "2026-11-20"}
        self.pdir = os.path.join(self.root, "out")
        P.render_proposal(self.p, os.path.join(self.pdir, "proposal.md"))
        self.pjson = os.path.join(self.pdir, "proposal.json")

    def tearDown(self):
        self.tmp.cleanup()

    def trail_toml(self, rid):
        return os.path.join(self.root, rid, "trail.toml")

    def test_apply_adds_place_tables_stamp_and_hash_by_line_edits(self):
        before = open(self.trail_toml("aa")).read()
        written = P.apply(self.pjson, self.root, "2026-11-20")
        self.assertIn("aa", written)
        after = open(self.trail_toml("aa")).read()
        data = read_toml(self.trail_toml("aa"))
        self.assertEqual(data["places_checked"], "2026-11-20")
        self.assertEqual(data["places_track"],
                         C.track_hash(os.path.join(self.root, "aa", "line.geojson")))
        self.assertEqual(data["place"][0]["slug"], "alpha-park")
        # everything that was there before is still there, byte for byte, as lines
        for line in before.splitlines():
            if line.strip():
                self.assertIn(line, after.splitlines(), line)

    def test_apply_leaves_a_trail_with_no_track_alone_for_a_person_to_place(self):
        before = open(self.trail_toml("zz"), "rb").read()
        written = P.apply(self.pjson, self.root, "2026-11-20")
        self.assertNotIn("zz", written)
        self.assertEqual(open(self.trail_toml("zz"), "rb").read(), before)

    def test_apply_adds_one_history_entry_naming_place_with_no_distance_in_it(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        data = read_toml(self.trail_toml("aa"))
        self.assertEqual(len(data["history"]), 2)
        e = data["history"][-1]
        self.assertEqual(e["fields"], ["place"])
        self.assertEqual(e["asked_by"], "the dataset's own check")
        self.assertTrue(e["basis_url"].startswith("http"))
        self.assertIsNone(_re.search(r"\d\s*(km|mi)", e["change"] + e["basis"]))

    def test_a_rerun_that_only_changes_km_adds_no_history_and_keeps_the_stamp_date_rule(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        data = json.load(open(self.pjson))
        data["per_trail"]["aa"][0]["km"] += 1.25
        data["per_place"]["park/alpha-park"]["trails"][0]["km"] += 1.25
        p2 = os.path.join(self.pdir, "proposal2.json")
        json.dump(data, open(p2, "w"))
        P.apply(p2, self.root, "2026-12-01")
        rec = read_toml(self.trail_toml("aa"))
        self.assertEqual(len(rec["history"]), 2)  # no new entry
        self.assertEqual(rec["places_checked"], "2026-12-01")
        self.assertAlmostEqual(rec["place"][0]["km"], data["per_trail"]["aa"][0]["km"], delta=0.06)

    def test_a_rerun_that_adds_or_removes_a_place_adds_history(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        data = json.load(open(self.pjson))
        data["per_trail"]["aa"] = []
        p2 = os.path.join(self.pdir, "proposal2.json")
        json.dump(data, open(p2, "w"))
        P.apply(p2, self.root, "2026-12-01")
        rec = read_toml(self.trail_toml("aa"))
        self.assertEqual(len(rec["history"]), 3)
        self.assertNotIn("place", rec)

    def test_registry_lists_only_named_places_and_is_sorted(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        reg = read_toml(os.path.join(self.root, "places.toml"))["place"]
        self.assertEqual([e["slug"] for e in reg], ["alpha-park"])
        self.assertEqual(reg[0]["source_version"], "2026-11-20")
        self.assertEqual(reg[0]["box"], [-110.0, 43.0, -109.0, 44.0])

    def test_the_registry_holds_the_parent_of_a_named_range_though_no_record_names_it(self):
        big = outline("range", "R0", "Big Range", Polygon([(-111, 42), (-108, 42), (-108, 45), (-111, 45)]))
        big.path = "World > Big Range"
        small = outline("range", "R1", "Small Range", Polygon([(-110, 43), (-109, 43), (-109, 44), (-110, 44)]))
        small.path = "World > Big Range > Small Range"
        small.within = ("big-range",)
        track = LineString([(-109.5, 43.2), (-109.5, 43.29)])
        p = P.propose([rec("aa", ["WY"], track), rec("bb", ["WY"], track), rec("cc", ["WY"], track)],
                      [big, small])
        p.versions = {"nps": "2026-11-20"}
        d = os.path.join(self.root, "out2")
        P.render_proposal(p, os.path.join(d, "proposal.md"))
        P.apply(os.path.join(d, "proposal.json"), self.root, "2026-11-20")
        self.assertEqual([pl["slug"] for pl in read_toml(self.trail_toml("aa"))["place"]], ["small-range"])
        reg = {e["slug"]: e for e in read_toml(os.path.join(self.root, "places.toml"))["place"]}
        self.assertEqual(set(reg), {"big-range", "small-range"})
        self.assertEqual(reg["small-range"]["within"], ["big-range"])

    def test_a_reviewed_where_in_the_registry_survives_a_rerun(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        path = os.path.join(self.root, "places.toml")
        text = open(path).read()
        self.assertIn('where = ["WY"]', text)
        open(path, "w").write(text.replace('where = ["WY"]', 'where = ["MT", "WY"]'))
        P.apply(self.pjson, self.root, "2026-12-01")
        self.assertEqual(read_toml(path)["place"][0]["where"], ["MT", "WY"])

    def test_stated_requires_an_http_source_a_quote_and_a_trackless_record(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        with self.assertRaises(ValueError):
            P.add_stated(self.root, "zz", "park", "alpha-park", "a book", "It says so.", "2026-11-20")
        with self.assertRaises(ValueError):
            P.add_stated(self.root, "zz", "park", "alpha-park", "https://example.org/", "", "2026-11-20")
        with self.assertRaises(ValueError):
            P.add_stated(self.root, "aa", "park", "alpha-park", "https://example.org/", "Q.", "2026-11-20")
        P.add_stated(self.root, "zz", "park", "alpha-park", "https://example.org/t",
                     "The trail crosses Alpha Park.", "2026-11-20")
        rec = read_toml(self.trail_toml("zz"))
        self.assertEqual(rec["place"][0]["basis"], "stated")
        self.assertEqual(rec["places_checked"], "2026-11-20")
        self.assertEqual(rec["history"][-1]["fields"], ["place"])

    def test_a_second_apply_of_the_same_proposal_leaves_every_record_byte_identical(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        before = {t: open(self.trail_toml(t)).read() for t in ("aa", "bb", "cc")}
        self.assertEqual(P.apply(self.pjson, self.root, "2026-11-20"), [])
        for t, text in before.items():
            self.assertEqual(open(self.trail_toml(t)).read(), text)

    def test_stated_many_writes_every_place_with_one_history_entry(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        reg = P.registry_entries(self.root)
        reg.append({"slug": "beta-range", "kind": "range", "name": "Beta Range", "where": ["WY"],
                    "source": "gmba-v2", "source_id": "1", "source_version": "x", "box": [0, 0, 1, 1]})
        P.write_registry(self.root, reg)
        before = len(read_toml(self.trail_toml("zz"))["history"])
        P.add_stated_many(self.root, "zz", [
            {"kind": "park", "slug": "alpha-park", "source": "https://example.org/t", "quote": "Q one."},
            {"kind": "range", "slug": "beta-range", "source": "https://example.org/t", "quote": "Q one."},
        ], "2026-11-20")
        rec = read_toml(self.trail_toml("zz"))
        self.assertEqual([p["slug"] for p in rec["place"]], ["alpha-park", "beta-range"])
        self.assertEqual(len(rec["history"]), before + 1)
        self.assertIn("Alpha Park and Beta Range", rec["history"][-1]["change"])
        self.assertEqual(rec["history"][-1]["fields"], ["place"])

    def test_stamp_none_sets_places_checked_with_no_place_tables_and_no_history(self):
        P.stamp_none(self.root, "zz", "2026-11-20")
        rec = read_toml(self.trail_toml("zz"))
        self.assertEqual(rec["places_checked"], "2026-11-20")
        self.assertNotIn("place", rec)
        self.assertEqual(len(rec["history"]), 1)

    def test_check_reports_a_place_gained_lost_a_moved_boundary_and_a_place_crossing_three_trails(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        records = P.load_records(self.root)
        moved = outline("park", "P1", "Alpha Park",
                        Polygon([(-110, 43), (-109, 43), (-109, 43.25), (-110, 43.25)]), hint=["WY"])
        diffs = P.check(self.root, None, outlines=[moved], versions={"nps": "2026-11-20"},
                        records=records)
        text = "\n".join(diffs)
        self.assertIn("measurement changed", text)  # the moved boundary
        gone = outline("park", "P9", "Elsewhere Park",
                       Polygon([(-100, 43), (-99, 43), (-99, 44), (-100, 44)]), hint=["WY"])
        diffs = P.check(self.root, None, outlines=[gone], versions={"nps": "2026-11-20"},
                        records=records)
        text = "\n".join(diffs)
        self.assertIn("lost park/alpha-park", text)
        self.assertIn("crossed the 3-trail line", text)

    def test_check_exits_nonzero_with_differences_and_zero_without(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        records = P.load_records(self.root)
        self.assertEqual(P.check(self.root, None, outlines=[self.park],
                                 versions={"nps": "2026-11-20"}, records=records), [])

    def test_the_written_records_pass_check_places(self):
        P.apply(self.pjson, self.root, "2026-11-20")
        P.stamp_none(self.root, "zz", "2026-11-20")
        trails = [read_toml(self.trail_toml(r)) for r in ("aa", "bb", "cc", "zz")]
        errors = []
        C.check(self.root, trails, errors)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
