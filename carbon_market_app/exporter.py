from __future__ import annotations

from io import BytesIO

import pandas as pd


def to_excel_bytes(
    all_results: pd.DataFrame,
    significant_results: pd.DataFrame,
    threshold_results: pd.DataFrame | None = None,
) -> bytes:
    """Export MVP result tables to an in-memory Excel workbook."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        if threshold_results is not None:
            threshold_results.to_excel(
                writer, index=False, sheet_name="threshold_results"
            )
        significant_results.to_excel(
            writer, index=False, sheet_name="significant_results"
        )
        all_results.to_excel(writer, index=False, sheet_name="all_results")

        workbook = writer.book
        percent_format = workbook.add_format({"num_format": "0.00%"})
        pvalue_format = workbook.add_format({"num_format": "0.0000"})

        sheets = {
            "significant_results": significant_results,
            "all_results": all_results,
        }
        if threshold_results is not None:
            sheets = {"threshold_results": threshold_results, **sheets}

        for sheet_name, data in sheets.items():
            worksheet = writer.sheets[sheet_name]
            worksheet.freeze_panes(1, 0)
            for idx, column in enumerate(data.columns):
                fmt = None
                if column.endswith("_ratio") or column.endswith("_prob"):
                    fmt = percent_format
                elif column == "p_value":
                    fmt = pvalue_format
                worksheet.set_column(
                    idx, idx, max(12, min(28, len(str(column)) + 2)), fmt
                )

    return buffer.getvalue()
