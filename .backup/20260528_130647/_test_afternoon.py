"""临时验证脚本：单只股票策略测试"""
import os
os.environ["DATA_SOURCE"] = "tencent"

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "strategies"))
sys.path.insert(0, str(ROOT / "scripts"))

from common import get_stock_data
from afternoon import check_breakout_1450, check_pullback_1450

df = get_stock_data("sh.600000", days=400)
print(f"浦发银行: {len(df)} 条数据, 最新日期 {df.iloc[-1]['date']}")

bt = check_breakout_1450(df)
print(f"突破检测: signal={bt.get('signal')}, reason={bt.get('reason')}")

pt = check_pullback_1450(df)
print(f"回踩检测: signal={pt.get('signal')}, reason={pt.get('reason')}")
