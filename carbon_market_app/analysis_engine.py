from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

import numpy as np
import pandas as pd

from significance import add_significance


FOCUS_COMBOS = [
    "1,1,1",
    "1,1,-1",
    "1,-1,1",
    "1,-1,-1",
    "-1,1,1",
    "-1,1,-1",
    "-1,-1,1",
    "-1,-1,-1",
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
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Analyze every min_ma <= a < b <= max_ma pair.

    Core functions only return DataFrames. They do not save files or draw charts.
    """
    thresholds = thresholds or AnalysisThresholds()
    daily_frames: list[pd.DataFrame] = []
    combo_frames: list[pd.DataFrame] = []

    for short_ma, long_ma in combinations(range(min_ma, max_ma + 1), 2):
        for cross_type in cross_types:
            daily, combos = analyze_pair(
                df=df,
                short_ma=short_ma,
                long_ma=long_ma,
                cross_type=cross_type,
                thresholds=thresholds,
            )
            if not daily.empty:
                daily_frames.append(daily)
            if not combos.empty:
                combo_frames.append(combos)

    daily_results = (
        pd.concat(daily_frames, ignore_index=True)
        if daily_frames
        else pd.DataFrame(columns=_daily_columns(include_significance=False))
    )
    daily_results = add_significance(daily_results, alpha=alpha)

    combo_results = (
        pd.concat(combo_frames, ignore_index=True)
        if combo_frames
        else pd.DataFrame(
            columns=[
                "pair",
                "cross_type",
                "signal_count",
                "combo",
                "combo_count",
                "combo_ratio",
                "is_combo_alert",
            ]
        )
    )
    return daily_results, combo_results


def analyze_pair(
    df: pd.DataFrame,
    short_ma: int,
    long_ma: int,
    cross_type: str,
    thresholds: AnalysisThresholds,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    short_col = f"Mean{short_ma}"
    long_col = f"Mean{long_ma}"
    pair = f"{short_ma}/{long_ma}"

    if short_col not in df.columns or long_col not in df.columns or "Mean" not in df.columns:
        return pd.DataFrame(columns=_daily_columns(include_significance=False)), pd.DataFrame()

    clean = df.dropna(subset=[short_col, long_col]).reset_index(drop=True)
    if clean.empty:
        return pd.DataFrame(columns=_daily_columns(include_significance=False)), pd.DataFrame()

    signal_mask = _cross_signal_mask(clean, short_col, long_col, cross_type)
    base_idx = clean.index[signal_mask]
    signal_count = int(signal_mask.sum())

    if signal_count == 0:
        return pd.DataFrame(columns=_daily_columns(include_significance=False)), pd.DataFrame()

    daily_rows = []
    for day in (1, 2, 3):
        signs = _future_price_signs(clean, base_idx, day)
        up_count = int((signs == 1).sum())
        down_count = int((signs == -1).sum())
        flat_count = int((signs == 0).sum())
        total_count = len(signs)
        up_ratio = up_count / total_count if total_count else 0.0
        down_ratio = down_count / total_count if total_count else 0.0

        daily_rows.append(
            {
                "pair": pair,
                "cross_type": cross_type,
                "day": day,
                "signal_count": signal_count,
                "up_count": up_count,
                "down_count": down_count,
                "flat_count": flat_count,
                "up_ratio": up_ratio,
                "down_ratio": down_ratio,
                "threshold_alert": _daily_threshold_alert(up_ratio, down_ratio, thresholds),
            }
        )

    combos = _three_day_combos(clean, base_idx, pair, cross_type, signal_count, thresholds)
    return pd.DataFrame(daily_rows), combos


def _cross_signal_mask(df: pd.DataFrame, short_col: str, long_col: str, cross_type: str) -> pd.Series:
    """Return crossover signal mask.

    The current Excel data is assumed to be sorted in descending date order.
    Therefore shift(-1) means "yesterday", and base_idx - N means the Nth day
    after the signal. If the source file is changed to ascending date order,
    all index directions in this module must be adjusted together.
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


def _three_day_combos(
    df: pd.DataFrame,
    base_idx: pd.Index,
    pair: str,
    cross_type: str,
    signal_count: int,
    thresholds: AnalysisThresholds,
) -> pd.DataFrame:
    valid_base_idx = base_idx[base_idx - 3 >= 0]
    if len(valid_base_idx) == 0:
        return pd.DataFrame()

    combos = []
    for idx in valid_base_idx:
        base_price = pd.to_numeric(pd.Series([df.loc[idx, "Mean"]]), errors="coerce").iloc[0]
        future_prices = pd.to_numeric(
            pd.Series([df.loc[idx - day, "Mean"] for day in (1, 2, 3)]),
            errors="coerce",
        )
        if pd.isna(base_price) or future_prices.isna().any():
            continue

        signs = np.sign(future_prices.to_numpy() - base_price).astype(int)
        combos.append(f"{signs[0]},{signs[1]},{signs[2]}")

    if not combos:
        return pd.DataFrame()

    combo_series = pd.Series(combos).where(lambda values: values.isin(FOCUS_COMBOS), "other")
    counts = combo_series.value_counts()
    total = int(counts.sum())

    rows = []
    for combo, count in counts.items():
        ratio = count / total if total else 0.0
        rows.append(
            {
                "pair": pair,
                "cross_type": cross_type,
                "signal_count": signal_count,
                "combo": combo,
                "combo_count": int(count),
                "combo_ratio": ratio,
                "is_combo_alert": bool(ratio * 100 > thresholds.three_day),
            }
        )
    return pd.DataFrame(rows)


def _daily_threshold_alert(up_ratio: float, down_ratio: float, thresholds: AnalysisThresholds) -> str:
    alerts = []
    if up_ratio * 100 > thresholds.high:
        alerts.append("up_ratio_high")
    if up_ratio * 100 < thresholds.low:
        alerts.append("up_ratio_low")
    if down_ratio * 100 > thresholds.high:
        alerts.append("down_ratio_high")
    if down_ratio * 100 < thresholds.low:
        alerts.append("down_ratio_low")
    return ",".join(alerts)


def _daily_columns(include_significance: bool) -> list[str]:
    columns = [
        "pair",
        "cross_type",
        "day",
        "signal_count",
        "up_count",
        "down_count",
        "flat_count",
        "up_ratio",
        "down_ratio",
        "threshold_alert",
    ]
    if include_significance:
        columns.extend(["p_value", "is_significant", "jeffreys_up_prob", "jeffreys_down_prob"])
    return columns
