"""tracker_metrics 单元测试"""
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from tracker_metrics import compute_returns


def _make_bars(close_seq):
    return pd.DataFrame({
        "date": pd.date_range("2026-05-10", periods=len(close_seq), freq="B"),
        "close": close_seq,
    })


class TestComputeReturns(unittest.TestCase):

    def test_t1_t3_t5_basic(self):
        # 信号日 close=10，T+1=11 (+10%), T+3=12 (+20%), T+5=11 (+10%)
        bars = _make_bars([10, 11, 11.5, 12, 11.8, 11])
        signal_date = bars["date"].iloc[0]
        out = compute_returns(bars, signal_date, horizons=(1, 3, 5))
        self.assertAlmostEqual(out[1], 10.0, places=2)
        self.assertAlmostEqual(out[3], 20.0, places=2)
        self.assertAlmostEqual(out[5], 10.0, places=2)

    def test_missing_future_bar_returns_none(self):
        # 只有信号日 + 2 根，T+3 / T+5 应返回 None
        bars = _make_bars([10, 11, 12])
        signal_date = bars["date"].iloc[0]
        out = compute_returns(bars, signal_date, horizons=(1, 3, 5))
        self.assertAlmostEqual(out[1], 10.0, places=2)
        self.assertIsNone(out[3])
        self.assertIsNone(out[5])

    def test_signal_date_not_in_frame_returns_all_none(self):
        bars = _make_bars([10, 11])
        out = compute_returns(bars, pd.Timestamp("2024-01-01"), horizons=(1, 3, 5))
        self.assertIsNone(out[1])
        self.assertIsNone(out[3])
        self.assertIsNone(out[5])


if __name__ == "__main__":
    unittest.main()
