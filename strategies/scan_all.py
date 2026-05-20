"""
全市场扫描入口（手动运行）
推荐定时任务使用: scripts/run_daily_scan.sh
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from daily_scan import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
