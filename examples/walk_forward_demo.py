"""TRACE end to end on synthetic data, walk forward with no look-ahead.

For every round of season two:
  R  fit the goals model on results played before that round only
  A  blend match-result probabilities with the (synthetic) market
  T  publish one call per fixture to a hash-chained log before kick off
  E  settle each call, then score the season against two baselines
  C  fit a calibration curve on the settled calls and show its effect

Run:  python examples/walk_forward_demo.py
"""

import csv
import os
import sys
import tempfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from accuratepredict_trace import (GoalsModel, PlattCalibrator, PredictionLog, PredictionRecord,
                                   blend_with_market, brier_score, choose_call, devig, log_loss,
                                   reliability_table, settle)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "synthetic_league.csv")


def load():
    if not os.path.exists(DATA):
        from make_synthetic_data import main as make
        make()
    with open(DATA, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            yield {**r, "date": date.fromisoformat(r["date"]), "season": int(r["season"]),
                   "home_goals": int(r["home_goals"]), "away_goals": int(r["away_goals"]),
                   "odds": {"home": float(r["odds_home"]), "draw": float(r["odds_draw"]),
                            "away": float(r["odds_away"])}}


def iso(d, hour):
    return datetime(d.year, d.month, d.day, hour, tzinfo=timezone.utc).isoformat()


def main():
    rows = list(load())
    history = [(r["date"], r["home"], r["away"], r["home_goals"], r["away_goals"]) for r in rows]
    rounds = defaultdict(list)
    for r in rows:
        if r["season"] == 2:
            rounds[r["date"]].append(r)

    log = PredictionLog(os.path.join(tempfile.mkdtemp(), "predictions.jsonl"))
    result_probs = {"model": [], "market": [], "home_always": []}
    calls = []
    for day in sorted(rounds):
        model = GoalsModel().fit(history, as_of=day)
        for r in rounds[day]:
            mk = model.markets(r["home"], r["away"])
            mk["1X2"] = blend_with_market(mk["1X2"], r["odds"], model_weight=0.5)
            outcome = ("home" if r["home_goals"] > r["away_goals"] else
                       "away" if r["home_goals"] < r["away_goals"] else "draw")
            mkt = devig(r["odds"])
            for name, probs in (("model", mk["1X2"]), ("market", mkt),
                                ("home_always", {"home": 0.999, "draw": 0.0005, "away": 0.0005})):
                result_probs[name].append(sum((probs[k] - (k == outcome)) ** 2 for k in probs))
            # The demo picks from the informative markets only, with a ceiling,
            # so near-certain lines (under 4.5 goals and the like) cannot
            # flatter the strike rate.
            call = choose_call({k: mk[k] for k in ("1X2", "OU2.5", "BTTS")},
                               floor=0.5, ceiling=0.8)
            if not call:
                continue
            market, sel, p = call
            fid = "%s-%s-%s" % (day.isoformat(), r["home"], r["away"])
            log.publish(PredictionRecord(
                fixture_id=fid, kickoff=iso(day, 15), published_at=iso(day, 6),
                market=market, selection=sel, probability=round(p, 4),
                model_version="trace-demo-0.1.0",
                inputs_fetched_at={"results": iso(day - timedelta(days=1), 23),
                                   "odds": iso(day, 5)}))
            status = settle(market, sel, r["home_goals"], r["away_goals"])
            if status != "void":
                calls.append((p, 1 if status == "won" else 0))

    n = len(result_probs["model"])
    print("SYNTHETIC DATA. These numbers describe a generated league, not any")
    print("real competition and not AccuratePredict's published record.\n")
    print("Season two, %d fixtures, walk forward (no look-ahead)\n" % n)
    print("Match result, multi-class Brier score (lower is better)")
    for name in ("model", "market", "home_always"):
        print("  %-12s %.4f" % (name, sum(result_probs[name]) / n))

    print("\nPublished calls: %d, won %d (%.1f%%)" % (
        len(calls), sum(y for _, y in calls), 100 * sum(y for _, y in calls) / len(calls)))
    print("  Brier %.4f   log loss %.4f" % (brier_score(calls), log_loss(calls)))
    print("\nReliability (stated vs observed)")
    for row in reliability_table(calls, bins=10):
        print("  %s  n=%-4d stated %.3f  observed %.3f" % (
            row["bin"], row["n"], row["stated"], row["observed"]))

    cal = PlattCalibrator(min_samples=100).fit(calls)
    print("\nCalibration curve fitted on %d calls: a=%.3f b=%.3f (a=1, b=0 is no change)"
          % (cal.n, cal.a, cal.b))
    print("  a stated 0.60 becomes %.3f" % cal(0.60))

    problems = log.verify()
    print("\nPrediction log: %d records, chain %s" % (
        len(log.records), "intact" if not problems else "BROKEN: %s" % problems[:3]))


if __name__ == "__main__":
    main()
