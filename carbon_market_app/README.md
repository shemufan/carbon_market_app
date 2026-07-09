# 碳市场均线交叉显著性分析系统

这是一个基于 Streamlit 的数据分析小工具，用于分析欧盟碳市场价格中，多日均线交叉信号与未来 1-3 日价格涨跌之间的统计关系。

## 功能

- 默认提供内置样例数据，打开网页后无需上传 Excel 也可以直接体验分析流程。
- 支持切换为上传 Excel 文件，分析自己的数据。
- 设置行号范围、均线范围、阈值初筛参数、显著性阈值 `alpha` 和分析类型。
- 自动遍历 `min_ma <= a < b <= max_ma` 的均线组合。
- 展示阈值初筛结果、最终显著结果、按信号数排序结果、上穿结果、下穿结果和全部结果。
- 使用 `BytesIO` 在内存中生成 Excel 下载文件，不在服务器磁盘保存用户上传文件或结果文件。

## 数据

### 内置默认数据

项目内置样例文件，该文件是用于课程项目演示的模拟样例数据，包含 `Mean` 和 `Mean1` 到 `Mean40`。允许使用者可以直接使用默认文件来进行操作，而无需上传自己的文件，从而快速进行操作分析。

### 本地数据要求

#### 如果要上传本地自己的数据

Excel 至少需要包含：

- `Mean`：平均价格列。如果列名为 `Mean Price`，程序会自动改名为 `Mean`。
- `Mean1` 到 `MeanN`：均线列，实际需要的最大列由页面中自定义的的 `max_ma` 决定。

当前默认 Excel 按日期倒序排列：`shift(-1)` 表示昨天，交叉行索引减 1/2/3 表示交叉后的第 1/2/3 天。如果数据改成日期正序，需要调整 `analysis_engine.py` 中的索引方向。

`threshold_high`、`threshold_low`、`threshold_3day` 是阈值初筛参数，`alpha` 是最终显著性筛选阈值，当前逻辑会先进行初筛再显著性选择。结果表会对 day=1/2/3 的 `up_ratio` 和 `down_ratio` 做初筛：比例百分比大于 `threshold_high` 或小于 `threshold_low` 时，`threshold_triggered` 为 `True`，触发原因写入 `threshold_alerts`。程序同时也会计算完整三日涨跌组合，例如 `1,-1,1`，当组合占比大于 `threshold_3day` 时，在 day=3 行写入三日组合提醒。而最终显著结果由单点二项概率 `p_value < alpha` 决定。

## 本地运行（建议使用虚拟环境）

```bash
cd carbon_market_app
pip install -r requirements.txt
streamlit run app.py
```

## 并发访问说明

应用不会把上传文件保存到固定文件名，也不会把输出结果保存到固定文件名。每次分析都使用当前用户选择的数据源，并通过 `BytesIO` 在内存中生成下载文件。

当前用户的分析结果保存在 `st.session_state` 中。Streamlit 会为不同浏览器会话维护独立的 session state，因此两个用户同时选择不同数据源或上传不同 Excel 并运行分析时，结果不会互相覆盖。

本项目没有使用 `st.cache_data`。原因是上传文件属于用户私有输入，缓存它可能造成不必要的数据驻留和跨会话混淆，因此不设置缓存机制。

## 输出列说明

| 列名 | 含义 |
| --- | --- |
| `pair` | 均线配比对，例如 `4/17` 表示 `Mean4` 和 `Mean17`。 |
| `cross_type` | 交叉类型，`up` 表示上穿，`down` 表示下穿。 |
| `day` | 交叉后的第几天，当前统计第 1、2、3 天。 |
| `signal_count` | 当前配比对和交叉类型在数据范围内出现的交叉信号总数。 |
| `up_count` | 对应 `day` 上价格上涨的次数。 |
| `down_count` | 对应 `day` 上价格下跌的次数。 |
| `flat_count` | 对应 `day` 上价格持平的次数。 |
| `up_ratio` | 上涨比例，等于 `up_count / 可计算样本数`。 |
| `down_ratio` | 下跌比例，等于 `down_count / 可计算样本数`。 |
| `threshold_triggered` | 是否触发阈值初筛。 |
| `threshold_alerts` | 触发阈值初筛的具体原因，例如 `up_ratio > 60%`。 |
| `p_value` | 单点二项概率，表示在 50/50 假设下刚好出现当前上涨/下跌次数组合的概率。 |
| `is_significant` | 最终显著性判断，当前规则为 `p_value < alpha`。 |
| `jeffreys_up_prob` | Jeffreys 修正后的上涨概率估计，忽略持平样本。 |
| `jeffreys_down_prob` | Jeffreys 修正后的下跌概率估计，忽略持平样本。 |

其中，`up_ratio` 和 `down_ratio` 的分母包含持平样本；`p_value` 和 Jeffreys 概率计算时暂时忽略持平样本，只使用 `up_count + down_count` 作为有效样本数。当前 `p_value` 使用单点概率口径；如果后续需要切回双侧二项检验，可以集中修改 `significance.py` 中的 p 值计算函数。
