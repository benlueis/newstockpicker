## ADDED Requirements

### Requirement: 回测引擎核心功能

系统 SHALL 提供 `backtest()` 函数，对指定策略在历史日期范围内跑回测。

#### Scenario: 正常回测运行
- **WHEN** 调用 `backtest(check_breakout, stock_list, "2026-01-01", "2026-05-01")`
- **THEN** 返回一个 DataFrame，包含列 `["代码", "名称", "信号日期", "T+1", "T+3", "T+5", "T+10", "T+20"]`，每行代表一笔信号

#### Scenario: 无信号日期
- **WHEN** 回测区间内没有任何股票触发信号
- **THEN** 返回空 DataFrame（有正确的列名），不抛出异常

#### Scenario: 数据不足
- **WHEN** 某只股票在信号日期之前的历史数据少于策略所需的最低天数
- **THEN** 该股票在该日期被跳过，记录到日志，不中断整个回测

### Requirement: 回测统计摘要

系统 SHALL 提供 `backtest_summary()` 函数，对回测结果进行汇总统计。

#### Scenario: 计算胜率和均收益
- **WHEN** 调用 `backtest_summary(results_df, horizon=5)`
- **THEN** 返回字典包含 `win_rate`（胜率）、`avg_return`（均收益）、`total_signals`（总信号数）、`max_drawdown`（最大回撤）

#### Scenario: 空结果统计
- **WHEN** 对空 DataFrame 调用 `backtest_summary()`
- **THEN** 返回所有统计值为 `None` 或 `0` 的字典，不报错

### Requirement: 回测数据来源

回测引擎 SHALL 复用 `cache_manager.load()` 获取历史 K 线数据。

#### Scenario: 缓存命中
- **WHEN** 回测时某股票的历史数据已在 SQLite/Parquet 缓存中
- **THEN** 直接读取缓存，不发起网络请求

#### Scenario: 缓存未命中
- **WHEN** 回测时某股票的历史数据不在缓存中
- **THEN** 回退到 baostock 在线拉取（与 `common.get_stock_data()` 行为一致）
