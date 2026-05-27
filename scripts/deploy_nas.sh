#!/bin/bash
# ============================================================================
# newstockpicker — QNAP NAS 一键部署
# 用法:
#   1. SSH 到 NAS，把项目代码放到 /share/Container/newstockpicker
#   2. bash scripts/deploy_nas.sh
#
# 前置条件:
#   - QNAP Container Station 已安装并启用
#   - 已设置 BARK_URL 环境变量 (可选，推送用)
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONTAINER_NAME="stockpicker"
IMAGE_NAME="stockpicker:latest"
DATA_DIR="$PROJECT_ROOT/data"
LOG_DIR="$DATA_DIR/logs"

echo "============================================"
echo " newstockpicker — QNAP NAS 部署"
echo " 项目路径: $PROJECT_ROOT"
echo "============================================"

# ── 目录准备 ──────────────────────────────────
mkdir -p "$LOG_DIR"
echo "[log dir] $LOG_DIR"

# ── 股票池生成 ──────────────────────────────
if [ ! -f "$DATA_DIR/stock_list.csv" ]; then
    echo "[stock list] 首次生成股票池..."
    docker exec "$CONTAINER_NAME" python data/get_stock_list.py 2>/dev/null || {
        echo "⚠️  容器尚未运行，股票池将在首次扫描前自动生成"
    }
else
    echo "[stock list] 已存在 ($(wc -l < "$DATA_DIR/stock_list.csv") 行)"
fi

# ── (重新)构建镜像 ────────────────────────────
echo "[docker] 构建镜像 $IMAGE_NAME ..."
cd "$PROJECT_ROOT"
docker build -t "$IMAGE_NAME" .

# ── 停止旧容器（如果存在）────────────────────
if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
    echo "[docker] 停止旧容器..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
fi

# ── 启动新容器 ──────────────────────────────
echo "[docker] 启动容器 $CONTAINER_NAME ..."
docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    --memory="2g" \
    -v "$DATA_DIR:/app/data" \
    -v "$SCRIPT_DIR:/app/scripts" \
    -v "$PROJECT_ROOT/strategies:/app/strategies" \
    -v "$PROJECT_ROOT/app.py:/app/app.py" \
    -e BARK_URL="${BARK_URL:-https://api.day.app/hen9ePKgKGwLGi4VLvwrJn/}" \
    -e TZ=Asia/Shanghai \
    "$IMAGE_NAME"

echo "[docker] 容器运行中: $(docker ps --filter name=$CONTAINER_NAME --format '{{.Status}}')"

# ── 首次生成股票池 ────────────────────────────
echo "[stock list] 生成股票池..."
docker exec "$CONTAINER_NAME" python data/get_stock_list.py || {
    echo "⚠️  股票池生成失败，请稍后重试或检查网络"
}

# ── 安装 crontab ─────────────────────────────
CRON_FILE="$SCRIPT_DIR/crontab.nas"
if [ -f "$CRON_FILE" ]; then
    echo "[cron] 安装定时任务..."
    # 将 crontab 中的路径替换为实际路径
    sed "s|PROJECT_ROOT|$PROJECT_ROOT|g" "$CRON_FILE" | crontab -
    echo "[cron] 当前 crontab:"
    crontab -l | grep stockpicker || echo "  (无 stockpicker 条目)"
else
    echo "⚠️  未找到 crontab.nas，跳过定时任务安装"
    echo "   手动添加: crontab -e"
fi

echo ""
echo "============================================"
echo " 部署完成"
echo "============================================"
echo ""
echo " 容器状态:   docker ps --filter name=$CONTAINER_NAME"
echo " 查看日志:   docker logs -f $CONTAINER_NAME"
echo " 手动扫描:   docker exec $CONTAINER_NAME python scripts/afternoon_scan.py"
echo " 全量扫描:   docker exec $CONTAINER_NAME python strategies/scan_all.py"
echo " 进入容器:   docker exec -it $CONTAINER_NAME bash"
echo ""
echo " 定时任务:"
echo "   14:40 尾盘精选 → docker exec $CONTAINER_NAME python scripts/afternoon_scan.py"
echo "   16:00 收盘全量 → docker exec $CONTAINER_NAME python scripts/run_all.py"
echo ""
echo " 日志目录: $LOG_DIR"
