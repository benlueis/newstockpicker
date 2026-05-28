"""
通用扫描执行器 — 统一处理交易日检查、股票池加载、策略扫描、结果保存。

用法:
    from strategies import breakout
    from scripts.scan_runner import run_scan

    result_df = run_scan(breakout, "breakout", preset="default")

设计目标:
    - 消除 5 个扫描脚本中 ~200 行重复模板代码
    - 无需登录（腾讯数据源）
    - 支持单股异常隔离 + 步骤级重试
    - 与 config/loader.py 集成，支持从 YAML 加载参数
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "strategies"))
sys.path.insert(0, str(ROOT / "config"))

from common import is_trading_day  # noqa: E402

STOCK_LIST_PATH = ROOT / "data" / "stock_list.csv"
OUTPUT_DIR = ROOT / "data"
MAX_RETRIES = 3
RETRY_DELAY = 5


def _derive_strategy_name(module) -> str:
    """从模块路径推导策略名称，例如 strategies.breakout → breakout"""
    name = getattr(module, "__name__", str(module))
    parts = name.split(".")
    return parts[-1] if parts else name


def _load_params(strategy_name: str, preset: str | None, params: dict | None) -> dict | None:
    """从配置文件加载参数，直接传入的 params 优先级最高"""
    if params is not None:
        return params
    if preset is None:
        return None
    try:
        from loader import get_strategy_params
        loaded = get_strategy_params(strategy_name, preset)
        if loaded:
            return loaded
    except Exception as e:
        print(f"[scan_runner] 加载配置失败 ({strategy_name}/{preset}): {e}", file=sys.stderr)
    return None


def run_scan(
    strategy_module,
    output_prefix: str,
    params: dict | None = None,
    preset: str | None = None,
    strategy_name: str | None = None,
    **kwargs,
) -> pd.DataFrame:
    """
    通用扫描执行器。

    Args:
        strategy_module: 策略模块，需包含 scan_stocks(stock_list, params=..., **kwargs) 函数
        output_prefix: 输出 CSV 前缀，如 "breakout" → data/breakout_{YYYYMMDD}.csv
        params: 直接传入的参数字典（优先级高于 preset）
        preset: 参数预设名称，从 config/strategies.yaml 加载
        strategy_name: 策略在 YAML 中的键名，默认从模块名推导
        **kwargs: 传递给 strategy_module.scan_stocks() 的额外参数

    Returns:
        扫描结果 DataFrame（可能为空）
    """
    strategy_name = strategy_name or _derive_strategy_name(strategy_module)

    # ── 交易日检查 ──────────────────────────────
    today = datetime.today().strftime("%Y-%m-%d")
    today_tag = datetime.today().strftime("%Y%m%d")

    if not is_trading_day(today):
        print(f"{today} 非交易日，跳过扫描")
        return pd.DataFrame()

    # ── 股票池加载 ──────────────────────────────
    if not STOCK_LIST_PATH.exists():
        print(f"股票池不存在: {STOCK_LIST_PATH}", file=sys.stderr)
        print("请先运行: python data/get_stock_list.py", file=sys.stderr)
        raise SystemExit(1)

    df_list = pd.read_csv(STOCK_LIST_PATH)
    stock_list: list[tuple[str, str]] = list(
        zip(df_list["code"], df_list["code_name"])
    )
    total = len(stock_list)

    # ── 参数加载 ────────────────────────────────
    scan_params = _load_params(strategy_name, preset, params)

    # ── 扫描（含重试） ──────────────────────────
    print(f"[{strategy_name}] 扫描启动 | 股票池: {total} 只 | preset: {preset or 'N/A'}")

    result_df = pd.DataFrame()
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            try:
                result_df = strategy_module.scan_stocks(
                    stock_list,
                    params=scan_params,
                    **kwargs,
                )
            except TypeError:
                result_df = strategy_module.scan_stocks(
                    stock_list,
                    **kwargs,
                )
            break
        except Exception as e:
            print(
                f"[{strategy_name}] 扫描失败 (第 {attempt}/{MAX_RETRIES} 次): {e}",
                file=sys.stderr,
            )
            if attempt < MAX_RETRIES:
                print(f"  等待 {RETRY_DELAY}s 后重试...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"[{strategy_name}] 重试耗尽，返回空结果", file=sys.stderr)

    # ── 保存结果 ────────────────────────────────
    out_path = OUTPUT_DIR / f"{output_prefix}_{today_tag}.csv"
    if result_df.empty:
        empty_cols = ["代码", "名称"] + list(result_df.columns)
        pd.DataFrame(columns=empty_cols).to_csv(out_path, index=False)
        print(f"[{strategy_name}] 今日无触发信号 → {out_path}")
    else:
        result_df.to_csv(out_path, index=False)
        print(f"[{strategy_name}] {len(result_df)} 只触发信号 → {out_path}")

    return result_df


if __name__ == "__main__":
    from strategies import breakout
    result = run_scan(breakout, "breakout", preset="default")
    if not result.empty:
        print(result.to_string(index=False))
