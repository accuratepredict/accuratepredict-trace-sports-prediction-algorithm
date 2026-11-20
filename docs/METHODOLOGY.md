# The TRACE methodology

The plain-English version, written for readers rather than developers, is on
the AccuratePredict site,
**[accuratepredict.com](https://accuratepredict.com)**.
This note maps each part of it to the code in this repository.

## T: Timestamped (`timestamp.py`)

A forecast that can be edited after the event is not a forecast. Every call
is written before the start with its publication time and the time each
input was fetched; an input fetched after publication is rejected. Updates
create a new version. Each record stores the hash of the one before it, so
`PredictionLog.verify()` detects any change to history. The version settled
is the last one published before kick off.

## R: Ratings (`ratings/`)

- **Goals model** for sports with draws and low scores. Attack and defence
  strengths with exponential time decay, a league home advantage, Poisson
  scores and the Dixon and Coles (1997) correction for 0-0, 1-0, 0-1 and 1-1.
  Teams with little history are shrunk towards the league average.
- **Margin Elo** for points sports. Ratings move after each game by an
  amount that depends on surprise and a capped margin multiplier; the
  rating gap predicts a margin and a normal model turns it into win (and,
  optionally, draw) probabilities.

## A: Adjusted (`adjust.py`)

Venue is handled in the rating models. Rest gives a small, capped edge to
the fresher side. Where a market exists, its decimal odds are de-vigged and
blended with the model. A well-informed market is a strong forecast, and
blending with it is usually better than ignoring it.

## C: Calibrated (`calibrate.py`)

A two-parameter Platt curve on the log-odds corrects consistent over or
under confidence. It stays inactive until enough calls have settled, and is
penalised towards "no change" so small samples cannot swing it.

## E: Evaluated (`evaluate.py`)

Settlement follows set rules per market (a total landing exactly on a
whole-number line is void). Forecasts are scored with the Brier score and
log loss, which reward honest probabilities, and a reliability table
compares stated with observed frequencies. Always compare with baselines:
"home team always wins" and the de-vigged market.

## References

- Dixon, M. J. and Coles, S. G. (1997). Modelling association football
  scores and inefficiencies in the football betting market. *JRSS Series C* 46(2).
- Maher, M. J. (1982). Modelling association football scores.
  *Statistica Neerlandica* 36(3).
- Elo, A. (1978). *The Rating of Chessplayers, Past and Present.*
- Platt, J. (1999). Probabilistic outputs for support vector machines.
- Brier, G. W. (1950). Verification of forecasts expressed in terms of
  probability. *Monthly Weather Review* 78(1).
