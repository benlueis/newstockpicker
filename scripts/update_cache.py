"""每日缓存增量更新入口（多线程并发）。"""
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import baostock as bs
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from cache_manager import incremental_update  # noqa: E402

STOCK_LIST = ROOT / "data" / "stock_list.csv"
WORKERS = 10


def update_one(code: str) -> tuple[str, bool]:
    try:
        bs.login()
        df = incremental_update(code)
        bs.logout()
        return code, not df.empty
    except Exception:
        try:
            bs.logout()
        except Exception:
            pass
        return code, False


def main() -> int:
    if not STOCK_LIST.exists():
        print(f"股票池不存在: {STOCK_LIST}")
        return 1

    df_list = pd.read_csv(STOCK_LIST)
    codes = df_list["code"].tolist()
    total = len(codes)
    print(f"开始增量更新缓存: {total} 只股票, {WORKERS} 线程")

    done = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(update_one, c): c for c in codes}
        for fut in as_completed(futures):
            code, ok = fut.result()
            done += 1
            if not ok:
                failed += 1
            if done % 100 == 0 or done == total:
                print(f"  进度 {done}/{total} (失败 {failed})")

    print(f"缓存更新完成: 成功 {total - failed}, 失败 {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
