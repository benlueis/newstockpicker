"""
每日低位突破扫描入口（供定时任务调用）
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies"))

from scripts.scan_runner import run_scan  # noqa: E402


def main() -> int:
    """Thin wrapper: 委托 run_scan 处理所有通用逻辑"""
    from strategies import breakout

    result_df = run_scan(breakout, "breakout", preset="default")
    if result_df.empty:
        return 0

    result_df = result_df.sort_values("vol_ratio", ascending=False)
    print(f"\n=== 触发突破信号：{len(result_df)} 只 ===")
    print(result_df.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
