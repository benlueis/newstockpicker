"""策略共用：行情拉取（缓存优先，腾讯数据源）、交易日判断"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from cache_manager import load as _cache_load  # noqa: E402

logger = logging.getLogger(__name__)

INDEX_CODE = "sh.000300"
SHANGHAI_INDEX = "sh.000001"


def merge_params(params: dict | None, defaults: dict) -> dict:
    """合并 params 与 defaults，用户 params 优先。各策略共用。"""
    if params is None:
        return dict(defaults)
    merged = dict(defaults)
    merged.update(params)
    return merged


def get_stock_data(code: str, days: int = 300) -> pd.DataFrame:
    """从本地缓存读取 K 线数据（缓存由 cache_manager 维护，默认腾讯数据源）。"""
    return _cache_load(code, days=days)


def get_index_data(days: int = 300) -> pd.DataFrame:
    return get_stock_data(INDEX_CODE, days=days)


def is_trading_day(today: str | None = None) -> bool:
    """
    判断是否为交易日。

    策略：
    1. 周末直接排除
    2. 检查上证指数缓存中是否有当日数据
    3. 缓存不可用时：当天默认 True（可能是新交易日），历史日期默认 False
    """
    today = today or datetime.today().strftime("%Y-%m-%d")
    dt = datetime.strptime(today, "%Y-%m-%d")

    if dt.weekday() >= 5:
        return False

    try:
        df = get_stock_data(SHANGHAI_INDEX, days=5)
        if not df.empty:
            last_date = str(df["date"].iloc[-1])[:10]
            return last_date >= today
    except Exception as e:
        logger.warning(f"[common] 检查交易日时获取上证指数数据失败: {e}")

    # 缓存不可用：当天默认 True（不阻塞扫描），历史日期默认 False
    return today == datetime.today().strftime("%Y-%m-%d")


def load_industry_map(cache_path: Path | None = None) -> dict[str, str]:
    """
    股票 -> 行业名称（从本地缓存读取）。

    缓存有效期 90 天。缓存不存在时返回空字典。
    """
    cache_path = cache_path or ROOT / "data" / "industry_map.csv"
    if cache_path.exists():
        try:
            age_days = (datetime.now().timestamp() - cache_path.stat().st_mtime) / 86400
            if age_days < 90:
                df = pd.read_csv(cache_path, dtype=str)
                return dict(zip(df["code"], df["industry"]))
            else:
                logger.warning(f"[common] 行业映射缓存已过期 ({age_days:.1f} 天): {cache_path}")
        except Exception as e:
            logger.error(f"[common] 加载行业映射缓存失败: {e}")
    else:
        logger.warning(f"[common] 行业映射缓存不存在: {cache_path}")

    return {}
