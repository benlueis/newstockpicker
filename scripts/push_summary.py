"""读取当日三策略 CSV，汇总后通过 Bark 推送到 iPhone。"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from notify import send  # noqa: E402

DATA_DIR = ROOT / "data"

STRATEGIES = [
    ("低位横盘突破", "breakout"),
    ("市场龙头", "dragon_leader"),
    ("横盘向上突破", "sideways_breakout"),
    ("回踩5日线", "pullback_ma5"),
]


def format_row(row: pd.Series) -> str:
    name = row.get("名称", "")
    code = row.get("代码", "")
    bits = [f"{name}({code.split('.')[-1] if isinstance(code, str) else code})"]
    if "leader_score" in row.index and pd.notna(row.get("leader_score")):
        bits.append(f"分{float(row['leader_score']):.0f}")
    if "vol_ratio" in row.index and pd.notna(row.get("vol_ratio")):
        bits.append(f"量{float(row['vol_ratio']):.1f}")
    if "breakout_pct" in row.index and pd.notna(row.get("breakout_pct")):
        bits.append(f"破{float(row['breakout_pct']):.1f}%")
    elif "pct_chg" in row.index and pd.notna(row.get("pct_chg")):
        bits.append(f"涨{float(row['pct_chg']):.1f}%")
    if "position_120d" in row.index and pd.notna(row.get("position_120d")):
        bits.append(f"位{float(row['position_120d']):.2f}")
    elif "position" in row.index and pd.notna(row.get("position")):
        bits.append(f"位{float(row['position']):.2f}")
    return " ".join(bits)


def _latest_csv(prefix: str) -> Path | None:
    paths = sorted(DATA_DIR.glob(f"{prefix}_*.csv"))
    return paths[-1] if paths else None


def build_curated(tag: str) -> str:
    """从龙头+横盘 CSV 中筛选最具确定性的 Top 5"""
    lines = ["【🔥 最具确定性精选】"]

    path_d = DATA_DIR / f"dragon_leader_{tag}.csv"
    if path_d.exists():
        df = pd.read_csv(path_d)
        if not df.empty and "leader_score" in df.columns:
            df = df[(df["ret_5d"] <= 15) & (df["pct_chg"] <= 8.5)].copy()
            df["final_score"] = df["leader_score"] + df["leader_type"].apply(
                lambda x: 10 if "板块龙头" in str(x) else 0
            )
            df = df.sort_values("final_score", ascending=False)
            top = df.head(5)
            for _, r in top.iterrows():
                code = r["代码"].split(".")[-1]
                dual = "🔥" if "板块龙头" in str(r.get("leader_type", "")) else ""
                lines.append(
                    f"{dual}{r['名称']}({code}) "
                    f"分{r['final_score']:.0f} "
                    f"20日{r['ret_20d']:.0f}% "
                    f"5日{r['ret_5d']:.1f}% "
                    f"量{r['vol_ratio']:.1f}"
                )

    path_s = DATA_DIR / f"sideways_breakout_{tag}.csv"
    if path_s.exists():
        df = pd.read_csv(path_s)
        if not df.empty:
            df = df.sort_values("vol_ratio", ascending=False)
            top = df.head(3)
            if len(top) > 0:
                lines.append("─ 横盘突破 ─")
            for _, r in top.iterrows():
                code = r["代码"].split(".")[-1]
                lines.append(
                    f"  {r['名称']}({code}) "
                    f"破{r['breakout_pct']:.1f}% "
                    f"量{r['vol_ratio']:.1f}"
                )

    if len(lines) == 1:
        return "【🔥 最具确定性精选】无信号"
    return "\n".join(lines)


def build_section(label: str, prefix: str, tag: str) -> str:
    path = DATA_DIR / f"{prefix}_{tag}.csv"
    if not path.exists():
        # 当日文件不存在时回退到最近一次扫描结果（用于盘前提醒）
        latest = _latest_csv(prefix)
        if latest is None:
            return f"【{label}】(无文件)"
        path = latest
    df = pd.read_csv(path)
    if df.empty or "代码" not in df.columns:
        return f"【{label}】无信号"

    # 龙头按 leader_score 排序，其余按 vol_ratio
    if "leader_score" in df.columns:
        df = df.sort_values("leader_score", ascending=False)
    elif "vol_ratio" in df.columns:
        df = df.sort_values("vol_ratio", ascending=False)

    lines = [f"【{label}】共{len(df)}只"]
    lines.extend(format_row(r) for _, r in df.iterrows())
    return "\n".join(lines)


def main() -> int:
    tag = datetime.today().strftime("%Y%m%d")
    today = datetime.today().strftime("%Y-%m-%d")

    # 允许通过参数指定 title 前缀（盘前提醒 vs 收盘扫描）
    title_prefix = sys.argv[1] if len(sys.argv) > 1 else "选股扫描"

    curated = build_curated(tag)
    sections = [build_section(label, prefix, tag) for label, prefix in STRATEGIES]
    body = curated + "\n\n" + "\n\n".join(sections)
    title = f"{today} {title_prefix}"

    print(title)
    print(body)
    send(title, body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
