"""
每日市场龙头扫描入口
用法: python scripts/scan_dragon.py
       ./scripts/run_dragon_scan.sh
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
    from strategies import dragon_leader

    result_df = run_scan(dragon_leader, "dragon_leader", preset="default")
    if result_df.empty:
        print("今日无龙头信号")
        return 0

    print(f"\n=== 市场/板块龙头：{len(result_df)} 只 ===")
    print(result_df.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
