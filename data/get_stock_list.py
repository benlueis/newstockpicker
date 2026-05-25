"""
生成 / 更新股票池 CSV（从本地 parquet 缓存读取，近乎秒级）

用法：
    python data/get_stock_list.py          # 7 天内已生成则跳过
    python data/get_stock_list.py --force  # 强制重新生成
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import baostock as bs
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

OUTPUT = ROOT / "data" / "stock_list.csv"
FRESH_DAYS = 7  # stock_list.csv 缓存有效天数

# 过滤参数
MIN_CLOSE = 6
MAX_CLOSE = 300
MIN_MKTCAP = 50  # 亿元


def _get_stock_basic() -> pd.DataFrame:
    """获取主板 non-ST 股票基础列表（快速 baostock 查询）"""
    rs = bs.query_stock_basic(code_name="")
    data = []
    while rs.error_code == "0" and rs.next():
        data.append(rs.get_row_data())

    df = pd.DataFrame(data, columns=rs.fields)
    df = df[df["code"].str.match(r"^(sh\.6[^8]|sz\.00)")]
    df = df[df["type"] == "1"]
    df = df[~df["code_name"].str.contains("ST|退", na=False)]
    df = df[["code", "code_name"]].reset_index(drop=True)
    print(f"主板非ST股票: {len(df)} 只")
    return df


def _compute_mktcap(close: float, amount: float, turn: float) -> bool:
    """计算并判断是否满足股价/市值过滤"""
    if not (close > 0 and amount > 0 and turn > 0):
        return False
    if not (MIN_CLOSE <= close <= MAX_CLOSE):
        return False
    mktcap = amount / turn * 100 / 1e8
    return mktcap >= MIN_MKTCAP


def _regenerate() -> None:
    """从 SQLite 批量读取，过滤后输出 CSV"""
    df_basic = _get_stock_basic()

    results: list[dict] = []

    # ── 一次 SQL 查询拿到所有股票最新 5 条数据 ──
    from sqlite3 import connect as _sqlite_conn
    db_path = ROOT / "data" / "cache" / "stocks.db"
    codes_in_db: set[str] = set()

    if db_path.exists():
        conn = _sqlite_conn(str(db_path))
        try:
            all_codes = [r[0] for r in conn.execute("SELECT DISTINCT code FROM kline").fetchall()]
            codes_in_db = set(all_codes)
            print(f"SQLite 中已有 {len(codes_in_db)} 只股票数据")

            placeholders = ",".join("?" for _ in all_codes)
            bulk = pd.read_sql_query(
                f"""SELECT code, date, close, amount, turn
                    FROM kline
                    WHERE code IN ({placeholders})
                    ORDER BY code, date DESC
                """,
                conn, params=all_codes,
            )
            for code, grp in bulk.groupby("code"):
                for _, r in grp.head(5).iterrows():
                    c, a, t = r["close"], r["amount"], r["turn"]
                    if _compute_mktcap(c, a, t):
                        mc = a / t * 100 / 1e8
                        results.append({"code": code, "close": round(c, 2), "mktcap": round(mc, 2)})
                        break
        finally:
            conn.close()

    # ── 不在 SQLite 中的股票，在线补查 ──
    missing = [c for c in df_basic["code"] if c not in codes_in_db]
    if missing:
        print(f"  在线补查 {len(missing)} 只（不在 SQLite 中）...")
        from datetime import datetime, timedelta

        for code in missing:
            try:
                end = datetime.today().strftime("%Y-%m-%d")
                start = (datetime.today() - timedelta(days=10)).strftime("%Y-%m-%d")
                rs = bs.query_history_k_data_plus(
                    code, "date,close,amount,turn",
                    start_date=start, end_date=end,
                    frequency="d", adjustflag="3",
                )
                rows = []
                while rs.error_code == "0" and rs.next():
                    rows.append(rs.get_row_data())
                valid = []
                for rec in rows[-5:]:
                    try:
                        c, a, t = float(rec[1]), float(rec[2]), float(rec[3])
                        if c > 0 and a > 0 and t > 0:
                            valid.append((c, a, t))
                    except (ValueError, IndexError):
                        continue
                if valid:
                    cp = valid[-1][0]
                    mc = sum(a / t * 100 / 1e8 for _, a, t in valid) / len(valid)
                    if MIN_CLOSE <= cp <= MAX_CLOSE and mc >= MIN_MKTCAP:
                        results.append({"code": code, "close": round(cp, 2), "mktcap": round(mc, 2)})
            except Exception:
                continue

    # 合并名称 & 输出
    name_map = dict(zip(df_basic["code"], df_basic["code_name"]))
    out = pd.DataFrame(results)
    if out.empty:
        print("没有任何股票满足过滤条件！")
        return

    out["code_name"] = out["code"].map(name_map)
    out = out[["code", "code_name", "close", "mktcap"]]
    out.to_csv(OUTPUT, index=False)

    print(f"\n最终股票池: {len(out)} 只")
    print(f"股价范围: {out['close'].min():.0f} ~ {out['close'].max():.0f} 元")
    print(f"市值范围: {out['mktcap'].min():.1f} ~ {out['mktcap'].max():.1f} 亿元")
    print(out.head(10).to_string(index=False))


def main() -> int:
    force = "--force" in sys.argv

    if not force and OUTPUT.exists():
        age = datetime.now().timestamp() - OUTPUT.stat().st_mtime
        if age < FRESH_DAYS * 86400:
            days_ago = age / 86400
            print(f"stock_list.csv 是 {days_ago:.1f} 天前生成的，跳过（加 --force 强制刷新）")
            df = pd.read_csv(OUTPUT)
            print(f"当前股票池: {len(df)} 只")
            return 0

    bs.login()
    try:
        _regenerate()
        return 0
    finally:
        bs.logout()


if __name__ == "__main__":
    raise SystemExit(main())
