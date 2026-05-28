#!/bin/bash
# ============================================================================
# CodeRabbit 安装脚本
# 用法: bash scripts/install_coderabbit.sh
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================"
echo " CodeRabbit 安装向导"
echo " 项目路径: $PROJECT_ROOT"
echo "============================================"

# 检查 Git 仓库
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo "❌ 错误: 不是 Git 仓库"
    exit 1
fi

# 检查远程仓库
echo ""
echo "📌 检查远程仓库..."
git remote -v

# 检查 GitHub CLI
if command -v gh &> /dev/null; then
    echo "✅ GitHub CLI 已安装"
    
    # 检查是否已登录
    if gh auth status &> /dev/null; then
        echo "✅ 已登录 GitHub"
    else
        echo "⚠️  请先登录 GitHub: gh auth login"
    fi
else
    echo "⚠️  GitHub CLI 未安装，建议安装以简化流程"
    echo "   安装命令: brew install gh"
fi

# 检查配置文件
echo ""
echo "📌 检查配置文件..."

if [ -f "$PROJECT_ROOT/.coderabbit.yaml" ]; then
    echo "✅ .coderabbit.yaml 已存在"
else
    echo "⚠️  .coderabbit.yaml 不存在，将创建默认配置"
fi

if [ -f "$PROJECT_ROOT/.github/workflows/coderabbit.yml" ]; then
    echo "✅ coderabbit.yml 工作流已存在"
else
    echo "⚠️  coderabbit.yml 工作流不存在"
fi

# 检查依赖
echo ""
echo "📌 检查依赖..."

if command -v python &> /dev/null; then
    echo "✅ Python 已安装: $(python --version)"
else
    echo "❌ Python 未安装"
    exit 1
fi

if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    echo "✅ requirements.txt 存在"
else
    echo "⚠️  requirements.txt 不存在"
fi

# 提供安装选项
echo ""
echo "============================================"
echo " 安装选项"
echo "============================================"
echo ""
echo "1. 安装 CodeRabbit GitHub App (推荐)"
echo "   - 访问: https://app.coderabbit.ai/login?free-trial"
echo "   - 使用 GitHub 账户登录"
echo "   - 选择仓库: benlueis/newstockpicker"
echo ""
echo "2. 手动配置"
echo "   - 复制 .coderabbit.yaml 到项目根目录"
echo "   - 复制 .github/workflows/coderabbit.yml 到 .github/workflows/"
echo "   - 推送代码到 GitHub"
echo ""
echo "3. 运行代码检查"
echo "   - 安装 ruff: pip install ruff"
echo "   - 运行检查: ruff check ."
echo "   - 运行测试: pytest tests/"
echo ""
echo "4. 查看文档"
echo "   - 安装指南: docs/coderabbit-setup.md"
echo "   - 配置说明: .coderabbit.yaml"
echo ""
echo "============================================"
echo " 下一步"
echo "============================================"
echo ""
echo "1. 访问 https://app.coderabbit.ai/login?free-trial"
echo "2. 使用 GitHub 账户登录"
echo "3. 选择仓库: benlueis/newstockpicker"
echo "4. 完成安装"
echo "5. 创建 Pull Request 测试"
echo ""
echo "安装完成后，CodeRabbit 将自动审查您的 Pull Request"
echo ""
echo "需要帮助？请查看: docs/coderabbit-setup.md"