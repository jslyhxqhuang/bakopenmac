# -*- coding: utf-8 -*-
"""
QQ 推送模块
使用腾讯 QQ 开放平台 API 直接发送 C2C 消息
"""

import json
import time
import urllib.request
import urllib.parse


# ── 凭证（从 openclaw.json 读取）─────────────────────────────────────────────
CONFIG_PATH = "/Users/magichuang/.openclaw/openclaw.json"
BOT_API_BASE = "https://bots.qq.com"
API_BASE = "https://api.sgroup.qq.com"

def load_qq_credentials():
    with open(CONFIG_PATH) as f:
        d = json.load(f)
    qq = d.get("channels", {}).get("qqbot", {})
    acc = qq.get("accounts", {}).get(qq.get("defaultAccount", "default"), qq)
    return acc.get("appId", ""), acc.get("clientSecret", "")

APP_ID, CLIENT_SECRET = load_qq_credentials()


# ── Token 管理（缓存）────────────────────────────────────────────────────────

_token_cache = {"token": None, "expires_at": 0}


def get_access_token() -> str:
    """获取 QQ Bot Access Token（剩余 10 分钟内自动刷新）"""
    global _token_cache
    if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 600:
        return _token_cache["token"]

    url = "https://bots.qq.com/app/getAppAccessToken"
    payload = json.dumps({"appId": APP_ID, "clientSecret": CLIENT_SECRET}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if data.get("access_token"):
        _token_cache["token"] = data["access_token"]
        _token_cache["expires_at"] = time.time() + int(data.get("expires_in", 7200))
        return _token_cache["token"]
    else:
        raise RuntimeError(f"获取 access_token 失败: {data}")


# ── 核心发送函数 ─────────────────────────────────────────────────────────────

def _api_request(method, path, body=None, token=None):
    """通用 API 请求"""
    url = API_BASE + path
    headers = {
        "Content-Type": "application/json;charset=utf-8",
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0",
    }
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_c2c_text(openid: str, text: str) -> bool:
    """
    发送 C2C 文本消息
    - 单条上限约 500 字，超长自动拆分为多条
    - markdown 模式: msg_type=2
    """
    token = get_access_token()

    # 拆分长消息（按换行符尽量保持段落完整）
    MAX_LEN = 450
    lines = text.split("\n")
    chunks, buf = [], ""

    for line in lines:
        if len(buf) + len(line) + 1 <= MAX_LEN:
            buf += ("\n" if buf else "") + line
        else:
            if buf:
                chunks.append(buf)
            buf = line
    if buf:
        chunks.append(buf)

    ok = True
    for i, chunk in enumerate(chunks):
        body = {"content": chunk, "msg_type": 0}
        try:
            result = _api_request("POST", f"/v2/users/{openid}/messages", body, token)
            code = result.get("code", result.get("retcode", 0))
            if code == 0:
                print(f"  [{i+1}/{len(chunks)}] 发送成功")
            else:
                print(f"  [{i+1}/{len(chunks)}] 发送失败: {result}")
                ok = False
        except Exception as e:
            print(f"  [{i+1}/{len(chunks)}] 异常: {e}")
            ok = False

        if i < len(chunks) - 1:
            time.sleep(0.4)  # 避免频率限制

    return ok


# ── CLI 入口 ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("用法: python3 qq_sender.py <openid> <消息内容>")
        sys.exit(1)

    _, openid, *msg_parts = sys.argv
    text = " ".join(msg_parts)
    print(f"向 {openid} 发送消息 ({len(text)} 字)...")
    success = send_c2c_text(openid, text)
    print("完成:", "✅ 成功" if success else "❌ 失败")
    sys.exit(0 if success else 1)
