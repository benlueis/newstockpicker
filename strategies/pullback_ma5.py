"""
回踩 5 日线选股策略（趋势中继买点）

逻辑：
个股处于上升趋势（MA5 > MA10 > MA20，且昨日收盘在 MA5 之上），
今日盘中回踩或接近 5 日均线（最低价触及 MA5 附近），
收盘价基本收在 MA5 附近，成交量较均量萎缩 ——
这是上涨中继的经典买入信号。
"""

from __future__ import annotations
import sys
import pandas as pd
from common import get_stock_data, merge_params

# ── 默认参数（YAML 缺失时的回退值）─────────────
DEFAULT_PARAMS: dict = {
    # 硬约束
    "min_data_days": 60,
    "min_amount": 8e7,             # 8000 万
    "max_pct_chg": 9.5,            # 涨停排除
    "min_pct_chg": -9.5,           # 跌停排除
    # 趋势参数
    "trend_confirm_days": 8,
    "min_days_above_ma5": 5,
    "min_recent_gain": 0.10,       # 近 20 日涨幅至少 10%
    # 回踩参数
    "max_close_above_ma5_pct": 1.5,
    "min_close_below_ma5_pct": -1.5,
    "min_low_touch_ma5_ratio": 0.995,
    # 量能参数
    "max_vol_ratio": 1.2,
    # 形态参数
    "min_rebound_ratio": 0.3,
    "max_recent_drop": -7.0,
}


def check_pullback_ma5(df: pd.DataFrame, params: dict | None = None) -> dict:
    """判断今日是否满足回踩5日线条件"""
    p = merge_params(params, DEFAULT_PARAMS)

    if len(df) < p["min_data_days"]:
        return {"signal": False, "reason": "数据不足"}

    close = df["close"]
    vol = df["volume"]
    today = df.iloc[-1]

    # ── 基础过滤 ──────────────────────────────
    if today["pctChg"] >= p["max_pct_chg"]:
        return {"signal": False, "reason": "涨停"}
    if today["pctChg"] <= p["min_pct_chg"]:
        return {"signal": False, "reason": "跌停"}
    if today["high"] == today["low"]:
        return {"signal": False, "reason": "一字板"}

    today_amount = float(today["amount"]) if pd.notna(today.get("amount")) else 0.0
    if today_amount < p["min_amount"]:
        return {"signal": False, "reason": "成交额不足"}

    # ── 均线计算 ──────────────────────────────
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

    # ── 趋势确认 ──────────────────────────────
    trend_golden = ma5_today > ma10_today > ma20_today
    above_ma20 = today_close > ma20_today
    ma5_slope_up = ma5.iloc[-1] > ma5.iloc[-2] if len(df) >= 6 else True

    recent_above = int(
        (close.iloc[-p["trend_confirm_days"]:-1] > ma5.iloc[-p["trend_confirm_days"]:-1]).sum()
    )
    was_above_ma5 = recent_above >= p["min_days_above_ma5"]
    recent_gain = (close.iloc[-1] / close.iloc[-20] - 1) >= p["min_recent_gain"]

    trend_ok = trend_golden and above_ma20 and ma5_slope_up and was_above_ma5 and recent_gain

    if not trend_ok:
        return {
            "signal": False,
            "reason": "未确认上升趋势",
            "trend_golden": trend_golden,
            "above_ma20": above_ma20,
            "ma5_slope_up": ma5_slope_up,
            "days_above_ma5": recent_above,
            "recent_gain": round((close.iloc[-1] / close.iloc[-20] - 1) * 100, 2),
        }

    # ── 近期无大阴线（排除出货形态）─────────────
    max_drop = df["pctChg"].iloc[-10:].min()
    no_big_drop = max_drop > p["max_recent_drop"]
    if not no_big_drop:
        return {"signal": False, "reason": f"近10日有大阴线({round(max_drop,1)}%)"}

    # ── 回踩判断 ──────────────────────────────
    close_ma5_pct = (today_close / ma5_today - 1) * 100
    low_touched_ma5 = today_low <= ma5_today
    low_not_too_deep = today_low >= ma5_today * p["min_low_touch_ma5_ratio"]
    close_near_ma5 = p["min_close_below_ma5_pct"] <= close_ma5_pct <= p["max_close_above_ma5_pct"]

    candle_range = today_high - today_low
    rebound_ratio = (today_close - today_low) / candle_range if candle_range > 0 else 0
    rebound_ok = rebound_ratio >= p["min_rebound_ratio"]

    pullback_ok = low_touched_ma5 and low_not_too_deep and close_near_ma5 and rebound_ok

    # ── 量能（用今日之前5日均量，不含今日）──────
    vol_ma5 = vol.iloc[-6:-1].mean()
    vol_ratio = float(today["volume"]) / vol_ma5 if vol_ma5 > 0 else 0
    vol_ok = vol_ratio <= p["max_vol_ratio"]

    signal = pullback_ok and vol_ok

    return {
        "signal": signal,
        "reason": "回踩5日线，缩量企稳" if signal else "未满足回踩条件",
        "close_ma5_pct": round(close_ma5_pct, 2),
        "low_touched_ma5": low_touched_ma5,
        "low_not_too_deep": low_not_too_deep,
        "close_near_ma5": close_near_ma5,
        "rebound_ratio": round(rebound_ratio, 2),
        "rebound_ok": rebound_ok,
        "vol_ratio": round(vol_ratio, 2),
        "vol_ok": vol_ok,
        "ma5": round(ma5_today, 2),
        "ma10": round(ma10_today, 2),
        "ma20": round(ma20_today, 2),
        "pct_chg": round(float(today["pctChg"]), 2),
        "amount_yi": round(today_amount / 1e8, 2),
        "days_above_ma5": recent_above,
        "recent_gain_pct": round((close.iloc[-1] / close.iloc[-20] - 1) * 100, 2),
        "max_drop_10d": round(max_drop, 2),
        # 趋势诊断字段
        "trend_ok": trend_ok,
        "trend_golden": trend_golden,
    }


def scan_stocks(stock_list: list, params: dict | None = None) -> pd.DataFrame:
    """扫描股票列表，返回触发信号的股票"""
    results = []
    total = len(stock_list)

    for i, (code, name) in enumerate(stock_list):
        print(f"\r扫描中 {i+1}/{total}: {code} {name}    ", end="", flush=True)
        try:
            df = get_stock_data(code, days=200)
            if df.empty:
                continue
            result = check_pullback_ma5(df, params=params)
            if result["signal"]:
                results.append({"代码": code, "名称": name, **result})
        except Exception as e:
            print(f"\n⚠️ {code} {name}: {e}", file=sys.stderr)

    print("\n扫描完成！")
    return pd.DataFrame(results)


if __name__ == "__main__":
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]

    df_list = pd.read_csv(ROOT / "data" / "stock_list.csv")
    stock_list = list(zip(df_list["code"], df_list["code_name"]))

    print(f"开始扫描 {len(stock_list)} 只股票...")
    result_df = scan_stocks(stock_list)

    if result_df.empty:
        print("今日无触发信号")
    else:
        result_df["score"] = result_df["rebound_ratio"] - result_df["vol_ratio"] * 0.3
        result_df = result_df.sort_values("score", ascending=False)
        print(f"\n=== 回踩5日线信号：{len(result_df)} 只 ===")
        cols = ["代码", "名称", "pct_chg", "close_ma5_pct", "rebound_ratio", "vol_ratio", "recent_gain_pct", "amount_yi"]
        print(result_df[cols].to_string(index=False))

        from datetime import datetime
        today = datetime.today().strftime("%Y%m%d")
        out = ROOT / "data" / f"pullback_ma5_{today}.csv"
        result_df.to_csv(out, index=False)
