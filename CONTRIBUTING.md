# Contributing to AccuratePredict TRACE

Thank you for helping. Good contributions:

- tests for edge cases (settlement rules, odd timestamps, tiny samples)
- new rating models for other sports, with a reference to the published method
- documentation, worked examples and translations
- bug reports with a minimal example

Ground rules:

1. **No third-party data.** Do not commit fixtures, odds or results from any
   data provider. Use generated data, or a script that downloads data the
   user is licensed to use.
2. **No dependencies** in the core package. The standard library only.
3. **Honest claims.** Do not describe any method as sure, guaranteed or
   certain. Probabilities are probabilities.
4. **Tests pass:** `python -m unittest discover -s tests` and
   `python examples/walk_forward_demo.py`.

By contributing you agree that your contribution is licensed under the
Apache License 2.0, the licence of this repository.
