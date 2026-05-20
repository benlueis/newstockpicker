import baostock as bs
import pandas as pd

# 登录
lg = bs.login()
print("登录状态:", lg.error_msg)

# 拉贵州茅台日K（前复权）
rs = bs.query_history_k_data_plus(
    "sh.600519",
    "date,open,high,low,close,volume,turn,pctChg",
    start_date="2024-01-01",
    frequency="d",
    adjustflag="2"
)

data = []
while (rs.error_code == '0') and rs.next():
    data.append(rs.get_row_data())

df = pd.DataFrame(data, columns=rs.fields)

# 转换数据类型
for col in ['open','high','low','close','volume','turn','pctChg']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

print(df.tail())
print("\n字段列表:", df.columns.tolist())
print("数据行数:", len(df))

bs.logout()
