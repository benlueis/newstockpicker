## ADDED Requirements

### Requirement: 单步重试

管道的每个关键步骤（缓存更新、策略扫描、推送）SHALL 在失败时自动重试。

#### Scenario: 网络超时重试成功
- **WHEN** baostock 查询因网络超时失败（第 1 次）
- **THEN** 等待 5 秒后重试，最多 3 次。若第 2 次成功则继续

#### Scenario: 重试耗尽
- **WHEN** 某步骤连续失败 3 次
- **THEN** 记录错误日志（含堆栈），跳到下一步骤（不阻塞整个管道）

### Requirement: 单股异常隔离

扫描过程中单只股票的处理失败 SHALL 不影响其他股票。

#### Scenario: 单股数据异常
- **WHEN** 扫描过程中某只股票的 K 线数据格式异常导致 `check_*` 抛出异常
- **THEN** 打印 `⚠️ {code} {name}: {error}` 到 stderr，继续扫描下一只股票

### Requirement: 失败汇总推送

管道执行完毕后 SHALL 汇总失败信息并通过 Bark 推送。

#### Scenario: 有失败
- **WHEN** 管道有 3 只股票的缓存更新失败
- **THEN** 在最终推送消息中包含 "⚠️ 3 只缓存更新失败: sh.600xxx, sz.000xxx, ..."

#### Scenario: 无失败
- **WHEN** 管道全部成功
- **THEN** 推送消息中不包含失败信息

### Requirement: 步骤超时控制

每个步骤 SHALL 有超时限制，防止无限等待。

#### Scenario: baostock 查询超时
- **WHEN** `bs.query_history_k_data_plus()` 超过 30 秒未返回
- **THEN** 终止该次查询，视为失败并进入重试逻辑
