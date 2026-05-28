## Context

当前项目是一个 A 股选股系统，4 个核心策略（breakout / dragon_leader / sideways_breakout / pullback_ma5）+ 1 个尾盘精选（afternoon），通过 5 个独立脚本定时扫描，输出 CSV → Streamlit 回顾。

**现状问题（基于代码阅读）：**
- 策略参数散落在各模块的模块级常量中（`strategies/breakout.py:13-21`），调参需要改代码
- `afternoon.py` 内联复制了 breakout 逻辑（`strategies/afternoon.py:24-110`）和 pullback_ma5 逻辑（`strategies/afternoon.py:114-230`），约 200 行几乎重复
- 5 个扫描脚本（`scripts/daily_scan.py`, `scan_dragon.py`, `sideways_scan.py`, `pullback_ma5_scan.py`, `afternoon_scan.py`）各 40-60 行几乎完全相同的模板
- 无回测引擎 —— 参数优化靠直觉
- `strategies/scan_all.py` 反向 import `scripts/daily_scan`，目录依赖混乱（`strategies/scan_all.py:13`）
- 午后扫描的缓存更新是串行 `for` 循环（`scripts/afternoon_scan.py:105-113`），而 `update_cache.py` 用了 6 进程池（`scripts/update_cache.py:34`）
- `backtest/tracker.py` 硬编码绝对路径 `SIGNAL_FILE`（`backtest/tracker.py:12`）和信号日期（`backtest/tracker.py:10`）
- 单个股票的异常会被 `except Exception: continue` 静默吞掉

**约束：** 数据源保持三后端不变、缓存后端不变、Streamlit app 不变、已有 CSV 输出格式保留。

## Goals / Non-Goals

**Goals:**
1. 所有策略参数集中到 YAML 配置文件 `config/strategies.yaml`，支持 `default` / `tight` 预设
2. 每个 `check_*` 函数接受 `params: dict`，消除模块级常量
3. `afternoon.py` 改为调用原策略函数 + tightened params，不再内联代码
4. 提取通用扫描执行器 `run_scan()` → `scripts/scan_runner.py`
5. 新建 `backtest/engine.py`，支持历史日期批量回测
6. `tracker.py` 用 `argparse` 参数化
7. 午后缓存更新改多进程并行
8. 管道增加重试/超时/失败汇总

**Non-Goals:** 不改策略核心逻辑、不改数据源/缓存后端、不新增策略、不引入 ML 模型。

## Decisions

### 1. 配置格式: YAML

YAML 可读性好，支持注释，`pyyaml` 在大多数 Python 环境已可用。每个策略模块保留 `DEFAULT_PARAMS` 字典作为 YAML 缺失时的回退。

### 2. 策略函数签名

```python
# Before
def check_breakout(df: pd.DataFrame, box_days: int = 20) -> dict:
    # 模块级常量: MAX_POSITION, MAX_BOX_RANGE, ...

# After
def check_breakout(df: pd.DataFrame, params: dict | None = None) -> dict:
    p = params or DEFAULT_PARAMS
```

`scan_stocks()` 同样接受 `params`。`params=None` 时使用内置 `DEFAULT_PARAMS`，保证向后兼容。

### 3. afternoon.py 重构

不再定义 `check_breakout_1450()` 和 `check_pullback_1450()`。直接从 `breakout` 和 `pullback_ma5` import，传入 tight params。仅保留编排逻辑（两轮扫描 + 降级 + 打分 + 排序）。

### 4. 扫描执行器

```python
# scripts/scan_runner.py
def run_scan(strategy_module, output_prefix, params=None, **kwargs) -> int:
    # 交易日检查 → 股票池加载 → 扫描 → 保存 CSV
```

所有现有扫描脚本变为 1 行 thin wrapper，保留独立入口供 cron/launchd。

### 5. 回测引擎

```python
def backtest(check_fn, stock_list, start_date, end_date, params=None, horizons=[1,3,5,10,20]) -> pd.DataFrame
```

遍历每个交易日，用历史数据运行策略，记录信号后用后续真实数据计算 T+N 收益。复用 `cache_manager.load()`。纯 pandas 实现，不引入 `empyrical`。

### 6. tracker.py 参数化

`argparse` 代替代码内常量：`--signal-file`（必填）、`--signal-date`、`--output-dir`（默认 `data/reports/`）。

## Risks / Trade-offs

- **YAML 语法错误 → 静默回退**: 启动时 validate 配置，warn + 用内置默认值
- **回测耗时**: 离线任务，利用缓存加速，非本次重点优化
- **向后兼容**: 保留所有现有脚本文件作为入口点，只改内部实现
- **不引入新依赖**: 回测用纯 pandas，不引入 `empyrical`
