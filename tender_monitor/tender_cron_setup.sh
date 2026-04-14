#!/bin/bash
# tender_cron_setup.sh
# 安装江苏招标监控 + QQ 推送定时任务

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="/opt/homebrew/bin/python3"
CRAWLER="$SCRIPT_DIR/tender_crawler.py"
QQ_SENDER="$SCRIPT_DIR/qq_sender.py"
PUSH_CHECKER="$SCRIPT_DIR/push_checker.py"
PUSH_FILE="$SCRIPT_DIR/pending_push.txt"
CRAWLER_LOG="$SCRIPT_DIR/run.log"
PUSH_LOG="$SCRIPT_DIR/push.log"
USER_OPENID="E19D02C454BEE853199D3F98AB573C06"

# ── 定时任务 ────────────────────────────────────────────────────────────────
# 1. 工作日 12:30  执行爬虫（抓数据 + 写 pending_push.txt）
CRAWLER_CRON="30 12 * * 1-5 cd $SCRIPT_DIR && $PYTHON_BIN $CRAWLER >> $CRAWLER_LOG 2>&1"

# 2. 工作日 每30分钟 检查 pending_push.txt，有内容则尝试 QQ 推送
PUSH_CRON="0,30 9-18 * * 1-5 $PYTHON_BIN $PUSH_CHECKER $USER_OPENID >> $PUSH_LOG 2>&1"

install_cron() {
    local label="$1"
    local cron_line="$2"
    echo "─── $label ───"
    echo "$cron_line"
    existing=$(crontab -l 2>/dev/null | grep -v "$label" | grep -v "^#.*tender_monitor\|^#.*push_checker" | grep .)
    (echo "$existing"; echo "# $label"; echo "$cron_line") | crontab -
    echo "✅ 已安装"
    echo ""
}

echo "开始安装定时任务..."
echo ""

install_cron "江苏招标爬虫 (工作日 12:30)" "$CRAWLER_CRON"
install_cron "QQ推送检查 (工作日 9:00-18:00 每30分)" "$PUSH_CRON"

echo "─── 当前全部定时任务 ───"
crontab -l 2>/dev/null | grep -v "^# " | grep -v "^$" || echo "（无）"
echo ""
echo "✅ 安装完成"
