import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "strategies"))

import pandas as pd

from sideways_breakout import check_sideways_breakout


HIGH_AMOUNT = 1.5e8  # 满足 1 亿门槛


def make_sideways_breakout_frame():
    rows = []

    for i in range(89):
        rows.append({
            "date": pd.Timestamp("2026-01-01") + pd.Timedelta(days=i),
            "open": 8.9 + i * 0.005,
            "high": 9.0 + i * 0.005,
            "low": 8.8 + i * 0.005,
            "close": 9.0 + i * 0.005,
            "volume": 1000,
            "amount": HIGH_AMOUNT,
            "pctChg": 0.2,
        })

    for i in range(30):
        close = 9.75 + (i % 6) * 0.06
        rows.append({
            "date": pd.Timestamp("2026-01-01") + pd.Timedelta(days=89 + i),
            "open": close - 0.02,
            "high": close + 0.05,
            "low": close - 0.05,
            "close": close,
            "volume": 900,
            "amount": HIGH_AMOUNT,
            "pctChg": 0.1,
        })

    rows.append({
        "date": pd.Timestamp("2026-05-01"),
        "open": 10.15,
        "high": 10.55,
        "low": 10.08,
        "close": 10.45,
        "volume": 1900,  # vol_ratio ≈ 2.1 > 1.8
        "amount": HIGH_AMOUNT,
        "pctChg": 3.2,
    })

    return pd.DataFrame(rows)


class SidewaysBreakoutTest(unittest.TestCase):
    def test_returns_buy_signal_for_120_day_sideways_breakout(self):
        df = make_sideways_breakout_frame()
        result = check_sideways_breakout(df)
        self.assertTrue(result["signal"], msg=result)
        self.assertEqual(result["action"], "BUY")
        self.assertEqual(result["reason"], "横盘向上突破，放量确认")
        self.assertTrue(result["price_break"])
        self.assertTrue(result["vol_surge"])
        self.assertTrue(result["trend_ok"])
        self.assertLessEqual(result["base_position_120d"], 0.75)

    def test_rejects_breakout_without_volume_confirmation(self):
        df = make_sideways_breakout_frame()
        df.loc[df.index[-1], "volume"] = 1000  # vol_ratio ≈ 1.1 < 1.8
        result = check_sideways_breakout(df)
        self.assertFalse(result["signal"])
        self.assertEqual(result["action"], "WAIT")
        self.assertFalse(result["vol_surge"])

    def test_rejects_when_amount_below_threshold(self):
        df = make_sideways_breakout_frame()
        df.loc[df.index[-1], "amount"] = 5e7  # 5000 万，低于 1 亿门槛
        result = check_sideways_breakout(df)
        self.assertFalse(result["signal"])
        self.assertEqual(result["reason"], "成交额不足")

    def test_rejects_when_today_is_limit_up(self):
        df = make_sideways_breakout_frame()
        df.loc[df.index[-1], "pctChg"] = 9.9
        result = check_sideways_breakout(df)
        self.assertFalse(result["signal"])
        self.assertEqual(result["reason"], "涨停或追高")

    def test_rejects_when_long_upper_shadow(self):
        df = make_sideways_breakout_frame()
        # 长上影：high 拉很高，close 仅小幅突破
        df.loc[df.index[-1], "high"] = 11.50
        df.loc[df.index[-1], "close"] = 10.30
        result = check_sideways_breakout(df)
        self.assertFalse(result["signal"])


if __name__ == "__main__":
    unittest.main()
