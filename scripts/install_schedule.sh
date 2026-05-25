#!/bin/bash
# 安装 macOS launchd 定时任务：
#   - com.stockpicker.daily-scan     每天 14:40（全量收盘扫描）
#   - com.stockpicker.afternoon-scan  每天 14:45（尾盘精选）
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$PROJECT_ROOT/.venv/bin/python"

mkdir -p "$PROJECT_ROOT/data/logs"
mkdir -p "$HOME/Library/LaunchAgents"

# ── 14:40 全量扫描 ─────────────────────────────
PLIST_DAILY_SRC="$PROJECT_ROOT/scripts/com.stockpicker.daily-scan.plist"
PLIST_DAILY_DST="$HOME/Library/LaunchAgents/com.stockpicker.daily-scan.plist"
LABEL_DAILY="com.stockpicker.daily-scan"

chmod +x "$PROJECT_ROOT/scripts/run_daily_scan.sh"

if [ -f "$PLIST_DAILY_SRC" ]; then
  sed "s|/Users/xifeiyou/Documents/workspace/stock-picker|$PROJECT_ROOT|g" \
    "$PLIST_DAILY_SRC" > "$PLIST_DAILY_DST"

  launchctl bootout "gui/$(id -u)/$LABEL_DAILY" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST_DAILY_DST"
  launchctl enable "gui/$(id -u)/$LABEL_DAILY"

  echo "✅ 已安装: $LABEL_DAILY（每天 14:40）"
  echo "   日志: $PROJECT_ROOT/data/logs/"
else
  echo "⚠️  跳过: $PLIST_DAILY_SRC 不存在"
fi

# ── 14:45 尾盘精选 ─────────────────────────────
PLIST_AFTER_SRC="$PROJECT_ROOT/scripts/com.stockpicker.afternoon-scan.plist"
PLIST_AFTER_DST="$HOME/Library/LaunchAgents/com.stockpicker.afternoon-scan.plist"
LABEL_AFTER="com.stockpicker.afternoon-scan"

if [ -f "$PLIST_AFTER_SRC" ]; then
  sed "s|/Users/xifeiyou/Documents/workspace/newstockpicker|$PROJECT_ROOT|g" \
    "$PLIST_AFTER_SRC" > "$PLIST_AFTER_DST"

  launchctl bootout "gui/$(id -u)/$LABEL_AFTER" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST_AFTER_DST"
  launchctl enable "gui/$(id -u)/$LABEL_AFTER"

  echo "✅ 已安装: $LABEL_AFTER（每天 14:45）"
  echo "   日志: $PROJECT_ROOT/data/logs/afternoon.*.log"
else
  echo "⚠️  跳过: $PLIST_AFTER_SRC 不存在"
fi

echo ""
echo "── 手动运行 ──"
echo "  全量扫描: $PROJECT_ROOT/scripts/run_daily_scan.sh"
echo "  尾盘精选: $PYTHON $PROJECT_ROOT/scripts/afternoon_scan.py"
echo ""
echo "── 查看任务状态 ──"
echo "  launchctl print gui/$(id -u)/$LABEL_DAILY"
echo "  launchctl print gui/$(id -u)/$LABEL_AFTER"
