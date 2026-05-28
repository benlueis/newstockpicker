"""本地缓存管理：SQLite / Parquet 双后端 + 多数据源。

接口（与后端无关）：
    load(code, days)       -> DataFrame
    full_download(code)    -> DataFrame
    incremental_update(code) -> DataFrame

数据源（环境变量 DATA_SOURCE）：
    tencent   (默认) — 腾讯行情 API，免费且实时
    baostock  — baostock.com，免费但有延迟
    pytdx     — 直连通达信服务器，免费且实时

存储后端（环境变量 CACHE_BACKEND）：
    sqlite    (默认) — data/cache/stocks.db
    parquet   — data/cache/{code}.parquet
"""
from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = CACHE_DIR / "stocks.db"

FIELDS = "date,open,high,low,close,volume,amount,turn,pctChg"
NUMERIC_COLS = ["open", "high", "low", "close", "volume", "amount", "turn", "pctChg"]

BACKEND = os.environ.get("CACHE_BACKEND", "sqlite").lower()
DATA_SOURCE = os.environ.get("DATA_SOURCE", "tencent").lower()

# ── 通达信服务器列表（pytdx 用）─────────────────────
TDX_SERVERS = [
    ("119.147.212.81", 7709),
    ("60.191.117.39", 7709),
    ("115.29.207.53", 7709),
    ("218.75.126.173", 7709),
    ("120.198.46.189", 7709),
]

# ── 数据获取层（多数据源）─────────────────────────


def _bs_fetch(code: str, start: str, end: str) -> pd.DataFrame:
    """通过 baostock 拉取 K 线（懒加载 bs 模块）"""
    import baostock as bs
    rs = bs.query_history_k_data_plus(
        code, FIELDS,
        start_date=start, end_date=end,
        frequency="d", adjustflag="2",
    )
    data = []
    while rs.error_code == "0" and rs.next():
        data.append(rs.get_row_data())
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data, columns=rs.fields)
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    return df.dropna(subset=["close"]).reset_index(drop=True)


def _tdx_fetch(code: str, start: str, end: str) -> pd.DataFrame:
    """通过 pytdx（通达信）拉取 K 线"""
    from pytdx.hq import TdxHq_API

    m = re.match(r"^(sh|sz)\.(\d{6})$", code)
    if not m:
        return pd.DataFrame()
    market = 1 if m.group(1) == "sh" else 0
    code_num = m.group(2)

    day_count = (datetime.strptime(end, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")).days + 30

    for ip, port in TDX_SERVERS:
        api = TdxHq_API()
        try:
            api.connect(ip, port)
            df = api.get_security_bars(9, market, code_num, 0, max(day_count, 5))
            api.disconnect()
            if df is not None and not df.empty:
                break
        except Exception:
            try:
                api.disconnect()
            except Exception:
                pass
            continue
    else:
        return pd.DataFrame()

    df = df.rename(columns={"year": "_y", "month": "_m", "day": "_d"})
    df["date"] = pd.to_datetime(
        df["_y"].astype(str) + "-" + df["_m"].astype(str) + "-" + df["_d"].astype(str)
    )
    for col in ["open", "high", "low", "close", "volume", "amount"]:
        df[col] = df[col].astype(float)
    df["turn"] = 0.0
    df["pctChg"] = df["close"].pct_change() * 100

    df = df[(df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))]
    df = df.sort_values("date").reset_index(drop=True)
    return df[["date", "open", "high", "low", "close", "volume", "amount", "turn", "pctChg"]]


def _tencent_fetch(code: str, start: str, end: str) -> pd.DataFrame:
    """通过腾讯行情 API 拉取复权日 K 线"""
    import requests

    m = re.match(r"^(sh|sz)\.(\d{6})$", code)
    if not m:
        return pd.DataFrame()
    code_tdx = m.group(1) + m.group(2)

    # 注意：腾讯行情 API 仅支持 HTTP，不支持 HTTPS
    # 这是已知的安全限制，金融数据本身非敏感信息
    url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code_tdx},day,,,400,qfq"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
    except Exception:
        return pd.DataFrame()

    try:
        rows = data["data"][code_tdx]["qfqday"]
    except (KeyError, TypeError):
        try:
            rows = data["data"][code_tdx]["day"]
        except (KeyError, TypeError):
            return pd.DataFrame()

    records = []
    for row in rows:
        if not row or len(row) < 6:
            continue
        d, o, c, h, l, v = row[0], float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])
        if not (start <= d <= end):
            continue
        # 成交量单位为手(1手=100股)，估算成交额 ≈ 均价 × 股数
        avg_price = (o + h + l + c) / 4
        amount_est = v * 100 * avg_price
        records.append({
            "date": pd.Timestamp(d), "open": o, "high": h,
            "low": l, "close": c, "volume": v * 100,  # 转为股
            "amount": float(round(amount_est, 2)),
            "turn": 0.0, "pctChg": 0.0,
        })

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records).sort_values("date").reset_index(drop=True)
    df["pctChg"] = df["close"].pct_change() * 100
    df["pctChg"] = df["pctChg"].fillna(0.0)
    return df


def fetch_intraday_bar(code: str) -> pd.DataFrame:
    """拉取今日分钟线，合成为一条日K线（用于盘中扫描）。"""
    import requests

    m = re.match(r"^(sh|sz)\.(\d{6})$", code)
    if not m:
        return pd.DataFrame()
    code_tdx = m.group(1) + m.group(2)

    url = f"http://ifzq.gtimg.cn/appstock/app/kline/mkline?param={code_tdx},m5,,,80"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        bars = data["data"][code_tdx]["m5"]
    except Exception:
        return pd.DataFrame()

    if not bars:
        return pd.DataFrame()

    # 格式: [datetime, open, close, high, low, volume, {}, pct_chg]
    opens, highs, lows, closes, volumes = [], [], [], [], []
    today_str = datetime.today().strftime("%Y-%m-%d")
    for b in bars:
        if len(b) < 6:
            continue
        d = b[0][:8]
        if d != today_str.replace("-", ""):
            continue
        try:
            o, c, h, l, v = float(b[1]), float(b[2]), float(b[3]), float(b[4]), float(b[5])
        except (ValueError, TypeError):
            continue
        opens.append(o)
        highs.append(h)
        lows.append(l)
        closes.append(c)
        volumes.append(v * 100)  # 手 → 股

    if not closes:
        return pd.DataFrame()

    bar_open = opens[0]
    bar_high = max(highs)
    bar_low = min(lows)
    bar_close = closes[-1]
    bar_volume = sum(volumes)
    avg_price = (bar_open + bar_high + bar_low + bar_close) / 4
    bar_amount = bar_volume * avg_price
    bar_pct = round((bar_close / closes[0] - 1) * 100, 2) if closes[0] else 0

    return pd.DataFrame([{
        "date": pd.Timestamp(today_str),
        "open": bar_open,
        "high": bar_high,
        "low": bar_low,
        "close": bar_close,
        "volume": bar_volume,
        "amount": float(round(bar_amount, 2)),
        "turn": 0.0,
        "pctChg": bar_pct,
    }])


def _fetch_from_source(code: str, start: str, end: str) -> pd.DataFrame:
    """按 DATA_SOURCE 路由到具体数据源"""
    if DATA_SOURCE == "tencent":
        return _tencent_fetch(code, start, end)
    if DATA_SOURCE == "pytdx":
        return _tdx_fetch(code, start, end)
    return _bs_fetch(code, start, end)

# ── SQLite 后端 ──────────────────────────────────


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS kline (
        code TEXT, date TEXT,
        open REAL, high REAL, low REAL, close REAL,
        volume REAL, amount REAL, turn REAL, pctChg REAL,
        PRIMARY KEY (code, date)
    )""")
    return conn


def _sqlite_batch_upsert(conn: sqlite3.Connection, code: str, df: pd.DataFrame) -> None:
    """批量插入或更新 K 线数据到 SQLite"""
    if df.empty:
        return

    # 准备数据：添加 code 列并转换格式
    df_insert = df.copy()
    df_insert["code"] = code
    df_insert["date"] = df_insert["date"].astype(str)

    # 确保所有数值列都是 float 类型
    numeric_cols = ["open", "high", "low", "close", "volume", "amount", "turn", "pctChg"]
    for col in numeric_cols:
        if col in df_insert.columns:
            df_insert[col] = pd.to_numeric(df_insert[col], errors="coerce").fillna(0.0)

    # 选择需要的列并转换为元组列表
    columns = ["code", "date", "open", "high", "low", "close", "volume", "amount", "turn", "pctChg"]
    rows = df_insert[columns].values.tolist()

    conn.executemany(
        "INSERT OR REPLACE INTO kline VALUES (?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()


def _sqlite_load(code: str, days: int = 300) -> pd.DataFrame:
    conn = _get_conn()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM kline WHERE code = ? ORDER BY date DESC LIMIT ?",
            conn, params=(code, days),
        )
        if df.empty:
            return df
        df = df.iloc[::-1].reset_index(drop=True)
        df["date"] = pd.to_datetime(df["date"])
        return df
    finally:
        conn.close()


def _sqlite_full_download(code: str, days: int = 400) -> pd.DataFrame:
    conn = _get_conn()
    try:
        end = datetime.today().strftime("%Y-%m-%d")
        start = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
        df = _fetch_from_source(code, start, end)
        if df.empty:
            return df
        _sqlite_batch_upsert(conn, code, df)
        return df
    finally:
        conn.close()


def _sqlite_incremental_update(code: str) -> pd.DataFrame:
    conn = _get_conn()
    try:
        cur = conn.execute("SELECT MAX(date) FROM kline WHERE code = ?", (code,))
        row = cur.fetchone()
        last_date = pd.Timestamp(row[0]) if row and row[0] else None
        today = pd.Timestamp(datetime.today().strftime("%Y-%m-%d"))

        if last_date is not None and last_date >= today:
            return _sqlite_load(code)

        start = (last_date + timedelta(days=1)).strftime("%Y-%m-%d") if last_date else (
            datetime.today() - timedelta(days=400)
        ).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")

        df = _fetch_from_source(code, start, end)
        if df.empty:
            return _sqlite_load(code)

        _sqlite_batch_upsert(conn, code, df)

        # 基于 SQLite 全量数据重算最新两天的 pctChg
        pivots = conn.execute(
            "SELECT date, close FROM kline WHERE code=? ORDER BY date DESC LIMIT 2",
            (code,),
        ).fetchall()
        if len(pivots) == 2:
            yesterday_close = pivots[1][1]
            today_close = pivots[0][1]
            if yesterday_close and today_close and yesterday_close > 0:
                pct = round((today_close / yesterday_close - 1) * 100, 4)
                conn.execute(
                    "UPDATE kline SET pctChg=? WHERE code=? AND date=?",
                    (pct, code, pivots[0][0]),
                )
                conn.commit()

        return _sqlite_load(code)
    finally:
        conn.close()


# ── Parquet 后端（原逻辑保持不变）───────────────


def _cache_path(code: str) -> Path:
    return CACHE_DIR / f"{code}.parquet"


def _parquet_full_download(code: str, days: int = 400) -> pd.DataFrame:
    end = datetime.today().strftime("%Y-%m-%d")
    start = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    df = _fetch_from_source(code, start, end)
    if not df.empty:
        df.to_parquet(_cache_path(code), index=False)
    return df


def _parquet_incremental_update(code: str) -> pd.DataFrame:
    path = _cache_path(code)
    if not path.exists():
        return _parquet_full_download(code)

    df = pd.read_parquet(path)
    if df.empty:
        return _parquet_full_download(code)

    last_date = pd.Timestamp(df["date"].max())
    today = pd.Timestamp(datetime.today().strftime("%Y-%m-%d"))

    if last_date >= today:
        return df

    start = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")
    new_data = _fetch_from_source(code, start, end)

    if not new_data.empty:
        df = pd.concat([df, new_data], ignore_index=True)
        df = df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
        df.to_parquet(path, index=False)
    return df


def _parquet_load(code: str, days: int = 300) -> pd.DataFrame:
    path = _cache_path(code)
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    if df.empty:
        return df
    return df.tail(days).reset_index(drop=True)


# ── 公开接口（自动路由）────────────────────────


def load(code: str, days: int = 300) -> pd.DataFrame:
    if BACKEND == "sqlite":
        return _sqlite_load(code, days)
    return _parquet_load(code, days)


def full_download(code: str, days: int = 400) -> pd.DataFrame:
    if BACKEND == "sqlite":
        return _sqlite_full_download(code, days)
    return _parquet_full_download(code, days)


def incremental_update(code: str) -> pd.DataFrame:
    if BACKEND == "sqlite":
        return _sqlite_incremental_update(code)
    return _parquet_incremental_update(code)
