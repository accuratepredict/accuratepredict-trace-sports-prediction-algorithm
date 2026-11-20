import json
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from accuratepredict_trace import (GoalsModel, MarginElo, PlattCalibrator, PredictionLog,
                                   PredictionRecord, blend_with_market, brier_score, choose_call,
                                   devig, rest_factor, settle)


def rec(fid="f1", pub="2026-01-10T06:00:00+00:00", p=0.6, **kw):
    base = dict(fixture_id=fid, kickoff="2026-01-10T15:00:00+00:00", published_at=pub,
                market="1X2", selection="home", probability=p, model_version="t")
    base.update(kw)
    return PredictionRecord(**base)


class Timestamped(unittest.TestCase):
    def test_versions_and_settled_version(self):
        log = PredictionLog()
        log.publish(rec(p=0.55))
        log.publish(rec(pub="2026-01-10T12:00:00+00:00", p=0.58))
        log.publish(rec(pub="2026-01-10T16:00:00+00:00", p=0.90))   # after kick off
        self.assertEqual([r.version for r in log.history("f1")], [1, 2, 3])
        self.assertEqual(log.settled_version("f1").probability, 0.58)
        self.assertEqual(log.version_at("f1", "2026-01-10T07:00:00+00:00").version, 1)

    def test_tampering_is_detected(self):
        path = os.path.join(tempfile.mkdtemp(), "log.jsonl")
        log = PredictionLog(path)
        log.publish(rec())
        log.publish(rec(fid="f2"))
        self.assertEqual(log.verify(), [])
        lines = open(path).read().splitlines()
        first = json.loads(lines[0])
        first["probability"] = 0.99
        lines[0] = json.dumps(first)
        open(path, "w").write("\n".join(lines) + "\n")
        self.assertTrue(PredictionLog(path).verify())

    def test_inputs_fetched_after_publication_are_rejected(self):
        with self.assertRaises(ValueError):
            PredictionLog().publish(rec(inputs_fetched_at={"odds": "2026-01-10T07:00:00+00:00"}))

    def test_naive_timestamps_are_rejected(self):
        with self.assertRaises(ValueError):
            PredictionLog().publish(rec(pub="2026-01-10T06:00:00"))


class Ratings(unittest.TestCase):
    def setUp(self):
        d = date(2025, 1, 1)
        self.results = []
        for i in range(30):
            day = d + timedelta(days=7 * i)
            self.results += [(day, "Strong", "Weak", 3, 0), (day, "Weak", "Strong", 0, 2),
                             (day, "Mid", "Weak", 1, 1), (day, "Strong", "Mid", 2, 1)]

    def test_goals_model_orders_teams_and_sums_to_one(self):
        m = GoalsModel().fit(self.results, as_of=date(2026, 1, 1))
        mk = m.markets("Strong", "Weak")
        self.assertGreater(mk["1X2"]["home"], 0.7)
        self.assertAlmostEqual(sum(mk["1X2"].values()), 1.0, places=9)
        self.assertAlmostEqual(mk["OU2.5"]["over"] + mk["OU2.5"]["under"], 1.0, places=9)

    def test_goals_model_never_learns_from_the_future(self):
        with self.assertRaises(ValueError):
            GoalsModel().fit(self.results, as_of=date(2024, 1, 1))

    def test_unknown_team_is_league_average(self):
        m = GoalsModel().fit(self.results, as_of=date(2026, 1, 1))
        a, d = m._strength("Newcomer")
        self.assertEqual((a, d), (1.0, 1.0))

    def test_elo(self):
        e = MarginElo()
        for _ in range(20):
            e.update("A", "B", 110, 90)
        p = e.probabilities("A", "B")
        self.assertGreater(p["home"], 0.8)
        self.assertAlmostEqual(sum(p.values()), 1.0)
        e3 = MarginElo(draw_band=0.5)
        self.assertAlmostEqual(sum(e3.probabilities("A", "B").values()), 1.0)


class Adjusted(unittest.TestCase):
    def test_devig_and_blend(self):
        odds = {"home": 1.8, "draw": 3.6, "away": 4.5}
        self.assertAlmostEqual(sum(devig(odds).values()), 1.0)
        model = {"home": 0.6, "draw": 0.25, "away": 0.15}
        self.assertEqual(blend_with_market(model, odds, model_weight=1.0), model)
        b = blend_with_market(model, odds, model_weight=0.5)
        self.assertAlmostEqual(sum(b.values()), 1.0)

    def test_rest_is_capped(self):
        self.assertEqual(rest_factor(14, 2), 1.03)
        self.assertEqual(rest_factor(2, 14), 0.97)


class Calibrated(unittest.TestCase):
    def test_inactive_below_threshold(self):
        c = PlattCalibrator().fit([(0.7, 1)] * 50)
        self.assertEqual(c(0.7), 0.7)

    def test_overconfidence_is_pulled_down(self):
        pairs = [(0.8, 1)] * 60 + [(0.8, 0)] * 40       # stated 80, observed 60
        c = PlattCalibrator(min_samples=50).fit(pairs)
        self.assertLess(c(0.8), 0.75)


class Evaluated(unittest.TestCase):
    def test_settlement(self):
        self.assertEqual(settle("1X2", "draw", 1, 1), "won")
        self.assertEqual(settle("OU2.5", "over", 2, 1), "won")
        self.assertEqual(settle("OU3.0", "over", 2, 1), "void")
        self.assertEqual(settle("BTTS", "yes", 1, 0), "lost")

    def test_brier(self):
        self.assertAlmostEqual(brier_score([(1.0, 1), (0.0, 0)]), 0.0)
        self.assertAlmostEqual(brier_score([(0.5, 1)]), 0.25)

    def test_choose_call_respects_ceiling_and_floor(self):
        mk = {"1X2": {"home": 0.95, "draw": 0.03, "away": 0.02}, "BTTS": {"yes": 0.6, "no": 0.4}}
        self.assertEqual(choose_call(mk), ("BTTS", "yes", 0.6))
        self.assertIsNone(choose_call({"1X2": {"home": 0.4, "draw": 0.3, "away": 0.3}}))


if __name__ == "__main__":
    unittest.main()
