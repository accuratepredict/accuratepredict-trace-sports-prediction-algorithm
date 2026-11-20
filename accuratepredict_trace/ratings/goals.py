"""A goals model for football-like sports.

Each team has an attack and a defence strength. Expected goals are

    home_xg = attack[home] * defence[away] * home_advantage
    away_xg = attack[away] * defence[home]

Strengths are estimated from time-weighted results by iterative proportional
fitting (the classic Maher 1982 approach), which needs no optimiser. Score
probabilities use independent Poissons with the Dixon & Coles (1997)
low-score correction.

References
    Maher, M. J. (1982). Modelling association football scores.
        Statistica Neerlandica 36(3).
    Dixon, M. J. & Coles, S. G. (1997). Modelling association football scores
        and inefficiencies in the football betting market. JRSS C 46(2).

Defaults here are illustrative. Production values are tuned per league and
are not published.
"""

import math
from datetime import date
from typing import Dict, Iterable, List, Optional, Tuple

Result = Tuple[date, str, str, int, int]   # (played_on, home, away, home_goals, away_goals)


def time_weight(age_days: float, half_life_days: float) -> float:
    return 0.5 ** (age_days / half_life_days)


def _poisson(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _tau(h: int, a: int, lh: float, la: float, rho: float) -> float:
    if h == 0 and a == 0:
        return 1 - lh * la * rho
    if h == 0 and a == 1:
        return 1 + lh * rho
    if h == 1 and a == 0:
        return 1 + la * rho
    if h == 1 and a == 1:
        return 1 - rho
    return 1.0


class GoalsModel:
    def __init__(self, half_life_days: float = 180.0, rho: float = -0.05,
                 min_weighted_games: float = 4.0, max_goals: int = 10):
        self.half_life_days = half_life_days
        self.rho = rho
        self.min_weighted_games = min_weighted_games
        self.max_goals = max_goals
        self.attack: Dict[str, float] = {}
        self.defence: Dict[str, float] = {}
        self.home_advantage = 1.0
        self.weighted_games: Dict[str, float] = {}

    def fit(self, results: Iterable[Result], as_of: date, iterations: int = 60) -> "GoalsModel":
        rows: List[Tuple[str, str, int, int, float]] = []
        for played, h, a, hg, ag in results:
            if played >= as_of:          # never learn from the future
                continue
            w = time_weight((as_of - played).days, self.half_life_days)
            rows.append((h, a, hg, ag, w))
            self.weighted_games[h] = self.weighted_games.get(h, 0) + w
            self.weighted_games[a] = self.weighted_games.get(a, 0) + w
        if not rows:
            raise ValueError("no results before %s" % as_of)
        teams = sorted(self.weighted_games)
        att = {t: 1.0 for t in teams}
        dfn = {t: 1.0 for t in teams}
        ha = 1.0
        for _ in range(iterations):
            num = {t: 0.0 for t in teams}
            den = {t: 0.0 for t in teams}
            for h, a, hg, ag, w in rows:
                num[h] += w * hg
                den[h] += w * dfn[a] * ha
                num[a] += w * ag
                den[a] += w * dfn[h]
            att = {t: num[t] / den[t] if den[t] else 1.0 for t in teams}
            mean = sum(att.values()) / len(att)
            att = {t: v / mean for t, v in att.items()}
            num = {t: 0.0 for t in teams}
            den = {t: 0.0 for t in teams}
            for h, a, hg, ag, w in rows:
                num[a] += w * hg             # goals conceded by the away side
                den[a] += w * att[h] * ha
                num[h] += w * ag
                den[h] += w * att[a]
            dfn = {t: num[t] / den[t] if den[t] else 1.0 for t in teams}
            hn = sum(w * hg for h, a, hg, ag, w in rows)
            hd = sum(w * att[h] * dfn[a] for h, a, hg, ag, w in rows)
            ha = hn / hd if hd else 1.0
        self.attack, self.defence, self.home_advantage = att, dfn, ha
        return self

    def _strength(self, team: str) -> Tuple[float, float]:
        # Teams with too little history are shrunk to the league average.
        g = self.weighted_games.get(team, 0.0)
        k = min(1.0, g / self.min_weighted_games)
        return (1 + k * (self.attack.get(team, 1.0) - 1),
                1 + k * (self.defence.get(team, 1.0) - 1))

    def expected_goals(self, home: str, away: str, neutral: bool = False,
                       home_factor: float = 1.0, away_factor: float = 1.0) -> Tuple[float, float]:
        ah, dh = self._strength(home)
        aa, da = self._strength(away)
        hadv = 1.0 if neutral else self.home_advantage
        return ah * da * hadv * home_factor, aa * dh * away_factor

    def score_matrix(self, home_xg: float, away_xg: float) -> List[List[float]]:
        n = self.max_goals + 1
        m = [[_poisson(i, home_xg) * _poisson(j, away_xg) * _tau(i, j, home_xg, away_xg, self.rho)
              for j in range(n)] for i in range(n)]
        total = sum(map(sum, m))
        return [[v / total for v in row] for row in m]

    def markets(self, home: str, away: str, neutral: bool = False,
                home_factor: float = 1.0, away_factor: float = 1.0,
                lines: Optional[List[float]] = None) -> Dict[str, Dict[str, float]]:
        """Match result, totals and both teams to score, all from one score table."""
        hx, ax = self.expected_goals(home, away, neutral, home_factor, away_factor)
        m = self.score_matrix(hx, ax)
        n = len(m)
        hw = sum(m[i][j] for i in range(n) for j in range(n) if i > j)
        dr = sum(m[i][i] for i in range(n))
        out = {"1X2": {"home": hw, "draw": dr, "away": 1 - hw - dr},
               "BTTS": {"yes": sum(m[i][j] for i in range(1, n) for j in range(1, n))}}
        out["BTTS"]["no"] = 1 - out["BTTS"]["yes"]
        for line in lines or [1.5, 2.5, 3.5]:
            over = sum(m[i][j] for i in range(n) for j in range(n) if i + j > line)
            out["OU%s" % line] = {"over": over, "under": 1 - over}
        out["xg"] = {"home": hx, "away": ax}
        return out
