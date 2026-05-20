"""Pytest/unittest 共用：把 strategies/ 加入 sys.path，方便测试 import。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "strategies"))
