#!/bin/bash
# ============================================================================
# 自动修复代码质量问题
# 用法: bash scripts/fix_code_issues.sh
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================"
echo " 代码质量问题自动修复"
echo " 项目路径: $PROJECT_ROOT"
echo "============================================"

# 1. 修复 backtest/engine.py 中的未使用变量
echo ""
echo "📌 修复 backtest/engine.py 中的未使用变量..."
if [ -f "$PROJECT_ROOT/backtest/engine.py" ]; then
    # 使用 sed 替换 except Exception as e: 为 except Exception:
    sed -i '' 's/except Exception as e:/except Exception:/g' "$PROJECT_ROOT/backtest/engine.py"
    echo "✅ 已修复: 移除未使用的变量 'e'"
fi

# 2. 修复 backtest/tracker.py 中的空 f-string
echo ""
echo "📌 修复 backtest/tracker.py 中的空 f-string..."
if [ -f "$PROJECT_ROOT/backtest/tracker.py" ]; then
    # 移除无占位符的 f-string 前缀
    sed -i '' "s/f'<span style=\"background:#27ae60/<span style=\"background:#27ae60/g" "$PROJECT_ROOT/backtest/tracker.py"
    sed -i '' "s/f'border-radius:4px;font-size:11px\">收盘数据<\/span>'/'border-radius:4px;font-size:11px\">收盘数据<\/span>'/g" "$PROJECT_ROOT/backtest/tracker.py"
    echo "✅ 已修复: 移除空的 f-string 前缀"
fi

# 3. 修复 config/loader.py 中的未使用导入
echo ""
echo "📌 修复 config/loader.py 中的未使用导入..."
if [ -f "$PROJECT_ROOT/config/loader.py" ]; then
    # 移除未使用的 os 导入
    sed -i '' '/^import os$/d' "$PROJECT_ROOT/config/loader.py"
    # 移除未使用的 Optional 导入
    sed -i '' 's/Optional, //g' "$PROJECT_ROOT/config/loader.py"
    echo "✅ 已修复: 移除未使用的导入 'os' 和 'Optional'"
fi

echo ""
echo "============================================"
echo " 修复完成"
echo "============================================"
echo ""
echo "建议运行以下命令验证修复:"
echo "1. ruff check . --select=E,F,W --ignore=E501"
echo "2. pytest tests/ -v"
echo ""
echo "如果一切正常，可以提交修复:"
echo "git add ."
echo "git commit -m 'fix: 修复代码质量问题'"
echo "git push neworigin main"