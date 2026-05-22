"""选股回顾页面用的纯函数：可用日期、读 CSV、T+N 涨幅、桶胜率。"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pandas as pd

STRATEGY_PREFIXES = ("breakout", "dragon_leader", "sideways_breakout")


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

