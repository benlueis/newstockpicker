# CodeRabbit 代码审查集成

## 📋 项目状态

✅ **CodeRabbit 配置已完成**

本项目已配置 CodeRabbit AI 代码审查工具，用于自动审查 Pull Request 并提供代码改进建议。

## 🚀 快速开始

### 1. 安装 CodeRabbit GitHub App

访问以下链接安装 CodeRabbit：
- **安装链接**: https://app.coderabbit.ai/login?free-trial
- **选择仓库**: `benlueis/newstockpicker`

### 2. 测试安装

1. 创建一个新的 Pull Request
2. 等待 2-5 分钟，CodeRabbit 会自动开始审查
3. 在 PR 评论中查看 CodeRabbit 的反馈

## 📁 配置文件

| 文件 | 用途 |
|------|------|
| `.coderabbit.yaml` | CodeRabbit 配置文件 |
| `.github/workflows/coderabbit.yml` | GitHub Actions 工作流 |
| `scripts/install_coderabbit.sh` | 安装脚本 |
| `scripts/fix_code_issues.sh` | 代码质量修复脚本 |

## 📚 文档

- [安装指南](docs/coderabbit-setup.md)
- [安装报告](docs/coderabbit-installation-report.md)
- [最终报告](docs/coderabbit-final-report.md)

## 🔧 代码质量

### 当前状态
- **测试**: 35 个测试全部通过
- **代码检查**: 发现 561 个代码风格问题（大部分可自动修复）
- **已修复**: 部分关键问题已修复

### 运行代码检查

```bash
# 安装 ruff
pip install ruff

# 运行代码检查
ruff check . --select=E,F,W --ignore=E501

# 自动修复可修复的问题
ruff check . --select=E,F,W --ignore=E501 --fix

# 运行测试
pytest tests/ -v
```

## 🎯 CodeRabbit 功能

### 自动审查
- 创建 Pull Request 时自动开始审查
- 提供代码质量反馈
- 检测安全漏洞和性能问题

### 交互式审查
- 在 PR 评论中与 CodeRabbit 交互
- 使用 `@coderabbitai` 命令触发审查
- 获取代码改进建议

### 配置选项
- 支持中文审查
- 可自定义审查重点
- 支持多种编程语言

## 📊 项目架构

```
newstockpicker/
├── strategies/          # 策略模块
│   ├── breakout.py     # 低位横盘突破策略
│   ├── dragon_leader.py # 市场龙头策略
│   ├── sideways_breakout.py # 横盘向上突破策略
│   └── pullback_ma5.py # 回踩5日线策略
├── scripts/            # 脚本模块
│   ├── cache_manager.py # 数据缓存管理
│   ├── scan_runner.py  # 通用扫描执行器
│   └── notify.py       # Bark推送通知
├── config/             # 配置模块
│   ├── strategies.yaml # 策略参数配置
│   └── loader.py       # 配置加载器
├── backtest/           # 回测模块
├── app.py              # Streamlit Web界面
└── tests/              # 测试模块
```

## 🔍 代码审查重点

CodeRabbit 会重点审查以下内容：

1. **安全漏洞**: API 密钥、凭据、敏感信息
2. **性能问题**: 数据库查询、数据处理、算法效率
3. **代码质量**: 代码重复、命名规范、文档完整性
4. **错误处理**: 异常处理、日志记录、错误恢复
5. **依赖管理**: 版本固定、未使用依赖、兼容性

## 🆘 常见问题

### Q: CodeRabbit 没有自动审查？
A: 检查 CodeRabbit App 是否已正确安装，确认仓库权限设置正确。

### Q: 如何手动触发审查？
A: 在 PR 评论中输入 `@coderabbitai review`

### Q: 审查结果不准确？
A: 检查 `.coderabbit.yaml` 配置文件，根据项目需求调整审查重点。

## 📞 技术支持

- [CodeRabbit 文档](https://docs.coderabbit.ai)
- [GitHub 仓库](https://github.com/coderabbitai)
- [配置示例](https://docs.coderabbit.ai/configuration/example)

## 📝 更新日志

- **2026-05-28**: 初始配置完成
- 已创建 `.coderabbit.yaml` 配置文件
- 已创建 GitHub Actions 工作流
- 已修复部分代码质量问题
- 已创建安装文档和脚本