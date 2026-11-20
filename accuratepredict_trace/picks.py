"""One named call per fixture.

Every priced selection is a candidate. Nothing is ever shown as certain, so
probabilities above `ceiling` are excluded, and nothing below `floor` is
picked. Among the rest, the highest probability wins, with an optional bonus
for a positive edge over the market.

The production selection rules carry more terms than this and are not
published.
"""

from typing import Dict, Optional, Tuple


def choose_call(markets: Dict[str, Dict[str, float]], floor: float = 0.55,
                ceiling: float = 0.90, edges: Optional[Dict[Tuple[str, str], float]] = None,
                edge_weight: float = 0.25) -> Optional[Tuple[str, str, float]]:
    best, best_score = None, -1.0
    for market, sels in markets.items():
        if market == "xg":
            continue
        for sel, p in sels.items():
            if not floor <= p <= ceiling:
                continue
            score = p + edge_weight * max(0.0, (edges or {}).get((market, sel), 0.0))
            if score > best_score:
                best, best_score = (market, sel, p), score
    return best
