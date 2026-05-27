import sys, random
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "strategies"))
sys.path.insert(0, str(ROOT / "scripts"))
from common import get_stock_data
from pullback_ma5 import check_pullback_ma5
df_list = pd.read_csv(ROOT / "data" / "stock_list.csv")
stocks = list(zip(df_list["code"], df_list["code_name"]))
random.seed(42)
sample = random.sample(stocks, 100)
stats = {}
for i, (code, name) in enumerate(sample):
    print(f"\r{i+1}/100 {code} {name}    ", end="", flush=True)
    try:
        df = get_stock_data(code, days=200)
        if df.empty: continue
        r = check_pullback_ma5(df)
        reason = r.get("reason", "未知")
        stats[reason] = stats.get(reason, 0) + 1
    except: stats["异常"] = stats.get("异常", 0) + 1
print("")
for k, v in sorted(stats.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")
