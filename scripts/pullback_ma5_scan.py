"""
每日回踩 5 日线扫描入口
用法: python scripts/pullback_ma5_scan.py
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
    from strategies import pullback_ma5

    result_df = run_scan(pullback_ma5, "pullback_ma5", preset="default")
    if result_df.empty:
        print("今日无回踩 5 日线信号")
        return 0

    # 按量比升序（缩量最明显的排前面）
    result_df = result_df.sort_values("vol_ratio", ascending=True)
    print(f"\n=== 回踩 5 日线信号：{len(result_df)} 只 ===")
    print(result_df.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
