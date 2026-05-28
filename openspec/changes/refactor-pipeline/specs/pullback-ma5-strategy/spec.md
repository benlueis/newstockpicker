## MODIFIED Requirements

### Requirement: check_pullback_ma5 接受 params 参数

`check_pullback_ma5(df, params=None)` SHALL 接受可选的 `params` 字典。

#### Scenario: 使用自定义参数
- **WHEN** 调用 `check_pullback_ma5(df, params={"min_recent_gain": 0.15, "max_vol_ratio": 0.85})`
- **THEN** 使用传入值进行判断

#### Scenario: 使用默认参数
- **WHEN** 调用 `check_pullback_ma5(df)`（不传 params）
- **THEN** 行为与重构前完全一致

### Requirement: 返回字典格式不变

`check_pullback_ma5()` 的返回字典 SHALL 保持包含 `signal`, `reason`, `close_ma5_pct`, `rebound_ratio`, `vol_ratio`, `ma5`, `ma10`, `ma20`, `days_above_ma5`, `recent_gain_pct` 等全部原有字段。

### Requirement: 模块提供 DEFAULT_PARAMS

`pullback_ma5.py` 模块 SHALL 导出 `DEFAULT_PARAMS`。

#### Scenario: 默认参数完整
- **WHEN** 导入 `DEFAULT_PARAMS`
- **THEN** 包含 `min_data_days`, `min_amount`, `max_pct_chg`, `min_pct_chg`, `trend_confirm_days`, `min_days_above_ma5`, `min_recent_gain`, `max_close_above_ma5_pct`, `min_close_below_ma5_pct`, `min_low_touch_ma5_ratio`, `max_vol_ratio`, `min_rebound_ratio`, `max_recent_drop` 等全部参数
