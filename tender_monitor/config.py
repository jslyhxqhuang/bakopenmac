# -*- coding: utf-8 -*-
"""
江苏公共资源交易网 招标监控配置
"""

# 江苏公共资源交易网 base URL
BASE_URL = "https://jsggzy.jszwfw.gov.cn"

# 公告类别配置
CATEGORIES = {
    "003002001": "招标公告",
    "003002010": "招标文件提前公示",
    "003002005": "招标计划",
}

# 默认监控类别（可按需增减）
DEFAULT_CATEGORIES = list(CATEGORIES.keys())

# 地区优先级
REGION_PRIORITY = ["常州", "常州市"]

# 关键词过滤（不做投标的类别，包含任意关键词则跳过）
EXCLUDE_KEYWORDS = [
    "设计",
    "监理",
    "技术服务",
    "勘察",
    "造价",
    "审计",
    "招标代理",
    "全过程咨询",
]

# 重点关键词（优先推送，包含任意关键词则命中）
INCLUDE_KEYWORDS_KEY = [
    "高速",
    "公路",
    "桥梁",
    "路面",
    "施工",
    "改建",
    "新建",
    "养护",
    "省道",
    "国道",
]

# 推送时间（cron 表达式，工作日 12:30）
# 0 12 * * 1-5

# 本地记录文件（去重）
SEEN_FILE = "/Users/magichuang/.openclaw/workspace/tender_monitor/seen_records.json"

# 日志文件
LOG_FILE = "/Users/magichuang/.openclaw/workspace/tender_monitor/crawler.log"

# 请求头（模拟浏览器）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://jsggzy.jszwfw.gov.cn/",
}
