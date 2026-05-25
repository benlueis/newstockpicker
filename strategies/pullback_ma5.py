"""
回踩 5 日线选股策略（趋势中继买点）

逻辑：
个股处于上升趋势（MA5 > MA10 > MA20，且昨日收盘在 MA5 之上），
今日盘中回踩或接近 5 日均线（最低价触及 MA5 附近），
收盘价基本收在 MA5 附近，成交量较均量萎缩 ——
这是上涨中继的经典买入信号。
"""

from __future__ import annotations
import pandas as pd
from common import get_stock_data

# ── 硬约束 ────────────────────────────────────
MIN_DATA_DAYS       = 60        # 最少需要 60 日数据
MIN_AMOUNT          = 8e7       # 当日最低成交额（元）8000万
MAX_PCT_CHG         = 9.5       # 涨停排除
MIN_PCT_CHG         = -9.5      # 跌停排除

# ── 趋势参数 ───────────────────────────────────
TREND_CONFIRM_DAYS  = 8         # 回看天数确认趋势
MIN_DAYS_ABOVE_MA5  = 5         # 过去N日中至少M天收盘在MA5之上
MIN_RECENT_GAIN     = 0.10      # 近20日涨幅至少10%，确认有启动

# ── 回踩参数 ───────────────────────────────────
MAX_CLOSE_ABOVE_MA5_PCT  = 1.5  # 收盘最多高于MA5的百分比
MIN_CLOSE_BELOW_MA5_PCT  = -1.5 # 收盘最多低于MA5的百分比
MIN_LOW_TOUCH_MA5_RATIO  = 0.995 # 最低价不低于MA5的99.5%

# ── 量能参数 ───────────────────────────────────
MAX_VOL_RATIO       = 1.2       # 当日量/5日均量上限（放宽到1.2）

# ── 形态参数 ───────────────────────────────────
MIN_REBOUND_RATIO   = 0.3       # 收盘反弹幅度：(收-低)/(高-低) > 0.3
MAX_RECENT_DROP     = -7.0      # 近10日单日最大跌幅不超过-7%


def check_pullback_ma5(df: pd.DataFrame) -> dict:
    """判断今日是否满足回踩5日线条件"""
    if len(df) < MIN_DATA_DAYS:
        return {"signal": False, "reason": "数据不足"}

    close  = df["close"]
    vol    = df["volume"]
    today  = df.iloc[-1]

    # ── 基础过滤 ──────────────────────────────
    if today["pctChg"] >= MAX_PCT_CHG:
        return {"signal": False, "reason": "涨停"}
    if today["pctChg"] <= MIN_PCT_CHG:
        return {"signal": False, "reason": "跌停"}
    if today["high"] == today["low"]:
        return {"signal": False, "reason": "一字板"}

    today_amount = float(today["amount"]) if pd.notna(today.get("amount")) else 0.0
    if today_amount < MIN_AMOUNT:
        return {"signal": False, "reason": "成交额不足"}

    # ── 均线计算 ──────────────────────────────
    ma5  = close.rolling(5).mean()
    ma10 = close.rolling(10).mean()
    ma20 = close.rolling(20).mean()

    ma5_today  = ma5.iloc[-1]
    ma10_today = ma10.iloc[-1]
    ma20_today = ma20.iloc[-1]

    if pd.isna(ma5_today) or pd.isna(ma10_today) or pd.isna(ma20_today):
        return {"signal": False, "reason": "均线数据不足"}

    today_close = float(close.iloc[-1])
    today_low   = float(today["low"])
    today_high  = float(today["high"])

    # ── 趋势确认 ──────────────────────────────
    # 多头排列
    trend_golden  = ma5_today > ma10_today > ma20_today
    # 收盘在MA20之上
    above_ma20    = today_close > ma20_today
    # MA5斜率向上
    ma5_slope_up  = ma5.iloc[-1] > ma5.iloc[-2] if len(df) >= 6 else True
    # 近期大部分时间在MA5之上
    recent_above  = int(
        (close.iloc[-TREND_CONFIRM_DAYS:-1] > ma5.iloc[-TREND_CONFIRM_DAYS:-1]).sum()
    )
    was_above_ma5 = recent_above >= MIN_DAYS_ABOVE_MA5
    # 近20日有明确涨幅（确认启动，不是横盘磨底）
    recent_gain   = (close.iloc[-1] / close.iloc[-20] - 1) >= MIN_RECENT_GAIN

    trend_ok = trend_golden and above_ma20 and ma5_slope_up and was_above_ma5 and recent_gain

    if not trend_ok:
        return {
            "signal":        False,
            "reason":        "未确认上升趋势",
            "trend_golden":  trend_golden,
            "above_ma20":    above_ma20,
            "ma5_slope_up":  ma5_slope_up,
            "days_above_ma5": recent_above,
            "recent_gain":   round((close.iloc[-1] / close.iloc[-20] - 1) * 100, 2),
        }

    # ── 近期无大阴线（排除出货形态）─────────────
    max_drop    = df["pctChg"].iloc[-10:].min()
    no_big_drop = max_drop > MAX_RECENT_DROP
    if not no_big_drop:
        return {"signal": False, "reason": f"近10日有大阴线({round(max_drop,1)}%)"}

    # ── 回踩判断 ──────────────────────────────
    close_ma5_pct   = (today_close / ma5_today - 1) * 100
    # 盘中触及MA5
    low_touched_ma5  = today_low <= ma5_today
    # 没有破位太深
    low_not_too_deep = today_low >= ma5_today * MIN_LOW_TOUCH_MA5_RATIO
    # 收盘在MA5附近
    close_near_ma5   = MIN_CLOSE_BELOW_MA5_PCT <= close_ma5_pct <= MAX_CLOSE_ABOVE_MA5_PCT
    # 收盘从低点反弹（有资金承接）
    candle_range  = today_high - today_low
    rebound_ratio = (today_close - today_low) / candle_range if candle_range > 0 else 0
    rebound_ok    = rebound_ratio >= MIN_REBOUND_RATIO

    pullback_ok = low_touched_ma5 and low_not_too_deep and close_near_ma5 and rebound_ok

    # ── 量能（用今日之前5日均量，不含今日）──────
    vol_ma5   = vol.iloc[-6:-1].mean()   # ✅ 不含今日，避免自身拉低均值
    vol_ratio = float(today["volume"]) / vol_ma5 if vol_ma5 > 0 else 0
    vol_ok    = vol_ratio <= MAX_VOL_RATIO

    signal = pullback_ok and vol_ok

    return {
        "signal":          signal,
        "reason":          "回踩5日线，缩量企稳" if signal else "未满足回踩条件",
        "close_ma5_pct":   round(close_ma5_pct, 2),
        "low_touched_ma5": low_touched_ma5,
        "low_not_too_deep":low_not_too_deep,
        "close_near_ma5":  close_near_ma5,
        "rebound_ratio":   round(rebound_ratio, 2),
        "rebound_ok":      rebound_ok,
        "vol_ratio":       round(vol_ratio, 2),
        "vol_ok":          vol_ok,
        "ma5":             round(ma5_today, 2),
        "ma10":            round(ma10_today, 2),
        "ma20":            round(ma20_today, 2),
        "pct_chg":         round(float(today["pctChg"]), 2),
        "amount_yi":       round(today_amount / 1e8, 2),
        "days_above_ma5":  recent_above,
        "recent_gain_pct": round((close.iloc[-1] / close.iloc[-20] - 1) * 100, 2),
        "max_drop_10d":    round(max_drop, 2),
    }


def scan_stocks(stock_list: list) -> pd.DataFrame:
    results = []
    total   = len(stock_list)

    for i, (code, name) in enumerate(stock_list):
        print(f"\r扫描中 {i+1}/{total}: {code} {name}    ", end="", flush=True)
        try:
            df = get_stock_data(code, days=200)
            if df.empty:
                continue
            result = check_pullback_ma5(df)
            if result["signal"]:
                results.append({"代码": code, "名称": name, **result})
        except Exception:
            continue

    print("\n扫描完成！")
    return pd.DataFrame(results)


if __name__ == "__main__":
    import baostock as bs
    from pathlib import Path
    import pandas as pd

    ROOT = Path(__file__).resolve().parents[1]
    bs.login()

    df_list    = pd.read_csv(ROOT / "data" / "stock_list.csv")
    stock_list = list(zip(df_list['code'], df_list['code_name']))

    print(f"开始扫描 {len(stock_list)} 只股票...")
    result_df = scan_stocks(stock_list)

    if result_df.empty:
        print("今日无触发信号")
    else:
        result_df["score"] = result_df["rebound_ratio"] - result_df["vol_ratio"] * 0.3
        result_df = result_df.sort_values("score", ascending=False)
        print(f"\n=== 回踩5日线信号：{len(result_df)} 只 ===")
        cols = ["代码","名称","pct_chg","close_ma5_pct","rebound_ratio","vol_ratio","recent_gain_pct","amount_yi"]
        print(result_df[cols].to_string(index=False))

        from datetime import datetime
        today = datetime.today().strftime("%Y%m%d")
        out   = ROOT / "data" / f"pullback_ma5_{today}.csv"
        result_df.to_csv(out, index=False)
        print(f"\n结果已保存：{out}")

    bs.logout()
