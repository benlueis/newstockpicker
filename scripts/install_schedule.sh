#!/bin/bash
# 安装 macOS launchd 定时任务：每个交易日 14:40 扫描
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_SRC="$PROJECT_ROOT/scripts/com.stockpicker.daily-scan.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.stockpicker.daily-scan.plist"

chmod +x "$PROJECT_ROOT/scripts/run_daily_scan.sh"

mkdir -p "$PROJECT_ROOT/data/logs"
mkdir -p "$HOME/Library/LaunchAgents"

# 若路径变更，用当前项目路径重写 plist 中的脚本路径
sed "s|/Users/xifeiyou/Documents/workspace/stock-picker|$PROJECT_ROOT|g" \
  "$PLIST_SRC" > "$PLIST_DST"

launchctl bootout "gui/$(id -u)/com.stockpicker.daily-scan" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"
launchctl enable "gui/$(id -u)/com.stockpicker.daily-scan"

echo "已安装定时任务: com.stockpicker.daily-scan"
echo "  时间: 每天 14:40（脚本内会跳过周末与非交易日）"
echo "  日志: $PROJECT_ROOT/data/logs/"
echo ""
echo "手动立即跑一次:"
echo "  $PROJECT_ROOT/scripts/run_daily_scan.sh"
echo ""
echo "查看任务状态:"
echo "  launchctl print gui/$(id -u)/com.stockpicker.daily-scan"
