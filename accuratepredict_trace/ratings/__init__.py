"""R: Ratings. Team strength models, one per scoring shape.

goals.GoalsModel  low-scoring sports with draws (football, hockey):
                  attack/defence strengths, Poisson scores, Dixon-Coles correction
elo.MarginElo     points sports (basketball, NFL, ...): one rating per team,
                  updated after every game, predicting a margin
"""
