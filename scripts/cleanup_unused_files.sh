#!/bin/bash
# ============================================================================
# 清理未使用的文件
# 用法: bash scripts/cleanup_unused_files.sh
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================"
echo " 清理未使用的文件"
echo " 项目路径: $PROJECT_ROOT"
echo "============================================"

# 创建备份目录
BACKUP_DIR="$PROJECT_ROOT/.backup/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
echo "备份目录: $BACKUP_DIR"

# 定义要清理的文件
UNUSED_FILES=(
    "scripts/_backfill_0526.py"
    "scripts/_clr.py"
    "scripts/_diag_pt.py"
    "scripts/_test_afternoon.py"
    "scripts/com.stockpicker.afternoon-scan.plist"
    "scripts/com.stockpicker.daily-scan.plist"
)

# 清理文件
echo ""
echo "📌 清理未使用的文件..."

for file in "${UNUSED_FILES[@]}"; do
    full_path="$PROJECT_ROOT/$file"
    if [ -f "$full_path" ]; then
        # 备份文件
        cp "$full_path" "$BACKUP_DIR/"
        echo "✅ 已备份: $file"
        
        # 删除文件
        rm "$full_path"
        echo "🗑️  已删除: $file"
    else
        echo "⚠️  文件不存在: $file"
    fi
done

echo ""
echo "============================================"
echo " 清理完成"
echo "============================================"
echo ""
echo "备份位置: $BACKUP_DIR"
echo ""
echo "如果需要恢复文件，可以从备份目录复制回来"
echo ""
echo "建议运行以下命令验证:"
echo "1. ls scripts/ | grep -E '^_'"
echo "2. git status"