"""
每日市场龙头扫描入口
用法: python scripts/scan_dragon.py
      ./scripts/run_dragon_scan.sh
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
from dragon_leader import scan_stocks  # noqa: E402

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
        mktcap_map = dict(zip(df_list["code"], df_list["mktcap"])) if "mktcap" in df_list.columns else {}

        print(f"开始龙头扫描 {len(stock_list)} 只股票（{today}）...")
        result_df = scan_stocks(stock_list, mktcap_map=mktcap_map)

        out_path = OUTPUT_DIR / f"dragon_leader_{today_tag}.csv"
        if result_df.empty:
            print("今日无龙头信号")
            pd.DataFrame(columns=["代码", "名称"]).to_csv(out_path, index=False)
        else:
            print(f"\n=== 市场/板块龙头：{len(result_df)} 只 ===")
            print(result_df.to_string(index=False))
            result_df.to_csv(out_path, index=False)

        print(f"\n结果已保存: {out_path}")
        return 0
    finally:
        bs.logout()


if __name__ == "__main__":
    raise SystemExit(main())
