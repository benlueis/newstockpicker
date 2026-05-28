## Why

当前项目 4 个核心策略各自为战，扫描脚本大量重复代码，`afternoon.py` 内联复制了 breakout 和 pullback 的完整逻辑（~200 行），配置散落在各模块的模块级常量中，无回测引擎、无统一错误处理。重构后预期：**更高的信号质量**（策略可调参+回测验证）、**更低的维护成本**（消除重复）、**更稳定的流水线**（统一配置+错误恢复）。

## What Changes

- **统一配置系统** — 所有策略参数集中到 YAML/TOML 配置文件，支持多套预设（tight/loose/default），消除模块级魔法常量
- **策略参数化** — 每个策略函数接受 `params` dict，`afternoon.py` 不再内联复制代码，改为调用策略函数并传入 tightened params
- **扫描脚本统一** — 提取 `run_scan(strategy_module, output_prefix)` 公共函数，消除 5 个脚本中 ~200 行重复模板代码
- **回测引擎** — 新建 `backtest/engine.py`，支持对任意策略+参数组合跑历史回测，输出收益曲线、胜率、最大回撤、夏普比率
- **管道错误恢复** — 扫描脚本增加重试、超时、失败摘要推送
- **午后扫描并行化** — `afternoon_scan.py` 的增量缓存更新改为 `ProcessPoolExecutor`
- **修复 cross-import** — `strategies/scan_all.py` 不再从 `scripts/` 导入，改为 `scripts/run_all.py` 直接调度
- **tracker.py 通用化** — 消除硬编码路径和日期，支持任意策略的信号跟踪
- **测试补全** — 补充策略边界条件测试、回测引擎测试、配置加载测试

## Capabilities

### New Capabilities

- `unified-config`: 统一 YAML 配置文件，每个策略支持多套参数预设
- `backtest-engine`: 回测引擎，支持批量跑策略参数组合
- `scan-runner`: 通用扫描执行器，消除脚本重复代码
- `pipeline-error-recovery`: 管道错误处理、重试、告警

### Modified Capabilities

- `breakout-strategy`: 从模块级常量迁移到可注入 params
- `dragon-leader-strategy`: 同上
- `sideways-breakout-strategy`: 同上
- `pullback-ma5-strategy`: 同上
- `afternoon-scan`: 从内联代码改为调用策略函数 + tightened params

## Impact

- **strategies/**: 全部 5 个策略模块需重构函数签名（添加 `params` 参数）
- **scripts/**: 全部 5 个扫描脚本 + `afternoon_scan.py` 需改为调用通用 runner
- **backtest/**: `tracker.py` 重构，新增 `engine.py`
- **tests/**: 新增 3-5 个测试文件
- **配置**: 新增 `config/` 目录存放 YAML 配置
- **依赖**: 可能新增 `pyyaml`、`empyrical`（可选，用于夏普比率）
