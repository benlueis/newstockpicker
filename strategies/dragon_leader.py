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

from typing import Any

import pandas as pd

from common import get_index_data, get_stock_data, load_industry_map

# ── 硬过滤 ──────────────────────────────────
MIN_POSITION = 0.85          # 现价 / 250 日高点
MIN_RET_20D = 8.0            # 20 日涨幅 %
MAX_RET_20D = 70.0           # 过热保护：20 日涨幅上限
MAX_RET_5D = 25.0            # 过热保护：5 日涨幅上限
MIN_RS_20D = 3.0             # 相对沪深 300 超额 %
MIN_VOL_RATIO = 1.2          # 5 日均量 / 20 日均量
MIN_PCT_CHG = 1.0            # 龙头当日应是上涨的
MAX_PCT_CHG = 9.5            # 排除涨停
MIN_AMOUNT = 2e8             # 龙头流动性门槛：2 亿

# 输出 / 评分
TOP_MARKET = 20
TOP_PER_INDUSTRY = 1
MIN_LEADER_SCORE = 65.0


def _period_return(close: pd.Series, n: int) -> float | None:
    if len(close) <= n:
        return None
    base = close.iloc[-n - 1]
    if base <= 0:
        return None
    return round((close.iloc[-1] / base - 1) * 100, 2)


def evaluate_leader(df: pd.DataFrame, bench_ret_20d: float, bench_ret_5d: float) -> dict[str, Any]:
    """计算单只股票龙头指标与得分"""
    if len(df) < 60:
        return {"signal": False, "reason": "数据不足"}

    close = df["close"]
    vol = df["volume"]
    today = df.iloc[-1]

    # 涨停 / 一字板：无法买入
    if today["pctChg"] >= MAX_PCT_CHG:
        return {"signal": False, "reason": "涨停或追高"}
    if today["high"] == today["low"]:
        return {"signal": False, "reason": "一字板"}

    # 流动性
    today_amount = float(today["amount"]) if pd.notna(today.get("amount")) else 0.0
    if today_amount < MIN_AMOUNT:
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
    strong_pos = position >= MIN_POSITION
    momentum_ok = MIN_RET_20D <= ret_20d <= MAX_RET_20D and 0 < ret_5d <= MAX_RET_5D
    rs_ok = rs_20d >= MIN_RS_20D
    vol_ok = vol_ratio >= MIN_VOL_RATIO
    today_strong = today["pctChg"] >= MIN_PCT_CHG

    hard_ok = all([trend_ok, strong_pos, momentum_ok, rs_ok, vol_ok, today_strong])

    # ── 综合分 0-100 ─────────────────────────────
    score = 0.0
    # 动量（35）：8~50% 之间线性给分，过 50% 不再加分
    score += min(max(ret_20d - MIN_RET_20D, 0) / (50 - MIN_RET_20D) * 35, 35)
    # 相对强度（25）：3~20% 超额线性
    score += min(max(rs_20d - MIN_RS_20D, 0) / (20 - MIN_RS_20D) * 25, 25)
    # 位置（15）：0.85~1.0 线性
    score += min(max(position - MIN_POSITION, 0) / (1.0 - MIN_POSITION) * 15, 15)
    # 量能（15）：1.2~3.0 线性
    score += min(max(vol_ratio - MIN_VOL_RATIO, 0) / (3.0 - MIN_VOL_RATIO) * 15, 15)
    # 趋势（10）
    score += 10 if trend_ok else 0
    # 过热惩罚：ret_20d 超过 60% 之后每超 1% 扣 0.5 分（封顶扣 10 分）
    if ret_20d > 60:
        score -= min((ret_20d - 60) * 0.5, 10)
    leader_score = round(max(min(score, 100), 0), 1)

    return {
        "signal": hard_ok and leader_score >= MIN_LEADER_SCORE,
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
    }


def _benchmark_returns() -> tuple[float, float]:
    idx = get_index_data(days=120)
    if len(idx) < 25:
        return 0.0, 0.0
    r5 = _period_return(idx["close"], 5) or 0.0
    r20 = _period_return(idx["close"], 20) or 0.0
    return r5, r20


def _assign_leader_types(rows: list[dict]) -> list[dict]:
    """标注板块龙一 + 市场龙头"""
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
        for r in group[:TOP_PER_INDUSTRY]:
            sector_codes.add(r["代码"])

    market_codes = {r["代码"] for r in rows[:TOP_MARKET]}

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
            m = evaluate_leader(df, bench_20d, bench_5d)
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
        except Exception:
            continue

    print("\n扫描完成，正在评定龙头...")
    # 改名 industry → 中文列对齐
    for r in candidates:
        r["industry"] = r["行业"]
    tagged = _assign_leader_types(candidates)
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
    import baostock as bs

    bs.login()
    try:
        test = [
            ("sh.600519", "贵州茅台"),
            ("sz.300750", "宁德时代"),
            ("sh.601318", "中国平安"),
        ]
        out = scan_stocks(test)
        print(out.to_string(index=False) if not out.empty else "测试样本无龙头信号")
    finally:
        bs.logout()
