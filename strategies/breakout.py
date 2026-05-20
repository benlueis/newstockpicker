"""
低位横盘突破选股策略（高确定性版）
逻辑：低位（相对 250 日高点）+ 横盘（箱体振幅小且缩量）+ 放量阳线突破箱顶
"""

from __future__ import annotations

import baostock as bs
import pandas as pd

from common import get_stock_data

# ── 硬约束（高确定性）──────────────────────────
MAX_POSITION = 0.60          # 现价 / 250 日高点：必须真正低位
MAX_BOX_RANGE = 0.10         # 箱体振幅 (high-low)/low，<=10%
MIN_BREAKOUT_PCT = 3.0       # 突破当日涨幅
MIN_VOL_RATIO = 1.5          # 当日量 / 箱体期均量
MAX_PCT_CHG = 9.5            # 涨停板排除
MIN_AMOUNT = 1e8             # 当日最小成交额（元）
MAX_UPPER_SHADOW_RATIO = 0.5 # 上影 / 全振幅
MIN_DATA_DAYS = 120


def check_breakout(df: pd.DataFrame, box_days: int = 20) -> dict:
    """判断是否满足低位横盘突破条件"""
    if len(df) < MIN_DATA_DAYS:
        return {"signal": False, "reason": "数据不足"}

    close = df["close"]
    vol = df["volume"]
    today = df.iloc[-1]

    # 一字板 / 涨停过滤
    if today["pctChg"] >= MAX_PCT_CHG:
        return {"signal": False, "reason": "涨停或追高"}
    if today["high"] == today["low"]:
        return {"signal": False, "reason": "一字板"}

    # 流动性
    today_amount = float(today["amount"]) if pd.notna(today.get("amount")) else 0.0
    if today_amount < MIN_AMOUNT:
        return {"signal": False, "reason": "成交额不足"}

    # ── 低位（核心约束）──────────────────────────
    high_250 = close.iloc[-min(250, len(df)):].max()
    position = close.iloc[-1] / high_250 if high_250 > 0 else 1.0
    low_pos = position < MAX_POSITION
    if not low_pos:
        return {"signal": False, "reason": "不在低位", "position": round(position, 3)}

    ma20 = close.rolling(20).mean().iloc[-1]
    below_ma20 = close.iloc[-1] < ma20 * 1.05

    # ── 横盘（振幅 + 缩量都要满足）────────────────
    box_close = close.iloc[-box_days - 1:-1]
    box_high = box_close.max()
    box_low = box_close.min()
    box_range = (box_high - box_low) / box_low if box_low > 0 else float("inf")
    is_flat = box_range <= MAX_BOX_RANGE

    vol_ma = vol.iloc[-box_days - 1:-1].mean()
    vol_shrink = vol.iloc[-5:-1].mean() < vol_ma * 0.85

    if not (is_flat and vol_shrink):
        return {
            "signal": False,
            "reason": "未形成横盘缩量",
            "box_range": round(box_range, 3),
        }

    # ── 突破当日 ────────────────────────────────
    breakout_pct = (today["close"] / box_high - 1) * 100 if box_high > 0 else 0
    price_break = today["close"] > box_high and breakout_pct >= MIN_BREAKOUT_PCT
    vol_ratio = today["volume"] / vol_ma if vol_ma > 0 else 0
    vol_surge = vol_ratio >= MIN_VOL_RATIO
    up_candle = today["close"] > today["open"]

    bar_range = today["high"] - today["low"]
    upper_shadow_ratio = (
        (today["high"] - today["close"]) / bar_range if bar_range > 0 else 0
    )
    no_long_upper = upper_shadow_ratio <= MAX_UPPER_SHADOW_RATIO

    signal = price_break and vol_surge and up_candle and no_long_upper

    return {
        "signal": signal,
        "reason": "低位横盘放量突破" if signal else "未满足突破条件",
        "position": round(position, 3),
        "box_range": round(box_range, 3),
        "breakout_pct": round(breakout_pct, 2),
        "vol_ratio": round(vol_ratio, 2),
        "pct_chg": round(float(today["pctChg"]), 2),
        "amount_yi": round(today_amount / 1e8, 2),
        "upper_shadow": round(upper_shadow_ratio, 2),
        "below_ma20": below_ma20,
    }


def scan_stocks(stock_list: list) -> pd.DataFrame:
    """扫描股票列表，返回触发信号的股票"""
    results = []
    total = len(stock_list)

    for i, (code, name) in enumerate(stock_list):
        print(f"\r扫描中 {i+1}/{total}: {code} {name}    ", end="", flush=True)
        try:
            df = get_stock_data(code, days=400)
            if df.empty:
                continue
            result = check_breakout(df)
            if result["signal"]:
                results.append({"代码": code, "名称": name, **result})
        except Exception:
            continue

    print("\n扫描完成！")
    return pd.DataFrame(results)


if __name__ == "__main__":
    bs.login()
    test_stocks = [
        ("sh.600519", "贵州茅台"),
        ("sz.000001", "平安银行"),
        ("sz.300750", "宁德时代"),
        ("sh.601318", "中国平安"),
        ("sz.000858", "五粮液"),
        ("sh.600036", "招商银行"),
        ("sz.002475", "立讯精密"),
        ("sh.688111", "金山办公"),
    ]
    result_df = scan_stocks(test_stocks)
    if result_df.empty:
        print("今日无触发信号（测试股票样本小，属正常）")
    else:
        print("\n=== 触发突破信号的股票 ===")
        print(result_df.to_string(index=False))
    bs.logout()
