# MEMORY.md - 长期记忆

## 关于 Magic
- 名字：Magic
- 时区：Asia/Shanghai (GMT+8)
- 通过 openclaw-tui 沟通
- 偏好：简洁直接，不废话

## 重要配置
- 记忆备份仓库：https://github.com/jslyhxqhuang/bakopenmac.git（私有）
- 每日自动同步时间：09:00（crontab）
- 自动同步脚本：~/.openclaw/workspace/.git_sync.sh

## 恢复流程
```bash
cd ~/.openclaw/workspace
git clone https://github.com/jslyhxqhuang/bakopenmac.git .
```

## running_page 项目 (jslyhxqhuang/running_page)
- 仓库：https://github.com/jslyhxqhuang/running_page
- 问题：步行、徒步、游泳、骑行被错误计入跑步统计
- 修复内容：
  1. `run_page/generator/__init__.py`：sync() 和 load() 过滤改为 `Run + Trail Run`（原来只过滤 Run，导致走路/徒步混入）
  2. `run_page/gen_svg.py`：--sport-type running 同时包含 running 和 trail running（解决越野跑被误排除）
  3. `.github/workflows/run_data_sync.yml`：strava_sync 命令加上 --only-run 参数，防止每次 sync 把走路数据重新拉回来
  4. 手动清理 `src/static/activities.json`，移除所有非跑步历史记录（Walk 231条、Swim 173条、Hike 97条、Ride 143条等）
- 关键 commit：fd7f7558（加 --only-run）、bf8e7a39（清理历史数据）、2fe31b2d（black 格式化）
- 修复后数据：1787 条纯跑步记录（Run）
- 注意：需确保 workflow 里的 strava_sync 命令始终带有 --only-run

## 江苏招标监控项目 (tender_monitor)
- 路径：`~/.openclaw/workspace/tender_monitor/`
- 功能：监控江苏公共资源交易网（jsggzy.jszwfw.gov.cn）交通工程招标公告
- 监控类别：003002001（招标公告）/ 003002010（文件提前公示）/ 003002005（招标计划）
- 过滤规则：排除设计/监理/技术服务，只保留施工类（高速公路/国道/省道/桥梁/路面/养护）
- 推送时间：每天 13:00（工作日），cron 配置在 `tender_cron_setup.sh`
- 推送渠道：QQ 私聊（c2c），API 主动推送有 500 错误（需先激活授权）
- 已扫描记录：51 条（持续积累）
- Git：`https://github.com/jslyhxqhuang/bakopenmac.git`

## 每日简报定时任务（2026-04-20 修复）
- 监控页面：https://jtyst.jiangsu.gov.cn/col/col41407/index.html（江苏交通运输厅建设管理）
- 定时时间：每天下午 4:00（macOS LaunchAgent）
- 脚本：~/.openclaw/workspace/cron-jt.sh（修复版，用绝对路径 /opt/homebrew/bin/node 和 /opt/homebrew/bin/openclaw）
- LaunchAgent：~/Library/LaunchAgents/com.magichuang.openclaw.jt-monitor.plist
- 内容类型：公路水运信用评价、资质审批、材料指导价格（非招标公告）

## 模型配置（2026-04-20 更新）
- **当前默认模型**：`aicodee/MiniMax-M2.7-highspeed`（`newapimac` 已不可用，用户确认切换至此）
- aicodee provider（https://v2.aicodee.com）仅暴露 2 个模型：MiniMax-M2.5-highspeed、MiniMax-M2.7-highspeed
- `newapimac/MiniMax-M2.7-highspeed` — 曾为默认模型（2026-04-16 配置），现不可用

## MiniMax TTS HD（2026-04-28 配置）
- **用途**：每日新闻语音播报（news_voice_daily.py）
- **API**：POST `https://api.minimaxi.com/v1/t2a_v2`
- **模型**：speech-2.8-hd，声音：`Cantonese_GentleLady`（粤语·温柔女声）
- **API Key**：`sk-cp-bBvPXT4d8MrklAmqrYlA-_4TlbzfSpIdbfYfajC2onRid6zV_zD6vXbqIlS8b29kGFkv06ct674CuL7itzDfTvPAguL5k3MDnAQNY15-61dgNOUUkbWNMGg`
- **重要**：MiniMax 返回 raw PCM（32kHz/16bit/mono），不是 MP3！需 ffmpeg 转码后再送 silk-wasm
- **TTS 脚本**：`~/.openclaw/workspace/scripts/news_voice_daily.py`
- **声音**：`Cantonese_GentleLady`（粤语·温柔女声，2026-04-29 确认）
- **Fallback**：额度超限 → macOS say Tingting（女声）
- **字数上限**：1500 字/天（MiniMax 4000 tokens 额度，约 3000 tokens，保留 buffer）

## FNOS 服务器 (hermes-agent)
- 主机：jslyhxq@FNOS（Docker 环境）
- 容器名：hermes-agent
- 中转 API：https://newapi.hizui.cn/v1（即 newapimac provider）
- API Key：sk-47MWXrCifE78aVvQS7NJv82gFIkN8kdThxrwgw6IKBYDsYAS
- 模型：MiniMax-M2.7，Provider：openai-compatible
- 配置路径：/opt/data/.hermes/
- 状态：配置写入成功，API 认证问题仍在调试

## 已完成的重要事项
- 2026-04-04：完成记忆 GitHub 私有仓库备份配置，每日自动 sync
- 2026-04-11：OpenClaw v2026.4.2 → v2026.4.10 更新，经历 npm ENOTEMPTY 冲突，通过 openclaw doctor --fix 修复，Gateway 现正常运行
- 2026-04-17：完成浏览器自动化能力（Playwright + browser-cli），可在 Mac mini 上做网页截图、导航、元素交互

## 企业微信配置（未完成）
- 状态：DDNSTO 隧道已搭建（`https://wecomfn.tocmcc.cn`），卡在企微回调 URL 域名备案校验
- 障碍：企微要求回调 URL 域名 ICP 备案主体与企业主体一致，DDNSTO 域名不符合
- 方案：需用自有域名 jshclq.com + Cloudflare Tunnel，但 DNS 迁移复杂暂缓
- OpenClaw 企微插件已安装（openclaw-wecom-channel）

## browser-cli 浏览器自动化
- 路径：`~/.openclaw/workspace/browser-cli.js`
- 引擎：Playwright + 完整 Google Chrome（`/Applications/Google Chrome.app`）
- 解决了 macOS ARM 上 Chromium Headless Shell 渲染白屏问题
- 命令：navigate / screenshot / act / extract / close
- TOOLS.md 已更新记录

## 每日新闻语音播报（中文版，全量重构 2026-04-28）
- 脚本：`~/.openclaw/workspace/scripts/news_voice_daily.py`
- 触发时间：每天早上 6:00（LaunchAgent）
- 推送渠道：QQ 私聊（c2c）
- 代理：`http://127.0.0.1:7897`（Clash Verge）
- 发送方式：Node.js + silk-wasm 编码 SILK 格式，调用 QQ 机器人 API
- silk-wasm 路径：`/Users/magichuang/.openclaw/plugin-runtime-deps/openclaw-2026.4.24-da6bdffc3d96/node_modules/silk-wasm/lib/index.cjs`
- 排版风格：公众号样式（emoji 分类标题 + 简短条目，文字版 QQ 直接发文本）

### 新闻来源（共 9 个，并行抓取）
| 分类 | 来源 | 方式 |
|------|------|------|
| 科技/商业 | 钛媒体 RSS（tmtpost） | 代理 |
| 财经 | 新浪财经 | 代理 |
| 体育 | 网易体育 | 代理 |
| 军事政治 | 观察者网 | 代理 |
| 国际 | BBC 中文 RSS | 代理 |
| 海外华文 | 联合早报 + 大公网 | 代理 |
| 台港财经 | UDN 财经 + 星岛日报 | 代理 |

### 文字版推送
- 排版：公众号样式（emoji 分类 + 简短条目，QQ 直接发文本）
- 语音：say -v Tingting + ffmpeg 转 MP3 + silk-wasm 编码 SILK + QQ API 发送
