from __future__ import annotations

from typing import Iterable

import pandas as pd


def read_excel_file(uploaded_file, sheet_name=0) -> pd.DataFrame:
    """Read an uploaded Excel file and normalize common column names."""
    df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
    return normalize_columns(df)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized.columns = [str(column).strip() for column in normalized.columns]

    if "Mean" not in normalized.columns:
        for candidate in ("Mean Price", "MeanPrice", "平均价格"):
            if candidate in normalized.columns:
                normalized = normalized.rename(columns={candidate: "Mean"})
                break

    return normalized


def apply_row_range(df: pd.DataFrame, start_row: int, end_row: int) -> pd.DataFrame:
    """Apply an inclusive zero-based row range and reset the index."""
    if len(df) == 0:
        return df.reset_index(drop=True)

    start = max(0, int(start_row))
    end = min(len(df) - 1, int(end_row))
    if start > end:
        return df.iloc[0:0].reset_index(drop=True)

    return df.iloc[start : end + 1].reset_index(drop=True)


def apply_row_ranges(df: pd.DataFrame, row_ranges: Iterable[tuple[int, int]]) -> pd.DataFrame:
    """Compatibility helper for tests and future multi-range support."""
    selected_rows: set[int] = set()
    last_index = len(df) - 1
    for start, end in row_ranges:
        start = max(0, int(start))
        end = min(last_index, int(end))
        if start <= end:
            selected_rows.update(range(start, end + 1))

    if not selected_rows:
        return df.iloc[0:0].reset_index(drop=True)

    return df.iloc[sorted(selected_rows)].reset_index(drop=True)


def parse_row_ranges(text: str) -> list[tuple[int, int]]:
    """Compatibility helper for old tests; MVP UI uses start_row/end_row."""
    if not text or not text.strip():
        return []

    ranges: list[tuple[int, int]] = []
    for part in text.replace("，", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start, end = int(start_text.strip()), int(end_text.strip())
        else:
            start = end = int(part)
        if start > end:
            start, end = end, start
        ranges.append((start, end))
    return ranges


def required_ma_columns(min_ma: int, max_ma: int) -> list[str]:
    return [f"Mean{i}" for i in range(min_ma, max_ma + 1)]


def validate_input_columns(df: pd.DataFrame, min_ma: int, max_ma: int) -> None:
    missing = [column for column in ["Mean", *required_ma_columns(min_ma, max_ma)] if column not in df.columns]
    if missing:
        raise ValueError("Excel 缺少必要列: " + ", ".join(missing))
