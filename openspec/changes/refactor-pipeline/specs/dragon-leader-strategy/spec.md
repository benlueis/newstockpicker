## MODIFIED Requirements

### Requirement: evaluate_leader 接受 params 参数

`evaluate_leader(df, bench_ret_20d, bench_ret_5d, params=None)` SHALL 接受可选的 `params` 字典。

#### Scenario: 使用自定义参数
- **WHEN** 调用 `evaluate_leader(df, 5.0, 2.0, params={"min_position": 0.90, "min_leader_score": 70.0})`
- **THEN** 过滤条件和评分计算使用传入值

#### Scenario: 使用默认参数
- **WHEN** 调用 `evaluate_leader(df, 5.0, 2.0)`（不传 params）
- **THEN** 行为与重构前完全一致

### Requirement: 返回字典格式不变

`evaluate_leader()` 的返回字典 SHALL 保持原有字段不变。

#### Scenario: 信号触发时
- **WHEN** 一只股票被判定为龙头
- **THEN** 返回 `{"signal": True, "leader_score": ..., "position": ..., "ret_5d": ..., ...}` 包含所有原有字段

### Requirement: 模块提供 DEFAULT_PARAMS

`dragon_leader.py` 模块 SHALL 导出 `DEFAULT_PARAMS`。

#### Scenario: 默认参数完整
- **WHEN** 导入 `DEFAULT_PARAMS`
- **THEN** 包含 `min_position`, `min_ret_20d`, `max_ret_20d`, `min_rs_20d`, `min_vol_ratio`, `min_amount`, `min_leader_score`, `top_market`, `top_per_industry` 等全部参数
