"""C: Calibrated. Of everything rated 60 percent, close to 60 percent should win.

PlattCalibrator fits a two-parameter curve on the log-odds of the model
probability:

    p_calibrated = sigmoid(a * logit(p) + b)

a = 1, b = 0 is "no change". The fit is penalised towards no change so a
small sample cannot swing the curve, and below `min_samples` settled
outcomes the calibrator returns the model probability unchanged.

Reference
    Platt, J. (1999). Probabilistic outputs for support vector machines.

The production calibration layer, its thresholds and learned curves are not
part of this repository.
"""

import math
from typing import Iterable, Tuple

EPS = 1e-6


def _logit(p: float) -> float:
    p = min(1 - EPS, max(EPS, p))
    return math.log(p / (1 - p))


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


class PlattCalibrator:
    def __init__(self, min_samples: int = 200, l2: float = 1.0):
        self.min_samples = min_samples
        self.l2 = l2
        self.a, self.b = 1.0, 0.0
        self.n = 0

    @property
    def active(self) -> bool:
        return self.n >= self.min_samples

    def fit(self, pairs: Iterable[Tuple[float, int]], steps: int = 2000,
            lr: float = 0.05) -> "PlattCalibrator":
        """pairs: (model_probability, outcome 0/1) for settled calls."""
        data = [(_logit(p), y) for p, y in pairs]
        self.n = len(data)
        if not self.active:
            self.a, self.b = 1.0, 0.0
            return self
        a, b = 1.0, 0.0
        n = float(len(data))
        for _ in range(steps):
            ga = gb = 0.0
            for x, y in data:
                err = _sigmoid(a * x + b) - y
                ga += err * x
                gb += err
            ga = ga / n + self.l2 * (a - 1) / n
            gb = gb / n + self.l2 * b / n
            a -= lr * ga
            b -= lr * gb
        self.a, self.b = a, b
        return self

    def __call__(self, p: float) -> float:
        if not self.active:
            return p
        return _sigmoid(self.a * _logit(p) + self.b)
