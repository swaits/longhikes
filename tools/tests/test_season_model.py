"""Tests for tools/season_model.py: the measure, the thresholds, the
comparable trails, the blend and the leave-one-out fit. No network."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import season_model as M  # noqa: E402

P = M.Params(cold_c_min=5.0, heat_c_max=30.0, k=3, power=1, mix=0.7, cut=0.65)


def med(high, low=None):
    return (tuple(float(v) for v in high), tuple(float(v) for v in (low or high)))


SUMMER = [-5, -3, 0, 5, 10, 15, 20, 20, 14, 8, 0, -4]
WINTER = [14, 16, 20, 26, 33, 39, 42, 41, 36, 28, 20, 15]


class MatchTest(unittest.TestCase):
    def test_a_single_window_matches_within_one_month_at_each_end(self):
        self.assertTrue(M.match([6, 7, 8, 9], [6, 7, 8, 9]))
        self.assertTrue(M.match([5, 6, 7, 8, 9, 10], [6, 7, 8, 9]))
        self.assertFalse(M.match([4, 5, 6, 7, 8, 9], [6, 7, 8, 9]))
        self.assertFalse(M.match([], [6, 7, 8, 9]))

    def test_a_season_over_the_year_end_is_one_window(self):
        self.assertTrue(M.match([11, 12, 1, 2], [12, 1, 2, 3]))

    def test_a_year_round_season_matches_ten_or_more_months(self):
        year = list(range(1, 13))
        self.assertTrue(M.match(year, year))
        self.assertTrue(M.match(list(range(1, 11)), year))
        self.assertFalse(M.match(list(range(1, 10)), year))

    def test_two_windows_are_compared_window_by_window(self):
        spring_fall = [3, 4, 5, 9, 10, 11]
        self.assertTrue(M.match([3, 4, 5, 9, 10, 11], spring_fall))
        self.assertTrue(M.match([4, 5, 9, 10], spring_fall))
        # one long window covers the span but is not two windows
        self.assertFalse(M.match(list(range(3, 12)), spring_fall))
        # a window with no partner, and a window left over
        self.assertFalse(M.match([3, 4, 5], spring_fall))
        self.assertFalse(M.match([3, 4, 5, 7, 9, 10, 11], spring_fall))

    def test_the_strict_measure_counts_a_wrong_gap_in_the_middle_as_a_miss(self):
        # the ends-only measure passes March to May plus September to November
        # against a continuous March to November; the strict one does not
        gap = [3, 4, 5, 9, 10, 11]
        whole = list(range(3, 12))
        self.assertTrue(M.match(gap, whole))
        self.assertFalse(M.match_strict(gap, whole))
        self.assertFalse(M.match_strict(whole, gap))
        self.assertTrue(M.match_strict(whole, whole))
        self.assertTrue(M.match_strict([4, 5, 6, 7, 8, 9, 10], whole))
        self.assertTrue(M.match_strict(gap, gap))
        # a stray one-month window of the estimate has no partner in the truth
        self.assertFalse(M.match_strict([3, 4, 5, 6, 7, 11], [3, 4, 5, 6, 7]))
        self.assertTrue(M.match_strict(list(range(1, 11)), list(range(1, 13))))
        self.assertFalse(M.match_strict([], whole))

    def test_strict_never_matches_what_the_ends_only_measure_misses(self):
        import itertools
        seasons = [[3, 4, 5, 9, 10, 11], list(range(3, 12)), [6, 7, 8], [11, 12, 1, 2], [1, 2, 3, 7, 8],
                   list(range(1, 13)), [5, 6, 7, 8, 9, 10]]
        for est, src in itertools.product(seasons, seasons):
            if M.match_strict(est, src):
                self.assertTrue(M.match(est, src), (est, src))

    def test_masks_and_lists_agree(self):
        self.assertEqual(M.to_months(M.to_mask([3, 1, 12])), [1, 3, 12])
        self.assertEqual(M.match(M.to_mask([6, 7]), [6, 7]), True)

    def test_score_has_the_three_measures(self):
        a, b, c = M.score([6, 7, 8], [7, 8, 9])
        self.assertEqual(a, 1.0)
        self.assertAlmostEqual(b, 10 / 12)
        self.assertAlmostEqual(c, 2 / 4)
        self.assertEqual(M.score([1], [1]), (1.0, 1.0, 1.0))


class ThresholdsAndBlendTest(unittest.TestCase):
    def test_thresholds_use_high_ground_cold_and_low_ground_heat(self):
        got = M.threshold_mask(med(SUMMER, WINTER), P)
        # cold: high ground at least 5 in April to October; heat: low
        # ground at most 30 in October to April
        self.assertEqual(M.to_months(got), [4, 10])

    def test_a_vote_is_the_weighted_share_of_comparable_trails(self):
        a = M.Reference("a", med(SUMMER), [6, 7, 8])
        b = M.Reference("b", med(SUMMER), [7, 8, 9])
        near = [(0.0, a), (0.0, b)]
        v = M.vote(near, 1)
        self.assertEqual(v[5], 0.5)
        self.assertEqual(v[6], 1.0)
        self.assertEqual(v[8], 0.5)
        self.assertEqual(v[0], 0.0)

    def test_closer_trails_weigh_more(self):
        a = M.Reference("a", med(SUMMER), [6])
        b = M.Reference("b", med(SUMMER), [7])
        v = M.vote([(0.0, a), (0.5, b)], 2)
        self.assertGreater(v[5], v[6])

    def test_nearest_leaves_out_the_trail_itself(self):
        refs = [M.Reference("self", med(SUMMER), [7]),
                M.Reference("other", med([x + 1 for x in SUMMER]), [8])]
        got = M.nearest(med(SUMMER), refs, 5, exclude="self")
        self.assertEqual([r.id for _d, r in got], ["other"])

    def test_a_trail_inherits_a_cool_season_from_trails_like_it(self):
        desert = med(WINTER)
        refs = [M.Reference(f"d{i}", med([x + i * 0.2 for x in WINTER]),
                            [11, 12, 1, 2, 3]) for i in range(4)]
        near = M.nearest(desert, refs, 3)
        mask, scores, fell = M.blend(desert, near, P)
        self.assertEqual(M.to_months(mask), [1, 2, 3, 11, 12])
        self.assertFalse(fell)

    def test_without_comparable_trails_the_thresholds_stand_alone(self):
        mask, _s, fell = M.blend(med(SUMMER), [], P)
        self.assertEqual(M.to_months(mask), [4, 5, 6, 7, 8, 9, 10])
        self.assertFalse(fell)

    def test_an_empty_result_falls_back_to_three_months_and_says_so(self):
        arctic = med([-20, -18, -12, -6, -1, 3, 4, 2, -3, -9, -15, -19])
        mask, _s, fell = M.blend(arctic, [], P)
        self.assertTrue(fell)
        self.assertEqual(M.to_months(mask), [6, 7, 8])
        self.assertEqual(len(M.to_months(mask)), 3)

    def test_months_in_season_is_none_for_a_gap_and_never_empty(self):
        class Pt:
            def __init__(self, tmax, elev=100.0):
                self.tmax_c = tuple(tmax)
                self.elev_m = elev
        self.assertIsNone(M.months_in_season([Pt(SUMMER), None], P))
        self.assertIsNone(M.months_in_season([], P))
        got = M.months_in_season([Pt([-30] * 12)], P)
        self.assertEqual(len(got), 3)


class ConfidenceTest(unittest.TestCase):
    def refs(self, spread):
        return [M.Reference(f"r{i}", med([x + i * spread for x in SUMMER]), [6, 7, 8, 9])
                for i in range(4)]

    def test_close_agreeing_comparable_trails_give_high(self):
        near = M.nearest(med(SUMMER), self.refs(0.1), 4)
        mask, scores, fell = M.blend(med(SUMMER), near, P)
        level, why = M.confidence(med(SUMMER), near, scores, fell)
        self.assertEqual(level, "high", why)

    def test_far_comparable_trails_give_low(self):
        near = M.nearest(med(SUMMER), self.refs(8.0), 4)
        mask, scores, fell = M.blend(med(SUMMER), near, P)
        level, why = M.confidence(med(SUMMER), near, scores, fell)
        self.assertEqual(level, "low")
        self.assertIn("far", why)

    def test_disagreeing_comparable_trails_give_low(self):
        refs = self.refs(0.1)
        for ref, months in zip(refs, ([4, 5, 6], [7, 8, 9], [5, 6, 7, 8],
                                      [6, 7, 8, 9, 10])):
            ref.mask = M.to_mask(months)
        near = M.nearest(med(SUMMER), refs, 4)
        mask, scores, fell = M.blend(med(SUMMER), near, P)
        level, why = M.confidence(med(SUMMER), near, scores, fell)
        self.assertEqual(level, "low")
        self.assertIn("disagree", why)

    def test_no_comparable_trails_is_low(self):
        self.assertEqual(M.confidence(med(SUMMER), [], [0] * 12, False)[0], "low")


class FitTest(unittest.TestCase):
    def trails(self):
        out = []
        for i in range(8):
            out.append((f"alpine{i}", med([x + i * 0.3 for x in SUMMER]), [6, 7, 8, 9]))
            out.append((f"desert{i}", med([x + i * 0.3 for x in WINTER]), [11, 12, 1, 2, 3]))
        return out

    def test_leave_one_out_predicts_each_trail_from_the_others(self):
        params, loo = M.fit_model(self.trails())
        self.assertEqual(len(loo), 16)
        for tid, (mask, sc) in loo.items():
            self.assertEqual(sc[0], 1.0, tid)
        self.assertIsInstance(params, M.Params)

    def test_the_same_input_gives_the_same_fit_twice(self):
        self.assertEqual(M.fit_model(self.trails()), M.fit_model(self.trails()))

    def test_a_trail_is_never_scored_by_a_model_that_saw_it(self):
        trails = self.trails()
        # one alpine trail whose sourced months disagree with its twins:
        # leave-one-out cannot learn them, so it must not match
        odd = ("odd", med(SUMMER), [1, 2, 3])
        _p, loo = M.fit_model(trails + [odd])
        self.assertEqual(loo["odd"][1][0], 0.0)

    def test_params_round_trip_through_a_dict(self):
        self.assertEqual(M.Params.from_dict(P.as_dict()), P)


if __name__ == "__main__":
    unittest.main()
