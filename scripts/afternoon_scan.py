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
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# ── 必须在任何策略导入前设置数据源为实时源 ──
os.environ["DATA_SOURCE"] = "tencent"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "strategies"))
sys.path.insert(0, str(ROOT / "scripts"))

import pandas as pd

from cache_manager import incremental_update
from common import is_trading_day
from notify import send

STOCK_LIST = ROOT / "data" / "stock_list.csv"
OUTPUT_DIR = ROOT / "data"
TOP_N = 5
CACHE_WORKERS = 4  # 并行缓存更新的进程数


def _update_cache_parallel(stock_list: list[tuple[str, str]]) -> tuple[int, int, list[str]]:
    """
    并行增量更新缓存，返回 (成功数, 失败数, 失败代码列表)。
    使用 ProcessPoolExecutor，参照 update_cache.py 的多进程模式。
    """
    print(f"Step 1/2: 并行增量更新缓存 (workers={CACHE_WORKERS}) ...")
    total = len(stock_list)
    updated = 0
    failed = 0
    failed_codes: list[str] = []

    # 只更新缓存，不关心返回的 DataFrame（含重试应对 SQLite 并发）
    def _update_one(code: str) -> str | None:
        import time
        for attempt in range(3):
            try:
                df = incremental_update(code)
                return code if not df.empty else None
            except Exception:
                if attempt < 2:
                    time.sleep(1)
        return None

    # 提取纯 code 列表用于并行处理
    codes = [code for code, _ in stock_list]

    with ProcessPoolExecutor(max_workers=CACHE_WORKERS) as executor:
        futures = {executor.submit(_update_one, code): code for code in codes}
        completed = 0
        for future in as_completed(futures):
            completed += 1
            code = futures[future]
            if completed % 500 == 0 or completed == total:
                print(f"\r  缓存更新 {completed}/{total}    ", end="", flush=True)
            try:
                result = future.result(timeout=30)
                if result:
                    updated += 1
            except Exception as e:
                failed += 1
                failed_codes.append(code)
                print(f"\n⚠️ 缓存更新失败 {code}: {e}", file=sys.stderr)

    print(f"\r  缓存更新完成: {updated}/{total} 有效, {failed} 失败")
    return updated, failed, failed_codes


def _format_result(df: pd.DataFrame) -> str:
    """将结果 DataFrame 格式化为推送文本"""
    lines: list[str] = []
    for _, r in df.iterrows():
        code_short = str(r["代码"]).split(".")[-1]
        cross = "🔥" if r.get("cross_hit") else ""
        tier = r.get("tier", "")
        tier_tag = "" if tier == "tight" else " ⚠️"
        strategy = r.get("strategy", "")
        score = r.get("composite_score", 0)
        pct = r.get("pct_chg", 0)
        amount = r.get("amount_yi", 0)
        lines.append(
            f"{cross}{r['名称']}({code_short}){tier_tag} "
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
    if not is_trading_day(today):
        print(f"{today} 非交易日，跳过扫描")
        return 0

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

    # ── 第一步：并行增量更新缓存 ────────────────
    cache_updated, cache_failed, cache_failed_codes = _update_cache_parallel(stock_list)

    # ── 第二步：策略扫描 ─────────────────────────
    print("Step 2/2: 策略扫描...")
    from afternoon import scan_stocks  # noqa: E402

    result_df = scan_stocks(stock_list, top_n=TOP_N)

    # ── 输出 ────────────────────────────────────
    out_path = OUTPUT_DIR / f"afternoon_{today_tag}.csv"
    result_df.to_csv(out_path, index=False)
    print(f"\n结果已保存: {out_path}")

    # ── 推送（含失败汇总） ──────────────────────
    if result_df.empty:
        msg = "今日无符合条件的尾盘买入信号"
        if cache_failed > 0:
            msg += f"\n⚠️ {cache_failed} 只缓存更新失败"
        print(msg)
        send(f"{today} 14:45 尾盘精选", msg, group="afternoon-scan")
        return 0

    print(f"\n推送 Top {len(result_df)}:")
    body = _format_result(result_df)
    print(body)

    if cache_failed > 0:
        failed_preview = ", ".join(cache_failed_codes[:5])
        if len(cache_failed_codes) > 5:
            failed_preview += f", ... 共 {cache_failed} 只"
        body += f"\n\n⚠️ 缓存更新失败: {failed_preview}"

    send(f"{today} 14:45 尾盘精选", body, group="afternoon-scan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
