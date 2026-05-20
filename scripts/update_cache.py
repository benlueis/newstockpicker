"""每日缓存增量更新入口（进程池并发，避开 baostock 非线程安全）。"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

STOCK_LIST = ROOT / "data" / "stock_list.csv"
WORKERS = 6


def _init_worker() -> None:
    import baostock as bs
    bs.login()


def _update_one(code: str) -> tuple[str, bool]:
    from cache_manager import incremental_update
    try:
        df = incremental_update(code)
        return code, not df.empty
    except Exception:
        return code, False


def main() -> int:
    if not STOCK_LIST.exists():
        print(f"股票池不存在: {STOCK_LIST}")
        return 1

    df_list = pd.read_csv(STOCK_LIST)
    codes = df_list["code"].tolist()
    total = len(codes)
    print(f"开始增量更新缓存: {total} 只股票, {WORKERS} 进程")

    done = 0
    failed = 0
    with ProcessPoolExecutor(max_workers=WORKERS, initializer=_init_worker) as pool:
        futures = {pool.submit(_update_one, c): c for c in codes}
        for fut in as_completed(futures):
            _, ok = fut.result()
            done += 1
            if not ok:
                failed += 1
            if done % 200 == 0 or done == total:
                print(f"  进度 {done}/{total} (失败 {failed})", flush=True)

    print(f"缓存更新完成: 成功 {total - failed}, 失败 {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
