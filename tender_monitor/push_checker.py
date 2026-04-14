# -*- coding: utf-8 -*-
"""
push_checker.py
每 30 分钟检查 pending_push.txt，有内容则尝试 QQ 推送
"""
import sys
import os

# 将 tender_monitor 目录加入 path（以便导入 qq_sender）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PUSH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pending_push.txt")

def main():
    if len(sys.argv) < 2:
        print("用法: python3 push_checker.py <openid>")
        sys.exit(1)

    openid = sys.argv[1]

    # 读取待推送内容
    if not os.path.exists(PUSH_FILE):
        print("无待推送内容（文件不存在）")
        sys.exit(0)

    with open(PUSH_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        print("无待推送内容（文件为空）")
        sys.exit(0)

    print(f"发现待推送内容 ({len(content)} 字)，尝试发送...")

    # 发送 QQ 消息
    from qq_sender import send_c2c_text
    success = send_c2c_text(openid, content)

    if success:
        # 清空文件
        with open(PUSH_FILE, "w", encoding="utf-8") as f:
            f.write("")
        print("推送成功，已清空队列")
    else:
        print("推送失败，保留队列，下次重试")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
