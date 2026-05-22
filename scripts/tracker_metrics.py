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
