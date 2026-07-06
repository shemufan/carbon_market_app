from __future__ import annotations

import re
from pathlib import Path
from typing import BinaryIO

import pandas as pd
import streamlit as st

from analysis_engine import AnalysisThresholds, analyze_all_pairs
from data_loader import apply_row_range, read_excel_file, validate_input_columns
from exporter import to_excel_bytes

APP_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_PATH = APP_DIR / "sample_data" / "carbon_market_sample.xlsx"

SAMPLE_SOURCE = "使用内置样例数据"
UPLOAD_SOURCE = "上传 Excel 文件"

PROBABILITY_COLUMNS = [
    "up_ratio",
    "down_ratio",
    "p_value",
    "jeffreys_up_prob",
    "jeffreys_down_prob",
]

RESULT_STATE_KEY = "analysis_result_bundle"
DATA_STATE_KEY = "active_data_key"


st.set_page_config(page_title="碳市场均线交叉显著性分析系统", layout="wide")


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .main .block-container {
            padding-top: 2rem;
            max-width: 1280px;
        }
        .hero {
            border: 1px solid #d7e3df;
            border-left: 6px solid #1b6f5a;
            border-radius: 8px;
            padding: 1.2rem 1.4rem;
            background: #f7fbf9;
            margin-bottom: 1rem;
        }
        .hero h1 {
            margin: 0 0 .45rem 0;
            color: #133b33;
            font-size: 2rem;
            letter-spacing: 0;
        }
        .hero p {
            margin: 0;
            color: #48635c;
            font-size: 1rem;
            line-height: 1.6;
        }
        [data-testid="stMetric"] {
            border: 1px solid #dfe8e5;
            border-radius: 8px;
            padding: .85rem 1rem;
            background: #ffffff;
            box-shadow: 0 1px 4px rgba(20, 61, 52, .06);
        }
        [data-testid="stMetricLabel"] {
            color: #5b6f69;
        }
        [data-testid="stMetricValue"] {
            color: #143d34;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
        <div class="hero">
            <h1>碳市场均线交叉显著性分析系统</h1>
            <p>本系统用于分析欧盟碳市场价格中，多日均线交叉信号与未来 1-3 日价格涨跌之间的统计关系。</p>
            <p>如果只是体验分析流程，可以直接使用内置样例数据；如果需要分析自己的数据，可以切换为上传 Excel 文件。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def format_for_display(df: pd.DataFrame) -> pd.DataFrame:
    display_df = df.copy()
    for column in PROBABILITY_COLUMNS:
        if column in display_df.columns:
            display_df[column] = display_df[column].map(
                lambda value: "" if pd.isna(value) else f"{value:.2%}"
            )
    return display_df


def unique_pair_count(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    return len(df[["pair", "cross_type"]].drop_duplicates())


def total_signal_count(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    signal_rows = df[["pair", "cross_type", "signal_count"]].drop_duplicates()
    return int(signal_rows["signal_count"].sum())


def render_dataframe(df: pd.DataFrame) -> None:
    st.dataframe(format_for_display(df), width="stretch", hide_index=True)


def make_data_key(data_source: str, uploaded_file) -> str:
    if data_source == SAMPLE_SOURCE:
        if DEFAULT_DATA_PATH.exists():
            stat = DEFAULT_DATA_PATH.stat()
            return f"sample:{DEFAULT_DATA_PATH.name}:{stat.st_size}:{stat.st_mtime_ns}"
        return "sample:missing"

    if uploaded_file is None:
        return "upload:none"
    return f"upload:{uploaded_file.name}:{uploaded_file.size}"


def safe_download_name(source_name: str) -> str:
    base_name = source_name.rsplit(".", 1)[0]
    safe_name = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "_", base_name).strip("_")
    return f"{safe_name or 'carbon_market'}_analysis_results.xlsx"


def clear_results_for_new_data(data_source: str, uploaded_file) -> None:
    data_key = make_data_key(data_source, uploaded_file)
    if st.session_state.get(DATA_STATE_KEY) != data_key:
        st.session_state[DATA_STATE_KEY] = data_key
        st.session_state.pop(RESULT_STATE_KEY, None)


def render_results(result_bundle: dict) -> None:
    all_results = result_bundle["all_results"]
    threshold_sorted = result_bundle["threshold_sorted"]
    significant_sorted = result_bundle["significant_sorted"]
    signal_sorted = result_bundle["signal_sorted"]
    up_results = result_bundle["up_results"]
    down_results = result_bundle["down_results"]
    source_name = result_bundle["source_name"]
    total_pairs = result_bundle["total_pairs"]

    up_significant = significant_sorted[significant_sorted["cross_type"] == "up"]
    down_significant = significant_sorted[significant_sorted["cross_type"] == "down"]

    st.caption(
        "说明：当前默认 Excel 按日期倒序排列。程序使用 shift(-1) 表示昨天，"
        "使用交叉行索引减 1/2/3 表示交叉后的第 1/2/3 天。"
    )

    metric_cols = st.columns(5)
    metric_cols[0].metric("均线配比对数量", f"{total_pairs:,}")
    metric_cols[1].metric("总信号数", f"{total_signal_count(all_results):,}")
    metric_cols[2].metric(
        "显著配比对数量", f"{unique_pair_count(significant_sorted):,}"
    )
    metric_cols[3].metric("上穿显著数量", f"{unique_pair_count(up_significant):,}")
    metric_cols[4].metric("下穿显著数量", f"{unique_pair_count(down_significant):,}")

    tab_threshold, tab_sig, tab_signal, tab_up, tab_down, tab_all = st.tabs(
        [
            "阈值初筛结果",
            "最终显著结果",
            "按信号数排序",
            "上穿结果",
            "下穿结果",
            "全部结果",
        ]
    )

    with tab_threshold:
        render_dataframe(threshold_sorted)
    with tab_sig:
        render_dataframe(significant_sorted)
    with tab_signal:
        render_dataframe(signal_sorted)
    with tab_up:
        render_dataframe(up_results)
    with tab_down:
        render_dataframe(down_results)
    with tab_all:
        render_dataframe(all_results)

    excel_bytes = to_excel_bytes(all_results, significant_sorted, threshold_sorted)
    st.download_button(
        label="下载 Excel 结果",
        data=excel_bytes,
        file_name=safe_download_name(source_name),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )


def build_result_bundle(
    data_input: str | Path | BinaryIO,
    source_name: str,
    start_row: int,
    end_row: int,
    min_ma: int,
    max_ma: int,
    threshold_high: float,
    threshold_low: float,
    threshold_3day: float,
    alpha: float,
    cross_type: str,
) -> dict:
    df_full = read_excel_file(data_input)
    df = apply_row_range(df_full, start_row, end_row)
    validate_input_columns(df, min_ma, max_ma)

    cross_types = ["up", "down"] if cross_type == "both" else [cross_type]

    all_results = analyze_all_pairs(
        df=df,
        min_ma=min_ma,
        max_ma=max_ma,
        cross_types=cross_types,
        alpha=alpha,
        thresholds=AnalysisThresholds(
            high=threshold_high,
            low=threshold_low,
            three_day=threshold_3day,
        ),
    )

    threshold_results = all_results[all_results["threshold_triggered"]].copy()
    significant_results = all_results[all_results["is_significant"]].copy()
    total_pairs = (max_ma - min_ma + 1) * (max_ma - min_ma) // 2

    return {
        "source_name": source_name,
        "all_results": all_results,
        "threshold_sorted": threshold_results.sort_values(
            ["signal_count", "pair", "cross_type", "day"],
            ascending=[False, True, True, True],
        ),
        "significant_sorted": significant_results.sort_values(
            "p_value", ascending=True
        ),
        "signal_sorted": all_results.sort_values("signal_count", ascending=False),
        "up_results": all_results[all_results["cross_type"] == "up"].copy(),
        "down_results": all_results[all_results["cross_type"] == "down"].copy(),
        "total_pairs": total_pairs,
    }


inject_styles()
render_header()

data_source = st.radio(
    "数据来源",
    [SAMPLE_SOURCE, UPLOAD_SOURCE],
    index=0,
    horizontal=True,
)

uploaded_file = None
if data_source == UPLOAD_SOURCE:
    uploaded_file = st.file_uploader("上传 Excel 文件", type=["xlsx", "xls"])

clear_results_for_new_data(data_source, uploaded_file)

if data_source == SAMPLE_SOURCE:
    st.info("当前数据来源：内置样例数据")
    if not DEFAULT_DATA_PATH.exists():
        st.error("未找到内置样例数据文件：sample_data/carbon_market_sample.xlsx")
else:
    st.info("当前数据来源：上传 Excel 文件")
    if uploaded_file is None:
        st.info("请上传包含 Mean、Mean1、Mean2 ... 等列的 Excel 文件。")

with st.sidebar:
    st.header("参数设置")

    st.subheader("数据范围设置")
    start_row = st.number_input("start_row", min_value=0, value=0, step=1)
    end_row = st.number_input("end_row", min_value=0, value=2000, step=1)

    st.subheader("均线范围设置")
    min_ma = st.number_input("min_ma", min_value=1, max_value=40, value=1, step=1)
    max_ma = st.number_input("max_ma", min_value=1, max_value=40, value=40, step=1)

    st.subheader("判断阈值设置")
    threshold_high = st.number_input(
        "threshold_high (%)",
        min_value=0.0,
        max_value=100.0,
        value=60.0,
        step=1.0,
    )
    threshold_low = st.number_input(
        "threshold_low (%)",
        min_value=0.0,
        max_value=100.0,
        value=40.0,
        step=1.0,
    )
    threshold_3day = st.number_input(
        "threshold_3day (%)",
        min_value=0.0,
        max_value=100.0,
        value=25.0,
        step=1.0,
        help="用于筛选完整三日涨跌组合占比，例如 1,-1,1。",
    )

    st.subheader("显著性设置")
    alpha = st.number_input(
        "alpha", min_value=0.001, max_value=1.0, value=0.1, step=0.01
    )

    st.subheader("分析类型设置")
    cross_type = st.selectbox("cross_type", ["both", "up", "down"])

    sample_ready = data_source == SAMPLE_SOURCE and DEFAULT_DATA_PATH.exists()
    upload_ready = data_source == UPLOAD_SOURCE and uploaded_file is not None
    run_button = st.button(
        "开始分析",
        type="primary",
        disabled=not (sample_ready or upload_ready),
        width="stretch",
    )

if run_button:
    if int(start_row) > int(end_row):
        st.error("start_row 必须小于或等于 end_row。")
        st.stop()
    if int(min_ma) >= int(max_ma):
        st.error("min_ma 必须小于 max_ma。")
        st.stop()

    if data_source == SAMPLE_SOURCE:
        data_input = DEFAULT_DATA_PATH
        source_name = DEFAULT_DATA_PATH.name
    else:
        data_input = uploaded_file
        source_name = uploaded_file.name

    try:
        with st.spinner("正在遍历均线组合并计算显著性..."):
            st.session_state[RESULT_STATE_KEY] = build_result_bundle(
                data_input=data_input,
                source_name=source_name,
                start_row=int(start_row),
                end_row=int(end_row),
                min_ma=int(min_ma),
                max_ma=int(max_ma),
                threshold_high=float(threshold_high),
                threshold_low=float(threshold_low),
                threshold_3day=float(threshold_3day),
                alpha=float(alpha),
                cross_type=cross_type,
            )
    except Exception as exc:
        st.error(f"分析失败：{exc}")

if RESULT_STATE_KEY in st.session_state:
    render_results(st.session_state[RESULT_STATE_KEY])
