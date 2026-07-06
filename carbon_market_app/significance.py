from __future__ import annotations

import pandas as pd
from scipy.stats import binomtest


SIGNIFICANCE_COLUMNS = [
    "p_value",
    "is_significant",
    "jeffreys_up_prob",
    "jeffreys_down_prob",
]


def exact_binomtest_pvalue(success_count: int, valid_count: int, p: float = 0.5) -> float:
    """Return a two-sided exact binomial-test p-value.

    We use scipy.stats.binomtest with alternative="two-sided". The null
    hypothesis is that up and down are equally likely, p=0.5. For this project,
    "success_count" is the larger of up_count/down_count, so the test asks
    whether the observed imbalance is unusually far from 50/50 in either
    direction.
    """
    if valid_count <= 0:
        return 1.0

    return float(binomtest(success_count, valid_count, p=p, alternative="two-sided").pvalue)


def add_significance(results: pd.DataFrame, alpha: float) -> pd.DataFrame:
    """Convert raw up/down statistics into significance-ready results.

    Input is the raw DataFrame produced by analysis_engine.py. Each row should
    already represent one pair + cross_type + day combination and include
    up_count, down_count, flat_count, up_ratio, and down_ratio.

    Flat counts are ignored for the binomial test:
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
            success_count = max(up_count, down_count)
            p_value = exact_binomtest_pvalue(success_count, valid_count, p=0.5)
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
