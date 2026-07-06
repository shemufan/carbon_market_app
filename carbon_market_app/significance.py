from math import comb

import pandas as pd


def exact_binomtest_pvalue(success_count: int, valid_count: int, p: float = 0.5) -> float | None:
    """Return a two-sided exact binomial-test p-value.

    scipy.stats.binomtest is preferred when SciPy is installed. This fallback
    keeps the core analysis testable in lightweight environments.
    """
    if valid_count <= 0:
        return None

    try:
        from scipy.stats import binomtest

        return float(binomtest(success_count, valid_count, p=p).pvalue)
    except ImportError:
        observed_prob = comb(valid_count, success_count) * (p**success_count) * (
            (1 - p) ** (valid_count - success_count)
        )
        total = 0.0
        for k in range(valid_count + 1):
            prob = comb(valid_count, k) * (p**k) * ((1 - p) ** (valid_count - k))
            if prob <= observed_prob + 1e-15:
                total += prob
        return min(1.0, total)


def add_significance(results: pd.DataFrame, alpha: float) -> pd.DataFrame:
    """Add p-value and Jeffreys estimates to daily up/down statistics.

    Flat days are intentionally ignored for the binomial test and Jeffreys
    estimates, as requested by the business rules.
    """
    enriched = results.copy()
    if enriched.empty:
        for column in ["p_value", "is_significant", "jeffreys_up_prob", "jeffreys_down_prob"]:
            if column not in enriched.columns:
                enriched[column] = pd.Series(dtype="bool" if column == "is_significant" else "float")
        return enriched

    p_values: list[float | None] = []
    significant: list[bool] = []
    jeffreys_up: list[float | None] = []
    jeffreys_down: list[float | None] = []

    for row in enriched.itertuples(index=False):
        up_count = int(row.up_count)
        down_count = int(row.down_count)
        valid_count = up_count + down_count

        if valid_count == 0:
            p_values.append(None)
            significant.append(False)
            jeffreys_up.append(None)
            jeffreys_down.append(None)
            continue

        success_count = max(up_count, down_count)
        p_value = exact_binomtest_pvalue(success_count, valid_count, p=0.5)

        p_values.append(p_value)
        significant.append(bool(p_value is not None and p_value < alpha))
        jeffreys_up.append((up_count + 0.5) / (valid_count + 1))
        jeffreys_down.append((down_count + 0.5) / (valid_count + 1))

    enriched["p_value"] = p_values
    enriched["is_significant"] = significant
    enriched["jeffreys_up_prob"] = jeffreys_up
    enriched["jeffreys_down_prob"] = jeffreys_down
    return enriched
