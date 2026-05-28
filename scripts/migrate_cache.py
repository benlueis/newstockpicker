"""
将现有 parquet 缓存迁移到 SQLite。

用法：
    python scripts/migrate_cache.py          # 增量导入
    python scripts/migrate_cache.py --force  # 清空 SQLite 后重新导入
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "cache"
DB_PATH = CACHE_DIR / "stocks.db"


def main() -> int:
    force = "--force" in sys.argv

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS kline (
        code TEXT, date TEXT,
        open REAL, high REAL, low REAL, close REAL,
        volume REAL, amount REAL, turn REAL, pctChg REAL,
        PRIMARY KEY (code, date)
    )""")

    if force:
        conn.execute("DELETE FROM kline")
        conn.commit()
        print("已清空 SQLite 数据库")

    # 统计已导入的股票数
    existing = set(
        row[0] for row in conn.execute("SELECT DISTINCT code FROM kline").fetchall()
    )
    print(f"SQLite 已有 {len(existing)} 只股票的数据")

    parquet_files = sorted(CACHE_DIR.glob("*.parquet"))
    total = len(parquet_files)
    imported = 0
    skipped = 0

    for i, pf in enumerate(parquet_files):
        code = pf.stem  # e.g. sh.600519

        if code in existing and not force:
            skipped += 1
            continue

        try:
            df = pd.read_parquet(pf)
            if df.empty:
                continue
        except Exception:
            continue

        rows = []
        for _, r in df.iterrows():
            rows.append((
                code,
                str(r["date"]),
                float(r.get("open", 0)), float(r.get("high", 0)),
                float(r.get("low", 0)), float(r.get("close", 0)),
                float(r.get("volume", 0)), float(r.get("amount", 0)),
                float(r.get("turn", 0)), float(r.get("pctChg", 0)),
            ))

        conn.executemany(
            "INSERT OR REPLACE INTO kline VALUES (?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
        imported += 1

        if (i + 1) % 200 == 0 or (i + 1) == total:
            conn.commit()
            print(f"  进度 {i+1}/{total}  已导入 {imported}  跳过已有 {skipped}", flush=True)

    conn.commit()
    conn.close()

    # 最终统计
    conn2 = sqlite3.connect(str(DB_PATH))
    total_rows = conn2.execute("SELECT COUNT(*) FROM kline").fetchone()[0]
    total_stocks = conn2.execute("SELECT COUNT(DISTINCT code) FROM kline").fetchone()[0]
    db_size = DB_PATH.stat().st_size / 1024 / 1024
    conn2.close()

    print("\n完成！")
    print(f"  股票数: {total_stocks}")
    print(f"  总行数: {total_rows:,}")
    print(f"  数据库: ~{db_size:.1f} MB")
    print(f"  路径:   {DB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
