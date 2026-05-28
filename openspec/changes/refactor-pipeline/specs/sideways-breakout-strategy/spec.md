## MODIFIED Requirements

### Requirement: check_sideways_breakout 接受 params 参数

`check_sideways_breakout(df, params=None)` SHALL 接受可选的 `params` 字典。（注：当前函数签名已有单独参数 `lookback_days`, `box_days` 等，重构后统一为 `params` dict。）

#### Scenario: 使用 params 字典
- **WHEN** 调用 `check_sideways_breakout(df, params={"max_box_range": 1.08, "min_vol_ratio": 2.0})`
- **THEN** 使用传入的参数值进行判断

#### Scenario: 向后兼容
- **WHEN** 调用 `check_sideways_breakout(df)`（不传 params）
- **THEN** 使用 `DEFAULT_PARAMS`，行为与重构前一致

### Requirement: 返回字典格式不变

`check_sideways_breakout()` 的返回字典 SHALL 保持包含 `signal`, `action`, `reason`, `position_120d`, `box_range`, `breakout_pct`, `vol_ratio` 等全部原有字段。

### Requirement: 模块提供 DEFAULT_PARAMS

`sideways_breakout.py` 模块 SHALL 导出 `DEFAULT_PARAMS`。

#### Scenario: 默认参数完整
- **WHEN** 导入 `DEFAULT_PARAMS`
- **THEN** 包含 `lookback_days`, `box_days`, `max_box_range`, `min_breakout_pct`, `min_vol_ratio`, `max_position_120d`, `min_amount`, `max_upper_shadow_ratio` 等全部参数
