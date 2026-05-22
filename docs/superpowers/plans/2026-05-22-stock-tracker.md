# 选股回顾 Web Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 本地 Streamlit 网页，按日期看每日三策略选股 + T+1/T+3/T+5 涨跌幅 + 桶级胜率 + 个股 K 线

**Architecture:** Streamlit 单页 app 读取 `data/{strategy}_{date}.csv` 与 `data/cache/{code}.parquet`，业务逻辑抽到 `scripts/tracker_metrics.py`（纯函数、可测），视图层只做布局与控件。

**Tech Stack:** Python 3.11、streamlit、plotly、pandas、pyarrow（已装）、pytest（项目已有 unittest 风格测试）

---

## File Structure

| 文件 | 职责 | 状态 |
|---|---|---|
| `scripts/tracker_metrics.py` | 纯函数：扫描可用日期、读 CSV、计算 T+N 涨幅、计算桶胜率 | 新建 |
| `app.py` | Streamlit 入口：日期/口径控件、三表格、行点击展开 K 线 | 新建（项目根） |
| `tests/test_tracker_metrics.py` | tracker_metrics 单元测试 | 新建 |
| `requirements.txt` | 加 `streamlit`、`plotly` | 修改 |

---

## Task 1: 计算 T+N 涨跌幅（compute_returns）

**Files:**
- Test: `tests/test_tracker_metrics.py`
- Create: `scripts/tracker_metrics.py`

- [ ] **Step 1: 写失败测试**

写到 `tests/test_tracker_metrics.py`：

```python
"""tracker_metrics 单元测试"""
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from tracker_metrics import compute_returns


def _make_bars(close_seq):
    return pd.DataFrame({
        "date": pd.date_range("2026-05-10", periods=len(close_seq), freq="B"),
        "close": close_seq,
    })


class TestComputeReturns(unittest.TestCase):

    def test_t1_t3_t5_basic(self):
        # 信号日 close=10，T+1=11 (+10%), T+3=12 (+20%), T+5=11 (+10%)
        bars = _make_bars([10, 11, 11.5, 12, 11.8, 11])
        signal_date = bars["date"].iloc[0]
        out = compute_returns(bars, signal_date, horizons=(1, 3, 5))
        self.assertAlmostEqual(out[1], 10.0, places=2)
        self.assertAlmostEqual(out[3], 20.0, places=2)
        self.assertAlmostEqual(out[5], 10.0, places=2)

    def test_missing_future_bar_returns_none(self):
        # 只有信号日 + 2 根，T+3 / T+5 应返回 None
        bars = _make_bars([10, 11, 12])
        signal_date = bars["date"].iloc[0]
        out = compute_returns(bars, signal_date, horizons=(1, 3, 5))
        self.assertAlmostEqual(out[1], 10.0, places=2)
        self.assertIsNone(out[3])
        self.assertIsNone(out[5])

    def test_signal_date_not_in_frame_returns_all_none(self):
        bars = _make_bars([10, 11])
        out = compute_returns(bars, pd.Timestamp("2024-01-01"), horizons=(1, 3, 5))
        self.assertIsNone(out[1])
        self.assertIsNone(out[3])
        self.assertIsNone(out[5])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd /Users/xifeiyou/Documents/workspace/stock-picker
.venv/bin/python -m pytest tests/test_tracker_metrics.py -v
```

预期：`ModuleNotFoundError: No module named 'tracker_metrics'`

- [ ] **Step 3: 写最小实现**

新建 `scripts/tracker_metrics.py`：

```python
"""选股回顾页面用的纯函数：可用日期、读 CSV、T+N 涨幅、桶胜率。"""
from __future__ import annotations

from typing import Iterable

import pandas as pd


def compute_returns(
    bars: pd.DataFrame,
    signal_date: pd.Timestamp,
    horizons: Iterable[int] = (1, 3, 5),
) -> dict[int, float | None]:
    """
    输入：单只股票按日期升序的 K 线（含 date、close 列）+ 信号日
    输出：{1: T+1涨幅%, 3: T+3涨幅%, 5: T+5涨幅%}；未来数据缺失则 None
    """
    horizons = list(horizons)
    out: dict[int, float | None] = {h: None for h in horizons}

    if "date" not in bars.columns or "close" not in bars.columns:
        return out
    if bars.empty:
        return out

    df = bars.sort_values("date").reset_index(drop=True)
    sig_idx = df.index[df["date"] == signal_date]
    if len(sig_idx) == 0:
        return out

    base_idx = int(sig_idx[0])
    base = float(df["close"].iloc[base_idx])
    if base <= 0:
        return out

    for h in horizons:
        target = base_idx + h
        if target >= len(df):
            continue
        future = float(df["close"].iloc[target])
        out[h] = round((future / base - 1) * 100, 2)
    return out
```

- [ ] **Step 4: 跑测试确认通过**

```bash
.venv/bin/python -m pytest tests/test_tracker_metrics.py -v
```

预期：3 个测试全部 PASS

- [ ] **Step 5: 提交**

```bash
git add scripts/tracker_metrics.py tests/test_tracker_metrics.py
git commit -m "feat(tracker): compute_returns 计算 T+N 涨跌幅"
```

---

## Task 2: 桶级胜率（compute_bucket_winrate）

**Files:**
- Modify: `tests/test_tracker_metrics.py` (追加测试类)
- Modify: `scripts/tracker_metrics.py` (追加函数)

- [ ] **Step 1: 写失败测试**

在 `tests/test_tracker_metrics.py` 文件末尾追加（在 `if __name__ == "__main__"` 之前）：

```python
class TestBucketWinrate(unittest.TestCase):

    def test_basic_winrate(self):
        # 5 票，T+5 涨幅: 3 正 1 负 1 None → 3/4 = 75%
        rows = [
            {"代码": "a", "T+5": 1.5},
            {"代码": "b", "T+5": -2.0},
            {"代码": "c", "T+5": 0.1},
            {"代码": "d", "T+5": 5.0},
            {"代码": "e", "T+5": None},
        ]
        df = pd.DataFrame(rows)
        from tracker_metrics import compute_bucket_winrate
        wins, total = compute_bucket_winrate(df, horizon=5)
        self.assertEqual(wins, 3)
        self.assertEqual(total, 4)

    def test_all_pending_returns_zero_total(self):
        df = pd.DataFrame([{"代码": "a", "T+5": None}, {"代码": "b", "T+5": None}])
        from tracker_metrics import compute_bucket_winrate
        wins, total = compute_bucket_winrate(df, horizon=5)
        self.assertEqual((wins, total), (0, 0))

    def test_missing_column_returns_zero_zero(self):
        df = pd.DataFrame([{"代码": "a"}])
        from tracker_metrics import compute_bucket_winrate
        wins, total = compute_bucket_winrate(df, horizon=5)
        self.assertEqual((wins, total), (0, 0))
```

- [ ] **Step 2: 跑测试确认失败**

```bash
.venv/bin/python -m pytest tests/test_tracker_metrics.py::TestBucketWinrate -v
```

预期：FAIL（`ImportError` 或 `AttributeError`）

- [ ] **Step 3: 写最小实现**

在 `scripts/tracker_metrics.py` 末尾追加：

```python
def compute_bucket_winrate(df: pd.DataFrame, horizon: int) -> tuple[int, int]:
    """
    df 中需有 'T+{horizon}' 列；None/NaN 视为待计算从分母剔除。
    返回 (胜数, 已计算样本总数)
    """
    col = f"T+{horizon}"
    if col not in df.columns:
        return 0, 0
    valid = df[col].dropna()
    if valid.empty:
        return 0, 0
    wins = int((valid > 0).sum())
    return wins, int(len(valid))
```

- [ ] **Step 4: 跑测试确认通过**

```bash
.venv/bin/python -m pytest tests/test_tracker_metrics.py -v
```

预期：6 个测试全部 PASS

- [ ] **Step 5: 提交**

```bash
git add scripts/tracker_metrics.py tests/test_tracker_metrics.py
git commit -m "feat(tracker): compute_bucket_winrate 桶级胜率"
```

---

## Task 3: 列出可用信号日期（list_signal_dates）

**Files:**
- Modify: `tests/test_tracker_metrics.py`
- Modify: `scripts/tracker_metrics.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_tracker_metrics.py` 末尾追加（`if __name__` 之前）：

```python
class TestListSignalDates(unittest.TestCase):

    def test_dates_intersect_three_strategies(self, ):
        # 用 tmp_path 模式：手动建空 CSV 模拟 data 目录
        import tempfile
        from pathlib import Path as P
        with tempfile.TemporaryDirectory() as td:
            d = P(td)
            (d / "breakout_20260518.csv").write_text("代码,名称\n")
            (d / "breakout_20260519.csv").write_text("代码,名称\n")
            (d / "dragon_leader_20260519.csv").write_text("代码,名称\n")
            (d / "dragon_leader_20260520.csv").write_text("代码,名称\n")
            (d / "sideways_breakout_20260519.csv").write_text("代码,名称\n")
            (d / "sideways_breakout_20260520.csv").write_text("代码,名称\n")

            from tracker_metrics import list_signal_dates
            dates = list_signal_dates(d)
            # 三策略都有的只有 20260519
            self.assertEqual(dates, ["2026-05-19"])

    def test_no_files_returns_empty(self):
        import tempfile
        from pathlib import Path as P
        with tempfile.TemporaryDirectory() as td:
            from tracker_metrics import list_signal_dates
            self.assertEqual(list_signal_dates(P(td)), [])
```

- [ ] **Step 2: 跑测试确认失败**

```bash
.venv/bin/python -m pytest tests/test_tracker_metrics.py::TestListSignalDates -v
```

预期：FAIL

- [ ] **Step 3: 写最小实现**

在 `scripts/tracker_metrics.py` 顶部加 import，末尾加函数：

```python
import re
from pathlib import Path

STRATEGY_PREFIXES = ("breakout", "dragon_leader", "sideways_breakout")


def list_signal_dates(data_dir: Path) -> list[str]:
    """
    扫描 data_dir 下的 {prefix}_{YYYYMMDD}.csv，返回三策略都存在的日期，
    格式 'YYYY-MM-DD'，按降序排列（最新在前）。
    """
    pattern = re.compile(r"^(breakout|dragon_leader|sideways_breakout)_(\d{8})\.csv$")
    by_strategy: dict[str, set[str]] = {p: set() for p in STRATEGY_PREFIXES}

    for f in Path(data_dir).glob("*.csv"):
        m = pattern.match(f.name)
        if not m:
            continue
        prefix, tag = m.group(1), m.group(2)
        iso = f"{tag[:4]}-{tag[4:6]}-{tag[6:8]}"
        by_strategy[prefix].add(iso)

    common = set.intersection(*by_strategy.values()) if all(by_strategy.values()) else set()
    return sorted(common, reverse=True)
```

- [ ] **Step 4: 跑测试确认通过**

```bash
.venv/bin/python -m pytest tests/test_tracker_metrics.py -v
```

预期：8 个测试全部 PASS

- [ ] **Step 5: 提交**

```bash
git add scripts/tracker_metrics.py tests/test_tracker_metrics.py
git commit -m "feat(tracker): list_signal_dates 列出三策略共有日期"
```

---

## Task 4: 加载并补全 T+N 列（load_signal_csv_with_returns）

**Files:**
- Modify: `tests/test_tracker_metrics.py`
- Modify: `scripts/tracker_metrics.py`

这一步把 CSV 读取 + cache_manager.load + compute_returns 串起来，输出表格直接显示用的 DataFrame。

- [ ] **Step 1: 写失败测试**

在 `tests/test_tracker_metrics.py` 末尾追加：

```python
class TestLoadSignalCsvWithReturns(unittest.TestCase):

    def test_returns_appended(self):
        # 用 monkey patch 替换 cache load
        import tempfile
        from pathlib import Path as P
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            d = P(td)
            csv = d / "breakout_20260519.csv"
            csv.write_text("代码,名称\nsh.600519,贵州茅台\n")

            fake_bars = pd.DataFrame({
                "date": pd.date_range("2026-05-19", periods=6, freq="B"),
                "close": [100, 101, 102, 103, 104, 105],
            })

            with patch("tracker_metrics._load_cache_bars", return_value=fake_bars):
                from tracker_metrics import load_signal_csv_with_returns
                df = load_signal_csv_with_returns(csv)

            self.assertEqual(len(df), 1)
            self.assertAlmostEqual(df["T+1"].iloc[0], 1.0, places=2)
            self.assertAlmostEqual(df["T+3"].iloc[0], 3.0, places=2)
            self.assertAlmostEqual(df["T+5"].iloc[0], 5.0, places=2)

    def test_empty_csv_returns_empty(self):
        import tempfile
        from pathlib import Path as P
        with tempfile.TemporaryDirectory() as td:
            csv = P(td) / "breakout_20260519.csv"
            csv.write_text("代码,名称\n")
            from tracker_metrics import load_signal_csv_with_returns
            df = load_signal_csv_with_returns(csv)
            self.assertTrue(df.empty)
```

- [ ] **Step 2: 跑测试确认失败**

```bash
.venv/bin/python -m pytest tests/test_tracker_metrics.py::TestLoadSignalCsvWithReturns -v
```

预期：FAIL（`AttributeError`）

- [ ] **Step 3: 写最小实现**

在 `scripts/tracker_metrics.py` 末尾追加：

```python
def _load_cache_bars(code: str) -> pd.DataFrame:
    """从 parquet 缓存读取该股全历史 K（懒导入避免循环）。"""
    from cache_manager import load
    # load(code, days=N) 取尾部 N 条；这里要后向，先取较多再切
    return load(code, days=600)


_CSV_DATE_RE = re.compile(r"_(\d{8})\.csv$")


def load_signal_csv_with_returns(
    csv_path: Path,
    horizons: Iterable[int] = (1, 3, 5),
) -> pd.DataFrame:
    """读 CSV，对每只股票补全 T+N 涨幅列，返回新 DataFrame。"""
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path)
    if df.empty or "代码" not in df.columns:
        return df

    m = _CSV_DATE_RE.search(csv_path.name)
    if not m:
        return df
    tag = m.group(1)
    signal_date = pd.Timestamp(f"{tag[:4]}-{tag[4:6]}-{tag[6:8]}")

    horizons = list(horizons)
    cols = {h: [] for h in horizons}
    for code in df["代码"].astype(str):
        bars = _load_cache_bars(code)
        rets = compute_returns(bars, signal_date, horizons=horizons)
        for h in horizons:
            cols[h].append(rets[h])
    for h in horizons:
        df[f"T+{h}"] = cols[h]
    return df
```

- [ ] **Step 4: 跑测试确认通过**

```bash
.venv/bin/python -m pytest tests/test_tracker_metrics.py -v
```

预期：10 个测试全部 PASS

- [ ] **Step 5: 提交**

```bash
git add scripts/tracker_metrics.py tests/test_tracker_metrics.py
git commit -m "feat(tracker): load_signal_csv_with_returns 串联 CSV+缓存+T+N 涨幅"
```

---

## Task 5: 加 streamlit / plotly 依赖

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: 修改 requirements.txt**

在文件末尾追加两行：

```
streamlit
plotly
```

最终内容：

```
akshare
baostock
pandas
numpy
requests
fastapi
uvicorn
sqlalchemy
jupyter
matplotlib
ta
pyarrow
streamlit
plotly
```

- [ ] **Step 2: 安装到本地 venv**

```bash
cd /Users/xifeiyou/Documents/workspace/stock-picker
.venv/bin/pip install streamlit plotly
```

预期：成功，无错误。

- [ ] **Step 3: 验证**

```bash
.venv/bin/python -c "import streamlit, plotly; print(streamlit.__version__, plotly.__version__)"
```

预期：打印两个版本号

- [ ] **Step 4: 提交**

```bash
git add requirements.txt
git commit -m "chore: add streamlit + plotly for tracker web app"
```

---

## Task 6: Streamlit 应用 — 控件 + 三表格

**Files:**
- Create: `app.py`

这一步先做骨架：日期选择 + 胜率口径 + 三表格 + 桶胜率，**不含 K 线展开**。

- [ ] **Step 1: 创建 app.py**

新建 `/Users/xifeiyou/Documents/workspace/stock-picker/app.py`：

```python
"""选股回顾 Web Tracker — Streamlit 单页 app。

启动: streamlit run app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

from tracker_metrics import (  # noqa: E402
    compute_bucket_winrate,
    list_signal_dates,
    load_signal_csv_with_returns,
)

DATA_DIR = ROOT / "data"

STRATEGIES = [
    ("低位横盘突破", "breakout"),
    ("市场龙头", "dragon_leader"),
    ("横盘向上突破", "sideways_breakout"),
]

DISPLAY_COLS = ["代码", "名称", "T+1", "T+3", "T+5"]


def _date_to_tag(iso: str) -> str:
    return iso.replace("-", "")


@st.cache_data(show_spinner=False)
def _load_table(prefix: str, iso_date: str) -> pd.DataFrame:
    csv = DATA_DIR / f"{prefix}_{_date_to_tag(iso_date)}.csv"
    if not csv.exists():
        return pd.DataFrame()
    return load_signal_csv_with_returns(csv)


def _format_pct(v):
    if pd.isna(v):
        return "—"
    return f"{v:+.2f}%"


def main() -> None:
    st.set_page_config(page_title="选股回顾", layout="wide")
    st.title("选股回顾")

    dates = list_signal_dates(DATA_DIR)
    if not dates:
        st.warning("没有找到三策略都有的扫描日期。请先跑 scripts/run_all.py 等扫描脚本。")
        return

    col_l, col_r = st.columns([3, 1])
    with col_l:
        iso_date = st.selectbox("日期", dates, index=0)
    with col_r:
        horizon = st.selectbox("胜率口径", [1, 3, 5], index=2, format_func=lambda h: f"T+{h}")

    cols = st.columns(3)
    for (label, prefix), col in zip(STRATEGIES, cols):
        with col:
            df = _load_table(prefix, iso_date)
            wins, total = compute_bucket_winrate(df, horizon=horizon)
            rate = f"{wins}/{total} = {wins/total*100:.1f}%" if total else "—"
            pending = len(df) - total if not df.empty else 0
            suffix = f"  ({pending} 待数据)" if pending else ""
            st.subheader(f"{label}")
            st.caption(f"T+{horizon} 胜率: {rate}{suffix}")

            if df.empty:
                st.info("当日无信号")
                continue

            show = df[[c for c in DISPLAY_COLS if c in df.columns]].copy()
            for c in ("T+1", "T+3", "T+5"):
                if c in show.columns:
                    show[c] = show[c].map(_format_pct)
            st.dataframe(show, use_container_width=True, hide_index=True)

    st.caption(
        "T+N 数据来自 baostock 收盘后日 K，"
        "今天的 T+N 胜率最早要在第 N 个交易日收盘后才能完整。"
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 启动验证**

```bash
cd /Users/xifeiyou/Documents/workspace/stock-picker
.venv/bin/streamlit run app.py
```

打开浏览器到提示的地址（一般是 `http://localhost:8501`）。

预期：
- 页面显示"选股回顾"标题
- 顶部有日期下拉（默认 2026-05-19 或最新）和胜率口径下拉
- 三列分别显示三个策略的表格 + 桶胜率
- 数字单元格显示如 `+10.20%` 或 `—`

- [ ] **Step 3: 关掉 streamlit（Ctrl+C）后提交**

```bash
git add app.py
git commit -m "feat(tracker): Streamlit 单页骨架 + 三表格 + 桶胜率"
```

---

## Task 7: 行点击 → K 线展开

**Files:**
- Modify: `app.py`

- [ ] **Step 1: 加 K 线渲染函数**

在 `app.py` 顶部 import 区追加：

```python
import plotly.graph_objects as go
```

在 `_format_pct` 函数下方追加：

```python
def _render_kline(code: str, signal_date: str, days_before: int = 20, days_after: int = 20) -> None:
    """渲染 plotly candlestick，标注信号日竖线。"""
    from cache_manager import load
    bars = load(code, days=600)
    if bars.empty:
        st.info(f"{code} 无缓存数据")
        return

    sig_ts = pd.Timestamp(signal_date)
    df = bars.sort_values("date").reset_index(drop=True)
    sig_idx = df.index[df["date"] == sig_ts]
    if len(sig_idx) == 0:
        st.info(f"{code} 信号日 {signal_date} 不在数据范围内")
        return

    s = max(0, int(sig_idx[0]) - days_before)
    e = min(len(df), int(sig_idx[0]) + days_after + 1)
    seg = df.iloc[s:e]

    fig = go.Figure(data=[go.Candlestick(
        x=seg["date"],
        open=seg["open"],
        high=seg["high"],
        low=seg["low"],
        close=seg["close"],
        increasing_line_color="red",
        decreasing_line_color="green",
        name=code,
    )])
    fig.add_vline(x=sig_ts, line_color="blue", line_dash="dash",
                  annotation_text="信号日", annotation_position="top")
    fig.update_layout(
        height=400, margin=dict(l=10, r=10, t=30, b=10),
        xaxis_rangeslider_visible=False,
        title=f"{code}  信号日 {signal_date}",
    )
    st.plotly_chart(fig, use_container_width=True)
```

- [ ] **Step 2: 改三表格让行可点击**

把 `main()` 里 for 循环里那段 `st.dataframe(show, ...)` 替换为：

```python
            show = df[[c for c in DISPLAY_COLS if c in df.columns]].copy()
            for c in ("T+1", "T+3", "T+5"):
                if c in show.columns:
                    show[c] = show[c].map(_format_pct)

            event = st.dataframe(
                show,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key=f"table_{prefix}",
            )
            sel_rows = event.selection.rows if event and event.selection else []
            if sel_rows:
                code = str(df["代码"].iloc[sel_rows[0]])
                st.session_state["selected"] = (code, iso_date)
```

并在三个表格 for 循环 **之后**（仍在 `main()` 内）追加：

```python
    sel = st.session_state.get("selected")
    if sel:
        code, sig = sel
        st.divider()
        _render_kline(code, sig)
```

- [ ] **Step 3: 启动验证**

```bash
.venv/bin/streamlit run app.py
```

预期：
- 表格行可点击（左侧出现选中态）
- 点中某行 → 页面下方画出该股 K 线，含蓝色虚线标注信号日
- 切换日期或重选行，K 线刷新
- Ctrl+C 退出 streamlit

- [ ] **Step 4: 提交**

```bash
git add app.py
git commit -m "feat(tracker): 行点击展开 plotly candlestick K 线"
```

---

## Task 8: 文档更新（README 启动指引）

**Files:**
- Modify: `cmd.md`（用户的本地命令笔记，已 gitignored）

cmd.md 是用户私有命令笔记，记下启动方法即可。

- [ ] **Step 1: 在 cmd.md 末尾追加**

```bash
# 启动选股回顾 Web Tracker
cd ~/Documents/workspace/stock-picker && .venv/bin/streamlit run app.py
```

- [ ] **Step 2: 不需要提交**（文件 gitignored）

---

## 自审

**Spec 覆盖检查**：
- ✅ Streamlit 单页 app — Task 6
- ✅ 单页三表格 — Task 6
- ✅ T+1/T+3/T+5 涨跌幅 — Task 1, 4
- ✅ 桶级胜率 — Task 2
- ✅ 日期选择 + 胜率口径切换 — Task 6
- ✅ K 线点击展开 — Task 7
- ✅ 数据时效说明 caption — Task 6
- ✅ 不引入数据库 — 全程文件读取
- ✅ 单测覆盖 tracker_metrics — Task 1-4

**类型一致性**：
- `compute_returns` 返回 `dict[int, float | None]` ✓
- `compute_bucket_winrate` 返回 `tuple[int, int]` ✓
- `list_signal_dates` 返回 `list[str]`（ISO 格式）✓
- `load_signal_csv_with_returns` 返回带 `T+1/T+3/T+5` 列的 DataFrame ✓
- `app.py` 中 `iso_date` 始终是 `YYYY-MM-DD` 字符串 ✓

**占位符扫描**：无 TBD/TODO/省略号。

**作用域检查**：单一交付物 `app.py` + 一个工具模块 + 单测，可一次性实现。
