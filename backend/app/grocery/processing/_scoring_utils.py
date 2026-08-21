"""Shared deterministic scoring utilities.

Used by both the Ranking Engine (Phase 11, per-product scoring) and the
Recommendation Generator's basket-selection step (Phase 12, per-store
scoring) — promoted out of ``ranking.py`` specifically so Phase 12
doesn't duplicate this exact normalization logic. Phase 11's own module
re-exports this under its original private name for backward
compatibility with tests written against it.
"""


def min_max_normalize(values: list[float]) -> list[float]:
    """Scale a list of values to [0, 1]: 0 = best (lowest) in the set,
    1 = worst (highest).

    All-equal values normalize to 0 for every entry — no penalty when
    there's no actual variation to penalize on that dimension, and no
    divide-by-zero.
    """

    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.0] * len(values)
    return [(v - lo) / (hi - lo) for v in values]
