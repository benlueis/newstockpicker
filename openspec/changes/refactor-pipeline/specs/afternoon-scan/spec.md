## MODIFIED Requirements

### Requirement: afternoon.py 调用原策略函数而非内联代码

`afternoon.py` 的 `scan_stocks()` SHALL 从 `breakout` 和 `pullback_ma5` 模块导入 `check_breakout` 和 `check_pullback_ma5`，传入 tightened params，而非定义内联的 `check_breakout_1450()` 和 `check_pullback_1450()`。

#### Scenario: tight 扫描调用原策略
- **WHEN** 午后扫描第一轮（tight）
- **THEN** 调用 `check_breakout(df, params=TIGHT_BREAKOUT_PARAMS)` 和 `check_pullback_ma5(df, params=TIGHT_PULLBACK_PARAMS)`，其中 params 来自配置文件

#### Scenario: loose 降级调用原策略
- **WHEN** tight 命中不足，触发降级扫描
- **THEN** 调用 `check_breakout(df)` 和 `check_pullback_ma5(df)`（不传 params，使用默认值）

### Requirement: 内联函数已移除

`afternoon.py` SHALL NOT 包含 `check_breakout_1450()` 和 `check_pullback_1450()` 函数定义。

#### Scenario: 模块导入
- **WHEN** 检查 `afternoon.py` 的顶层定义
- **THEN** 不包含名为 `check_breakout_1450` 或 `check_pullback_1450` 的函数

### Requirement: 输出格式不变

午后扫描的输出 CSV 格式 SHALL 与重构前完全一致。

#### Scenario: 输出字段完整
- **WHEN** 午后扫描完成并保存 CSV
- **THEN** 包含 `代码`, `名称`, `tier`, `strategy`, `cross_hit`, `composite_score`, `score_bt`, `score_pt`, `position`, `box_range`, `breakout_pct`, `vol_ratio`, `pct_chg`, `amount_yi` 等全部原有字段，值与重构前一致

### Requirement: 午后缓存更新的并行化

`afternoon_scan.py` 的缓存增量更新 SHALL 使用 `ProcessPoolExecutor` 并行处理，而非当前逐股循环。

#### Scenario: 多进程缓存更新
- **WHEN** 午后扫描执行缓存更新步骤
- **THEN** 使用 `ProcessPoolExecutor(max_workers=4)` 并行调用 `incremental_update(code)`，总体耗时应显著低于逐股串行
