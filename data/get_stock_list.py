import baostock as bs
import pandas as pd

bs.login()

# 获取基础列表
rs = bs.query_stock_basic(code_name="")
data = []
while (rs.error_code == '0') and rs.next():
    data.append(rs.get_row_data())

df = pd.DataFrame(data, columns=rs.fields)

# 只保留沪深主板，排除ST
df = df[df['code'].str.match(r'^(sh\.6[^8]|sz\.00)')]
df = df[df['type'] == '1']
df = df[~df['code_name'].str.contains('ST|退', na=False)]
df = df[['code', 'code_name']].reset_index(drop=True)
print(f"主板非ST股票: {len(df)} 只，开始过滤...")

# 先验证字段：看看 amount 和 turn 长什么样
rs_test = bs.query_history_k_data_plus(
    "sh.600519",
    "date,close,amount,turn",
    start_date="2026-04-01",
    frequency="d",
    adjustflag="3"
)
test_data = []
while (rs_test.error_code == '0') and rs_test.next():
    test_data.append(rs_test.get_row_data())
print("字段验证 (茅台最近3条):")
for row in test_data[-3:]:
    print(" ", row)

filtered = []
total = len(df)

for i, row in df.iterrows():
    print(f"\r过滤中 {i+1}/{total}: {row['code']}    ", end="", flush=True)
    try:
        rs2 = bs.query_history_k_data_plus(
            row['code'],
            "date,close,amount,turn",
            start_date="2026-04-01",
            frequency="d",
            adjustflag="3"
        )
        d = []
        while (rs2.error_code == '0') and rs2.next():
            d.append(rs2.get_row_data())

        if not d:
            continue

        # 取最近5天有效数据的均值，避免单天异常
        valid = []
        for rec in d[-5:]:
            try:
                c = float(rec[1])
                a = float(rec[2])   # 成交额（元）
                t = float(rec[3])   # 换手率（%）
                if c > 0 and a > 0 and t > 0:
                    valid.append((c, a, t))
            except:
                continue

        if not valid:
            continue

        close  = valid[-1][0]                          # 最新收盘价
        # 流通市值（亿元）= 成交额 / 换手率% * 100 / 1e8
        mktcap_list = [a / t * 100 / 1e8 for _, a, t in valid]
        mktcap = sum(mktcap_list) / len(mktcap_list)  # 取均值更稳定

        # 过滤条件
        if not (6 <= close <= 300):
            continue
        if mktcap < 50:
            continue

        filtered.append({
            'code':      row['code'],
            'code_name': row['code_name'],
            'close':     round(close, 2),
            'mktcap':    round(mktcap, 2),
        })

    except Exception as e:
        continue

print("\n过滤完成！")
result = pd.DataFrame(filtered)
result.to_csv('/Users/xifeiyou/Documents/workspace/stock-picker/data/stock_list.csv', index=False)

print(f"最终股票池: {len(result)} 只")
print(f"股价范围: {result['close'].min()} ~ {result['close'].max()} 元")
print(f"市值范围: {result['mktcap'].min():.1f} ~ {result['mktcap'].max():.1f} 亿元")
print(result.head(10))

bs.logout()
