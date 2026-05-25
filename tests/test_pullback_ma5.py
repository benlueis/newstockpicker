import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "strategies"))

import pandas as pd

from pullback_ma5 import check_pullback_ma5

MIN_AMOUNT = 8e7  # 8000 万门槛


def make_uptrend_frame() -> pd.DataFrame:
    """
    构建上升趋势 + 最后一天回踩 MA5 的测试数据。
    前 60 天：缓慢上涨 → 加速上涨 → 最后一天回踩 MA5。
    """
    rows = []

    # 阶段1：缓慢爬升 40 天（close 从 10 涨到 13）
    for i in range(40):
        c = 10.0 + i * 0.075
        rows.append({
            "date": pd.Timestamp("2026-03-01") + pd.Timedelta(days=i),
            "open": round(c - 0.1, 2),
            "high": round(c + 0.15, 2),
            "low": round(c - 0.15, 2),
            "close": round(c, 2),
            "volume": 1500,
            "amount": MIN_AMOUNT,
            "pctChg": 0.5,
        })

    # 阶段2：加速上涨 15 天（close 从 13 到 15）
    for i in range(15):
        c = 13.0 + i * 0.133
        rows.append({
            "date": pd.Timestamp("2026-04-10") + pd.Timedelta(days=i),
            "open": round(c - 0.1, 2),
            "high": round(c + 0.2, 2),
            "low": round(c - 0.1, 2),
            "close": round(c, 2),
            "volume": 2000,
            "amount": MIN_AMOUNT,
            "pctChg": 1.0,
        })

    # 阶段3：高位横盘偏强 5 天（close 约 15，始终在 MA5 之上）
    for i in range(5):
        c = 15.0 + i * 0.05
        rows.append({
            "date": pd.Timestamp("2026-04-25") + pd.Timedelta(days=i),
            "open": round(c - 0.05, 2),
            "high": round(c + 0.1, 2),
            "low": round(c - 0.1, 2),
            "close": round(c, 2),
            "volume": 1800,
            "amount": MIN_AMOUNT,
            "pctChg": 0.3,
        })

    df = pd.DataFrame(rows)

    # 计算 MA5 作为参考
    ma5 = df["close"].rolling(5).mean()
    ma5_last = ma5.iloc[-1]

    # 最后一天：回踩 MA5，缩量
    last_date = df["date"].iloc[-1] + pd.Timedelta(days=1)
    rows.append({
        "date": last_date,
        "open": round(ma5_last + 0.2, 2),
        "high": round(ma5_last + 0.4, 2),
        "low": round(ma5_last - 0.01, 2),  # 低开触及 MA5
        "close": round(ma5_last + 0.05, 2),  # 收在 MA5 附近
        "volume": 1200,  # 缩量
        "amount": MIN_AMOUNT,
        "pctChg": -0.3,
    })

    return pd.DataFrame(rows)


class PullbackMA5Test(unittest.TestCase):

    def test_pullback_signal_triggered(self):
        df = make_uptrend_frame()
        result = check_pullback_ma5(df)
        self.assertTrue(result["signal"], msg=f"预期信号但返回: {result}")
        self.assertIn("回踩5日线", result["reason"])
        self.assertTrue(result["low_touched_ma5"])
        self.assertTrue(result["close_near_ma5"])
        self.assertTrue(result["vol_ok"])
        self.assertTrue(result["trend_ok"])
        self.assertGreaterEqual(result["days_above_ma5"], 5)

    def test_rejects_when_amount_too_low(self):
        df = make_uptrend_frame()
        df.loc[df.index[-1], "amount"] = 5e7  # 5000 万
        result = check_pullback_ma5(df)
        self.assertFalse(result["signal"])
        self.assertEqual(result["reason"], "成交额不足")

    def test_rejects_limit_up(self):
        df = make_uptrend_frame()
        df.loc[df.index[-1], "pctChg"] = 9.9
        result = check_pullback_ma5(df)
        self.assertFalse(result["signal"])
        self.assertEqual(result["reason"], "涨停")

    def test_rejects_limit_down(self):
        df = make_uptrend_frame()
        df.loc[df.index[-1], "pctChg"] = -9.9
        result = check_pullback_ma5(df)
        self.assertFalse(result["signal"])
        self.assertEqual(result["reason"], "跌停")

    def test_rejects_when_price_far_above_ma5(self):
        """收盘价大幅远离 MA5，不是回踩"""
        df = make_uptrend_frame()
        ma5 = df["close"].rolling(5).mean().iloc[-1]
        df.loc[df.index[-1], "close"] = ma5 * 1.03  # 高 3%
        df.loc[df.index[-1], "low"] = ma5 * 1.02  # 低也没触及 MA5
        result = check_pullback_ma5(df)
        self.assertFalse(result["signal"])

    def test_rejects_when_price_broke_too_deep(self):
        """跌破 MA5 太深，不是正常回踩"""
        df = make_uptrend_frame()
        ma5 = df["close"].rolling(5).mean().iloc[-1]
        df.loc[df.index[-1], "low"] = ma5 * 0.98  # 跌破 MA5 达 2%
        df.loc[df.index[-1], "close"] = ma5 * 0.98
        result = check_pullback_ma5(df)
        self.assertFalse(result["signal"])

    def test_rejects_when_volume_not_shrinking(self):
        """放量下跌不是回踩"""
        df = make_uptrend_frame()
        df.loc[df.index[-1], "volume"] = 5000  # 放量
        result = check_pullback_ma5(df)
        self.assertFalse(result["signal"])
        self.assertFalse(result["vol_ok"])

    def test_rejects_when_trend_broken(self):
        """均线多头排列被破坏"""
        df = make_uptrend_frame()
        # 让最近几天 close 暴跌，破坏 MA5 > MA10 > MA20
        last_idx = df.index[-1]
        df.loc[last_idx, "close"] = df["close"].iloc[-2] * 0.85
        result = check_pullback_ma5(df)
        self.assertFalse(result["signal"])

    def test_provides_detail_on_no_trend(self):
        """无趋势时返回详细诊断信息"""
        full = make_uptrend_frame()
        # 数据量足够（>= 60），但把最后几天 close 拉低破坏多头排列
        for i in range(5):
            idx = len(full) - 1 - i
            full.loc[full.index[idx], "close"] = (
                full["close"].iloc[max(0, idx - 1)] * 0.85
            )
        result = check_pullback_ma5(full)
        self.assertFalse(result["signal"])
        self.assertIn("trend_golden", result)
        self.assertIn("days_above_ma5", result)


if __name__ == "__main__":
    unittest.main()
