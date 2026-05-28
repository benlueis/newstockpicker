"""
生成 / 更新股票池 CSV

用法：
    python data/get_stock_list.py          # 7 天内已生成则跳过
    python data/get_stock_list.py --force  # 强制重新生成
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import akshare as ak
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

OUTPUT = ROOT / "data" / "stock_list.csv"
FRESH_DAYS = 7

# 过滤参数
MIN_CLOSE = 6
MAX_CLOSE = 300
MIN_MKTCAP = 50  # 亿元


def _get_stock_basic() -> pd.DataFrame:
    """获取主板 non-ST 股票基础列表（通过 akshare）"""
    df = ak.stock_info_a_code_name()
    df = df.rename(columns={"code": "code", "name": "code_name"})

    # 过滤：只保留沪市主板 600-603 和深市主板 000-002
    df = df[df["code"].str.match(r"^(60[0-3]|000|001|002)\d{3}$")]
    # 排除 ST
    df = df[~df["code_name"].str.contains("ST|退", na=False)]
    df = df[["code", "code_name"]].reset_index(drop=True)

    # 转换为 sh./sz. 格式
    df["code"] = df["code"].apply(
        lambda c: f"sh.{c}" if c.startswith("60") else f"sz.{c}"
    )
    print(f"主板非ST股票: {len(df)} 只")
    return df


def _regenerate() -> None:
    """从 SQLite 批量读取，过滤后输出 CSV"""
    df_basic = _get_stock_basic()

    results: list[dict] = []

    # ── 一次 SQL 查询拿到所有股票最新数据 ──
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
                    if c > 0 and a > 0 and t > 0:
                        if MIN_CLOSE <= c <= MAX_CLOSE:
                            mc = a / t * 100 / 1e8
                            if mc >= MIN_MKTCAP:
                                results.append({"code": code, "close": round(c, 2), "mktcap": round(mc, 2)})
                                break
        finally:
            conn.close()

    # ── 不在 SQLite 中的股票，使用 akshare 在线补查 ──
    missing = [c for c in df_basic["code"] if c not in codes_in_db]
    if missing:
        print(f"  在线补查 {len(missing)} 只（不在 SQLite 中）...")
        try:
            spot = ak.stock_zh_a_spot_em()
            spot["code_raw"] = spot["代码"].apply(
                lambda c: f"sh.{c}" if c.startswith("6") else f"sz.{c}"
            )
            spot_map = {}
            for _, r in spot.iterrows():
                code = r["code_raw"]
                try:
                    close = float(r["最新价"])
                    mktcap = float(r["总市值"]) / 1e8 if pd.notna(r.get("总市值")) else None
                    if close > 0 and mktcap:
                        spot_map[code] = (close, mktcap)
                except (ValueError, KeyError):
                    continue

            for code in missing:
                if code in spot_map:
                    cp, mc = spot_map[code]
                    if MIN_CLOSE <= cp <= MAX_CLOSE and mc >= MIN_MKTCAP:
                        results.append({"code": code, "close": round(cp, 2), "mktcap": round(mc, 2)})
        except Exception as e:
            print(f"  在线补查失败: {e}")

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

    _regenerate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
