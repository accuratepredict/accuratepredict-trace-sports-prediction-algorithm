"""AccuratePredict TRACE: a reference implementation of the TRACE sports
forecasting framework.

TRACE stands for Timestamped, Ratings, Adjusted, Calibrated, Evaluated:

    T  timestamp.py   append-only, versioned, hash-chained prediction log
    R  ratings/       team strength ratings (Dixon-Coles goals model, margin Elo)
    A  adjust.py      venue, rest and bookmaker-market adjustments
    C  calibrate.py   probability recalibration against settled outcomes
    E  evaluate.py    settlement, Brier score, log loss, reliability tables

This package is the open skeleton of the framework used on
https://accuratepredict.com. It uses textbook methods and illustrative
default parameters. The tuned parameters, data pipeline and production
models are not part of this repository.
"""

__version__ = "0.1.0"

from .timestamp import PredictionLog, PredictionRecord
from .ratings.goals import GoalsModel
from .ratings.elo import MarginElo
from .adjust import devig, blend_with_market, rest_factor
from .calibrate import PlattCalibrator
from .evaluate import brier_score, log_loss, reliability_table, settle
from .picks import choose_call

__all__ = [
    "PredictionLog", "PredictionRecord", "GoalsModel", "MarginElo",
    "devig", "blend_with_market", "rest_factor", "PlattCalibrator",
    "brier_score", "log_loss", "reliability_table", "settle", "choose_call",
]
