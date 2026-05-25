"""
每日回踩 5 日线扫描入口
用法: python scripts/pullback_ma5_scan.py
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import baostock as bs
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "strategies"))

from common import is_trading_day  # noqa: E402
from pullback_ma5 import scan_stocks  # noqa: E402

STOCK_LIST = ROOT / "data" / "stock_list.csv"
OUTPUT_DIR = ROOT / "data"


def main() -> int:
    today = datetime.today().strftime("%Y-%m-%d")
    today_tag = datetime.today().strftime("%Y%m%d")

    if not STOCK_LIST.exists():
        print(f"股票池不存在: {STOCK_LIST}")
        print("请先运行: python data/get_stock_list.py")
        return 1

    bs.login()
    try:
        if not is_trading_day(today):
            print(f"{today} 非交易日，跳过扫描")
            return 0

        df_list = pd.read_csv(STOCK_LIST)
        stock_list = list(zip(df_list["code"], df_list["code_name"]))
        print(f"开始回踩 5 日线扫描 {len(stock_list)} 只股票（{today}）...")

        result_df = scan_stocks(stock_list)
        out_path = OUTPUT_DIR / f"pullback_ma5_{today_tag}.csv"

        if result_df.empty:
            print("今日无回踩 5 日线信号")
            pd.DataFrame(columns=["代码", "名称", "reason"]).to_csv(out_path, index=False)
            print(f"空结果已保存: {out_path}")
            return 0

        # 按量比升序（缩量最明显的排前面）
        result_df = result_df.sort_values("vol_ratio", ascending=True)
        print(f"\n=== 回踩 5 日线信号：{len(result_df)} 只 ===")
        print(result_df.to_string(index=False))

        result_df.to_csv(out_path, index=False)
        print(f"\n结果已保存: {out_path}")
        return 0
    finally:
        bs.logout()


if __name__ == "__main__":
    raise SystemExit(main())
