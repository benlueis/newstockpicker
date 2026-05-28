## ADDED Requirements

### Requirement: 配置文件存在且格式正确

系统 SHALL 在 `config/strategies.yaml` 中存储所有策略参数，支持 `default` 和 `tight` 两套预设。

#### Scenario: 配置文件存在且格式正确
- **WHEN** 配置加载器读取 `config/strategies.yaml`
- **THEN** 返回包含所有策略名称的字典，每个策略包含 `default` 和 `tight` 子键

#### Scenario: 配置文件不存在
- **WHEN** 配置文件路径不存在
- **THEN** 系统 SHALL 打印警告并使用各策略模块内置的 `DEFAULT_PARAMS` 作为回退

#### Scenario: 配置文件格式错误
- **WHEN** 配置文件包含无效 YAML 语法
- **THEN** 系统 SHALL 打印错误信息并使用内置 `DEFAULT_PARAMS` 回退

### Requirement: 配置验证

系统 SHALL 在加载配置时验证每个参数的类型和合法范围。

#### Scenario: 参数类型不匹配
- **WHEN** 配置中 `max_position` 的值为字符串 `"0.6"` 而非数字
- **THEN** 系统 SHALL 打印警告，将该参数回退到内置默认值

#### Scenario: 参数超出合法范围
- **WHEN** 配置中 `min_breakout_pct` 的值为`-5.0`（负数，不合理）
- **THEN** 系统 SHALL 打印警告，将该参数回退到内置默认值

### Requirement: 策略函数接受 params 参数

所有 `check_*` 函数 SHALL 接受可选的 `params: dict` 参数来覆盖默认配置。

#### Scenario: 传入自定义 params
- **WHEN** 调用 `check_breakout(df, params={"max_position": 0.50, "max_box_range": 0.08})`
- **THEN** 函数使用传入的参数值而非模块默认值进行判断

#### Scenario: params 为 None
- **WHEN** 调用 `check_breakout(df)` 或 `check_breakout(df, params=None)`
- **THEN** 函数使用内置 `DEFAULT_PARAMS`，行为与重构前完全一致
