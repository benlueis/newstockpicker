"""
14:45 尾盘精选策略（收盘前买入专用）

双策略 + 交叉验证 + 综合评分：
  1. 低位横盘突破（收紧参数）
  2. 回踩 5 日线企稳（收紧参数）
  一只股票同时触发两个策略时额外加分，置信度最高。

要求数据源为实时源（tencent / pytdx），否则无法拿到当日盘中数据。

v2: 不再内联策略逻辑，改为调用 breakout / pullback_ma5 原函数 + tightened params。
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "config"))
sys.path.insert(0, str(ROOT / "scripts"))

from common import get_stock_data
from breakout import check_breakout
from pullback_ma5 import check_pullback_ma5
from cache_manager import fetch_intraday_bar  # noqa: E402


# ── 尾盘收紧参数（从 YAML 加载，缺失时回退到内置值）──────
def _load_tight_params():
    """尝试从 config/strategies.yaml 加载 tight 预设，失败则用内置值"""
    try:
        from loader import get_strategy_params
        bt_tight = get_strategy_params("breakout", "tight") or {}
        pt_tight = get_strategy_params("pullback_ma5", "tight") or {}
        if bt_tight and pt_tight:
            return bt_tight, pt_tight
    except Exception:
        pass

    # 内置回退值（与 YAML 中 tight 预设一致）
    bt_tight = {
        "max_position": 0.50,
        "max_box_range": 0.08,
        "min_breakout_pct": 4.0,
        "min_vol_ratio": 2.0,
        "max_pct_chg": 9.0,
        "min_amount": 150000000,
        "max_upper_shadow_ratio": 0.4,
        "min_data_days": 120,
        "box_days": 20,
    }
    pt_tight = {
        "min_data_days": 60,
        "min_amount": 8e7,
        "max_pct_chg": 9.5,
        "min_pct_chg": -9.5,
        "trend_confirm_days": 8,
        "min_days_above_ma5": 6,
        "min_recent_gain": 0.10,
        "max_close_above_ma5_pct": 1.0,
        "min_close_below_ma5_pct": -1.0,
        "min_low_touch_ma5_ratio": 0.998,
        "max_vol_ratio": 0.85,
        "min_rebound_ratio": 0.5,
        "max_recent_drop": -5.0,
    }
    return bt_tight, pt_tight


TIGHT_BT, TIGHT_PT = _load_tight_params()

# ── 参数别名映射：YAML key → afternoon 内部名称 ────
# breakout 参数使用大写 key（与 YAML/breakout 模块一致）
_BT = TIGHT_BT
# pullback 参数使用小写 key（与 pullback_ma5 DEFAULT_PARAMS 一致）
_PT = TIGHT_PT


# ============================================================
#  收紧版评分（从返回值计算得分，替代内联逻辑）
# ============================================================

def _score_breakout_tight(r: dict) -> float:
    """对 breakout 返回结果计算收紧版得分 0-100"""
    score = 0.0
    breakout_pct = r.get("breakout_pct", 0)
    vol_ratio = r.get("vol_ratio", 0)
    position = r.get("position", 1.0)
    upper_shadow = r.get("upper_shadow", 0)
    box_range = r.get("box_range", 0)

    score += min(max((breakout_pct - _BT["min_breakout_pct"]) / 6 * 40, 0), 40)
    score += min(max((vol_ratio - _BT["min_vol_ratio"]) / 2 * 25, 0), 25)
    score += max((_BT["max_position"] - position) / 0.3 * 15, 0)
    score += max(10 - upper_shadow / _BT["max_upper_shadow_ratio"] * 10, 0)
    score += max((_BT["max_box_range"] - box_range) / _BT["max_box_range"] * 10, 0)
    return round(min(score, 100), 1)


def _score_pullback_tight(r: dict) -> float:
    """对 pullback_ma5 返回结果计算收紧版得分 0-100"""
    score = 0.0
    rebound_ratio = r.get("rebound_ratio", 0)
    vol_ratio = r.get("vol_ratio", 0)
    recent_gain_pct = r.get("recent_gain_pct", 0)
    days_above_ma5 = r.get("days_above_ma5", 0)
    close_ma5_pct = r.get("close_ma5_pct", 0)

    score += min(max((rebound_ratio - _PT["min_rebound_ratio"]) / 0.5 * 30, 0), 30)
    score += max((_PT["max_vol_ratio"] - vol_ratio) / _PT["max_vol_ratio"] * 25, 0)
    score += min(max(recent_gain_pct - _PT["min_recent_gain"] * 100, 0) / 20 * 20, 20)
    score += min(max(days_above_ma5 - _PT["min_days_above_ma5"], 0) / 2 * 15, 15)
    ma5_proximity = 1.0 - abs(close_ma5_pct) / max(
        abs(_PT["max_close_above_ma5_pct"]), abs(_PT["min_close_below_ma5_pct"])
    )
    score += max(ma5_proximity * 10, 0)
    return round(min(score, 100), 1)


# ============================================================
#  联合扫描 + 交叉打分（含降级策略）
# ============================================================

def _build_tight_results(
    breakout_hits: list[dict],
    pullback_hits: list[dict],
) -> list[dict]:
    """组装收紧版结果并交叉打分"""
    bt_codes = {r["代码"] for r in breakout_hits}
    pt_codes = {r["代码"] for r in pullback_hits}
    cross_codes = bt_codes & pt_codes

    results: list[dict] = []
    for r in breakout_hits:
        is_cross = r["代码"] in cross_codes
        results.append({
            **r,
            "tier": "tight",
            "strategy": "低位突破",
            "cross_hit": is_cross,
            "composite_score": round(r.get("score_bt", 0) + (25 if is_cross else 0), 1),
            "score_pt": None,
        })

    for r in pullback_hits:
        is_cross = r["代码"] in cross_codes
        results.append({
            **r,
            "tier": "tight",
            "strategy": "回踩企稳",
            "cross_hit": is_cross,
            "composite_score": round(r.get("score_pt", 0) + (25 if is_cross else 0), 1),
            "score_bt": None,
        })
    return results


def _score_loose_breakout(r: dict) -> float:
    """原版突破策略 → 简易评分 (0-60)"""
    score = 0.0
    vol = r.get("vol_ratio", 1.0)
    pct = r.get("breakout_pct", 0.0)
    score += min(vol * 10, 30)
    score += min(pct * 3, 20)
    score += min(r.get("box_range", 0.1) * 100, 10)
    return round(score, 1)


def _score_loose_pullback(r: dict) -> float:
    """原版回踩策略 → 简易评分 (0-60)"""
    score = 0.0
    vol = r.get("vol_ratio", 1.0)
    rebound = r.get("rebound_ratio", 0.0)
    score += max(15 - vol * 10, 0)
    score += min(rebound * 35, 25)
    gain = r.get("recent_gain_pct", 0.0)
    score += min(max(gain - 5, 0), 20)
    return round(score, 1)


def scan_stocks(
    stock_list: list[tuple[str, str]],
    top_n: int = 5,
    fallback_threshold: int = 3,
    intraday_map: dict | None = None,
) -> pd.DataFrame:
    """
    全市场扫描。

    Args:
        intraday_map: {code: DataFrame} 预取的盘中分钟线合成日K，避免逐股HTTP请求
    """
    total = len(stock_list)

    # ── 第一轮：收紧扫描 ────────────────────────
    tight_breakout: list[dict] = []
    tight_pullback: list[dict] = []

    for i, (code, name) in enumerate(stock_list):
        print(f"\r[tight]  {i+1}/{total}: {code} {name}    ", end="", flush=True)
        try:
            df = get_stock_data(code, days=400)
            if df.empty:
                continue

            # 融合盘中分钟线数据（当日实时K线）
            intraday = intraday_map.get(code) if intraday_map else fetch_intraday_bar(code)
            if intraday is not None and not intraday.empty and len(df) > 0:
                last_date = str(df["date"].iloc[-1])[:10]
                today_str = datetime.today().strftime("%Y-%m-%d")
                if str(intraday["date"].iloc[0])[:10] == today_str:
                    # 避免重复：如果已有今日数据（盘后），跳过
                    if last_date != today_str:
                        df = pd.concat([df, intraday], ignore_index=True)
                        df["pctChg"] = df["close"].pct_change() * 100
                        df["pctChg"] = df["pctChg"].fillna(0.0)

            # 调用原策略 + tightened params
            bt = check_breakout(df, params=TIGHT_BT)
            if bt["signal"]:
                bt["score_bt"] = _score_breakout_tight(bt)
                tight_breakout.append({"代码": code, "名称": name, **bt})

            pt = check_pullback_ma5(df, params=TIGHT_PT)
            if pt["signal"]:
                pt["score_pt"] = _score_pullback_tight(pt)
                tight_pullback.append({"代码": code, "名称": name, **pt})
        except Exception as e:
            print(f"\n⚠️ {code} {name}: {e}", file=sys.stderr)

    tight_total = len(tight_breakout) + len(tight_pullback)
    print(f"\n[tight]  扫描完成 → 突破 {len(tight_breakout)} | 回踩 {len(tight_pullback)}")

    results = _build_tight_results(tight_breakout, tight_pullback)

    # ── 第二轮：原版降级（仅当 tight 不够）───────
    if tight_total < fallback_threshold:
        print(f"[loose] tight 仅 {tight_total} 只 (阈值 {fallback_threshold})，降级到原版参数...")

        loose_breakout: list[dict] = []
        loose_pullback: list[dict] = []

        for i, (code, name) in enumerate(stock_list):
            print(f"\r[loose] {i+1}/{total}: {code} {name}    ", end="", flush=True)
            try:
                df = get_stock_data(code, days=400)
                if df.empty:
                    continue

                bt = check_breakout(df)  # 不传 params，使用默认值
                if bt["signal"]:
                    loose_breakout.append({"代码": code, "名称": name, **bt})

                pt = check_pullback_ma5(df)  # 不传 params
                if pt["signal"]:
                    loose_pullback.append({"代码": code, "名称": name, **pt})
            except Exception as e:
                print(f"\n⚠️ {code} {name}: {e}", file=sys.stderr)

        bt_codes = {r["代码"] for r in loose_breakout}
        pt_codes = {r["代码"] for r in loose_pullback}
        cross_codes = bt_codes & pt_codes

        for r in loose_breakout:
            is_cross = r["代码"] in cross_codes
            score = _score_loose_breakout(r) + (15 if is_cross else 0)
            results.append({
                **r,
                "tier": "loose",
                "strategy": "低位突破",
                "cross_hit": is_cross,
                "composite_score": round(score, 1),
                "score_bt": None,
                "score_pt": None,
            })

        for r in loose_pullback:
            is_cross = r["代码"] in cross_codes
            score = _score_loose_pullback(r) + (15 if is_cross else 0)
            results.append({
                **r,
                "tier": "loose",
                "strategy": "回踩企稳",
                "cross_hit": is_cross,
                "composite_score": round(score, 1),
                "score_bt": None,
                "score_pt": None,
            })

        print(f"\n[loose] 扫描完成 → 突破 {len(loose_breakout)} | 回踩 {len(loose_pullback)}")

    # ── 排序：tight 在前，同 tier 按得分降序 ─────
    def _sort_key(r: dict) -> tuple[int, float]:
        return (0 if r.get("tier") == "tight" else 1, -r.get("composite_score", 0))

    results.sort(key=_sort_key)

    seen: set[str] = set()
    deduped: list[dict] = []
    for r in results:
        if r["代码"] not in seen:
            seen.add(r["代码"])
            deduped.append(r)

    top = deduped[:top_n]

    # ── 汇总 ────────────────────────────────────
    tight_count = sum(1 for r in top if r.get("tier") == "tight")
    loose_count = sum(1 for r in top if r.get("tier") == "loose")
    print("\n=== 14:45 尾盘精选 ===")
    print(f"tight {tight_total} 只 | loose 降级补充 | 推送 Top {min(top_n, len(top))}")
    print(f"  tight: {tight_count}  loose: {loose_count}")

    return pd.DataFrame(top)
