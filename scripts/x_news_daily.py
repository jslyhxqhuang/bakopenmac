#!/usr/bin/env python3
"""
X (Twitter) 热点新闻每日推送脚本
每天早上 7 点抓取并推送到 QQ
"""

import requests
import re
import sys
import os
import json
from datetime import datetime

# ========== 配置区 ==========
APP_ID = os.environ.get("QQBOT_APP_ID", "1903672709")
APP_SECRET = os.environ.get("QQBOT_CLIENT_SECRET", "cCmNyZAlMyaCoQ2eHuXAnQ3gKycGuYCr")
USER_ID = "E19D02C454BEE853199D3F98AB573C06"  # Magic's QQ OpenID

TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"
API_BASE = "https://api.sgroup.qq.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ========== 核心函数 ==========

def get_access_token():
    """获取 QQ Bot Access Token"""
    payload = {"appId": APP_ID, "clientSecret": APP_SECRET}
    try:
        resp = requests.post(TOKEN_URL, json=payload, timeout=10)
        data = resp.json()
        if resp.status_code == 200 and "access_token" in data:
            return data["access_token"]
        else:
            print(f"❌ Token 获取失败: {data}")
    except Exception as e:
        print(f"❌ Token 请求异常: {e}")
    return None


def clean_text(text):
    """清理 HTML 实体和多余空白"""
    text = re.sub(r'&#\d+;', '', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def fetch_hackernews_top(limit=5):
    """抓取 Hacker News 热点"""
    news = []
    try:
        resp = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            headers=HEADERS, timeout=10
        )
        if resp.status_code != 200:
            return news
        ids = resp.json()[:limit]
        for sid in ids:
            r = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                headers=HEADERS, timeout=10
            )
            if r.status_code == 200:
                item = r.json()
                title = clean_text(item.get("title", ""))
                score = item.get("score", 0)
                url = item.get("url", f"https://news.ycombinator.com/item?id={sid}")
                # 标记 X/Twitter 相关
                if "x.com" in url or "twitter.com" in url:
                    title = f"🐦 {title}"
                elif score > 100:
                    title = f"🔥 {title}"
                news.append(f"  • {title}")
    except Exception as e:
        print(f"  ⚠️ HN 抓取异常: {e}")
    return news


def fetch_reddit_trending(subreddits, limit=3):
    """抓取 Reddit 热门帖子"""
    results = {}
    for sub in subreddits:
        try:
            resp = requests.get(
                f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}",
                headers={**HEADERS, "Accept": "application/json"}, timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                posts = data.get("data", {}).get("children", [])
                titles = []
                for p in posts[:limit]:
                    title = clean_text(p["data"].get("title", ""))
                    score = p["data"].get("score", 0)
                    if score > 5000:
                        title = f"🔥 {title}"
                    titles.append(f"  • {title}")
                results[sub] = titles
            else:
                results[sub] = []
        except Exception as e:
            print(f"  ⚠️ r/{sub} 抓取异常: {e}")
            results[sub] = []
    return results


def fetch_x_trending():
    """尝试抓取 X (Twitter) 热搜"""
    topics = []
    try:
        # 尝试 X 的热搜页面
        resp = requests.get(
            "https://x.com/search?q=%E7%83%AD%E7%82%B9&src=search",
            headers=HEADERS, timeout=10
        )
        if resp.status_code == 200:
            # 提取热搜词
            matches = re.findall(r'"trend[^"]*"[^>]*>([^<]+)<', resp.text)
            for m in matches[:8]:
                m = clean_text(m)
                if m and len(m) > 2:
                    topics.append(f"  • #{m}")
    except Exception as e:
        print(f"  ⚠️ X 热搜抓取异常: {e}")
    
    if not topics:
        # Fallback: 用必应搜索 X 相关热点
        try:
            resp = requests.get(
                "https://cn.bing.com/search?q=site%3Ax.com+trending&count=5",
                headers=HEADERS, timeout=10
            )
            if resp.status_code == 200:
                titles = re.findall(r'<h2[^>]*>[^<]*<a[^>]*>([^<]+)</a>', resp.text)
                for t in titles[:5]:
                    t = clean_text(t)
                    if t:
                        topics.append(f"  • {t}")
        except Exception:
            pass
    
    return topics if topics else []


def build_message():
    """构建每日热点消息"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        "📰 X / 海外热点 · 每日推送",
        f"🗓️ {now}",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]
    
    # X 热搜
    lines.append("🐦 【X 热搜】")
    x_news = fetch_x_trending()
    if x_news:
        for item in x_news[:5]:
            lines.append(item)
    else:
        lines.append("  (X 热搜暂无，获取中...)")
    lines.append("")
    
    # 科技
    lines.append("💻 【科技】")
    x_tech = fetch_x_trending()
    if x_tech:
        for item in x_tech[:3]:
            lines.append(item)
    hn_news = fetch_hackernews_top(limit=3)
    for item in hn_news[:3]:
        lines.append(item)
    lines.append("")
    
    # 体育 (Reddit)
    lines.append("⚽ 【体育】")
    reddit_sports = fetch_reddit_trending(["sports", "nba", "soccer"], limit=3)
    for sub in ["sports", "nba", "soccer"]:
        for item in reddit_sports.get(sub, [])[:1]:
            lines.append(item)
    lines.append("")
    
    # 文化 (Reddit)
    lines.append("🎬 【文化】")
    reddit_culture = fetch_reddit_trending(["movies", "television", "music"], limit=2)
    for sub in ["movies", "television", "music"]:
        for item in reddit_culture.get(sub, [])[:1]:
            lines.append(item)
    lines.append("")
    
    # 财经
    lines.append("📈 【财经】")
    reddit_finance = fetch_reddit_trending(["economy", "Finance", "investing"], limit=3)
    for sub in ["economy", "Finance", "investing"]:
        for item in reddit_finance.get(sub, [])[:1]:
            lines.append(item)
    lines.append("")
    
    # 中国相关
    lines.append("🇨🇳 【中国】")
    china_news = fetch_reddit_trending(["worldnews", "China"], limit=3)
    for sub in ["worldnews", "China"]:
        for item in china_news.get(sub, [])[:2]:
            lines.append(item)
    lines.append("")
    
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("🤖 by 小M | 数据来源：X/Reddit/HN")
    
    return "\n".join(lines)

def send_qq_message(token, content):
    """发送 QQ 私聊消息"""
    url = f"{API_BASE}/v2/users/{USER_ID}/messages"
    headers = {
        "Authorization": f"QQBot {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "content": content,
        "msg_type": 0,
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            msg_id = data.get("id", "unknown")
            print(f"✅ 消息发送成功 (ID: {msg_id[:30]}...)")
            return True
        else:
            print(f"❌ 发送失败 ({resp.status_code}): {resp.text}")
            return False
    except Exception as e:
        print(f"❌ 发送异常: {e}")
        return False


# ========== 主流程 ==========

def main():
    print(f"🔔[{datetime.now().strftime('%H:%M:%S')}] X 热点推送开始...")
    
    # 1. 获取 Token
    token = get_access_token()
    if not token:
        print("❌ 无法获取 access token，退出")
        sys.exit(1)
    print(f"✅ Token 获取成功")
    
    # 2. 构建消息
    print("📡 开始抓取热点新闻...")
    message = build_message()
    print(f"\n📝 消息长度: {len(message)} 字符")
    
    # 3. 发送
    success = send_qq_message(token, message)
    
    if success:
        print(f"🎉 推送完成！")
    else:
        print(f"❌ 推送失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
