from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

import numpy as np
import pandas as pd

from significance import add_significance


MVP_COLUMNS = [
    "pair",
    "cross_type",
    "day",
    "signal_count",
    "up_count",
    "down_count",
    "flat_count",
    "up_ratio",
    "down_ratio",
    "p_value",
    "is_significant",
    "jeffreys_up_prob",
    "jeffreys_down_prob",
]


@dataclass(frozen=True)
class AnalysisThresholds:
    high: float = 60.0
    low: float = 40.0
    three_day: float = 25.0


def analyze_all_pairs(
    df: pd.DataFrame,
    min_ma: int,
    max_ma: int,
    cross_types: Iterable[str],
    alpha: float,
    thresholds: AnalysisThresholds | None = None,
) -> pd.DataFrame:
    """Analyze every min_ma <= a < b <= max_ma moving-average pair.

    thresholds is accepted by the MVP API because the UI exposes those values.
    The MVP result table is driven by counts, ratios, p-values, and Jeffreys
    estimates; threshold-based alert tables can be added later without changing
    the app entry point.
    """
    _ = thresholds or AnalysisThresholds()
    frames: list[pd.DataFrame] = []

    for short_ma, long_ma in combinations(range(min_ma, max_ma + 1), 2):
        for cross_type in cross_types:
            result = analyze_pair(df, short_ma, long_ma, cross_type)
            if not result.empty:
                frames.append(result)

    if frames:
        results = pd.concat(frames, ignore_index=True)
    else:
        results = pd.DataFrame(columns=[column for column in MVP_COLUMNS if column not in _significance_columns()])

    results = add_significance(results, alpha=alpha)
    return results[MVP_COLUMNS]


def analyze_pair(df: pd.DataFrame, short_ma: int, long_ma: int, cross_type: str) -> pd.DataFrame:
    short_col = f"Mean{short_ma}"
    long_col = f"Mean{long_ma}"
    pair = f"{short_ma}/{long_ma}"

    if short_col not in df.columns or long_col not in df.columns or "Mean" not in df.columns:
        return _empty_base_results()

    clean = df.dropna(subset=[short_col, long_col, "Mean"]).reset_index(drop=True)
    if clean.empty:
        return _empty_base_results()

    signal_mask = _cross_signal_mask(clean, short_col, long_col, cross_type)
    base_idx = clean.index[signal_mask]
    signal_count = int(signal_mask.sum())
    if signal_count == 0:
        return _empty_base_results()

    rows = []
    for day in (1, 2, 3):
        signs = _future_price_signs(clean, base_idx, day)
        total = len(signs)
        up_count = int((signs == 1).sum())
        down_count = int((signs == -1).sum())
        flat_count = int((signs == 0).sum())

        rows.append(
            {
                "pair": pair,
                "cross_type": cross_type,
                "day": day,
                "signal_count": signal_count,
                "up_count": up_count,
                "down_count": down_count,
                "flat_count": flat_count,
                "up_ratio": up_count / total if total else 0.0,
                "down_ratio": down_count / total if total else 0.0,
            }
        )

    return pd.DataFrame(rows)


def _cross_signal_mask(df: pd.DataFrame, short_col: str, long_col: str, cross_type: str) -> pd.Series:
    """Return crossover signal mask.

    Current default: source Excel rows are sorted in descending date order.
    Therefore shift(-1) means "yesterday", and base_idx - N means the Nth day
    after the signal. If future data is sorted ascending by date, the index
    direction in this module must be adjusted consistently.
    """
    if cross_type == "up":
        previous = df[short_col].shift(-1) < df[long_col].shift(-1)
        current = df[short_col] > df[long_col]
    elif cross_type == "down":
        previous = df[short_col].shift(-1) > df[long_col].shift(-1)
        current = df[short_col] < df[long_col]
    else:
        raise ValueError("cross_type must be 'up' or 'down'")

    return previous & current


def _future_price_signs(df: pd.DataFrame, base_idx: pd.Index, day: int) -> np.ndarray:
    future_idx = base_idx - day
    valid_mask = future_idx >= 0
    future_idx = future_idx[valid_mask]
    base_idx = base_idx[valid_mask]

    if len(future_idx) == 0:
        return np.array([], dtype=int)

    base_price = pd.to_numeric(df.loc[base_idx, "Mean"], errors="coerce").to_numpy()
    future_price = pd.to_numeric(df.loc[future_idx, "Mean"], errors="coerce").to_numpy()
    valid_prices = ~np.isnan(base_price) & ~np.isnan(future_price)
    return np.sign(future_price[valid_prices] - base_price[valid_prices]).astype(int)


def _significance_columns() -> list[str]:
    return ["p_value", "is_significant", "jeffreys_up_prob", "jeffreys_down_prob"]


def _empty_base_results() -> pd.DataFrame:
    return pd.DataFrame(columns=[column for column in MVP_COLUMNS if column not in _significance_columns()])
