## 1. 统一配置系统

- [ ] 1.1 创建 `config/strategies.yaml`，包含 5 个策略的 `default` 和 `tight` 参数
- [ ] 1.2 创建 `config/loader.py`，提供 `load_config()` 和 `get_params(strategy, preset)` 函数，含验证逻辑
- [ ] 1.3 每个策略模块导出 `DEFAULT_PARAMS` 字典（内嵌回退值）

## 2. 策略参数化

- [ ] 2.1 `breakout.py`: `check_breakout()` 和 `scan_stocks()` 接受 `params` 参数
- [ ] 2.2 `pullback_ma5.py`: `check_pullback_ma5()` 和 `scan_stocks()` 接受 `params` 参数
- [ ] 2.3 `sideways_breakout.py`: `check_sideways_breakout()` 统一为 `params` dict 签名
- [ ] 2.4 `dragon_leader.py`: `evaluate_leader()` 和 `scan_stocks()` 接受 `params` 参数

## 3. afternoon.py 去重

- [ ] 3.1 移除 `afternoon.py` 中 `check_breakout_1450()` 和 `check_pullback_1450()` 函数
- [ ] 3.2 改为 import `breakout.check_breakout` 和 `pullback_ma5.check_pullback_ma5`，传入 tight params
- [ ] 3.3 验证输出格式与重构前一致（字段、值、排序规则）

## 4. 扫描执行器

- [ ] 4.1 新建 `scripts/scan_runner.py`，实现 `run_scan()` 通用函数
- [ ] 4.2 重构 `scripts/daily_scan.py` 为 thin wrapper
- [ ] 4.3 重构 `scripts/scan_dragon.py` 为 thin wrapper
- [ ] 4.4 重构 `scripts/sideways_scan.py` 为 thin wrapper
- [ ] 4.5 重构 `scripts/pullback_ma5_scan.py` 为 thin wrapper
- [ ] 4.6 重构 `scripts/afternoon_scan.py` 为 thin wrapper + 并行化缓存更新

## 5. 午后扫描并行化

- [ ] 5.1 将 `afternoon_scan.py` 的缓存增量更新改为 `ProcessPoolExecutor` 并行执行
- [ ] 5.2 适配 baostock 的 per-process login 模式（参照 `update_cache.py` 的实现）

## 6. 回测引擎

- [ ] 6.1 新建 `backtest/engine.py`，实现 `backtest()` 和 `backtest_summary()` 函数
- [ ] 6.2 回测遍历交易日逻辑：利用 `common.is_trading_day()` 判断
- [ ] 6.3 复用 `cache_manager.load()` 获取历史数据

## 7. tracker.py 通用化

- [ ] 7.1 `backtest/tracker.py` 用 `argparse` 替换硬编码常量
- [ ] 7.2 支持 `--signal-file`、`--signal-date`、`--output-dir` 命令行参数

## 8. 管道错误恢复

- [ ] 8.1 各扫描脚本增加单股异常打印（`⚠️ {code} {name}: {error}` 到 stderr）
- [ ] 8.2 `scan_runner.py` 增加步骤级重试逻辑（默认 3 次，间隔 5s）
- [ ] 8.3 `afternoon_scan.py` 增加失败计数 + 推送摘要中包含失败信息

## 9. 跨导入修复 + 清理

- [ ] 9.1 移除 `strategies/scan_all.py` 对 `scripts/daily_scan` 的 import
- [ ] 9.2 更新 `scripts/run_all.py` 由自身直接调度所有扫描

## 10. 测试补全

- [ ] 10.1 `tests/test_config.py` — 配置加载、验证、回退逻辑测试
- [ ] 10.2 `tests/test_backtest_engine.py` — 回测引擎边界条件测试（空区间、无信号、缓存失效）
- [ ] 10.3 更新现有策略测试以验证 `params` 参数传递
- [ ] 10.4 验证所有现有策略测试仍然通过（向后兼容）
