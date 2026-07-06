# 碳市场均线交叉显著性分析系统

这是一个基于 Streamlit 的数据分析小工具，用于分析欧盟碳市场价格中，多日均线交叉信号与未来 1-3 日价格涨跌之间的统计关系。

## 功能

- 通过网页上传 Excel 文件。
- 设置行号范围、均线范围、判断阈值、显著性阈值和分析类型。
- 自动遍历 `min_ma <= a < b <= max_ma` 的均线组合。
- 展示显著配比对、按信号数排序结果、上穿结果、下穿结果和全部结果。
- 使用 `BytesIO` 在内存中生成 Excel 下载文件，不在服务器磁盘保存用户文件或结果文件。

## 数据要求

Excel 至少需要包含：

- `Mean`：平均价格列。如果列名为 `Mean Price`，程序会自动改名为 `Mean`。
- `Mean1` 到 `MeanN`：均线列，实际需要的最大列由页面中的 `max_ma` 决定。

当前默认 Excel 按日期倒序排列：`shift(-1)` 表示昨天，交叉行索引减 1/2/3 表示交叉后的第 1/2/3 天。如果未来数据改成日期正序，需要统一调整 `analysis_engine.py` 中的索引方向。

## 本地运行

```bash
cd carbon_market_app
pip install -r requirements.txt
streamlit run app.py
```

如果使用 Conda，建议先创建并激活独立环境：

```bash
conda create -n carbon_env python=3.11
conda activate carbon_env
pip install -r requirements.txt
streamlit run app.py
```

## 部署到 Streamlit Community Cloud

1. 将项目上传到 GitHub 仓库。
2. 确保仓库中包含 `carbon_market_app/app.py` 和依赖文件。当前项目同时提供了根目录 `requirements.txt` 和 `carbon_market_app/requirements.txt`，方便不同仓库结构部署。
3. 打开 Streamlit Community Cloud，选择该 GitHub 仓库。
4. Main file path 填写：

```text
carbon_market_app/app.py
```

5. 点击 Deploy。

如果把 `carbon_market_app` 目录内容放在仓库根目录，则保留同目录下的 `requirements.txt`，Main file path 填写：

```text
app.py
```

## 并发访问说明

应用不会把上传文件保存到固定文件名，也不会把输出结果保存到固定文件名。每次分析都使用当前用户上传的 Excel 文件对象，并通过 `BytesIO` 在内存中生成下载文件。

当前用户的分析结果保存在 `st.session_state` 中。Streamlit 会为不同浏览器会话维护独立的 session state，因此两个用户同时上传不同 Excel 并运行分析时，结果不会互相覆盖。

本项目没有使用 `st.cache_data`。原因是上传文件属于用户私有输入，缓存它可能造成不必要的数据驻留和跨会话混淆。后续如果要缓存，只建议缓存不含用户私有数据的静态配置或纯函数元数据。

## 输出列

- `pair`
- `cross_type`
- `day`
- `signal_count`
- `up_count`
- `down_count`
- `flat_count`
- `up_ratio`
- `down_ratio`
- `p_value`
- `is_significant`
- `jeffreys_up_prob`
- `jeffreys_down_prob`
