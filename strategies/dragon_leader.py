"""
市场龙头选股策略（高确定性版）

思路：
1. 趋势：收盘价 > MA20 > MA60
2. 强势位置：position >= 0.85（接近 250 日高点）
3. 动量 + 相对强度：跑赢沪深 300，但不允许过度透支
4. 量能：5 日均量 / 20 日均量 >= 1.2
5. 当日不能是涨停 / 一字板（无法买入）
6. 板块龙头：同一行业内综合得分最高（龙一）
7. 市场龙头：全池得分 Top N
"""

from __future__ import annotations

import sys
from typing import Any

import pandas as pd

from common import get_index_data, get_stock_data, load_industry_map, merge_params

# ── 默认参数（YAML 缺失时的回退值）─────────────
DEFAULT_PARAMS: dict = {
    # 硬过滤
    "min_position": 0.85,
    "min_ret_20d": 8.0,
    "max_ret_20d": 70.0,
    "max_ret_5d": 25.0,
    "min_rs_20d": 3.0,
    "min_vol_ratio": 1.2,
    "min_pct_chg": 1.0,
    "max_pct_chg": 9.5,
    "min_amount": 2e8,
    # 软约束
    "max_drawdown_20d": -20.0,   # 近20日最大回撤不超过-20%
    # 输出 / 评分
    "top_market": 20,
    "top_per_industry": 1,
    "min_leader_score": 65.0,
}


def _period_return(close: pd.Series, n: int) -> float | None:
    if len(close) <= n:
        return None
    base = close.iloc[-n - 1]
    if base <= 0:
        return None
    return round((close.iloc[-1] / base - 1) * 100, 2)


def evaluate_leader(
    df: pd.DataFrame,
    bench_ret_20d: float,
    bench_ret_5d: float,
    params: dict | None = None,
) -> dict[str, Any]:
    """计算单只股票龙头指标与得分"""
    p = merge_params(params, DEFAULT_PARAMS)

    if len(df) < 60:
        return {"signal": False, "reason": "数据不足"}

    close = df["close"]
    vol = df["volume"]
    today = df.iloc[-1]

    # 涨停 / 一字板：无法买入
    if today["pctChg"] >= p["max_pct_chg"]:
        return {"signal": False, "reason": "涨停或追高"}
    if today["high"] == today["low"]:
        return {"signal": False, "reason": "一字板"}

    # 流动性
    today_amount = float(today["amount"]) if pd.notna(today.get("amount")) else 0.0
    if today_amount < p["min_amount"]:
        return {"signal": False, "reason": "成交额不足"}

    ma20 = close.rolling(20).mean().iloc[-1]
    ma60 = close.rolling(60).mean().iloc[-1]
    price = close.iloc[-1]

    high_250 = close.iloc[-min(250, len(close)):].max()
    position = price / high_250 if high_250 > 0 else 0

    ret_5d = _period_return(close, 5)
    ret_20d = _period_return(close, 20)
    if ret_5d is None or ret_20d is None:
        return {"signal": False, "reason": "收益计算失败"}

    rs_20d = round(ret_20d - bench_ret_20d, 2)
    rs_5d = round(ret_5d - bench_ret_5d, 2)

    vol_ma5 = vol.iloc[-5:].mean()
    vol_ma20 = vol.iloc[-20:].mean()
    vol_ratio = round(vol_ma5 / vol_ma20, 2) if vol_ma20 > 0 else 0

    trend_ok = price > ma20 > ma60
    strong_pos = position >= p["min_position"]
    momentum_ok = p["min_ret_20d"] <= ret_20d <= p["max_ret_20d"] and 0 < ret_5d <= p["max_ret_5d"]
    rs_ok = rs_20d >= p["min_rs_20d"]
    vol_ok = vol_ratio >= p["min_vol_ratio"]
    today_strong = today["pctChg"] >= p["min_pct_chg"]

    # 软约束：近20日最大回撤
    close_20d = close.iloc[-20:]
    rolling_peak = close_20d.cummax()
    drawdown_20d = ((close_20d / rolling_peak - 1) * 100).min()
    drawdown_ok = drawdown_20d >= p["max_drawdown_20d"]

    hard_ok = all([trend_ok, strong_pos, momentum_ok, rs_ok, vol_ok, today_strong])

    # ── 综合分 0-100 ─────────────────────────────
    score = 0.0
    score += min(max(ret_20d - p["min_ret_20d"], 0) / (50 - p["min_ret_20d"]) * 35, 35)
    score += min(max(rs_20d - p["min_rs_20d"], 0) / (20 - p["min_rs_20d"]) * 25, 25)
    score += min(max(position - p["min_position"], 0) / (1.0 - p["min_position"]) * 15, 15)
    score += min(max(vol_ratio - p["min_vol_ratio"], 0) / (3.0 - p["min_vol_ratio"]) * 15, 15)
    score += 10 if trend_ok else 0
    if ret_20d > 60:
        score -= min((ret_20d - 60) * 0.5, 10)
    leader_score = round(max(min(score, 100), 0), 1)

    return {
        "signal": hard_ok and leader_score >= p["min_leader_score"],
        "leader_score": leader_score,
        "position": round(position, 3),
        "ret_5d": ret_5d,
        "ret_20d": ret_20d,
        "rs_5d": rs_5d,
        "rs_20d": rs_20d,
        "vol_ratio": vol_ratio,
        "pct_chg": round(float(today["pctChg"]), 2),
        "amount_yi": round(today_amount / 1e8, 2),
        "turn": round(float(today["turn"]), 2) if pd.notna(today.get("turn")) else None,
        "trend_ok": trend_ok,
        "strong_pos": strong_pos,
        "momentum_ok": momentum_ok,
        "rs_ok": rs_ok,
        "vol_ok": vol_ok,
        "drawdown_ok": drawdown_ok,
    }

def _benchmark_returns() -> tuple[float, float]:
    idx = get_index_data(days=120)
    if len(idx) < 25:
        print("[dragon] ⚠️ 基准数据不足，使用 0.0 作为回退", file=sys.stderr)
        return 0.0, 0.0
    r5 = _period_return(idx["close"], 5) or 0.0
    r20 = _period_return(idx["close"], 20) or 0.0
    return r5, r20


def _assign_leader_types(rows: list[dict], params: dict | None = None) -> list[dict]:
    """标注板块龙一 + 市场龙头"""
    p = merge_params(params, DEFAULT_PARAMS)

    if not rows:
        return []

    rows = sorted(rows, key=lambda x: x["leader_score"], reverse=True)

    by_industry: dict[str, list[dict]] = {}
    for r in rows:
        ind = r.get("industry") or "未知"
        by_industry.setdefault(ind, []).append(r)

    sector_codes: set[str] = set()
    for group in by_industry.values():
        group.sort(key=lambda x: x["leader_score"], reverse=True)
        for r in group[:p["top_per_industry"]]:
            sector_codes.add(r["代码"])

    market_codes = {r["代码"] for r in rows[:p["top_market"]]}

    result = []
    for r in rows:
        tags = []
        if r["代码"] in sector_codes:
            tags.append("板块龙头")
        if r["代码"] in market_codes:
            tags.append("市场龙头")
        if not tags:
            continue
        result.append({**r, "leader_type": "+".join(tags)})

    return sorted(result, key=lambda x: x["leader_score"], reverse=True)


def scan_stocks(
    stock_list: list[tuple[str, str]],
    mktcap_map: dict[str, float] | None = None,
    params: dict | None = None,
) -> pd.DataFrame:
    """扫描股票池，返回龙头列表"""
    mktcap_map = mktcap_map or {}
    bench_5d, bench_20d = _benchmark_returns()
    print(f"基准沪深300: 5日 {bench_5d:+.2f}% | 20日 {bench_20d:+.2f}%")

    print("加载行业分类...")
    industry_map = load_industry_map()

    candidates: list[dict] = []
    total = len(stock_list)

    for i, (code, name) in enumerate(stock_list):
        print(f"\r扫描中 {i+1}/{total}: {code} {name}    ", end="", flush=True)
        try:
            df = get_stock_data(code, days=300)
            if df.empty:
                continue
            m = evaluate_leader(df, bench_20d, bench_5d, params=params)
            if not m.get("signal"):
                continue
            candidates.append({
                "代码": code,
                "名称": name,
                "行业": industry_map.get(code, "未知"),
                "leader_score": m["leader_score"],
                "position": m["position"],
                "ret_5d": m["ret_5d"],
                "ret_20d": m["ret_20d"],
                "rs_5d": m["rs_5d"],
                "rs_20d": m["rs_20d"],
                "vol_ratio": m["vol_ratio"],
                "pct_chg": m["pct_chg"],
                "amount_yi": m["amount_yi"],
                "turn": m.get("turn"),
                "mktcap": mktcap_map.get(code),
            })
        except Exception as e:
            print(f"\n⚠️ {code} {name}: {e}", file=sys.stderr)

    print("\n扫描完成，正在评定龙头...")
    for r in candidates:
        r["industry"] = r["行业"]
    tagged = _assign_leader_types(candidates, params=params)
    if not tagged:
        return pd.DataFrame()

    df = pd.DataFrame(tagged)
    cols = [
        "代码", "名称", "行业", "leader_type", "leader_score",
        "ret_20d", "rs_20d", "ret_5d", "rs_5d",
        "position", "vol_ratio", "pct_chg", "amount_yi", "turn", "mktcap",
    ]
    return df[[c for c in cols if c in df.columns]].sort_values(
        "leader_score", ascending=False
    )


if __name__ == "__main__":
    test = [
        ("sh.600519", "贵州茅台"),
        ("sz.300750", "宁德时代"),
        ("sh.601318", "中国平安"),
    ]
    out = scan_stocks(test)
    print(out.to_string(index=False) if not out.empty else "测试样本无龙头信号")
