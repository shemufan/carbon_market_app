from __future__ import annotations

import pandas as pd
import streamlit as st

from analysis_engine import AnalysisThresholds, analyze_all_pairs
from data_loader import apply_row_ranges, parse_row_ranges, read_excel_file, validate_input_columns
from exporter import to_excel_bytes


st.set_page_config(page_title="碳市场均线交叉显著性分析系统", layout="wide")
st.title("碳市场均线交叉显著性分析系统")

uploaded_file = st.file_uploader("上传 Excel 文件", type=["xlsx", "xls"])

with st.sidebar:
    st.header("参数设置")
    row_ranges_text = st.text_input("行号范围 ROW_RANGES", value="9-2000")
    min_ma = st.number_input("min_ma", min_value=1, max_value=40, value=1, step=1)
    max_ma = st.number_input("max_ma", min_value=1, max_value=40, value=40, step=1)
    threshold_high = st.number_input("THRESHOLD_HIGH (%)", value=60.0, step=1.0)
    threshold_low = st.number_input("THRESHOLD_LOW (%)", value=40.0, step=1.0)
    threshold_3day = st.number_input("THRESHOLD_3DAY (%)", value=25.0, step=1.0)
    alpha = st.number_input("显著性阈值 alpha", min_value=0.001, max_value=1.0, value=0.1, step=0.01)
    analysis_type = st.selectbox("分析类型", ["上穿+下穿", "上穿", "下穿"])
    sort_by = st.selectbox("显著配比对排序", ["p_value", "signal_count", "jeffreys_up_prob", "jeffreys_down_prob"])
    ascending = st.checkbox("升序排序", value=True)

run_button = st.button("开始分析", type="primary", disabled=uploaded_file is None)

if uploaded_file is None:
    st.info("请先上传包含 Mean、Mean1 到 Mean40 等列的 Excel 文件。")

if run_button and uploaded_file is not None:
    if int(min_ma) >= int(max_ma):
        st.error("min_ma 必须小于 max_ma。")
        st.stop()

    try:
        row_ranges = parse_row_ranges(row_ranges_text)
        df_full = read_excel_file(uploaded_file)
        df = apply_row_ranges(df_full, row_ranges)
        validate_input_columns(df, int(min_ma), int(max_ma))

        cross_types = []
        if analysis_type in ("上穿", "上穿+下穿"):
            cross_types.append("up")
        if analysis_type in ("下穿", "上穿+下穿"):
            cross_types.append("down")

        thresholds = AnalysisThresholds(
            high=float(threshold_high),
            low=float(threshold_low),
            three_day=float(threshold_3day),
        )

        with st.spinner("正在遍历均线组合并计算显著性..."):
            all_results, combo_results = analyze_all_pairs(
                df=df,
                min_ma=int(min_ma),
                max_ma=int(max_ma),
                cross_types=cross_types,
                alpha=float(alpha),
                thresholds=thresholds,
            )

        significant_results = all_results[all_results["is_significant"]].copy()
        if not significant_results.empty and sort_by in significant_results.columns:
            significant_results = significant_results.sort_values(sort_by, ascending=ascending)

        up_results = all_results[all_results["cross_type"] == "up"].copy()
        down_results = all_results[all_results["cross_type"] == "down"].copy()

        st.caption(
            "说明：当前默认原始数据按日期倒序排列；程序使用 shift(-1) 表示昨天，"
            "使用交叉行索引减 1/2/3 表示交叉后的第 1/2/3 天。"
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("分析行数", len(df))
        c2.metric("结果行数", len(all_results))
        c3.metric("显著结果数", len(significant_results))

        st.subheader("显著配比对")
        st.dataframe(significant_results, use_container_width=True)

        tab_all, tab_up, tab_down, tab_combo = st.tabs(["全部结果", "上穿结果", "下穿结果", "后三天组合"])
        with tab_all:
            st.dataframe(all_results, use_container_width=True)
        with tab_up:
            st.dataframe(up_results, use_container_width=True)
        with tab_down:
            st.dataframe(down_results, use_container_width=True)
        with tab_combo:
            st.dataframe(combo_results, use_container_width=True)

        excel_bytes = to_excel_bytes(
            all_results=all_results,
            significant_results=significant_results,
            up_results=up_results,
            down_results=down_results,
            combo_results=combo_results,
        )
        st.download_button(
            label="下载 Excel 结果",
            data=excel_bytes,
            file_name="carbon_market_analysis_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as exc:
        st.error(f"分析失败：{exc}")
