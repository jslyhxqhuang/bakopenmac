#!/bin/bash
# tender_cron_setup.sh
# 设置工作日 12:30 自动执行江苏招标监控

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="/opt/homebrew/bin/python3"
PYTHON_SCRIPT="$SCRIPT_DIR/tender_crawler.py"
LOG="$SCRIPT_DIR/run.log"

# 定时任务行：工作日 12:30 执行
CRON_LINE="30 12 * * 1-5 cd $SCRIPT_DIR && $PYTHON_BIN $PYTHON_SCRIPT >> $LOG 2>&1"

echo "当前定时任务："
crontab -l 2>/dev/null | grep tender_crawler || echo "（无）"

echo ""
echo "将添加以下定时任务："
echo "$CRON_LINE"
echo ""

read -p "确认添加？(y/N) " confirm
if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
    (crontab -l 2>/dev/null | grep -v tender_crawler; echo "$CRON_LINE") | crontab -
    echo "✅ 已添加定时任务"
    crontab -l | grep tender_crawler
else
    echo "已取消"
fi
