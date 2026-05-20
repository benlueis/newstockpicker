#!/bin/bash
# 每日低位突破扫描（建议由 launchd 在 14:40 触发）
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

LOG_DIR="$PROJECT_ROOT/data/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/scan_$(date +%Y%m%d_%H%M%S).log"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# 周末跳过
DOW=$(date +%u)
if [ "$DOW" -gt 5 ]; then
  log "周末，跳过扫描"
  exit 0
fi

PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  log "错误: 未找到虚拟环境 $PYTHON"
  exit 1
fi

log "开始低位突破全市场扫描"
"$PYTHON" "$PROJECT_ROOT/scripts/daily_scan.py" >> "$LOG_FILE" 2>&1
STATUS=$?

if [ "$STATUS" -eq 0 ]; then
  log "扫描完成"
else
  log "扫描失败，退出码 $STATUS"
fi

exit "$STATUS"
