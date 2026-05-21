"""一键流程：增量更新缓存 → 三策略扫描 → Bark 推送完整列表。

用法：
    BARK_URL='https://api.day.app/xxx/' python scripts/run_all.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

STEPS = [
    ("更新缓存", [PY, str(ROOT / "scripts" / "update_cache.py")]),
    ("低位横盘突破", [PY, str(ROOT / "scripts" / "daily_scan.py")]),
    ("市场龙头", [PY, str(ROOT / "scripts" / "scan_dragon.py")]),
    ("横盘向上突破", [PY, str(ROOT / "scripts" / "sideways_scan.py")]),
    ("推送 iPhone", [PY, str(ROOT / "scripts" / "push_summary.py"), "收盘扫描"]),
]


def main() -> int:
    for label, cmd in STEPS:
        print(f"\n===== {label} =====", flush=True)
        rc = subprocess.call(cmd, cwd=ROOT)
        if rc != 0:
            print(f"[run_all] {label} 失败 rc={rc}，终止")
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
