# CodeRabbit 安装指南

## 概述

CodeRabbit 是一个 AI 代码审查工具，可以自动审查 Pull Request 并提供改进建议。本指南将帮助您在 newstockpicker 项目中安装和配置 CodeRabbit。

## 安装步骤

### 步骤 1: 安装 CodeRabbit GitHub App

1. 访问 [CodeRabbit 安装页面](https://app.coderabbit.ai/login?free-trial)
2. 使用您的 GitHub 账户登录
3. 授权 CodeRabbit 访问您的仓库
4. 选择 `benlueis/newstockpicker` 仓库
5. 完成安装

### 步骤 2: 配置仓库权限

确保 CodeRabbit 有以下权限：
- 读取代码
- 写入评论
- 读取 Pull Request
- 写入 Pull Request 状态

### 步骤 3: 设置环境变量（可选）

如果您想使用自定义配置，可以在 GitHub 仓库设置中添加以下 Secrets：

1. 访问仓库设置 → Secrets and variables → Actions
2. 添加以下 Secrets：
   - `CODERABBIT_API_KEY`: 您的 CodeRabbit API 密钥（可选）

### 步骤 4: 验证安装

1. 创建一个测试 Pull Request
2. 等待几分钟，CodeRabbit 应该会自动开始审查
3. 检查 PR 评论中是否有 CodeRabbit 的反馈

## 配置文件说明

项目中已创建 `.coderabbit.yaml` 配置文件，包含以下设置：

### 语言和语气
- 使用中文进行代码审查
- 专注于金融量化系统

### 审查策略
- 平衡模式（balanced）
- 请求更改工作流
- 高层次总结
- 审查状态更新

### 路径过滤
- 排除缓存文件、CSV 数据、报告文件
- 排除 GitHub Actions 工作流
- 排除文档和脚本文件

### 重点审查内容
- 安全漏洞
- 性能问题
- 代码质量
- 错误处理
- 依赖管理

### 工具集成
- Ruff 代码检查
- Pytest 测试运行

## GitHub Actions 工作流

项目中已创建 `.github/workflows/coderabbit.yml` 工作流，包含：

1. **代码检查**: 使用 Ruff 进行代码风格检查
2. **测试运行**: 使用 Pytest 运行单元测试
3. **AI 审查**: 使用 CodeRabbit 进行 AI 代码审查
4. **报告上传**: 上传检查报告作为构建产物

## 使用指南

### 自动审查
- 创建 Pull Request 时，CodeRabbit 会自动开始审查
- 审查结果会以评论形式出现在 PR 中
- 您可以回复评论与 CodeRabbit 交互

### 手动触发
在 PR 评论中输入以下命令可以手动触发审查：
```
@coderabbitai review
```

### 其他命令
- `@coderabbitai summary`: 生成 PR 摘要
- `@coderabbitai explain`: 解释代码变更
- `@coderabbitai suggestions`: 获取改进建议

## 故障排除

### 问题 1: CodeRabbit 没有自动审查
**解决方案:**
1. 检查 CodeRabbit App 是否已正确安装
2. 确认仓库权限设置正确
3. 等待几分钟后刷新 PR 页面

### 问题 2: 审查结果不准确
**解决方案:**
1. 检查 `.coderabbit.yaml` 配置文件
2. 根据项目需求调整审查重点
3. 提供更详细的项目说明

### 问题 3: GitHub Actions 工作流失败
**解决方案:**
1. 检查 `requirements.txt` 是否包含所有依赖
2. 确认 Python 版本兼容性
3. 查看工作流日志获取详细错误信息

## 最佳实践

1. **定期更新配置**: 根据项目发展调整审查重点
2. **提供上下文**: 在 PR 描述中提供足够的上下文信息
3. **处理反馈**: 及时处理 CodeRabbit 提供的建议
4. **监控质量**: 定期检查代码质量指标

## 相关资源

- [CodeRabbit 文档](https://docs.coderabbit.ai)
- [CodeRabbit GitHub](https://github.com/coderabbitai)
- [配置示例](https://docs.coderabbit.ai/configuration/example)
- [最佳实践](https://docs.coderabbit.ai/best-practices)

## 技术支持

如果遇到问题，可以：
1. 查看 CodeRabbit 文档
2. 在 GitHub 上提交 Issue
3. 联系 CodeRabbit 支持团队