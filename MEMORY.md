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

## 已完成的重要事项
- 2026-04-04：完成记忆 GitHub 私有仓库备份配置，每日自动 sync
