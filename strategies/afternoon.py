"""
14:45 尾盘精选策略（收盘前买入专用）

双策略 + 交叉验证 + 综合评分：
  1. 低位横盘突破（收紧参数）
  2. 回踩 5 日线企稳（收紧参数）
  一只股票同时触发两个策略时额外加分，置信度最高。

要求数据源为实时源（tencent / pytdx），否则无法拿到当日盘中数据。
"""

from __future__ import annotations

import pandas as pd

from common import get_stock_data

# ============================================================
#  低位横盘突破 — 收紧参数
# ============================================================
BT_MAX_POSITION = 0.60          # 现价 / 250 日高点 <= 60%
BT_MAX_BOX_RANGE = 0.08         # 箱体振幅 <= 8%（原 10%）
BT_MIN_BREAKOUT_PCT = 4.0       # 突破当日涨幅 >= 4%（原 3%）
BT_MIN_VOL_RATIO = 2.0          # 量比 >= 2.0（原 1.5）
BT_MAX_PCT_CHG = 9.5            # 排除涨停
BT_MIN_AMOUNT = 1e8             # 成交额 >= 1 亿
BT_MAX_UPPER_SHADOW = 0.30      # 上影 / 全振幅 <= 30%（原 50%）
BT_MIN_DATA_DAYS = 120
BT_BOX_DAYS = 20


def check_breakout_1450(df: pd.DataFrame) -> dict:
    """收紧版低位横盘突破判断"""
    if len(df) < BT_MIN_DATA_DAYS:
        return {"signal": False, "reason": "数据不足"}

    close = df["close"]
    vol = df["volume"]
    today = df.iloc[-1]

    if today["pctChg"] >= BT_MAX_PCT_CHG:
        return {"signal": False, "reason": "涨停"}
    if today["high"] == today["low"]:
        return {"signal": False, "reason": "一字板"}

    today_amount = float(today["amount"]) if pd.notna(today.get("amount")) else 0.0
    if today_amount < BT_MIN_AMOUNT:
        return {"signal": False, "reason": "成交额不足"}

    high_250 = close.iloc[-min(250, len(df)):].max()
    position = close.iloc[-1] / high_250 if high_250 > 0 else 1.0
    if position >= BT_MAX_POSITION:
        return {"signal": False, "reason": "不在低位", "position": round(position, 3)}

    box_close = close.iloc[-BT_BOX_DAYS - 1:-1]
    box_high = box_close.max()
    box_low = box_close.min()
    box_range = (box_high - box_low) / box_low if box_low > 0 else float("inf")
    if box_range > BT_MAX_BOX_RANGE:
        return {"signal": False, "reason": "箱体太宽", "box_range": round(box_range, 3)}

    vol_ma = vol.iloc[-BT_BOX_DAYS - 1:-1].mean()
    vol_5d_avg = vol.iloc[-5:-1].mean()
    if vol_5d_avg >= vol_ma * 0.85:
        return {"signal": False, "reason": "箱体期未缩量"}

    breakout_pct = (today["close"] / box_high - 1) * 100 if box_high > 0 else 0
    if not (today["close"] > box_high and breakout_pct >= BT_MIN_BREAKOUT_PCT):
        return {"signal": False, "reason": "突破幅度不足", "breakout_pct": round(breakout_pct, 2)}

    vol_ratio = today["volume"] / vol_ma if vol_ma > 0 else 0
    if vol_ratio < BT_MIN_VOL_RATIO:
        return {"signal": False, "reason": "放量不足", "vol_ratio": round(vol_ratio, 2)}

    if today["close"] <= today["open"]:
        return {"signal": False, "reason": "非阳线"}

    bar_range = today["high"] - today["low"]
    upper_shadow = (today["high"] - today["close"]) / bar_range if bar_range > 0 else 0
    if upper_shadow > BT_MAX_UPPER_SHADOW:
        return {"signal": False, "reason": "上影线过长", "upper_shadow": round(upper_shadow, 2)}

    # ── 单项得分 0-100 ────────────────────────
    score = 0.0
    score += min(max((breakout_pct - BT_MIN_BREAKOUT_PCT) / 6 * 40, 0), 40)
    score += min(max((vol_ratio - BT_MIN_VOL_RATIO) / 2 * 25, 0), 25)
    score += max((BT_MAX_POSITION - position) / 0.3 * 15, 0)
    score += max(10 - upper_shadow / BT_MAX_UPPER_SHADOW * 10, 0)
    score += max((BT_MAX_BOX_RANGE - box_range) / BT_MAX_BOX_RANGE * 10, 0)

    return {
        "signal": True,
        "reason": "14:45低位突破",
        "score_bt": round(min(score, 100), 1),
        "position": round(position, 3),
        "box_range": round(box_range, 3),
        "breakout_pct": round(breakout_pct, 2),
        "vol_ratio": round(vol_ratio, 2),
        "pct_chg": round(float(today["pctChg"]), 2),
        "amount_yi": round(today_amount / 1e8, 2),
        "upper_shadow": round(upper_shadow, 2),
    }


# ============================================================
#  回踩 5 日线企稳 — 收紧参数
# ============================================================
PT_MIN_DATA_DAYS = 60
PT_MIN_AMOUNT = 8e7
PT_MAX_PCT_CHG = 9.5
PT_MIN_PCT_CHG = -9.5
PT_TREND_CONFIRM_DAYS = 8
PT_MIN_DAYS_ABOVE_MA5 = 6           # 原 5
PT_MIN_RECENT_GAIN = 0.10           # 近 20 日涨幅 ≥ 10%
PT_MAX_CLOSE_ABOVE_MA5_PCT = 1.0    # 原 1.5
PT_MIN_CLOSE_BELOW_MA5_PCT = -1.0   # 原 -1.5
PT_MIN_LOW_TOUCH_MA5_RATIO = 0.998  # 原 0.995
PT_MAX_VOL_RATIO = 0.85             # 原 1.2（必须明显缩量）
PT_MIN_REBOUND_RATIO = 0.5          # 原 0.3（必须从低点明显反弹）
PT_MAX_RECENT_DROP = -5.0           # 原 -7.0


def check_pullback_1450(df: pd.DataFrame) -> dict:
    """收紧版回踩 5 日线判断"""
    if len(df) < PT_MIN_DATA_DAYS:
        return {"signal": False, "reason": "数据不足"}

    close = df["close"]
    vol = df["volume"]
    today = df.iloc[-1]

    if today["pctChg"] >= PT_MAX_PCT_CHG:
        return {"signal": False, "reason": "涨停"}
    if today["pctChg"] <= PT_MIN_PCT_CHG:
        return {"signal": False, "reason": "跌停"}
    if today["high"] == today["low"]:
        return {"signal": False, "reason": "一字板"}

    today_amount = float(today["amount"]) if pd.notna(today.get("amount")) else 0.0
    if today_amount < PT_MIN_AMOUNT:
        return {"signal": False, "reason": "成交额不足"}

    ma5 = close.rolling(5).mean()
    ma10 = close.rolling(10).mean()
    ma20 = close.rolling(20).mean()

    ma5_today = ma5.iloc[-1]
    ma10_today = ma10.iloc[-1]
    ma20_today = ma20.iloc[-1]

    if pd.isna(ma5_today) or pd.isna(ma10_today) or pd.isna(ma20_today):
        return {"signal": False, "reason": "均线数据不足"}

    today_close = float(close.iloc[-1])
    today_low = float(today["low"])
    today_high = float(today["high"])

    trend_golden = ma5_today > ma10_today > ma20_today
    above_ma20 = today_close > ma20_today
    ma5_slope_up = ma5.iloc[-1] > ma5.iloc[-2] if len(df) >= 6 else True

    recent_above = int(
        (close.iloc[-PT_TREND_CONFIRM_DAYS:-1] > ma5.iloc[-PT_TREND_CONFIRM_DAYS:-1]).sum()
    )
    was_above_ma5 = recent_above >= PT_MIN_DAYS_ABOVE_MA5
    recent_gain = (close.iloc[-1] / close.iloc[-20] - 1) >= PT_MIN_RECENT_GAIN

    if not (trend_golden and above_ma20 and ma5_slope_up and was_above_ma5 and recent_gain):
        return {"signal": False, "reason": "未确认上升趋势"}

    max_drop = df["pctChg"].iloc[-10:].min()
    if max_drop <= PT_MAX_RECENT_DROP:
        return {"signal": False, "reason": f"近10日有大阴线({round(max_drop,1)}%)"}

    close_ma5_pct = (today_close / ma5_today - 1) * 100
    low_touched_ma5 = today_low <= ma5_today
    low_not_too_deep = today_low >= ma5_today * PT_MIN_LOW_TOUCH_MA5_RATIO
    close_near_ma5 = PT_MIN_CLOSE_BELOW_MA5_PCT <= close_ma5_pct <= PT_MAX_CLOSE_ABOVE_MA5_PCT

    candle_range = today_high - today_low
    rebound_ratio = (today_close - today_low) / candle_range if candle_range > 0 else 0
    rebound_ok = rebound_ratio >= PT_MIN_REBOUND_RATIO

    if not (low_touched_ma5 and low_not_too_deep and close_near_ma5 and rebound_ok):
        return {"signal": False, "reason": "未满足回踩条件"}

    vol_ma5 = vol.iloc[-6:-1].mean()
    vol_ratio = float(today["volume"]) / vol_ma5 if vol_ma5 > 0 else 0
    if vol_ratio > PT_MAX_VOL_RATIO:
        return {"signal": False, "reason": "未缩量", "vol_ratio": round(vol_ratio, 2)}

    # ── 单项得分 0-100 ────────────────────────
    score = 0.0
    score += min(max((rebound_ratio - PT_MIN_REBOUND_RATIO) / 0.5 * 30, 0), 30)
    score += max((PT_MAX_VOL_RATIO - vol_ratio) / PT_MAX_VOL_RATIO * 25, 0)
    recent_gain_pct = (close.iloc[-1] / close.iloc[-20] - 1) * 100
    score += min(max(recent_gain_pct - PT_MIN_RECENT_GAIN * 100, 0) / 20 * 20, 20)
    score += min(max(recent_above - PT_MIN_DAYS_ABOVE_MA5, 0) / 2 * 15, 15)
    ma5_proximity = 1.0 - abs(close_ma5_pct) / max(
        abs(PT_MAX_CLOSE_ABOVE_MA5_PCT), abs(PT_MIN_CLOSE_BELOW_MA5_PCT)
    )
    score += max(ma5_proximity * 10, 0)

    return {
        "signal": True,
        "reason": "14:45回踩企稳",
        "score_pt": round(min(score, 100), 1),
        "close_ma5_pct": round(close_ma5_pct, 2),
        "rebound_ratio": round(rebound_ratio, 2),
        "vol_ratio": round(vol_ratio, 2),
        "ma5": round(ma5_today, 2),
        "pct_chg": round(float(today["pctChg"]), 2),
        "amount_yi": round(today_amount / 1e8, 2),
        "recent_gain_pct": round(recent_gain_pct, 2),
        "days_above_ma5": recent_above,
    }


# ============================================================
#  联合扫描 + 交叉打分
# ============================================================

def scan_stocks(
    stock_list: list[tuple[str, str]],
    top_n: int = 5,
) -> pd.DataFrame:
    """全市场扫描，返回交叉验证 Top N"""
    breakout_hits: list[dict] = []
    pullback_hits: list[dict] = []
    total = len(stock_list)

    for i, (code, name) in enumerate(stock_list):
        print(f"\r扫描中 {i+1}/{total}: {code} {name}    ", end="", flush=True)
        try:
            df = get_stock_data(code, days=400)
            if df.empty:
                continue

            bt = check_breakout_1450(df)
            if bt["signal"]:
                breakout_hits.append({"代码": code, "名称": name, **bt})

            pt = check_pullback_1450(df)
            if pt["signal"]:
                pullback_hits.append({"代码": code, "名称": name, **pt})
        except Exception:
            continue

    print("\n扫描完成！")

    bt_codes = {r["代码"] for r in breakout_hits}
    pt_codes = {r["代码"] for r in pullback_hits}
    cross_codes = bt_codes & pt_codes

    results: list[dict] = []

    for r in breakout_hits:
        is_cross = r["代码"] in cross_codes
        results.append({
            **r,
            "strategy": "低位突破",
            "cross_hit": is_cross,
            "composite_score": round(r.get("score_bt", 0) + (25 if is_cross else 0), 1),
            "score_pt": None,
        })

    for r in pullback_hits:
        is_cross = r["代码"] in cross_codes
        results.append({
            **r,
            "strategy": "回踩企稳",
            "cross_hit": is_cross,
            "composite_score": round(r.get("score_pt", 0) + (25 if is_cross else 0), 1),
            "score_bt": None,
        })

    results.sort(key=lambda x: x["composite_score"], reverse=True)
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in results:
        if r["代码"] not in seen:
            seen.add(r["代码"])
            deduped.append(r)

    top = deduped[:top_n]

    print(f"\n=== 14:45 尾盘精选 ===")
    print(f"低位突破: {len(breakout_hits)} | 回踩企稳: {len(pullback_hits)} | 双命中 🔥: {len(cross_codes)}")
    print(f"推送 Top {min(top_n, len(top))}")

    return pd.DataFrame(top)
