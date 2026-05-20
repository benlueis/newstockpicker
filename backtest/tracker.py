"""
信号跟踪脚本：支持盘中实时 + 收盘后日K两种模式
用法：python tracker.py
"""
import baostock as bs
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

SIGNAL_DATE = "2026-05-11"
SIGNAL_FILE = Path("/Users/xifeiyou/Documents/workspace/stock-picker/data/breakout_20260511.csv")
OUTPUT_DIR  = Path("/Users/xifeiyou/Documents/workspace/stock-picker/data/reports")
OUTPUT_DIR.mkdir(exist_ok=True)

SINA_HEADERS = {"Referer": "https://finance.sina.com.cn"}


def get_realtime_prices(codes: list) -> dict:
    sina_codes = [c.replace(".", "") for c in codes]
    url  = f"http://hq.sinajs.cn/list={','.join(sina_codes)}"
    resp = requests.get(url, headers=SINA_HEADERS, timeout=10)
    resp.encoding = "gbk"

    result = {}
    for line in resp.text.strip().split("\n"):
        line = line.strip()
        if not line or '=""' in line:
            continue
        try:
            code_part = line.split('"')[0].split("_")[-1]  # sz002011
            fields    = line.split('"')[1].split(",")
            yesterday = float(fields[1])   # 昨收 ✅
            price     = float(fields[3])   # 现价 ✅
            date      = fields[-3]
            time      = fields[-2]
            pct_chg   = round((price / yesterday - 1) * 100, 2) if yesterday else 0
            std_code  = code_part[:2] + "." + code_part[2:]
            result[std_code] = {
                "price":   price,
                "pct_chg": pct_chg,
                "date":    date,
                "time":    time,
            }
        except:
            continue
    return result


def get_hist_after_signal(code: str) -> list:
    end = (datetime.strptime(SIGNAL_DATE, "%Y-%m-%d") + timedelta(days=21)).strftime("%Y-%m-%d")
    rs  = bs.query_history_k_data_plus(
        code, "date,close",
        start_date=SIGNAL_DATE,
        end_date=end,
        frequency="d", adjustflag="3"
    )
    data = []
    while (rs.error_code == '0') and rs.next():
        data.append(rs.get_row_data())
    return data


def ret_str(val):
    if val is None:
        return "<td style='color:#aaa;text-align:right'>-</td>"
    c    = "#c0392b" if val > 0 else "#27ae60" if val < 0 else "#888"
    sign = "+" if val > 0 else ""
    return f'<td style="color:{c};font-weight:bold;text-align:right">{sign}{val}%</td>'


def sparkline(signal_close, closes):
    all_vals = [signal_close] + closes
    if len(all_vals) < 2:
        return "-"
    mn  = min(all_vals)
    mx  = max(all_vals)
    rng = mx - mn if mx != mn else 1
    pts = []
    for i, c in enumerate(all_vals):
        x = i * 14
        y = 30 - int((c - mn) / rng * 28)
        pts.append(f"{x},{y}")
    y0     = 30 - int((signal_close - mn) / rng * 28)
    w      = (len(all_vals) - 1) * 14
    last_y = pts[-1].split(",")[1]
    stroke = "#c0392b" if closes[-1] >= signal_close else "#27ae60"
    return (
        f'<svg width="{w+8}" height="34">'
        f'<line x1="0" y1="{y0}" x2="{w}" y2="{y0}" stroke="#eee" stroke-width="1" stroke-dasharray="3,2"/>'
        f'<polyline points="{" ".join(pts)}" fill="none" stroke="{stroke}" stroke-width="1.8"/>'
        f'<circle cx="{w}" cy="{last_y}" r="2.5" fill="{stroke}"/>'
        f'</svg>'
    )


def generate_html(records, today, now_str, is_realtime):
    mode_tag = (
        f'<span style="background:#e74c3c;color:#fff;padding:2px 8px;'
        f'border-radius:4px;font-size:11px">● 盘中实时 {now_str}</span>'
        if is_realtime else
        f'<span style="background:#27ae60;color:#fff;padding:2px 8px;'
        f'border-radius:4px;font-size:11px">收盘数据</span>'
    )

    has_d5  = [r for r in records if r.get("D5") is not None]
    summary = ""
    if has_d5:
        win    = sum(1 for r in has_d5 if r["D5"] > 0)
        rate   = round(win / len(has_d5) * 100)
        avg_d5 = round(sum(r["D5"] for r in has_d5) / len(has_d5), 2)
        sign   = "+" if avg_d5 > 0 else ""
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
  信号日：{SIGNAL_DATE}&nbsp;|&nbsp;
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


def main():
    now        = datetime.now()
    today      = now.strftime("%Y-%m-%d")
    now_str    = now.strftime("%Y-%m-%d %H:%M")
    is_trading = now.weekday() < 5 and (
        (now.hour == 9 and now.minute >= 30) or
        (10 <= now.hour <= 14) or
        (now.hour == 15 and now.minute == 0)
    )

    signals  = pd.read_csv(SIGNAL_FILE)
    code_col = '代码' if '代码' in signals.columns else 'code'
    name_col = '名称' if '名称' in signals.columns else 'name'
    codes    = signals[code_col].tolist()

    # ── 历史日K ───────────────────────────────────────────────
    bs.login()
    hist = {}
    print(f"拉取历史数据（{len(codes)} 只）...")
    for i, code in enumerate(codes):
        print(f"\r  {i+1}/{len(codes)}: {code}    ", end="", flush=True)
        rows = get_hist_after_signal(code)
        if rows:
            hist[code] = {
                "signal_close": round(float(rows[0][1]), 2),
                "closes_after": [float(r[1]) for r in rows[1:] if r[1]],
                "dates_after":  [r[0]        for r in rows[1:] if r[1]],
            }
    bs.logout()
    print("\n历史数据完成")

    # ── 实时行情 ──────────────────────────────────────────────
    realtime = {}
    if is_trading:
        print("盘中，拉取新浪实时行情...")
        try:
            realtime = get_realtime_prices(codes)
            print(f"实时行情：{len(realtime)} 只")
        except Exception as e:
            print(f"实时行情失败：{e}")

    # ── 组装 ──────────────────────────────────────────────────
    records = []
    for _, row in signals.iterrows():
        code = row[code_col]
        name = row[name_col]
        h    = hist.get(code)
        if not h:
            continue

        signal_close  = h["signal_close"]
        closes_after  = h["closes_after"][:]
        dates_after   = h["dates_after"][:]

        rt          = realtime.get(code, {})
        is_rt_added = False
        if rt and rt.get("price"):
            closes_after.append(rt["price"])
            dates_after.append(rt["date"])
            is_rt_added = True

        def ret(n):
            return round((closes_after[n-1] / signal_close - 1) * 100, 2) \
                   if len(closes_after) >= n else None

        rec = {
            "code":         code,
            "name":         name,
            "signal_close": signal_close,
            "position":     round(float(row["position"]), 3),
            "vol_ratio":    round(float(row["vol_ratio"]), 2),
            "D1":           ret(1),
            "D3":           ret(3),
            "D5":           ret(5),
            "closes_after": closes_after,
            "is_realtime":  is_rt_added,
            "rt_time":      rt.get("time", "") if is_rt_added else "",
        }
        if closes_after:
            rec["current"]      = round((closes_after[-1] / signal_close - 1) * 100, 2)
            rec["current_date"] = dates_after[-1]

        records.append(rec)

    html = generate_html(records, today, now_str, bool(realtime))
    out  = OUTPUT_DIR / f"track_{today}.html"
    out.write_text(html, encoding="utf-8")
    print(f"✅ {out}")


if __name__ == "__main__":
    main()
