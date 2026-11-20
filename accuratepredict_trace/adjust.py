"""A: Adjusted. Fixture-level adjustments on top of the ratings.

- rest_factor: a small, capped multiplier in favour of the better rested side
- devig: removes the bookmaker margin from decimal odds (proportional method)
- blend_with_market: a weighted blend of model and market probabilities

Venue is handled inside the rating models (home advantage, neutral flag).
Squad and line-up adjustments exist in production but depend on licensed
data feeds and are not included here.

The default market weight below is illustrative. How much weight a
production model gives the market is a tuned, per-sport decision.
"""

from typing import Dict


def rest_factor(rest_days_self: float, rest_days_opp: float,
                per_day: float = 0.01, cap: float = 0.03) -> float:
    """Multiplier for a side's expected scoring. Never moves more than `cap`."""
    shift = max(-cap, min(cap, (rest_days_self - rest_days_opp) * per_day))
    return 1.0 + shift


def devig(decimal_odds: Dict[str, float]) -> Dict[str, float]:
    if any(o <= 1.0 for o in decimal_odds.values()):
        raise ValueError("decimal odds must be greater than 1.0")
    implied = {k: 1.0 / o for k, o in decimal_odds.items()}
    total = sum(implied.values())
    return {k: v / total for k, v in implied.items()}


def blend_with_market(model: Dict[str, float], decimal_odds: Dict[str, float],
                      model_weight: float = 0.5) -> Dict[str, float]:
    if set(model) != set(decimal_odds):
        raise ValueError("model and market must price the same outcomes")
    if not 0.0 <= model_weight <= 1.0:
        raise ValueError("model_weight must be between 0 and 1")
    market = devig(decimal_odds)
    out = {k: model_weight * model[k] + (1 - model_weight) * market[k] for k in model}
    total = sum(out.values())
    return {k: v / total for k, v in out.items()}
