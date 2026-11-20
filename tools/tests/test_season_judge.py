"""Tests for tools/season_judge.py: the packets reviewers judge a season from,
the blind scoring, and the proposals that write the judged seasons.

Run from the repository root:
    python3 -m unittest discover tools/tests
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import season_judge as J  # noqa: E402
import season_climate as C  # noqa: E402
import season_model as M  # noqa: E402
import estimate_season as E  # noqa: E402
import test_refresh as TR  # noqa: E402
import refresh as R  # noqa: E402
import trail_history  # noqa: E402
import validate as V  # noqa: E402


class CleanTest(unittest.TestCase):
    def test_a_sentence_that_bears_on_timing_is_removed_and_logged(self):
        kept, removed = J.clean("A pretty ridge walk. Best in July and August. It has huts.")
        self.assertEqual(kept, "A pretty ridge walk. It has huts.")
        self.assertEqual(removed, ["Best in July and August."])

    def test_season_words_count_but_place_names_do_not(self):
        self.assertTrue(J.mentions_season("Snowmelt comes late."))
        self.assertTrue(J.mentions_season("Open year-round."))
        self.assertFalse(J.mentions_season("It crosses May Lake and Summer Lake."))
        self.assertFalse(J.mentions_season("It passes the Hot Springs."))

    def test_nothing_left_is_said_so(self):
        kept, _ = J.clean("Best in summer.")
        self.assertEqual(kept, "")
        self.assertIn("none left", J.shown(kept, "x"))
        self.assertEqual(J.shown("", None), "(not on file)")


class SplitTest(unittest.TestCase):
    def test_parts_are_disjoint_balanced_and_repeatable(self):
        src = [f"s{i}" for i in range(10)]
        oth = [f"o{i}" for i in range(7)]
        parts = J.split_parts(src, oth, 3, 1)
        flat = [t for p in parts for t in p]
        self.assertEqual(sorted(flat), sorted(src + oth))
        for part in parts:
            self.assertIn(sum(t in src for t in part), (3, 4))
            self.assertIn(sum(t in oth for t in part), (2, 3))
        self.assertEqual(parts, J.split_parts(src, oth, 3, 1))
        self.assertNotEqual(parts, J.split_parts(src, oth, 3, 2))


def med(base):
    return ([base] * 12, [base] * 12)


class ComparablesTest(unittest.TestCase):
    def test_a_trail_is_never_compared_with_its_own_part_or_itself(self):
        part_of = {"me": 0, "mate": 0, "a": 1, "b": 2}
        meds = {k: med(10.0) for k in part_of}
        centres = {k: (45.0, -110.0) for k in part_of}
        got = J.comparables("me", part_of, ["mate", "a", "b", "me"], meds, centres, k=10)
        self.assertEqual(sorted(got), ["a", "b"])

    def test_the_nearest_in_climate_and_place_come_first(self):
        part_of = {"me": 0, "near": 1, "far": 1, "cold": 2}
        meds = {"me": med(10.0), "near": med(10.0), "far": med(10.0), "cold": med(-5.0)}
        centres = {"me": (45.0, -110.0), "near": (45.5, -110.0),
                   "far": (30.0, -80.0), "cold": (45.1, -110.0)}
        got = J.comparables("me", part_of, ["near", "far", "cold"], meds, centres, k=2)
        self.assertEqual(got, ["near", "far"])


def info(kind="track"):
    pts = [C.PointNormals(lat=44.0 + i, lon=-110.0, elev_m=1000.0 * (i + 1),
                          tmax_c=tuple(float(v) for v in range(12)))
           for i in range(4)]
    return {"points": pts, "kind": kind, "profile": (3500.0, 800.0)}


class PacketTest(unittest.TestCase):
    def rec(self):
        return {"id": "tt", "name": "Test Trail", "country": "US", "regions": ["WY"],
                "length_km": 160.9344, "kind": "trail",
                "hike": {"summary": "A ridge walk. Best in July. It has huts.",
                         "start": "Trailhead.", "terrain": ["alpine"], "high_point_m": 3000,
                         "days": [8, 10]}}

    def text(self, **kw):
        args = dict(rec=self.rec(), info=info(), machine=[6, 7, 8],
                    comparables=[], pages=None, precip=None)
        args.update(kw)
        return J.packet_text(**args)

    def test_the_packet_states_the_trail_in_miles_and_feet_and_hides_timing(self):
        t = self.text()
        self.assertIn("length: 100 miles", t)
        self.assertIn("high point: 9843 ft", t)
        self.assertIn("A ridge walk. It has huts.", t)
        self.assertNotIn("Best in July", t)

    def test_it_never_carries_the_trails_own_season(self):
        rec = self.rec()
        rec["hike"].update(season="July to September", months=[7, 8, 9], season_basis="primary")
        t = self.text(rec=rec)
        self.assertNotIn("July to September", t)

    def test_it_gives_the_machine_estimate_and_the_climate(self):
        t = self.text()
        self.assertIn("Months: 6, 7, 8 (June, July, August)", t)
        self.assertIn("| Jan |", t)
        self.assertIn("Precipitation is not available", t)

    def test_precipitation_is_given_when_supplied(self):
        t = self.text(precip=[[25.4] * 12] * 4)
        self.assertIn("precip in", t)
        self.assertNotIn("Precipitation is not available", t)

    def test_what_pages_say_appears_only_when_given(self):
        self.assertNotIn("What pages say", self.text())
        self.assertIn("Months each gives: A 5-10", self.text(pages="Publisher(s): A\nMonths each gives: A 5-10"))

    def test_a_trail_with_no_climate_says_so(self):
        t = self.text(info=dict(info(), points=[]), machine=[])
        self.assertIn("No climate data is available", t)
        self.assertIn("Months: none", t)


class AnswersTest(unittest.TestCase):
    def write(self, text):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "a.tsv")
        with open(path, "w") as f:
            f.write(text)
        return path

    def test_good_rows_are_read_and_bad_rows_are_named(self):
        path = self.write(
            "aa\t7,8,9\tJuly to September\thigh\tSnow melts.\n"
            "bb\t\tNone\thigh\tEmpty.\n"
            "cc\t13\tX\thigh\tOut of range.\n"
            "dd\t6\tJune\tsure\tBad confidence.\n"
            "aa\t6\tJune\tlow\tDuplicate.\n"
            "zz\t6\tJune\tlow\tUnknown.\n"
            "ee\t5,6\tMay to June\tmedium\tFine.\n")
        ans, problems = J.read_answers(path, ["aa", "bb", "cc", "dd", "ee"])
        self.assertEqual(sorted(ans), ["aa", "ee"])
        self.assertEqual(ans["aa"], ([7, 8, 9], "July to September", "high", "Snow melts."))
        self.assertEqual(len(problems), 5)


class ScoreTest(unittest.TestCase):
    def test_matches_are_counted_within_a_month_at_each_end_by_confidence(self):
        truth = {"a": [6, 7, 8, 9], "b": [6, 7, 8, 9], "c": [6, 7, 8, 9], "d": [1, 2, 3]}
        ans = {"a": ([6, 7, 8, 9], "", "high", ""),   # exact
               "b": ([7, 8, 9, 10], "", "medium", ""),  # one month at each end
               "c": ([1, 2, 3], "", "low", ""),       # wrong
               "x": ([1], "", "high", "")}            # not a sourced trail: ignored
        got = J.score(ans, truth)
        self.assertEqual(got["tested"], 4)
        self.assertEqual(got["matched"], 2)
        self.assertEqual(got["by_confidence"]["high"], {"tested": 1, "matched": 1})
        self.assertEqual(got["by_confidence"]["medium"], {"tested": 1, "matched": 1})
        self.assertEqual(got["by_confidence"]["low"], {"tested": 1, "matched": 0})
        # d was never answered: it counts as tested and missed
        self.assertEqual(got["unanswered"], 1)

    def test_the_figure_file_round_trips_and_shares_are_computed(self):
        figures = {"tested": 148, "matched": 114, "unanswered": 0,
                   "by_confidence": {"high": {"tested": 52, "matched": 48},
                                     "medium": {"tested": 76, "matched": 55},
                                     "low": {"tested": 20, "matched": 11}}}
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "t.json")
        J.write_blind_test(path, figures, "2026-11-20")
        got = J.load_blind_test(path)
        self.assertEqual(got["date"], "2026-11-20")
        self.assertEqual(got["tested"], 148)
        self.assertEqual(got["matched"], 114)
        self.assertEqual(got["share"], 0.77)
        self.assertEqual(got["by_confidence"]["high"]["share"], 0.92)
        self.assertEqual(got["by_confidence"]["low"]["share"], 0.55)

    def test_a_loaded_file_must_add_up(self):
        bad = {"date": "2026-11-20", "tested": 10, "matched": 5, "share": 0.5,
               "by_confidence": {"high": {"tested": 4, "matched": 5, "share": 1.0},
                                 "medium": {"tested": 3, "matched": 1, "share": 0.33},
                                 "low": {"tested": 3, "matched": 1, "share": 0.33}}}
        self.assertTrue(J.check_blind_test(bad))


class CommittedFilesTest(unittest.TestCase):
    def test_the_committed_blind_test_adds_up_and_passes_the_bar(self):
        got = J.load_blind_test(os.path.join(J.ROOT, "tools", "season_blind_test.json"))
        self.assertEqual(J.check_blind_test(got), [])
        self.assertGreaterEqual(got["share"], E.BAR["within1_min"])

    def test_every_judged_row_is_well_formed_and_matches_its_record(self):
        ids = R.trail_ids(J.ROOT)
        ans, problems = J.read_answers(os.path.join(J.ROOT, "tools", "season_judged.tsv"), ids)
        self.assertEqual(problems, [])
        self.assertEqual(sorted(ans), sorted(ids))
        for tid in ids:
            hike = R.load_toml(os.path.join(J.ROOT, tid, "trail.toml")).get("hike") or {}
            if hike.get("season_basis") == "estimate" or hike.get("season_method"):
                months, _phrase, conf, _why = ans[tid]
                self.assertEqual(months, hike["months"], tid)
                self.assertEqual(J.season.confidence_of(hike["season_method"]), conf, tid)


class ProposalsTest(unittest.TestCase):
    HIKE = 'start_lonlat = [-110.0, 43.0]\nend_lonlat = [-110.0, 43.2]\n'

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = TR.make_repo(self.tmp, trails=[
            ("aaa", "Aaa", {"extra_hike": self.HIKE}),
            ("bbb", "Bbb", {"extra_hike": self.HIKE}),
            ("ccc", "Ccc", {"extra_hike": 'season = "June"\nmonths = [6]\nseason_basis = "source"\n' + self.HIKE}),
        ])
        self.stage = os.path.join(self.tmp, "stage")
        os.makedirs(self.stage)
        self.answers = os.path.join(self.tmp, "judged.tsv")
        with open(self.answers, "w") as f:
            f.write("aaa\t7,8,9\tJuly to September\thigh\tSnow melts late.\n"
                    "bbb\t5,6,7,8,9,10\tMay to October\tmedium\tThe pages differ.\n"
                    "ccc\t1,2\tJanuary to February\tlow\tNot used: it has a season.\n")
        self.pages = os.path.join(self.tmp, "pages.json")
        with open(self.pages, "w") as f:
            json.dump({"bbb": {
                "why": "The pages differ: one says May to September and one says June to October. "
                       "It was set by judgement from both and from the climate.",
                "sources": [
                    {"url": "https://a.example/bbb", "publisher": "Guide A", "quote": "Season: May to September"},
                    {"url": "https://b.example/bbb", "publisher": "Guide B", "quote": "Season: June to October"}]}}, f)

    def test_only_trails_with_no_season_are_staged(self):
        n = J.proposals(self.root, self.answers, self.pages, self.stage)
        self.assertEqual(n, 2)

    def test_collect_and_apply_write_valid_records_with_history(self):
        J.proposals(self.root, self.answers, self.pages, self.stage)
        code, out = TR.main(self.root, "--dir", self.stage, "collect")
        self.assertEqual(code, 0, out)
        coll = R.load_toml(os.path.join(self.stage, "collected.toml"))
        self.assertEqual({p["status"] for p in coll["proposal"]}, {"proposed"}, out)
        with open(os.path.join(self.stage, "owner.csv"), "w") as f:
            f.write("pid,decision,digest\n")
            for p in coll["proposal"]:
                f.write(f"{p['pid']},accept,{p['digest']}\n")
        code, out = TR.main(self.root, "--dir", self.stage, "collect")
        self.assertEqual(code, 0, out)
        code, out = TR.main(self.root, "--dir", self.stage, "apply")
        self.assertEqual(code, 0, out)
        a = R.load_toml(os.path.join(self.root, "aaa", "trail.toml"))
        h = a["hike"]
        self.assertEqual((h["season"], h["months"], h["season_basis"]),
                         ("July to September", [7, 8, 9], "estimate"))
        self.assertTrue(h["season_method"].endswith("Confidence: high."))
        self.assertIn("Snow melts late.", h["season_method"])
        self.assertEqual(len(h["source"]), 3)  # two the record had, and the climate data
        self.assertEqual(h["source"][-1]["facts"], ["season", "months"])
        self.assertIn("chelsa", h["source"][-1]["url"])
        errors = []
        V.check_hike("aaa", a, errors)
        trail_history.check_entries("aaa", a, errors)
        # (the fixture's own end-point fields are not what is under test)
        self.assertEqual([e for e in errors if "lonlat" not in e], [], errors)
        self.assertTrue(any("hike.season" in (e.get("fields") or []) for e in a["history"]))
        b = R.load_toml(os.path.join(self.root, "bbb", "trail.toml"))["hike"]
        self.assertEqual(b["season_basis"], "sources")
        self.assertIn("The pages differ", b["season_method"])
        self.assertEqual([s["publisher"] for s in b["source"]][-2:], ["Guide A", "Guide B"])
        errors = []
        V.check_hike("bbb", {"hike": b}, errors)
        self.assertEqual([e for e in errors if "lonlat" not in e], [], errors)


if __name__ == "__main__":
    unittest.main()
