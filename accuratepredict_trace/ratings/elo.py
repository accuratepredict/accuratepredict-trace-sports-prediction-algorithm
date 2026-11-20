"""A margin-aware Elo rating for points sports.

Each team starts at `base`. After a game the winner takes points from the
loser; how many depends on how surprising the result was and, through a
capped log multiplier, on the margin. The rating gap plus home advantage
predicts an expected margin, and the win probability is the chance a normal
distribution with that mean and the sport's spread lands above zero.

Reference
    Elo, A. (1978). The Rating of Chessplayers, Past and Present.
    The margin multiplier follows the widely used FiveThirtyEight NFL form.

Defaults are illustrative, not the tuned production values.
"""

import math
from typing import Dict, Iterable, Tuple

Game = Tuple[str, str, float, float]        # (home, away, home_points, away_points)


def _phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


class MarginElo:
    def __init__(self, k: float = 24.0, base: float = 1500.0, home_points: float = 2.5,
                 points_per_100: float = 3.5, spread: float = 13.0,
                 season_regression: float = 0.25, draw_band: float = 0.0):
        self.k, self.base = k, base
        self.home_points = home_points          # home advantage, in points
        self.points_per_100 = points_per_100    # margin worth 100 rating points
        self.spread = spread                    # standard deviation of the margin
        self.season_regression = season_regression
        self.draw_band = draw_band              # half width of the draw zone, in points
        self.ratings: Dict[str, float] = {}

    def rating(self, team: str) -> float:
        return self.ratings.get(team, self.base)

    def expected_margin(self, home: str, away: str, neutral: bool = False) -> float:
        gap = self.rating(home) - self.rating(away)
        return gap / 100 * self.points_per_100 + (0 if neutral else self.home_points)

    def probabilities(self, home: str, away: str, neutral: bool = False) -> Dict[str, float]:
        mu = self.expected_margin(home, away, neutral)
        if self.draw_band <= 0:
            p = 1 - _phi(-mu / self.spread)
            return {"home": p, "away": 1 - p}
        ph = 1 - _phi((self.draw_band - mu) / self.spread)
        pa = _phi((-self.draw_band - mu) / self.spread)
        return {"home": ph, "draw": 1 - ph - pa, "away": pa}

    def update(self, home: str, away: str, hp: float, ap: float, neutral: bool = False) -> None:
        rh, ra = self.rating(home), self.rating(away)
        hadv = 0 if neutral else self.home_points / self.points_per_100 * 100
        expected = 1 / (1 + 10 ** (-(rh + hadv - ra) / 400))
        actual = 1.0 if hp > ap else 0.0 if hp < ap else 0.5
        margin = abs(hp - ap)
        diff = (rh + hadv - ra) * (1 if hp >= ap else -1)
        mult = math.log(margin + 1) * 2.2 / (diff * 0.001 + 2.2) if margin else 1.0
        delta = self.k * mult * (actual - expected)
        self.ratings[home] = rh + delta
        self.ratings[away] = ra - delta

    def fit(self, games: Iterable[Game]) -> "MarginElo":
        for g in games:
            self.update(*g)
        return self

    def new_season(self) -> None:
        for t, r in self.ratings.items():
            self.ratings[t] = r - self.season_regression * (r - self.base)
