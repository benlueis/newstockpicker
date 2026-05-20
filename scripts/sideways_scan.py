"""每日横盘向上突破扫描入口。"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import baostock as bs
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "strategies"))

from common import is_trading_day  # noqa: E402
from sideways_breakout import scan_stocks  # noqa: E402

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
        print(f"开始扫描横盘向上突破信号 {len(stock_list)} 只股票（{today}）...")

        result_df = scan_stocks(stock_list)
        out_path = OUTPUT_DIR / f"sideways_breakout_{today_tag}.csv"

        if result_df.empty:
            print("今日无横盘向上突破买入提示")
            pd.DataFrame(columns=["代码", "名称", "action", "reason"]).to_csv(out_path, index=False)
            print(f"空结果已保存: {out_path}")
            return 0

        result_df = result_df.sort_values(
            ["vol_ratio", "breakout_pct"],
            ascending=False,
        )
        print(f"\n=== 横盘向上突破买入提示：{len(result_df)} 只 ===")
        print(result_df.to_string(index=False))

        result_df.to_csv(out_path, index=False)
        print(f"\n结果已保存: {out_path}")
        return 0
    finally:
        bs.logout()


if __name__ == "__main__":
    raise SystemExit(main())
