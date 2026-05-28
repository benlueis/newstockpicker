# QNAP NAS 部署用 Dockerfile
# 构建: docker build -t stockpicker .
# 运行: docker run -d --name stockpicker \
#          -v $(pwd)/data:/app/data \
#          -v $(pwd)/scripts:/app/scripts \
#          -v $(pwd)/strategies:/app/strategies \
#          -e BARK_URL=https://api.day.app/your-key/ \
#          stockpicker

FROM python:3.11-slim

LABEL description="newstockpicker - A股选股扫描"

# 系统依赖（pandas / matplotlib / pyarrow 编译需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libc6-dev \
    libfreetype6-dev libpng-dev \
    tzdata \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 依赖安装（分层缓存，改 requirements.txt 才重建这层）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 源码
COPY scripts/     ./scripts/
COPY strategies/  ./strategies/
COPY data/        ./data/
COPY app.py       .

# 创建非 root 用户运行
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 日志输出不缓冲（cron 中可即时看到）
ENV PYTHONUNBUFFERED=1

# 容器保持运行，由外部 cron 触发
CMD ["tail", "-f", "/dev/null"]
