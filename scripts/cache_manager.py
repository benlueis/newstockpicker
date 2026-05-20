"""本地 parquet 缓存管理：全量下载 / 增量更新 / 读取。"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import baostock as bs
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

FIELDS = "date,open,high,low,close,volume,amount,turn,pctChg"
NUMERIC_COLS = ["open", "high", "low", "close", "volume", "amount", "turn", "pctChg"]


def _cache_path(code: str) -> Path:
    return CACHE_DIR / f"{code}.parquet"


def _fetch(code: str, start: str, end: str) -> pd.DataFrame:
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


def full_download(code: str, days: int = 400) -> pd.DataFrame:
    end = datetime.today().strftime("%Y-%m-%d")
    start = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    df = _fetch(code, start, end)
    if not df.empty:
        df.to_parquet(_cache_path(code), index=False)
    return df


def incremental_update(code: str) -> pd.DataFrame:
    path = _cache_path(code)
    if not path.exists():
        return full_download(code)

    df = pd.read_parquet(path)
    if df.empty:
        return full_download(code)

    last_date = pd.Timestamp(df["date"].max())
    today = pd.Timestamp(datetime.today().strftime("%Y-%m-%d"))

    if last_date >= today:
        return df

    start = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")
    new_data = _fetch(code, start, end)

    if not new_data.empty:
        df = pd.concat([df, new_data], ignore_index=True)
        df = df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
        df.to_parquet(path, index=False)
    return df


def load(code: str, days: int = 300) -> pd.DataFrame:
    path = _cache_path(code)
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    if df.empty:
        return df
    return df.tail(days).reset_index(drop=True)
