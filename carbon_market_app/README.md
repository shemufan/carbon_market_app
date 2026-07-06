# 碳市场均线交叉显著性分析系统

一个基于 Streamlit 的小型网页工具，用于分析欧盟碳市场拍卖价格数据中的均线交叉信号。

## 功能

- 上传 Excel 文件，不再写死本地路径。
- 设置行号范围、均线范围、阈值、显著性 alpha 和分析类型。
- 自动遍历 `min_ma <= a < b <= max_ma` 的所有均线组合。
- 统计上穿、下穿信号后第 1、2、3 天价格上涨、下跌、持平情况。
- 使用二项检验计算显著性，并计算 Jeffreys 上涨/下跌概率。
- 展示显著配比对、全部结果、上穿结果、下穿结果和后三天组合。
- 下载 Excel 结果。

## 数据要求

Excel 至少需要包含：

- `Mean`：平均价格列。如果文件中是 `Mean Price`，程序会自动改名为 `Mean`。
- `Mean1` 到 `Mean40`：多日均线列。实际需要的列取决于页面中设置的 `min_ma` 和 `max_ma`。

当前默认原始数据按日期倒序排列：`shift(-1)` 表示昨天，交叉行索引减 1/2/3 表示交叉后的第 1/2/3 天。如果未来数据改成日期正序，需要统一调整 `analysis_engine.py` 中的索引方向。

## 安装与运行

```bash
cd carbon_market_app
pip install -r requirements.txt
streamlit run app.py
```

## 输出说明

每日显著性结果至少包含：

- `pair`：配比对，例如 `4/17`
- `cross_type`：`up` 或 `down`
- `day`：1、2、3
- `signal_count`
- `up_count`、`down_count`、`flat_count`
- `up_ratio`、`down_ratio`
- `p_value`
- `is_significant`
- `jeffreys_up_prob`
- `jeffreys_down_prob`

另有 `three_day_combos` 表保存后三天组合，例如 `1,1,1`、`1,1,-1`、`-1,1,-1` 的次数和比例。
