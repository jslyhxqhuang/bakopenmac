# -*- coding: utf-8 -*-
"""
江苏公共资源交易网 招标监控爬虫
用法:
  python3 tender_crawler.py              # 立即执行一次监控
  python3 tender_crawler.py --test        # 测试模式（仅抓取不打通知）
  python3 tender_crawler.py --debug       # 调试模式（详细输出）
"""

import os
import re
import sys
import json
import time
import logging
import argparse
import urllib.request
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from config import (
    BASE_URL,
    CATEGORIES,
    DEFAULT_CATEGORIES,
    REGION_PRIORITY,
    EXCLUDE_KEYWORDS,
    INCLUDE_KEYWORDS_KEY,
    SEEN_FILE,
    LOG_FILE,
)

# ─── 常量 ─────────────────────────────────────────────────────────────────────

API_URL = "http://jsggzy.jszwfw.gov.cn/inteligentsearch/rest/esinteligentsearch/getFullTextDataNew"
PAGES_PER_CONFIG = 2   # 每个类别查几页（每页30条）
DAYS_LIMIT = 7         # 只看最近 N 天内的公告
PUSH_QUEUE_FILE = "/Users/magichuang/.openclaw/workspace/tender_monitor/pending_push.txt"

# ─── 工具函数 ─────────────────────────────────────────────────────────────────

def clean_html_text(s):
    """去除 HTML 标签"""
    if not s:
        return ""
    return re.sub(r"<[^>]+>", "", s).strip()


# ─── 日志配置 ────────────────────────────────────────────────────────────────

def setup_log():
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


log = logging.getLogger("tender_monitor")


# ─── 存储 / 去重 ─────────────────────────────────────────────────────────────

def load_seen() -> set:
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f).get("seen_ids", []))
        except Exception:
            pass
    return set()


def save_seen(seen_ids: set):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump({"seen_ids": list(seen_ids)}, f, ensure_ascii=False, indent=2)


# ─── 过滤逻辑 ────────────────────────────────────────────────────────────────

def is_excluded(title: str) -> bool:
    """标题含排除关键词 → 跳过"""
    for kw in EXCLUDE_KEYWORDS:
        if kw in title:
            return True
    return False


def is_target(title: str, region: str = "") -> bool:
    """判断是否为目标招标项目（交通工程类）"""
    text = region + title
    return any(kw in text for kw in INCLUDE_KEYWORDS_KEY)


def is_recent(date_str: str) -> bool:
    """判断日期是否在 DAYS_LIMIT 天内"""
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return d >= datetime.now() - timedelta(days=DAYS_LIMIT)
    except Exception:
        return False


def get_region_priority(title: str, area: str = "") -> int:
    """返回地区优先级数值，越小优先级越高"""
    combined = area + title
    for i, kw in enumerate(REGION_PRIORITY):
        if kw in combined:
            return i
    return len(REGION_PRIORITY)


# ─── 爬取逻辑 ────────────────────────────────────────────────────────────────

def fetch_category(cat_name: str, cat_num: str) -> list:
    """
    抓取一个类别的所有页，返回记录列表
    """
    results = []
    for page in range(PAGES_PER_CONFIG):
        pn = page * 30
        payload = json.dumps({
            "token": "", "pn": pn, "rn": 30, "wd": "",
            "fields": "title,infodateformat,categoryname,categorynum,fieldvalue,linkurl,infoid",
            "cnum": "001",
            "sort": '{"infodateformat":"0"}',
            "ssort": "",
            "cl": 500,
            "terminal": "0",
            "condition": [
                {"fieldName": "categorynum", "isLike": False, "likeType": 1, "equal": cat_num}
            ],
            "time": None,
            "highlights": "title",
            "statistics": None,
            "unionCondition": None,
            "accuracy": "",
            "noParticiple": "",
            "searchRange": None,
            "isBusiness": "1",
        }).encode("utf-8")

        req = urllib.request.Request(
            API_URL,
            data=payload,
            headers={
                "Content-Type": "application/json;charset=utf-8",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            records = raw.get("result", {}).get("records", [])
            if not records:
                break
            results.extend(records)
            log.debug(f"  [{cat_name}] 第{page+1}页: 获得 {len(records)} 条")
            time.sleep(0.3)  # 礼貌爬取
        except Exception as e:
            log.error(f"  [{cat_name}] 第{page+1}页失败: {e}")
            break

    return results


def run_monitor(test: bool = False) -> list:
    """
    主流程：并发抓取 → 过滤 → 去重 → 返回新增记录
    """
    seen_ids = load_seen()
    all_items = []
    new_items = []

    log.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 监控启动 | 近{DAYS_LIMIT}天 | 类别: {list(CATEGORIES.keys())}")

    # 并发抓取三个类别
    def fetch_task(cat_num):
        cat_name = CATEGORIES.get(cat_num, cat_num)
        return cat_num, fetch_category(cat_name, cat_num)

    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(fetch_task, cn): cn for cn in DEFAULT_CATEGORIES}
        for f in as_completed(futures):
            try:
                cat_num, records = f.result()
                all_items.extend(records)
            except Exception as e:
                log.error(f"抓取任务异常: {e}")

    # 处理每条记录
    for r in all_items:
        raw_title = r.get("title", "")
        title = clean_html_text(raw_title)
        date = r.get("infodateformat", "")
        area = r.get("fieldvalue", "") or r.get("zhuanzai", "")
        cat_api = r.get("categoryname", "")

        # 组合 ID：infoid + categorynum 防止不同类别同一 infoid 重复
        item_id = f"{r.get('infoid', '')}_{r.get('categorynum', '')}"

        # 类别过滤（只保留目标类别）
        if not any(cat_api.startswith(t) for t in CATEGORIES.values()):
            continue

        # 日期过滤
        if not is_recent(date):
            continue

        # 排除关键词过滤
        if is_excluded(title):
            log.debug(f"跳过（排除词）: {title}")
            continue

        item = {
            "id": item_id,
            "title": title,
            "date": date,
            "area": area,
            "category": cat_api,
            "link": f"http://jsggzy.jszwfw.gov.cn{r.get('linkurl', '')}",
        }

        # 目标关键词过滤
        if not is_target(title, area):
            log.debug(f"跳过（非目标）: {title}")
            continue

        # 去重：未见过 → 新增
        if item_id not in seen_ids:
            new_items.append(item)
            seen_ids.add(item_id)
            log.info(f"✅ 新增: [{area}] {title} | {date}")
        else:
            log.debug(f"已见（跳过）: {title}")

    save_seen(seen_ids)

    # 按地区优先级排序（常州优先）
    new_items.sort(key=lambda x: (
        get_region_priority(x["title"], x.get("area", "")),
        x.get("date", ""),
    ))

    return new_items


# ─── 消息格式化 ──────────────────────────────────────────────────────────────

def format_message(items: list) -> str:
    """格式化为 QQ 推送消息"""
    lines = [
        f"🚨 *江苏省交通工程招标日报*",
        f"📅 {datetime.now().strftime('%Y-%m-%d')} | 工作日 12:30 自动推送\n",
        f"共发现 **{len(items)}** 条新公告\n",
        "─" * 40,
    ]

    # 按类别分组
    groups = {}
    for item in items:
        groups.setdefault(item["category"], []).append(item)

    for cat, cat_items in groups.items():
        lines.append(f"\n▶ *{cat}* （{len(cat_items)}条）")
        for i in cat_items:
            region_tag = "📍常州" if "常州" in (i.get("area") or "") else "📋江苏"
            lines.append(f"\n  {region_tag} {i['title']}")
            lines.append(f"  📅 {i['date']}")
            lines.append(f"  🔗 {i['link']}")

    lines.append("\n" + "─" * 40)
    lines.append("⚠️ 仅供参考，以官方公告为准")
    return "\n".join(lines)


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="江苏公共资源交易网招标监控")
    parser.add_argument("--test", action="store_true", help="测试模式：不写推送队列")
    parser.add_argument("--debug", action="store_true", help="调试模式：详细日志")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    setup_log()
    log.info("=" * 50)
    log.info("江苏招标监控 启动")

    new = run_monitor(test=args.test)

    if not new:
        log.info("今日无新增公告")
        sys.exit(0)

    if args.test:
        log.warning(f"[测试模式] 共发现 {len(new)} 条新记录")
        for item in new:
            print(f"  [{item['category']}] {item['title']} | {item['area']} | {item['date']}")
        sys.exit(0)

    # 正常模式：写入推送队列，并尝试直接 QQ 推送
    msg = format_message(new)
    with open(PUSH_QUEUE_FILE, "w", encoding="utf-8") as f:
        f.write(msg)
    log.info(f"已写入推送队列: {PUSH_QUEUE_FILE}")

    # 尝试直接 QQ 推送（如果接口可用）
    try:
        from qq_sender import send_c2c_text
        user_openid = "E19D02C454BEE853199D3F98AB573C06"
        ok = send_c2c_text(user_openid, msg)
        if ok:
            log.info("✅ QQ 推送成功")
            # 清空队列
            with open(PUSH_QUEUE_FILE, "w", encoding="utf-8") as f:
                f.write("")
        else:
            log.warning("⚠️ QQ 推送失败，保留队列供下次重试")
            print("\n⚠️ QQ 推送失败，消息已写入队列")
    except Exception as e:
        log.warning(f"QQ 推送异常: {e}，保留队列供下次重试")

    print("\n" + msg)
