# 江苏招标监控 · 使用说明

## 目录结构

```
tender_monitor/
├── config.py              # 配置文件（URL、关键词、过滤规则）
├── tender_crawler.py      # 主爬虫脚本
├── seen_records.json      # 已推送记录（自动生成）
├── crawler.log            # 运行日志（自动生成）
├── run.log                # cron 执行日志（自动生成）
├── tender_cron_setup.sh   # cron 安装脚本
└── README.md              # 本文件
```

## 快速开始

### 1. 本地调试（抓取一次，看输出结构）

```bash
cd ~/.openclaw/workspace/tender_monitor
python3 tender_crawler.py --debug
```

> 重点观察：日志里的 `响应状态` 和 `内容前200字`，这能帮你确认实际接口格式。

### 2. 测试模式（不打通知，仅显示会推送的内容）

```bash
python3 tender_crawler.py --test
```

### 3. 安装定时任务（工作日 12:30）

```bash
chmod +x tender_cron_setup.sh
./tender_cron_setup.sh
```

### 4. 查看日志

```bash
tail -f tender_monitor/crawler.log
```

---

## 关键配置（修改 config.py）

| 配置项 | 说明 |
|--------|------|
| `INCLUDE_KEYWORDS_KEY` | 命中哪些关键词才算目标招标 |
| `EXCLUDE_KEYWORDS` | 含这些词直接跳过（设计/监理/技术服务…） |
| `REGION_PRIORITY` | 地区优先级，列表中越靠前优先级越高 |
| `CATEGORIES` | 公告类别 ID |

---

## 🔧 接口适配（重点！）

江苏公共资源交易网有多种可能的接口形式，**你需要先跑一次 `--debug` 观察实际返回**，然后修改 `tender_crawler.py` 里两处 `# TODO` 注释对应的解析逻辑。

### 常见接口模式

**模式 A：JSON API**
```
https://jsggzy.jszwfw.gov.cn/jyzx/zbgg/003002001?page=1&size=20
```
响应示例：
```json
{
  "data": [
    {
      "title": "沪武高速公路...",
      "projectCode": "JSGG-20260414-001",
      "areaName": "常州市",
      "publishTime": "2026-04-14",
      "detailUrl": "/jyzx/zbgg/detail/xxx"
    }
  ]
}
```

**模式 B：HTML 列表页**
需要 BeautifulSoup 解析，修改 `parse_items_from_response` 里的 CSS 选择器。

---

## 推送渠道

目前代码会在 cron 执行后打印消息到日志。**接入 QQ 推送**需要修改 `run_monitor()` 末尾，通过 OpenClaw messaging API 发送。

如需飞书 / 邮件推送，告诉我，我来加。

---

## 常见问题

**Q: 报错 `fetch failed`**
→ 网站可能需要登录或 IP 白名单，先用浏览器验证能否访问。

**Q: 抓到的数据为空**
→ 接口 URL 或参数名可能有变化，检查 `--debug` 日志里的实际响应。

**Q: 重复推送**
→ `seen_records.json` 损坏，删掉重建即可：
  ```bash
  echo '{"seen_ids": []}' > seen_records.json
  ```
