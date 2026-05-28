"""
全市场扫描入口（手动运行）— 从 strategies/ 直接调用各策略扫描。
推荐定时任务使用: scripts/run_all.py（通过 subprocess 隔离各扫描进程）
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from strategies.breakout import scan_stocks as scan_breakout
from strategies.pullback_ma5 import scan_stocks as scan_pullback_ma5
from strategies.sideways_breakout import scan_stocks as scan_sideways
from strategies.dragon_leader import scan_stocks as scan_dragon


def run_all(
    stock_list: list[tuple[str, str]] | None = None,
    output_dir: Path | None = None,
) -> dict[str, pd.DataFrame]:
    """
    一键运行所有策略扫描。

    Args:
        stock_list: 股票列表，默认从 data/stock_list.csv 加载
        output_dir: 输出目录，默认 data/

    Returns:
        {"breakout": DataFrame, "dragon_leader": DataFrame, ...}
    """
    if stock_list is None:
        list_path = ROOT / "data" / "stock_list.csv"
        df_list = pd.read_csv(list_path)
        stock_list = list(zip(df_list["code"], df_list["code_name"]))

    output_dir = output_dir or ROOT / "data"
    results = {}

    # 1. 低位突破
    print("===== 低位突破扫描 =====")
    breakout_df = scan_breakout(stock_list)
    results["breakout"] = breakout_df

    # 2. 回踩 5 日线
    print("===== 回踩 5 日线扫描 =====")
    pullback_df = scan_pullback_ma5(stock_list)
    results["pullback_ma5"] = pullback_df

    # 3. 横盘突破
    print("===== 横盘突破扫描 =====")
    sideways_df = scan_sideways(stock_list)
    results["sideways_breakout"] = sideways_df

    # 4. 市场龙头
    print("===== 市场龙头扫描 =====")
    dragon_df = scan_dragon(stock_list)
    results["dragon_leader"] = dragon_df

    return results


if __name__ == "__main__":
    from strategies.breakout import scan_stocks
    list_path = ROOT / "data" / "stock_list.csv"
    df_list = pd.read_csv(list_path)
    stock_list = list(zip(df_list["code"], df_list["code_name"]))
    result = scan_stocks(stock_list)
    print(f"信号数: {len(result)}")
