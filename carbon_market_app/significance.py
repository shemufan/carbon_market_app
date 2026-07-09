from __future__ import annotations

from math import comb

import pandas as pd


SIGNIFICANCE_COLUMNS = [
    "p_value",
    "is_significant",
    "jeffreys_up_prob",
    "jeffreys_down_prob",
]


def exact_binomial_point_probability(observed_count: int, valid_count: int, p: float = 0.5) -> float:
    """Return the exact single-point binomial probability.

    Project requirement: p_value uses the probability of observing exactly the
    current up/down split, not a one-sided or two-sided tail probability. With
    p=0.5, using up_count or down_count gives the same point probability.
    """
    if valid_count <= 0:
        return 1.0

    if observed_count < 0 or observed_count > valid_count:
        return 0.0

    return float(
        comb(valid_count, observed_count)
        * (p ** observed_count)
        * ((1 - p) ** (valid_count - observed_count))
    )


def exact_binomtest_pvalue(success_count: int, valid_count: int, p: float = 0.5) -> float:
    """Backward-compatible alias for the current p_value calculation."""
    return exact_binomial_point_probability(success_count, valid_count, p=p)


def add_significance(results: pd.DataFrame, alpha: float) -> pd.DataFrame:
    """Convert raw up/down statistics into significance-ready results.

    Input is the raw DataFrame produced by analysis_engine.py. Each row should
    already represent one pair + cross_type + day combination and include
    up_count, down_count, flat_count, up_ratio, and down_ratio.

    Flat counts are ignored for the point-probability calculation:
        valid_count = up_count + down_count

    The returned DataFrame keeps all original columns and appends p_value,
    is_significant, jeffreys_up_prob, and jeffreys_down_prob, making it suitable
    for direct Streamlit display and Excel export.
    """
    enriched = results.copy()
    if enriched.empty:
        return _ensure_significance_columns(enriched)

    p_values: list[float] = []
    is_significant: list[bool] = []
    jeffreys_up_probs: list[float | None] = []
    jeffreys_down_probs: list[float | None] = []

    for row in enriched.itertuples(index=False):
        up_count = int(row.up_count)
        down_count = int(row.down_count)
        valid_count = up_count + down_count

        if valid_count == 0:
            p_value = 1.0
            jeffreys_up_prob = None
            jeffreys_down_prob = None
        else:
            observed_count = max(up_count, down_count)
            p_value = exact_binomial_point_probability(observed_count, valid_count, p=0.5)
            jeffreys_up_prob = (up_count + 0.5) / (valid_count + 1)
            jeffreys_down_prob = (down_count + 0.5) / (valid_count + 1)

        p_values.append(p_value)
        is_significant.append(bool(p_value < alpha))
        jeffreys_up_probs.append(jeffreys_up_prob)
        jeffreys_down_probs.append(jeffreys_down_prob)

    enriched["p_value"] = p_values
    enriched["is_significant"] = is_significant
    enriched["jeffreys_up_prob"] = jeffreys_up_probs
    enriched["jeffreys_down_prob"] = jeffreys_down_probs
    return enriched


def _ensure_significance_columns(df: pd.DataFrame) -> pd.DataFrame:
    enriched = df.copy()
    for column in SIGNIFICANCE_COLUMNS:
        if column not in enriched.columns:
            dtype = "bool" if column == "is_significant" else "float"
            enriched[column] = pd.Series(dtype=dtype)
    return enriched
