import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "strategies"))

import pandas as pd

from dragon_leader import evaluate_leader


HIGH_AMOUNT = 3e8


def make_leader_frame(
    ret_20d_pct: float = 30.0,
    ret_5d_pct: float = 10.0,
    today_pct_chg: float = 3.0,
    one_way: bool = False,
):
    """
    构造一个强趋势的样本：close 从 8 → 10 → 接近高点。
    ret_20d_pct: 期望的 20 日涨幅
    one_way: 是否一字板
    """
    rows = []
    base = 10.0
    # 前 200 日缓涨
    for i in range(200):
        close = 7.0 + (i / 200) * 3.0  # 7 → 10
        rows.append({
            "date": pd.Timestamp("2025-08-01") + pd.Timedelta(days=i),
            "open": close - 0.05,
            "high": close + 0.10,
            "low": close - 0.10,
            "close": close,
            "volume": 1000,
            "amount": HIGH_AMOUNT,
            "turn": 2.0,
            "pctChg": 0.15,
        })

    # 近 20 日强势上涨：从 10 涨到 10 * (1 + ret_20d_pct/100)
    start_close = 10.0
    end_close_target = start_close * (1 + ret_20d_pct / 100)
    five_d_start = end_close_target / (1 + ret_5d_pct / 100)

    # 0~14 (15 days): 从 10 → five_d_start，量能温和
    for i in range(15):
        close = start_close + (five_d_start - start_close) * (i + 1) / 15
        rows.append({
            "date": pd.Timestamp("2025-08-01") + pd.Timedelta(days=200 + i),
            "open": close - 0.05,
            "high": close + 0.10,
            "low": close - 0.10,
            "close": close,
            "volume": 1200,
            "amount": HIGH_AMOUNT,
            "turn": 3.0,
            "pctChg": 0.5,
        })

    # 15~19 (5 days, 包括今日): five_d_start → end_close_target，明显放量
    for i in range(5):
        close = five_d_start + (end_close_target - five_d_start) * (i + 1) / 5
        rows.append({
            "date": pd.Timestamp("2025-08-01") + pd.Timedelta(days=215 + i),
            "open": close - 0.05,
            "high": close + 0.10,
            "low": close - 0.10,
            "close": close,
            "volume": 2200,
            "amount": HIGH_AMOUNT,
            "turn": 4.0,
            "pctChg": 1.0,
        })

    # 设定今日 pctChg
    last = rows[-1]
    last["pctChg"] = today_pct_chg
    if one_way:
        last["open"] = last["close"]
        last["high"] = last["close"]
        last["low"] = last["close"]

    return pd.DataFrame(rows)


class DragonLeaderTest(unittest.TestCase):
    def test_strong_leader_passes(self):
        df = make_leader_frame(ret_20d_pct=30.0, ret_5d_pct=10.0, today_pct_chg=3.0)
        result = evaluate_leader(df, bench_ret_20d=2.0, bench_ret_5d=0.5)
        self.assertTrue(result.get("signal"), msg=result)
        self.assertGreaterEqual(result["leader_score"], 65.0)

    def test_rejects_limit_up_today(self):
        df = make_leader_frame(today_pct_chg=9.9)
        result = evaluate_leader(df, bench_ret_20d=2.0, bench_ret_5d=0.5)
        self.assertFalse(result["signal"])
        self.assertEqual(result["reason"], "涨停或追高")

    def test_rejects_one_way_limit_up(self):
        df = make_leader_frame(today_pct_chg=8.0, one_way=True)
        result = evaluate_leader(df, bench_ret_20d=2.0, bench_ret_5d=0.5)
        self.assertFalse(result["signal"])
        self.assertEqual(result["reason"], "一字板")

    def test_rejects_overheated_ret_20d(self):
        """ret_20d=100% 已经透支，应被拒。"""
        df = make_leader_frame(ret_20d_pct=100.0, ret_5d_pct=20.0)
        result = evaluate_leader(df, bench_ret_20d=2.0, bench_ret_5d=0.5)
        self.assertFalse(result["signal"], msg=result)

    def test_rejects_overheated_ret_5d(self):
        """ret_5d=35% 短期透支，应被拒。"""
        df = make_leader_frame(ret_20d_pct=50.0, ret_5d_pct=35.0)
        result = evaluate_leader(df, bench_ret_20d=2.0, bench_ret_5d=0.5)
        self.assertFalse(result["signal"], msg=result)

    def test_rejects_low_amount(self):
        df = make_leader_frame()
        df.loc[df.index[-1], "amount"] = 1e8  # 低于 2 亿龙头门槛
        result = evaluate_leader(df, bench_ret_20d=2.0, bench_ret_5d=0.5)
        self.assertFalse(result["signal"])
        self.assertEqual(result["reason"], "成交额不足")

    def test_rejects_negative_today(self):
        """龙头当日应是上涨的，跌或平就不算。"""
        df = make_leader_frame(today_pct_chg=-0.5)
        result = evaluate_leader(df, bench_ret_20d=2.0, bench_ret_5d=0.5)
        self.assertFalse(result["signal"])


if __name__ == "__main__":
    unittest.main()
