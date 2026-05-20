"""手动运行: python strategies/scan_dragon.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from scan_dragon import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
