"""补跑 5/26 全量四策略"""
import os, sys
from pathlib import Path
import pandas as pd
import baostock as bs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "strategies"))
sys.path.insert(0, str(ROOT / "scripts"))

from common import get_stock_data
from breakout import check_breakout
from pullback_ma5 import check_pullback_ma5
from sideways_breakout import check_sideways_breakout
from dragon_leader import evaluate_leader, _benchmark_returns, _assign_leader_types
from common import load_industry_map

TARGET = "2026-05-26"
TAG = "20260526"
STOCK_LIST = ROOT / "data" / "stock_list.csv"
OUT = ROOT / "data"

df_list = pd.read_csv(STOCK_LIST)
stocks = list(zip(df_list["code"], df_list["code_name"]))
total = len(stocks)
print(f"补跑 {TARGET} | {total} 只")

bs.login()
bench_5d, bench_20d = _benchmark_returns()
industry_map = load_industry_map()

bt, pt, sw, dr = [], [], [], []
for i, (code, name) in enumerate(stocks):
    print(f"\r{i+1}/{total}: {code} {name}    ", end="", flush=True)
    try:
        df = get_stock_data(code, days=400)
        if df.empty: continue
        df = df[df["date"].astype(str).str[:10] <= TARGET]
        if df.empty: continue

        r = check_breakout(df)
        if r["signal"]: bt.append({"代码": code, "名称": name, **r})

        df2 = get_stock_data(code, days=200)
        if not df2.empty:
            df2 = df2[df2["date"].astype(str).str[:10] <= TARGET]
            r2 = check_pullback_ma5(df2)
            if r2["signal"]: pt.append({"代码": code, "名称": name, **r2})

        r3 = check_sideways_breakout(df)
        if r3["signal"]: sw.append({"代码": code, "名称": name, **r3})

        m = evaluate_leader(df, bench_20d, bench_5d)
        if m.get("signal"):
            dr.append({"代码": code, "名称": name,
                       "industry": industry_map.get(code.split(".")[-1], "未知"),
                       **{k: v for k, v in m.items() if k != "signal"}})
    except: continue

print(f"\n突破:{len(bt)} 回踩:{len(pt)} 横盘:{len(sw)} 龙头:{len(dr)}")

pd.DataFrame(bt).to_csv(OUT / f"breakout_{TAG}.csv", index=False)
pd.DataFrame(pt).to_csv(OUT / f"pullback_ma5_{TAG}.csv", index=False)
pd.DataFrame(sw).to_csv(OUT / f"sideways_breakout_{TAG}.csv", index=False)

dr_rows = _assign_leader_types(dr)
pd.DataFrame(dr_rows).to_csv(OUT / f"dragon_leader_{TAG}.csv", index=False)

bs.logout()
print("完成")
