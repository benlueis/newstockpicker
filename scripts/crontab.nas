# ============================================================================
# newstockpicker — QNAP NAS crontab
# 由 scripts/deploy_nas.sh 自动安装，也可手动 crontab -e 粘贴以下内容。
#
# 说明:
#   - 所有脚本通过 docker exec 在 stockpicker 容器中执行
#   - 日志写入 PROJECT_ROOT/data/logs/
#   - 请设置 BARK_URL 环境变量以启用 iPhone 推送
# ============================================================================

# 每天 14:40 — 尾盘精选扫描（提前 5 分钟拉数据，14:45 拿到结果）
40 14 * * 1-5 docker exec stockpicker python scripts/afternoon_scan.py >> PROJECT_ROOT/data/logs/afternoon.log 2>&1

# 每天 16:00 — 收盘全量扫描（四策略 + Bark 推送）
0 16 * * 1-5 docker exec stockpicker python scripts/run_all.py >> PROJECT_ROOT/data/logs/daily.log 2>&1

# 每周一 8:00 — 刷新股票池（定期更新新股 / 退市）
0 8 * * 1 docker exec stockpicker python data/get_stock_list.py >> PROJECT_ROOT/data/logs/stocklist.log 2>&1
