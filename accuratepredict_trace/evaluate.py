"""E: Evaluated. Settle every call by set rules and score it honestly.

- settle: won / lost / void for 1X2, totals and both teams to score
- brier_score, log_loss: proper scoring rules for probability forecasts
- reliability_table: stated probability vs observed frequency, by bin

A forecast is judged on many results, never on one. Compare any model with
simple baselines (for example "home team always wins" and the de-vigged
market) before trusting it.
"""

import math
from typing import Dict, Iterable, List, Tuple


def settle(market: str, selection: str, home_goals: int, away_goals: int) -> str:
    if market == "1X2":
        outcome = "home" if home_goals > away_goals else "away" if home_goals < away_goals else "draw"
        return "won" if selection == outcome else "lost"
    if market == "BTTS":
        yes = home_goals > 0 and away_goals > 0
        return "won" if (selection == "yes") == yes else "lost"
    if market.startswith("OU"):
        line = float(market[2:])
        total = home_goals + away_goals
        if total == line:
            return "void"                   # a push on a whole-number line
        return "won" if (selection == "over") == (total > line) else "lost"
    raise ValueError("unknown market %r" % market)


def brier_score(pairs: Iterable[Tuple[float, int]]) -> float:
    pairs = list(pairs)
    return sum((p - y) ** 2 for p, y in pairs) / len(pairs)


def log_loss(pairs: Iterable[Tuple[float, int]], eps: float = 1e-12) -> float:
    pairs = list(pairs)
    return -sum(y * math.log(max(p, eps)) + (1 - y) * math.log(max(1 - p, eps))
                for p, y in pairs) / len(pairs)


def reliability_table(pairs: Iterable[Tuple[float, int]], bins: int = 10) -> List[Dict[str, float]]:
    buckets: Dict[int, List[Tuple[float, int]]] = {}
    for p, y in pairs:
        buckets.setdefault(min(bins - 1, int(p * bins)), []).append((p, y))
    rows = []
    for b in sorted(buckets):
        rows_b = buckets[b]
        rows.append({"bin": "%.1f-%.1f" % (b / bins, (b + 1) / bins),
                     "n": len(rows_b),
                     "stated": sum(p for p, _ in rows_b) / len(rows_b),
                     "observed": sum(y for _, y in rows_b) / len(rows_b)})
    return rows
