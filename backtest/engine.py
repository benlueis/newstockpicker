"""
回测引擎 — 支持对任意策略+参数组合跑历史回测。

用法:
    from backtest.engine import backtest, backtest_summary
    from breakout import check_breakout

    results = backtest(check_breakout, stock_list, "2026-01-01", "2026-05-01")
    summary = backtest_summary(results, horizon=5)
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies"))
sys.path.insert(0, str(ROOT / "scripts"))

from cache_manager import load as cache_load  # noqa: E402

logger = logging.getLogger(__name__)


def backtest(
    check_fn,
    stock_list: list[tuple[str, str]],
    start_date: str,
    end_date: str,
    params: dict | None = None,
    horizons: list[int] | None = None,
) -> pd.DataFrame:
    """
    对指定策略在历史日期范围内跑回测。

    Args:
        check_fn: 策略判断函数，签名为 check_fn(df, params=None) -> dict
        stock_list: [(code, name), ...] 股票列表
        start_date: 开始日期 "YYYY-MM-DD"
        end_date: 结束日期 "YYYY-MM-DD"
        params: 策略参数 dict
        horizons: T+N 持有期列表，默认 [1, 3, 5, 10, 20]

    Returns:
        DataFrame，列: ["代码", "名称", "信号日期", "T+1", "T+3", "T+5", "T+10", "T+20"]
    """
    if horizons is None:
        horizons = [1, 3, 5, 10, 20]

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    # 生成候选日期列表（跳过周末，避免逐日调用 is_trading_day 造成大量 cache 查询）
    trading_days: list[str] = []
    current = start
    while current <= end:
        if current.weekday() < 5:  # Mon-Fri only
            trading_days.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    if not trading_days:
        print("[backtest] 回测区间内无交易日")
        return _empty_result(horizons)

    all_signals: list[dict] = []
    total_days = len(trading_days)

    # 预加载所有股票数据到内存，避免重复磁盘读取
    stock_data_cache: dict[str, pd.DataFrame] = {}
    print(f"\n[backtest] 预加载 {len(stock_list)} 只股票数据...")
    for code, name in stock_list:
        df = cache_load(code, days=400)
        if not df.empty:
            stock_data_cache[code] = df.sort_values("date").reset_index(drop=True)
    print(f"[backtest] 预加载完成，{len(stock_data_cache)} 只股票有数据")

    for day_idx, signal_date in enumerate(trading_days):
        print(f"\r[backtest] {signal_date} ({day_idx+1}/{total_days})    ", end="", flush=True)

        for code, name in stock_list:
            try:
                # 从缓存获取数据
                df = stock_data_cache.get(code)
                if df is None or df.empty:
                    continue

                # 截断到信号日期之前（不含当日，避免未来数据泄露）
                signal_ts = pd.Timestamp(signal_date)
                df = df[df["date"] < signal_ts]
                if df.empty or len(df) < 60:
                    continue

                result = check_fn(df, params=params)
                if not result.get("signal"):
                    continue

                # 获取信号后的真实数据计算 T+N 收益
                future_df = stock_data_cache.get(code)
                if future_df is None or future_df.empty:
                    continue
                future_df = future_df[future_df["date"] > signal_ts]

                signal_close = float(df.iloc[-1]["close"])

                signal_record = {
                    "代码": code,
                    "名称": name,
                    "信号日期": signal_date,
                }

                # future_df 已按日期排序，iloc[h-1] 即信号日后第 h 根 K 线
                for h in horizons:
                    if len(future_df) >= h:
                        target_close = float(future_df.iloc[h - 1]["close"])
                        ret = round((target_close / signal_close - 1) * 100, 2)
                        signal_record[f"T+{h}"] = ret
                    else:
                        signal_record[f"T+{h}"] = None

                all_signals.append(signal_record)

            except Exception as e:
                logger.warning(f"[backtest] 处理 {code} ({name}) 时出错: {e}")
                continue

    print(f"\n[backtest] 完成，共 {len(all_signals)} 条信号")

    if not all_signals:
        return _empty_result(horizons)

    return pd.DataFrame(all_signals)


def backtest_summary(
    results: pd.DataFrame,
    horizon: int = 5,
) -> dict:
    """
    对回测结果进行汇总统计。

    Args:
        results: backtest() 返回的 DataFrame
        horizon: 统计的持有期，如 5 表示 T+5

    Returns:
        {"win_rate": 胜率%, "avg_return": 均收益%, "total_signals": 总信号数, "max_drawdown": 最大回撤%}
    """
    col = f"T+{horizon}"
    if results.empty or col not in results.columns:
        return {
            "win_rate": None,
            "avg_return": None,
            "total_signals": 0,
            "max_drawdown": None,
        }

    returns = results[col].dropna()
    total = len(returns)

    if total == 0:
        return {
            "win_rate": None,
            "avg_return": None,
            "total_signals": len(results),
            "max_drawdown": None,
        }

    win_rate = round((returns > 0).sum() / total * 100, 1)
    avg_return = round(returns.mean(), 2)

    # 计算最大回撤：假设等权买入，按信号日期顺序
    cumulative = (1 + returns / 100).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative / rolling_max - 1) * 100
    max_drawdown = round(drawdown.min(), 2)

    return {
        "win_rate": win_rate,
        "avg_return": avg_return,
        "total_signals": len(results),
        "max_drawdown": max_drawdown,
    }


def _empty_result(horizons: list[int]) -> pd.DataFrame:
    """返回空 DataFrame（有正确的列名）"""
    cols = ["代码", "名称", "信号日期"] + [f"T+{h}" for h in horizons]
    return pd.DataFrame(columns=cols)
