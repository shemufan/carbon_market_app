from __future__ import annotations

from io import BytesIO

import pandas as pd


def to_excel_bytes(
    all_results: pd.DataFrame,
    significant_results: pd.DataFrame,
    up_results: pd.DataFrame,
    down_results: pd.DataFrame,
    combo_results: pd.DataFrame,
) -> bytes:
    """Export analysis tables to an in-memory Excel workbook."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        significant_results.to_excel(writer, index=False, sheet_name="significant")
        all_results.to_excel(writer, index=False, sheet_name="all_results")
        up_results.to_excel(writer, index=False, sheet_name="up_results")
        down_results.to_excel(writer, index=False, sheet_name="down_results")
        combo_results.to_excel(writer, index=False, sheet_name="three_day_combos")

        workbook = writer.book
        percent_format = workbook.add_format({"num_format": "0.00%"})
        number_format = workbook.add_format({"num_format": "0.0000"})

        for sheet_name, data in {
            "significant": significant_results,
            "all_results": all_results,
            "up_results": up_results,
            "down_results": down_results,
            "three_day_combos": combo_results,
        }.items():
            worksheet = writer.sheets[sheet_name]
            worksheet.freeze_panes(1, 0)
            for idx, column in enumerate(data.columns):
                width = max(12, min(28, len(str(column)) + 2))
                fmt = None
                if column.endswith("_ratio") or column.endswith("_prob"):
                    fmt = percent_format
                elif column == "p_value":
                    fmt = number_format
                worksheet.set_column(idx, idx, width, fmt)

    return buffer.getvalue()
