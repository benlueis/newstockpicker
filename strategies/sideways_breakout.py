"""
横盘向上突破选股策略（高确定性版）
逻辑：120 日通道下半段 + 趋势良好 + 近期横盘 + 放量突破箱体上沿
"""

from __future__ import annotations

import sys
import pandas as pd

from common import get_stock_data, merge_params


BUY_REASON = "横盘向上突破，放量确认"
WAIT_ACTION = "WAIT"
BUY_ACTION = "BUY"

# ── 默认参数（YAML 缺失时的回退值）─────────────
DEFAULT_PARAMS: dict = {
    "lookback_days": 120,
    "box_days": 30,
    "max_box_range": 1.12,
    "min_breakout_pct": 2.0,
    "min_vol_ratio": 1.8,
    "max_position_120d": 0.75,
    "max_pct_chg": 9.5,
    "min_amount": 1e8,
    "max_upper_shadow_ratio": 0.5,
    "min_rows": None,  # 运行时计算: max(lookback_days, box_days + 1, 60)
}


def check_sideways_breakout(df: pd.DataFrame, params: dict | None = None) -> dict:
    """判断是否满足横盘向上突破买入条件"""
    p = merge_params(params, DEFAULT_PARAMS)

    min_rows = p["min_rows"] or max(p["lookback_days"], p["box_days"] + 1, 60)

    if len(df) < min_rows:
        return {"signal": False, "action": WAIT_ACTION, "reason": "数据不足"}

    close = df["close"]
    vol = df["volume"]
    today = df.iloc[-1]

    # 一字板 / 涨停
    if today["pctChg"] >= p["max_pct_chg"]:
        return {"signal": False, "action": WAIT_ACTION, "reason": "涨停或追高"}
    if today["high"] == today["low"]:
        return {"signal": False, "action": WAIT_ACTION, "reason": "一字板"}

    # 流动性
    today_amount = float(today["amount"]) if pd.notna(today.get("amount")) else 0.0
    if today_amount < p["min_amount"]:
        return {"signal": False, "action": WAIT_ACTION, "reason": "成交额不足"}

    window_120 = close.iloc[-p["lookback_days"]:]
    low_120 = window_120.min()
    high_120 = window_120.max()
    range_120 = high_120 - low_120
    if range_120 <= 0:
        return {"signal": False, "action": WAIT_ACTION, "reason": "通道无波动"}
    position_120d = (today["close"] - low_120) / range_120

    ma20 = close.rolling(20).mean().iloc[-1]
    ma60 = close.rolling(60).mean().iloc[-1]
    trend_ok = (today["close"] > ma20) and ((ma20 >= ma60 * 0.98) or (today["close"] > ma60))

    box_close = close.iloc[-p["box_days"] - 1:-1]
    box_high = box_close.max()
    box_low = box_close.min()
    box_range = box_high / box_low if box_low > 0 else float("inf")
    is_sideways = box_range <= p["max_box_range"]
    base_position_120d = (box_high - low_120) / range_120
    position_ok = base_position_120d <= p["max_position_120d"]

    vol_ma = vol.iloc[-p["box_days"] - 1:-1].mean()
    vol_ratio = today["volume"] / vol_ma if vol_ma > 0 else 0

    breakout_pct = (today["close"] / box_high - 1) * 100 if box_high > 0 else 0
    price_break = breakout_pct >= p["min_breakout_pct"]
    vol_surge = vol_ratio >= p["min_vol_ratio"]
    up_candle = today["close"] > today["open"]

    bar_range = today["high"] - today["low"]
    upper_shadow_ratio = (
        (today["high"] - today["close"]) / bar_range if bar_range > 0 else 0
    )
    no_long_upper = upper_shadow_ratio <= p["max_upper_shadow_ratio"]

    signal = (
        position_ok
        and trend_ok
        and is_sideways
        and price_break
        and vol_surge
        and up_candle
        and no_long_upper
    )

    return {
        "signal": signal,
        "action": BUY_ACTION if signal else WAIT_ACTION,
        "reason": BUY_REASON if signal else "未满足横盘向上突破条件",
        "position_120d": round(position_120d, 3),
        "base_position_120d": round(base_position_120d, 3),
        "box_range": round(box_range, 3),
        "breakout_pct": round(breakout_pct, 2),
        "vol_ratio": round(vol_ratio, 2),
        "pct_chg": round(float(today["pctChg"]), 2),
        "amount_yi": round(today_amount / 1e8, 2),
        "upper_shadow": round(upper_shadow_ratio, 2),
        "price_break": price_break,
        "vol_surge": vol_surge,
        "trend_ok": trend_ok,
        "position_ok": position_ok,
        "is_sideways": is_sideways,
        "up_candle": up_candle,
    }


def scan_stocks(stock_list: list, params: dict | None = None) -> pd.DataFrame:
    """扫描股票列表，返回触发横盘向上突破买入提示的股票"""
    results = []
    total = len(stock_list)

    for i, (code, name) in enumerate(stock_list):
        print(f"\r扫描中 {i+1}/{total}: {code} {name}    ", end="", flush=True)
        try:
            df = get_stock_data(code, days=300)
            if df.empty:
                continue
            result = check_sideways_breakout(df, params=params)
            if result["signal"]:
                results.append({"代码": code, "名称": name, **result})
        except Exception as e:
            print(f"\n⚠️ {code} {name}: {e}", file=sys.stderr)

    print("\n扫描完成！")
    return pd.DataFrame(results)
