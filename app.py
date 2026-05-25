"""选股回顾 Web Tracker — Streamlit 单页 app。

启动: streamlit run app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

from tracker_metrics import (  # noqa: E402
    compute_bucket_winrate,
    list_signal_dates,
    load_signal_csv_with_returns,
)
from cache_manager import load as _load_cache_bars  # noqa: E402

DATA_DIR = ROOT / "data"

STRATEGIES = [
    ("低位横盘突破", "breakout"),
    ("市场龙头", "dragon_leader"),
    ("横盘向上突破", "sideways_breakout"),
    ("回踩5日线", "pullback_ma5"),
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


def _render_kline(code: str, signal_date: str, days_before: int = 20, days_after: int = 20) -> None:
    """渲染 plotly candlestick，标注信号日竖线。"""
    bars = _load_cache_bars(code, days=600)
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
    fig.add_vline(x=sig_ts.to_pydatetime(), line_color="blue", line_dash="dash")
    fig.add_annotation(x=sig_ts.to_pydatetime(), y=0.95, yref="paper",
                       text="信号日", showarrow=False, font=dict(color="blue"))
    fig.update_layout(
        height=400, margin=dict(l=10, r=10, t=30, b=10),
        xaxis_rangeslider_visible=False,
        title=f"{code}  信号日 {signal_date}",
    )
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    st.plotly_chart(fig, use_container_width=True)


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

    cols = st.columns(len(STRATEGIES))
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

    sel = st.session_state.get("selected")
    if sel and sel[1] == iso_date:
        code, sig = sel
        st.divider()
        _render_kline(code, sig)

    st.caption(
        "T+N 数据来自 baostock 收盘后日 K，"
        "今天的 T+N 胜率最早要在第 N 个交易日收盘后才能完整。"
    )


if __name__ == "__main__":
    main()
