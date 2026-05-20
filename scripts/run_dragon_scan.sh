#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

LOG_DIR="$PROJECT_ROOT/data/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/dragon_$(date +%Y%m%d_%H%M%S).log"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

DOW=$(date +%u)
if [ "$DOW" -gt 5 ]; then
  log "周末，跳过龙头扫描"
  exit 0
fi

PYTHON="$PROJECT_ROOT/.venv/bin/python"
log "开始市场龙头扫描"
"$PYTHON" "$PROJECT_ROOT/scripts/scan_dragon.py" >> "$LOG_FILE" 2>&1
log "扫描结束，退出码 $?"
