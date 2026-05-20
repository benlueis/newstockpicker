import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "strategies"))

import pandas as pd

from breakout import check_breakout


HIGH_AMOUNT = 1.5e8


def make_low_breakout_frame():
    """
    构造：250 日高点 ≈ 20，近期低位（10~12）+ 20 日横盘缩量 + 今日放量突破。
    箱体前段（box_days 之前）保留高量，让"近 5 日缩量"对比有意义。
    """
    rows = []

    # 前 150 日：从 20 跌到 10（下跌过程，volume=1000）
    for i in range(150):
        close = 20 - (i / 150) * 10
        rows.append({
            "date": pd.Timestamp("2025-08-01") + pd.Timedelta(days=i),
            "open": close - 0.05,
            "high": close + 0.10,
            "low": close - 0.10,
            "close": close,
            "volume": 1000,
            "amount": HIGH_AMOUNT,
            "pctChg": -0.1,
        })

    # 横盘 30 日：前 25 日 volume=900（接近箱体均量），最后 5 日 600（明显缩量）
    for i in range(30):
        close = 10.5 + (i % 6) * 0.08
        rows.append({
            "date": pd.Timestamp("2025-08-01") + pd.Timedelta(days=150 + i),
            "open": close - 0.02,
            "high": close + 0.05,
            "low": close - 0.05,
            "close": close,
            "volume": 900 if i < 25 else 600,
            "amount": HIGH_AMOUNT,
            "pctChg": 0.1,
        })

    # 突破日：close 突破 11.0（箱顶 ≈ 10.9）
    rows.append({
        "date": pd.Timestamp("2025-08-01") + pd.Timedelta(days=180),
        "open": 11.0,
        "high": 11.55,
        "low": 10.95,
        "close": 11.50,
        "volume": 1800,
        "amount": HIGH_AMOUNT,
        "pctChg": 5.5,
    })

    return pd.DataFrame(rows)


def make_high_position_frame():
    """
    构造：高位（position 接近 1.0），价格 11~12 区间，近期横盘后突破。
    用来验证"在低位"是必要条件。
    """
    rows = []

    # 250 日全部在 11~12 区间小幅震荡
    for i in range(180):
        close = 11.5 + 0.4 * ((i % 10) / 10 - 0.5)  # 11.3 ~ 11.7
        rows.append({
            "date": pd.Timestamp("2025-08-01") + pd.Timedelta(days=i),
            "open": close - 0.02,
            "high": close + 0.05,
            "low": close - 0.05,
            "close": close,
            "volume": 900 if i < 175 else 600,
            "amount": HIGH_AMOUNT,
            "pctChg": 0.1,
        })

    # 突破日：close 11.95（接近高点 12，position 很高）
    rows.append({
        "date": pd.Timestamp("2025-08-01") + pd.Timedelta(days=180),
        "open": 11.7,
        "high": 12.0,
        "low": 11.65,
        "close": 11.95,
        "volume": 1800,
        "amount": HIGH_AMOUNT,
        "pctChg": 3.5,
    })

    return pd.DataFrame(rows)


class BreakoutTest(unittest.TestCase):
    def test_returns_signal_for_low_box_breakout(self):
        df = make_low_breakout_frame()
        result = check_breakout(df)
        self.assertTrue(result["signal"], msg=result)
        self.assertLess(result["position"], 0.60)

    def test_rejects_when_position_too_high(self):
        """高位（position > 0.6）哪怕走势完美也应该被拒——这是 review 发现的核心 bug。"""
        df = make_high_position_frame()
        result = check_breakout(df)
        self.assertFalse(result["signal"])
        self.assertEqual(result["reason"], "不在低位")

    def test_rejects_when_today_is_limit_up(self):
        df = make_low_breakout_frame()
        df.loc[df.index[-1], "pctChg"] = 9.9
        result = check_breakout(df)
        self.assertFalse(result["signal"])
        self.assertEqual(result["reason"], "涨停或追高")

    def test_rejects_when_amount_below_threshold(self):
        df = make_low_breakout_frame()
        df.loc[df.index[-1], "amount"] = 5e7
        result = check_breakout(df)
        self.assertFalse(result["signal"])
        self.assertEqual(result["reason"], "成交额不足")


if __name__ == "__main__":
    unittest.main()
