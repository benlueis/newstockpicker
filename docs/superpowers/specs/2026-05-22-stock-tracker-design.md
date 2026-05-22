# 选股回顾 Web Tracker — 设计

## Context
现有三策略每日扫描产物为 `data/{strategy}_{date}.csv`，但没有任何后续跟踪。需要本地部署一个网页，按日期回看每天的选股结果，并显示这些个股 T+1/T+3/T+5 的实际涨跌幅，用以验证策略胜率与确定性。

## 架构

- **框架**：Streamlit 单页应用，文件 `app.py` 放仓库根
- **启动**：`streamlit run app.py` → 浏览器自动开 `http://localhost:8501`
- **依赖新增**：`streamlit`、`plotly`，加入 `requirements.txt`
- **不引入数据库**，纯文件读取

## 数据来源

| 用途 | 路径 | 备注 |
|---|---|---|
| 当日选股 CSV | `data/breakout_*.csv` / `data/dragon_leader_*.csv` / `data/sideways_breakout_*.csv` | 已存在，gitignored |
| 历史日 K | `data/cache/{code}.parquet` | 已存在，由 `scripts/update_cache.py` 维护 |

## 页面结构（单页三表格）

```
┌─────────────────────────────────────────────────┐
│ 选股回顾  日期: [2026-05-19 ▼]  胜率口径: [T+5▼] │
├─────────────────────────────────────────────────┤
│ 🟢 低位横盘突破     │ 🔴 市场龙头   │ 🟡 横盘突破│
│ 当桶胜率: 4/5=80%  │ 11/17=64.7%   │ 1/4=25% │
│ ┌────────────────┐│ ┌──────────┐ │ ┌────────┐│
│ │代码 名称  T+1   ││ │...       │ │ │...     ││
│ │T+3  T+5  详情  ││ │          │ │ │        ││
│ └────────────────┘│ └──────────┘ │ └────────┘│
│ (点击行 → 下方展开 30 日 K 线)                   │
└─────────────────────────────────────────────────┘
```

- **顶部控件**：
  - 日期选择器：从 `data/` 下能扫到的所有 CSV 日期里取交集（确保三策略都跑过那天）
  - 胜率口径：T+1 / T+3 / T+5 切换（默认 T+5）
- **三个表格并列**：每个策略一张
  - 列：代码 / 名称 / T+1 % / T+3 % / T+5 % / 信号详情（量比、突破幅度等关键字段）
  - 行点击展开 → 表格下方显示该股 K 线
- **桶级胜率**：每个表格上方显示，定义见下

## 指标定义

- 设 `base = close[signal_date]`
- `T+N % = (close[signal_date + N 个交易日] / base − 1) × 100`，保留 2 位小数
- 若 `signal_date + N` 还没数据（cache 未到），单元格显示 `—`
- **桶级胜率**：当前选定口径下，T+N % > 0 的票数 / 总票数。涨幅样本不足时（cache 未到）从分母剔除
- **绝对胜率**起步，不做相对沪深 300 比较（YAGNI）

## K 线展开

- 点击表格行 → 表格下方折叠面板显示
- **图表库**：Plotly Candlestick
- **范围**：信号日前 20 日 + 信号日 + 后 20 日（共约 41 根，超出部分若 cache 没到则截断）
- **标注**：信号日画一条绿色竖线
- 一次只展开一只（点新行替换旧 K 线）

## 模块结构

文件清单：

| 文件 | 职责 |
|---|---|
| `app.py` | Streamlit 入口、页面布局、控件、表格渲染、点击交互 |
| `scripts/tracker_metrics.py` | 纯函数：`compute_returns(code, signal_date) -> {T+1, T+3, T+5}`、`compute_bucket_winrate(df, horizon) -> (wins, total)`、`get_available_dates() -> [date]` |

`tracker_metrics.py` 抽出来是为了方便单元测试，避免在 Streamlit app 里塞业务逻辑。

## 数据时效说明

显示在页面底部的小字提示：
- "T+N 数据由 baostock 收盘后日 K 提供。今天的胜率最早要在第 N 个交易日收盘后才能完整。"
- 当胜率分母 < 总票数时，显示 `4/5 已计算 (1 待数据更新)`，不让 user 误以为缺信号

## 不做的事（YAGNI）

- 不做用户登录、权限
- 不做实时盘中价（baostock 已够，且用户暂不需要）
- 不做手动建仓 / 平仓 / 盈亏 / 仓位模拟
- 不做策略对比、组合回测、参数调优
- 不做相对沪深 300 的相对胜率（起步只用绝对收益）
- 不做云部署（明确选择本地起步）

## 验证

1. 启动 `streamlit run app.py` → 打开 `http://localhost:8501`
2. 选择 `2026-05-19` → 应看到三个表格分别显示 0 / 17 / 5 只
3. 点击 sideways 表里 `sz.002527 新时达` → 下方应渲染含信号日竖线的 K 线
4. 切换胜率口径 T+1/T+3/T+5 → 三个桶胜率数字应同步刷新
5. 选择 `2026-05-20`（数据未到 T+5）→ 部分单元格显示 `—`，桶胜率显示 `4/5 已计算`
6. 单测 `pytest tests/test_tracker_metrics.py` → `compute_returns`、`compute_bucket_winrate` 跑通

## 关键文件参考

- 已有 `backtest/tracker.py`：信号跟踪原型，`get_hist_after_signal` 的思路可复用，但具体到 parquet 缓存读取需要重写（原版走 baostock 在线）
- `strategies/common.py::get_stock_data`：缓存优先的数据读取，可直接复用
- `scripts/cache_manager.py::load`：直接读 parquet，最快路径
