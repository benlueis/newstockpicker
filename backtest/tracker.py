"""
信号跟踪脚本：支持盘中实时 + 收盘后日K两种模式

用法：
    python backtest/tracker.py --signal-file data/breakout_20260511.csv
    python backtest/tracker.py --signal-file data/breakout_20260511.csv --signal-date 2026-05-11
    python backtest/tracker.py --signal-file data/breakout_20260511.csv --output-dir data/reports
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

# 模块级：确保 scripts/ 在路径中（供 get_hist_after_signal 使用）
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from cache_manager import load as cache_load  # noqa: E402

SINA_HEADERS = {"Referer": "https://finance.sina.com.cn"}


def get_realtime_prices(codes: list) -> dict:
    sina_codes = [c.replace(".", "") for c in codes]
    url = f"http://hq.sinajs.cn/list={','.join(sina_codes)}"
    resp = requests.get(url, headers=SINA_HEADERS, timeout=10)
    resp.encoding = "gbk"

    result = {}
    for line in resp.text.strip().split("\n"):
        line = line.strip()
        if not line or '=""' in line:
            continue
        try:
            code_part = line.split('"')[0].split("_")[-1]
            fields = line.split('"')[1].split(",")
            yesterday = float(fields[1])
            price = float(fields[3])
            date = fields[-3]
            time = fields[-2]
            pct_chg = round((price / yesterday - 1) * 100, 2) if yesterday else 0
            std_code = code_part[:2] + "." + code_part[2:]
            result[std_code] = {
                "price": price,
                "pct_chg": pct_chg,
                "date": date,
                "time": time,
            }
        except Exception:
            continue
    return result


def get_hist_after_signal(code: str, signal_date: str) -> list:
    """获取信号日之后的日K数据（[date, close] 格式）"""
    end = (datetime.strptime(signal_date, "%Y-%m-%d") + timedelta(days=21)).strftime("%Y-%m-%d")
    df = cache_load(code, days=200)
    if df.empty:
        return []

    df = df[(df["date"] >= pd.Timestamp(signal_date)) & (df["date"] <= pd.Timestamp(end))]
    df = df.sort_values("date")

    return [[str(d.date()), c] for d, c in zip(df["date"], df["close"])]


def ret_str(val):
    if val is None:
        return "<td style='color:#aaa;text-align:right'>-</td>"
    c = "#c0392b" if val > 0 else "#27ae60" if val < 0 else "#888"
    sign = "+" if val > 0 else ""
    return f'<td style="color:{c};font-weight:bold;text-align:right">{sign}{val}%</td>'


def sparkline(signal_close, closes):
    all_vals = [signal_close] + closes
    if len(all_vals) < 2:
        return "-"
    mn = min(all_vals)
    mx = max(all_vals)
    rng = mx - mn if mx != mn else 1
    pts = []
    for i, c in enumerate(all_vals):
        x = i * 14
        y = 30 - int((c - mn) / rng * 28)
        pts.append(f"{x},{y}")
    y0 = 30 - int((signal_close - mn) / rng * 28)
    w = (len(all_vals) - 1) * 14
    last_y = pts[-1].split(",")[1]
    stroke = "#c0392b" if closes[-1] >= signal_close else "#27ae60"
    return (
        f'<svg width="{w+8}" height="34">'
        f'<line x1="0" y1="{y0}" x2="{w}" y2="{y0}" stroke="#eee" stroke-width="1" stroke-dasharray="3,2"/>'
        f'<polyline points="{" ".join(pts)}" fill="none" stroke="{stroke}" stroke-width="1.8"/>'
        f'<circle cx="{w}" cy="{last_y}" r="2.5" fill="{stroke}"/>'
        f'</svg>'
    )


def generate_html(records, today, now_str, is_realtime, signal_date, signal_file):
    mode_tag = (
        f'<span style="background:#e74c3c;color:#fff;padding:2px 8px;'
        f'border-radius:4px;font-size:11px">● 盘中实时 {now_str}</span>'
        if is_realtime else
        '<span style="background:#27ae60;color:#fff;padding:2px 8px;'
        'border-radius:4px;font-size:11px">收盘数据</span>'
    )

    has_d5 = [r for r in records if r.get("D5") is not None]
    summary = ""
    if has_d5:
        win = sum(1 for r in has_d5 if r["D5"] > 0)
        rate = round(win / len(has_d5) * 100)
        avg_d5 = round(sum(r["D5"] for r in has_d5) / len(has_d5), 2)
        sign = "+" if avg_d5 > 0 else ""
        summary = (f"D+5 胜率 <b>{rate}%</b>（{win}/{len(has_d5)}）&nbsp;|&nbsp;"
                   f"D+5 均收益 <b>{sign}{avg_d5}%</b>&nbsp;|&nbsp;")

    rows_html = ""
    for r in records:
        cur_label = f"盘中 {r.get('rt_time','')}" if r.get("is_realtime") else "收盘"
        rows_html += f"""
        <tr>
          <td><b>{r['code']}</b></td>
          <td>{r['name']}</td>
          <td style="text-align:right">{r['signal_close']}</td>
          <td style="text-align:right">{r['position']}</td>
          <td style="text-align:right">{r['vol_ratio']}x</td>
          {ret_str(r.get('D1'))}
          {ret_str(r.get('D3'))}
          {ret_str(r.get('D5'))}
          {ret_str(r.get('current'))}
          <td style="color:#aaa;font-size:12px">{r.get('current_date','-')} {cur_label}</td>
          <td>{sparkline(r['signal_close'], r.get('closes_after',[]))}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="60">
<title>突破信号跟踪 {today}</title>
<style>
  body  {{ font-family:-apple-system,sans-serif; background:#f5f6fa; margin:0; padding:24px; }}
  h1    {{ color:#2c3e50; font-size:20px; margin-bottom:6px; }}
  .sub  {{ color:#888; font-size:13px; margin:0 0 16px; line-height:2.2; }}
  table {{ border-collapse:collapse; width:100%; background:#fff;
           border-radius:10px; overflow:hidden;
           box-shadow:0 2px 12px rgba(0,0,0,0.08); }}
  th    {{ background:#2c3e50; color:#fff; padding:11px 14px;
           text-align:left; font-size:13px; white-space:nowrap; }}
  td    {{ padding:10px 14px; font-size:13px;
           border-bottom:1px solid #f0f0f0; white-space:nowrap; }}
  tr:last-child td {{ border-bottom:none; }}
  tr:hover td      {{ background:#fafbfc; }}
  .note {{ color:#bbb; font-size:11px; margin-top:12px; }}
</style>
</head>
<body>
<h1>📈 突破信号跟踪报告 &nbsp;{mode_tag}</h1>
<p class="sub">
  信号日：{signal_date}&nbsp;|&nbsp;
  {summary}
  更新：{now_str}
</p>
<table>
  <thead>
    <tr>
      <th>代码</th><th>名称</th><th>信号日收盘</th>
      <th>位置</th><th>量比</th>
      <th>D+1</th><th>D+3</th><th>D+5</th>
      <th>最新涨跌</th><th>日期/状态</th><th>走势</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>
<p class="note">
  涨跌幅以信号日收盘价为基准&nbsp;|&nbsp;走势图首点为信号日&nbsp;|&nbsp;盘中每60秒自动刷新
</p>
</body>
</html>"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="突破信号跟踪报告生成器")
    parser.add_argument(
        "--signal-file",
        required=True,
        type=Path,
        help="信号 CSV 文件路径",
    )
    parser.add_argument(
        "--signal-date",
        default=None,
        help="信号日期 YYYY-MM-DD（默认从文件名推断）",
    )
    parser.add_argument(
        "--output-dir",
        default=Path("data/reports"),
        type=Path,
        help="输出目录（默认 data/reports）",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    signal_file: Path = args.signal_file
    if not signal_file.exists():
        print(f"信号文件不存在: {signal_file}", file=sys.stderr)
        return 1

    # 从文件名推断信号日期（如 breakout_20260511.csv）
    signal_date = args.signal_date
    if not signal_date:
        import re
        m = re.search(r"(\d{8})", signal_file.stem)
        if m:
            signal_date = f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:8]}"
        else:
            signal_date = datetime.today().strftime("%Y-%m-%d")

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    now_str = now.strftime("%Y-%m-%d %H:%M")
    
    # A股交易时间: 9:30-11:30 和 13:00-15:00
    is_realtime = now.weekday() < 5 and (
        (now.hour == 9 and now.minute >= 25) or  # 9:25-9:30 集合竞价
        (now.hour == 10) or  # 10:00-10:59
        (now.hour == 11 and now.minute <= 30) or  # 11:00-11:30
        (now.hour == 13) or  # 13:00-13:59
        (now.hour == 14) or  # 14:00-14:59
        (now.hour == 15 and now.minute == 0)  # 15:00 收盘
    )

    signals = pd.read_csv(signal_file)
    code_col = "代码" if "代码" in signals.columns else "code"
    name_col = "名称" if "名称" in signals.columns else "name"
    codes = signals[code_col].tolist()

    # ── 历史日K ───────────────────────────────────────────────
    hist = {}
    print(f"拉取历史数据（{len(codes)} 只）...")
    for i, code in enumerate(codes):
        print(f"\r  {i+1}/{len(codes)}: {code}    ", end="", flush=True)
        data = get_hist_after_signal(code, signal_date)
        hist[code] = data
    print()

    # ── 组装记录 ───────────────────────────────────────────────
    records = []
    for _, row in signals.iterrows():
        code = row[code_col]
        name = row.get(name_col, "")
        signal_close = row.get("close", row.get("breakout_close", 0))
        position = row.get("position", "-")
        vol_ratio = row.get("vol_ratio", "-")

        data = hist.get(code, [])
        closes_after = [float(d[1]) for d in data[1:]]  # 跳过信号日

        record = {
            "code": code,
            "name": name,
            "signal_close": signal_close,
            "position": position,
            "vol_ratio": vol_ratio,
            "closes_after": closes_after,
        }

        # D+1, D+3, D+5
        for d, label in [(1, "D1"), (3, "D3"), (5, "D5")]:
            if len(closes_after) >= d:
                pct = round((closes_after[d - 1] / signal_close - 1) * 100, 2)
                record[label] = pct
            else:
                record[label] = None

        # 实时价格
        if is_realtime and closes_after:
            record["is_realtime"] = True
            record["current"] = round((closes_after[-1] / signal_close - 1) * 100, 2)
            record["current_date"] = today
        else:
            record["is_realtime"] = False
            record["current"] = record.get("D5")
            record["current_date"] = data[-1][0] if data else "-"

        records.append(record)

    # ── 输出 HTML ───────────────────────────────────────────────
    html = generate_html(records, today, now_str, is_realtime, signal_date, str(signal_file))
    out_path = output_dir / f"tracker_{signal_date.replace('-', '')}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"报告已生成: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
