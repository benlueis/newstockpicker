"""策略共用：行情拉取、交易日判断"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import baostock as bs
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INDEX_CODE = "sh.000300"  # 沪深300，用于相对强度


def get_stock_data(code: str, days: int = 300) -> pd.DataFrame:
    """拉取单只股票前复权日 K"""
    end = datetime.today().strftime("%Y-%m-%d")
    start = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")

    rs = bs.query_history_k_data_plus(
        code,
        "date,open,high,low,close,volume,amount,turn,pctChg",
        start_date=start,
        end_date=end,
        frequency="d",
        adjustflag="2",
    )
    data = []
    while rs.error_code == "0" and rs.next():
        data.append(rs.get_row_data())

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data, columns=rs.fields)
    for col in ["open", "high", "low", "close", "volume", "amount", "turn", "pctChg"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    return df.dropna(subset=["close"]).reset_index(drop=True)


def get_index_data(days: int = 300) -> pd.DataFrame:
    return get_stock_data(INDEX_CODE, days=days)


def is_trading_day(today: str | None = None) -> bool:
    today = today or datetime.today().strftime("%Y-%m-%d")
    rs = bs.query_trade_dates(start_date=today, end_date=today)
    while rs.error_code == "0" and rs.next():
        row = rs.get_row_data()
        if len(row) >= 2 and row[1] == "1":
            return True
    return False


def load_industry_map(cache_path: Path | None = None) -> dict[str, str]:
    """
    股票 -> 行业名称（证监会行业，去掉字母代码前缀）
    结果缓存 7 天，避免每次全量拉取
    """
    import re

    cache_path = cache_path or ROOT / "data" / "industry_map.csv"
    if cache_path.exists():
        age_days = (datetime.now().timestamp() - cache_path.stat().st_mtime) / 86400
        if age_days < 7:
            df = pd.read_csv(cache_path, dtype=str)
            return dict(zip(df["code"], df["industry"]))

    rows = []
    rs = bs.query_stock_industry(code="", date="")
    while rs.error_code == "0" and rs.next():
        row = rs.get_row_data()
        if len(row) < 4:
            continue
        code, industry = row[1], row[3]
        if not industry:
            continue
        m = re.match(r"^[A-Z]\d+(.+)$", industry)
        name = m.group(1) if m else industry
        rows.append({"code": code, "industry": name})

    df = pd.DataFrame(rows).drop_duplicates("code")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_path, index=False)
    return dict(zip(df["code"], df["industry"]))
