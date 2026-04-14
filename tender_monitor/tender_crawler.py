# -*- coding: utf-8 -*-
"""
江苏公共资源交易网 招标监控爬虫
用法:
  python3 tender_crawler.py              # 立即执行一次监控
  python3 tender_crawler.py --test        # 测试模式（仅抓取不打通知）
"""

import os
import sys
import json
import time
import logging
import argparse
import requests
from datetime import datetime
from pathlib import Path

# 如果缺少 bs4，跳过 import，由调用方保证
try:
    from bs4 import BeautifulSoup
except Exception:

    def BeautifulSoup(*args, **kwargs):
        return None


from config import (
    BASE_URL,
    CATEGORIES,
    DEFAULT_CATEGORIES,
    REGION_PRIORITY,
    EXCLUDE_KEYWORDS,
    INCLUDE_KEYWORDS_KEY,
    SEEN_FILE,
    LOG_FILE,
    HEADERS,
)


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
    """返回已推送的项目编号集合"""
    if not os.path.exists(SEEN_FILE):
        return set()
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("seen_ids", []))
    except Exception:
        return set()


def save_seen(seen_ids: set):
    """保存已推送记录"""
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump({"seen_ids": list(seen_ids)}, f, ensure_ascii=False, indent=2)


# ─── 过滤逻辑 ────────────────────────────────────────────────────────────────

def is_excluded(title: str) -> bool:
    """标题含排除关键词 → 跳过"""
    title_lower = title.lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw in title:
            return True
    return False


def is_target(title: str, region: str = "") -> bool:
    """
    判断是否为目标招标项目
    - 地区优先：常州 > 江苏
    - 关键词：高速公路/公路/桥梁/路面/养护 等
    """
    text = region + title

    # 不满足任何重点关键词，直接跳过
    hit = any(kw in text for kw in INCLUDE_KEYWORDS_KEY)
    return hit


def get_region_priority(title: str, area: str = "") -> int:
    """返回地区优先级数值，越小优先级越高"""
    combined = area + title
    for i, kw in enumerate(REGION_PRIORITY):
        if kw in combined:
            return i
    return len(REGION_PRIORITY)  # 未命中任何重点地区


# ─── 爬取逻辑 ────────────────────────────────────────────────────────────────

def fetch_page(category_id: str, page: int = 1, page_size: int = 20) -> dict:
    """
    抓取指定分类的某一页数据
    返回 JSON dict（具体结构需按实际接口调整）
    """
    # ─────────────────────────────────────────────────────────────────────────
    # TODO: 这里的 URL 和 payload 格式需要根据江苏公共资源交易网实际接口调整
    #
    # 常见政府招标网站有两种模式：
    # 模式 A：JSON API（如 /jyzx/zbgg/{categoryId}?page=1&size=20）
    # 模式 B：HTML 页面（需要解析列表页）
    #
    # 建议先运行 python3 tender_crawler.py --debug 观察实际返回结构
    # ─────────────────────────────────────────────────────────────────────────

    # 示例 API URL（请根据实际情况修改）
    api_path = f"/jyzx/zbgg/{category_id}"
    params = {"page": page, "size": page_size}

    url = BASE_URL.rstrip("/") + api_path
    log.info(f"抓取页面: {url} | params={params}")

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        log.info(f"响应状态: {resp.status_code} | 内容前200字: {resp.text[:200]}")
        try:
            return resp.json()
        except Exception:
            log.warning("响应非 JSON，尝试 HTML 解析")
            return {"_html": resp.text}
    except Exception as e:
        log.error(f"请求失败 [{category_id} p{page}]: {e}")
        return {}


def parse_items_from_response(data: dict, category_id: str) -> list:
    """
    从响应数据中解析出招标记录列表
    返回 list of dict: {id, title, area, publish_date, category, url}
    """
    items = []

    # ─────────────────────────────────────────────────────────────────────────
    # TODO: 根据实际响应结构补充解析逻辑
    #       常见字段名：title, projectName, area, publishTime, projectCode, detailUrl
    # ─────────────────────────────────────────────────────────────────────────

    # 模式 A：标准列表字段
    if isinstance(data, dict):
        records = data.get("data", []) or data.get("records", []) or data.get("list", []) or data.get("result", [])
        if not isinstance(records, list):
            records = []

        for r in records:
            title = r.get("title") or r.get("projectName") or r.get("ggTitle", "")
            item_id = (
                r.get("id")
                or r.get("projectCode")
                or r.get("noticeNo")
                or r.get("infoCode", "")
            )
            area = r.get("areaName") or r.get("region") or r.get("city", "")
            pub_date = r.get("publishTime") or r.get("pubDate") or r.get("publishDate", "")
            detail_url = r.get("detailUrl") or r.get("url") or r.get("href", "")

            if not title:
                continue

            items.append({
                "id": str(item_id),
                "title": title.strip(),
                "area": area.strip(),
                "publish_date": str(pub_date),
                "category": CATEGORIES.get(category_id, category_id),
                "url": detail_url.strip() if detail_url else "",
            })

    # 模式 B：HTML 列表（BeautifulSoup 解析）
    if not items and "_html" in data:
        html = data["_html"]
        soup = BeautifulSoup(html, "lxml")
        # ─────────────────────────────────────────────────────────────────
        # TODO: 根据实际 HTML 结构补充选择器
        # 常见选择器示例：
        # rows = soup.select(".newsList li")
        # rows = soup.select("table tr")
        # rows = soup.select("div.article-list a")
        # ─────────────────────────────────────────────────────────────────
        rows = soup.select(".news-list a")  # 占位，需按实际调整
        for row in rows:
            title_el = row
            items.append({
                "id": row.get("href", "").strip(),
                "title": title_el.get_text(strip=True),
                "area": "",
                "publish_date": "",
                "category": CATEGORIES.get(category_id, category_id),
                "url": row.get("href", "").strip(),
            })

    return items


# ─── 主流程 ──────────────────────────────────────────────────────────────────

def run_monitor(categories: list = None, test: bool = False):
    """执行一次监控扫描"""
    seen_ids = load_seen()
    new_items = []

    categories = categories or DEFAULT_CATEGORIES

    for cat_id in categories:
        cat_name = CATEGORIES.get(cat_id, cat_id)
        log.info(f"\n{'='*50}\n开始抓取类别: {cat_name} ({cat_id})")

        for page in range(1, 5):  # 最多抓4页
            raw = fetch_page(cat_id, page=page)
            items = parse_items_from_response(raw, cat_id)
            if not items:
                break

            for item in items:
                title = item["title"]
                item_id = item["id"]

                # 跳过已推送
                if item_id in seen_ids:
                    continue

                # 跳过排除类
                if is_excluded(title):
                    log.debug(f"跳过（排除）: {title}")
                    continue

                # 标记为已见（即使不符合目标，也不再重复判断）
                seen_ids.add(item_id)

                # 检查是否为目标项目
                if is_target(title, item.get("area", "")):
                    new_items.append(item)
                    log.info(f"✅ 命中: [{item.get('area')}] {title} | {item_id}")

            time.sleep(1)  # 礼貌爬取，避免被封

    save_seen(seen_ids)

    if test:
        log.warning(f"[测试模式] 共发现 {len(new_items)} 条新记录（不发送通知）")
        for item in new_items:
            print(f"  [{item['category']}] {item['title']} | {item['area']} | {item['publish_date']}")
        return new_items

    if not new_items:
        log.info("本次扫描无新招标记录")
        return []

    # 按地区优先级排序
    new_items.sort(key=lambda x: get_region_priority(x["title"], x.get("area", "")))

    return new_items


def format_message(items: list) -> str:
    """将招标记录格式化为 QQ 推送消息"""
    lines = [
        f"🚨 *江苏招标推送* | {datetime.now().strftime('%m-%d %H:%M')}\n",
        f"共发现 *{len(items)}* 条新招标（去重后）\n",
        "─" * 40,
    ]

    for item in items:
        region_tag = "📍常州" if "常州" in (item.get("area") or "") else "📋江苏"
        lines.append(
            f"\n{region_tag} [{item['category']}]\n"
            f"{item['title']}\n"
            f"📅 {item['publish_date']}\n"
            f"🔗 {item['url'] or '（无链接）'}\n"
        )

    lines.append("\n─" * 40)
    lines.append("⚠️ 仅供参考，以官方公告为准")
    return "\n".join(lines)


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="江苏公共资源交易网招标监控")
    parser.add_argument("--test", action="store_true", help="测试模式：不发送通知")
    parser.add_argument("--debug", action="store_true", help="调试模式：输出详细信息")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    setup_log()
    log.info("=" * 50)
    log.info("江苏招标监控 启动")

    new = run_monitor(test=args.test)

    if new and not args.test:
        msg = format_message(new)
        print("\n【将要发送的消息】\n" + msg)
        # TODO: 这里接入 QQ 推送（通过 openclaw 工具）
        # 目前打印输出，后续接入 messaging
    elif not new and not args.test:
        log.info("无新招标，结束")
