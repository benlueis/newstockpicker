## ADDED Requirements

### Requirement: 通用扫描执行器

系统 SHALL 提供 `run_scan()` 函数，统一处理交易日检查、股票池加载、策略扫描、结果保存。

#### Scenario: 交易日正常扫描
- **WHEN** 调用 `run_scan(breakout_module, "breakout")` 且当天是交易日
- **THEN** 1) 检查交易日，2) 从 `data/stock_list.csv` 加载股票池，3) 调用 `breakout.scan_stocks()`，4) 结果保存到 `data/breakout_{YYYYMMDD}.csv`，5) 返回退出码 0

#### Scenario: 非交易日
- **WHEN** 调用 `run_scan(breakout_module, "breakout")` 且当天不是交易日
- **THEN** 打印 "非交易日，跳过扫描"，返回退出码 0，不执行扫描

#### Scenario: 股票池文件不存在
- **WHEN** `data/stock_list.csv` 不存在
- **THEN** 打印错误信息 "请先运行: python data/get_stock_list.py"，返回退出码 1

#### Scenario: 扫描无信号
- **WHEN** 策略扫描返回空 DataFrame
- **THEN** 保存一个仅含列名的空 CSV 文件，打印 "今日无触发信号"，返回退出码 0

### Requirement: 自动 baostock 登录/登出

`run_scan()` SHALL 自动管理 baostock 的登录和登出。

#### Scenario: 正常登录执行
- **WHEN** 调用 `run_scan()`
- **THEN** 在扫描前调用 `bs.login()`，扫描完成后在 `finally` 块中调用 `bs.logout()`

### Requirement: 扫描进度显示

`run_scan()` SHALL 在扫描过程中显示进度。

#### Scenario: 进度输出
- **WHEN** 扫描进行中
- **THEN** 每完成一支股票，使用 `\r` 覆盖方式更新进度行 `扫描中 {i}/{total}: {code} {name}`
