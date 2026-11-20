"""Generate a synthetic football league so the demo runs with no data licence.

Twenty fictional clubs, two double round-robin seasons, scores drawn from
Poisson distributions around hidden "true" strengths. No real team, league
or data provider is involved.

Run:  python examples/make_synthetic_data.py
"""

import csv
import math
import os
import random
from datetime import date, timedelta

CLUBS = ["Northbridge", "Eastvale", "Riverton", "Hollowmere", "Kingsport", "Ashford Vale",
         "Marlow Town", "Stonebay", "Westbrook", "Redcliff", "Larkspur", "Fernhill",
         "Oakridge", "Saltmarsh", "Brightwater", "Coldharbour", "Elmstead", "Greywell",
         "Harrowgate", "Ironbridge"]


def poisson(rng: random.Random, lam: float) -> int:
    l, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= l:
            return k
        k += 1


def true_1x2(lh: float, la: float, n: int = 11):
    pf = lambda k, l: math.exp(-l) * l ** k / math.factorial(k)
    ph = sum(pf(i, lh) * pf(j, la) for i in range(n) for j in range(n) if i > j)
    pd = sum(pf(i, lh) * pf(i, la) for i in range(n))
    tot = sum(pf(i, lh) * pf(j, la) for i in range(n) for j in range(n))
    return ph / tot, pd / tot, 1 - (ph + pd) / tot


def season_fixtures(rng, clubs, start):
    pairs = [(h, a) for h in clubs for a in clubs if h != a]
    rng.shuffle(pairs)
    per_round = len(clubs) // 2
    for i, (h, a) in enumerate(pairs):
        yield start + timedelta(days=7 * (i // per_round)), h, a


def main(seed: int = 2026) -> str:
    rng = random.Random(seed)
    attack = {c: math.exp(rng.gauss(0, 0.25)) for c in CLUBS}
    defence = {c: math.exp(rng.gauss(0, 0.2)) for c in CLUBS}
    home_adv = 1.25
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "synthetic_league.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "season", "home", "away", "home_goals", "away_goals",
                    "odds_home", "odds_draw", "odds_away"])
        for season, start in ((1, date(2024, 8, 10)), (2, date(2025, 8, 9))):
            for d, h, a in season_fixtures(rng, CLUBS, start):
                lh = attack[h] * defence[a] * home_adv * 1.1
                la = attack[a] * defence[h] * 1.1
                hg, ag = poisson(rng, lh), poisson(rng, la)
                # A synthetic "market": the true Poisson result probabilities,
                # lightly perturbed, with a 5 percent margin. It knows the hidden
                # strengths, so it is a hard benchmark, as real markets are.
                ph, pd, pa = true_1x2(lh * math.exp(rng.gauss(0, 0.05)),
                                      la * math.exp(rng.gauss(0, 0.05)))
                w.writerow([d.isoformat(), season, h, a, hg, ag] +
                           ["%.2f" % (1 / (q * 1.05)) for q in (ph, pd, pa)])
            # Strengths drift a little between seasons.
            attack = {c: v * math.exp(rng.gauss(0, 0.08)) for c, v in attack.items()}
            defence = {c: v * math.exp(rng.gauss(0, 0.06)) for c, v in defence.items()}
    return out


if __name__ == "__main__":
    print("written", main())
