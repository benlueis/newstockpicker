"""
14:45 尾盘精选扫描（收盘前买入专用）

数据源: tencent（腾讯行情，盘中实时）
策略:   afternoon.py — 低位突破(收紧) + 回踩企稳(收紧) + 交叉验证
输出:   data/afternoon_{date}.csv + Bark 推送 Top 5

用法:
    python scripts/afternoon_scan.py

环境变量:
    DATA_SOURCE=tencent  （强制，确保当日盘中数据可用）
    BARK_URL=...          （可选，Bark 推送地址）
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

# ── 必须在任何策略导入前设置数据源为实时源 ──
os.environ["DATA_SOURCE"] = "tencent"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "strategies"))
sys.path.insert(0, str(ROOT / "scripts"))

import baostock as bs
import pandas as pd

from cache_manager import incremental_update
from common import is_trading_day
from notify import send

STOCK_LIST = ROOT / "data" / "stock_list.csv"
OUTPUT_DIR = ROOT / "data"
TOP_N = 5


def _format_result(df: pd.DataFrame) -> str:
    """将结果 DataFrame 格式化为推送文本"""
    lines: list[str] = []
    for _, r in df.iterrows():
        code_short = str(r["代码"]).split(".")[-1]
        cross = "🔥" if r.get("cross_hit") else ""
        strategy = r.get("strategy", "")
        score = r.get("composite_score", 0)
        pct = r.get("pct_chg", 0)
        amount = r.get("amount_yi", 0)
        lines.append(
            f"{cross}{r['名称']}({code_short}) "
            f"涨{pct:.1f}% "
            f"分{score:.0f} "
            f"额{amount:.1f}亿 "
            f"[{strategy}]"
        )
    return "\n".join(lines)


def main() -> int:
    today = datetime.today().strftime("%Y-%m-%d")
    today_tag = datetime.today().strftime("%Y%m%d")

    # ── 交易日检查 ──────────────────────────────
    bs.login()
    try:
        if not is_trading_day(today):
            print(f"{today} 非交易日，跳过扫描")
            return 0
    finally:
        bs.logout()

    if not STOCK_LIST.exists():
        print(f"股票池不存在: {STOCK_LIST}")
        print("请先运行: python data/get_stock_list.py")
        return 1

    # ── 加载股票池 ──────────────────────────────
    df_list = pd.read_csv(STOCK_LIST)
    stock_list: list[tuple[str, str]] = list(
        zip(df_list["code"], df_list["code_name"])
    )
    total = len(stock_list)
    print(f"14:45 尾盘精选扫描启动 | 数据源: tencent | 股票池: {total} 只")

    # ── 第一步：增量更新缓存（确保有当日数据）────
    print("Step 1/2: 增量更新缓存...")
    updated = 0
    for i, (code, _) in enumerate(stock_list):
        if (i + 1) % 500 == 0 or (i + 1) == total:
            print(f"\r  缓存更新 {i+1}/{total}    ", end="", flush=True)
        try:
            df = incremental_update(code)
            if not df.empty:
                updated += 1
        except Exception:
            pass
    print(f"\r  缓存更新完成: {updated}/{total} 有效")

    # ── 第二步：策略扫描 ─────────────────────────
    print("Step 2/2: 策略扫描...")
    from afternoon import scan_stocks  # noqa: E402

    result_df = scan_stocks(stock_list, top_n=TOP_N)

    # ── 输出 ────────────────────────────────────
    out_path = OUTPUT_DIR / f"afternoon_{today_tag}.csv"
    result_df.to_csv(out_path, index=False)
    print(f"\n结果已保存: {out_path}")

    if result_df.empty:
        msg = "今日无符合条件的尾盘买入信号"
        print(msg)
        send(f"{today} 14:45 尾盘精选", msg, group="afternoon-scan")
        return 0

    print(f"\n推送 Top {len(result_df)}:")
    body = _format_result(result_df)
    print(body)

    send(f"{today} 14:45 尾盘精选", body, group="afternoon-scan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
