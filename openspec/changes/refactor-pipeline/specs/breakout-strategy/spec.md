## MODIFIED Requirements

### Requirement: check_breakout 接受 params 参数

`check_breakout(df, params=None)` SHALL 接受可选的 `params` 字典来覆盖策略参数。`params` 为 `None` 时使用内置 `DEFAULT_PARAMS`。

#### Scenario: 使用自定义参数
- **WHEN** 调用 `check_breakout(df, params={"max_position": 0.55, "min_vol_ratio": 2.0})`
- **THEN** 所有参数检查使用传入值，返回结果中的 `vol_ratio` 阈值按 2.0 判断

#### Scenario: 使用默认参数
- **WHEN** 调用 `check_breakout(df)`（不传 params）
- **THEN** 行为与重构前完全一致，使用模块内置 `DEFAULT_PARAMS`

#### Scenario: 部分参数覆盖
- **WHEN** 调用 `check_breakout(df, params={"min_vol_ratio": 2.0})`（只传一个参数）
- **THEN** `min_vol_ratio` 使用 2.0，其余参数使用 `DEFAULT_PARAMS` 中的默认值

### Requirement: 返回字典格式不变

`check_breakout()` 的返回字典格式 SHALL 与重构前完全一致。

#### Scenario: 信号触发时
- **WHEN** 一只股票满足全部突破条件
- **THEN** 返回 `{"signal": True, "reason": "低位横盘放量突破", "position": ..., "box_range": ..., ...}` 包含所有原有字段

#### Scenario: 信号未触发时
- **WHEN** 一只股票不满足条件
- **THEN** 返回 `{"signal": False, "reason": <具体原因>, ...}` 包含诊断字段

### Requirement: 模块提供 DEFAULT_PARAMS

`breakout.py` 模块 SHALL 导出 `DEFAULT_PARAMS` 字典，包含所有参数及其默认值。

#### Scenario: 访问默认参数
- **WHEN** 导入 `from breakout import DEFAULT_PARAMS`
- **THEN** 得到一个包含 `max_position`, `max_box_range`, `min_breakout_pct`, `min_vol_ratio`, `min_amount`, `max_upper_shadow`, `min_data_days`, `box_days`, `max_pct_chg` 的字典
