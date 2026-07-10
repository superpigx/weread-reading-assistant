# Changelog

本文件记录每次功能升级。**规则（与根目录 `VERSION` 同步）：**

- 新增 / 变更功能 → 在此**追加一个版本条目**，并同步修改根目录 `VERSION`。
- 升级后若已配置 GitHub remote → `git add -A && git commit -m "..." && git push`。
- 升级后记得同步更新 `SKILL.md`（命令说明）与 `README.md`（用户文档）。

格式参考 [Keep a Changelog](https://keepachangelog.com/)，版本号采用 [SemVer](https://semver.org/)。

---

## [1.0.0] - 2026-07-11

当前稳定基线。由早期 `weread-extract-mentioned`（提取提及书）与 `weread-add-to-shelf`（批量加书架）两个 skill 合并而来，统一为单一入口、共享引擎。

### Added
- 统一 CLI 入口 `scripts/weread.py`，命令注册表 `COMMANDS` 分发；新增功能只需在 `commands/` 加模块 + 登记一行。
- 子命令：`extract`（提取书中提及的书）、`expand`（扩展阅读清单，带微信读书链接、**不加书架**）、`shelf`（批量加书架，中文优先 + 评分最高）、`search`（单本搜索）、`verify`（登录态预检）、`login`（首次扫码登录）、`cleanup`（清理后台进程）、`seed`（克隆已登录 profile）。
- **Playwright 引擎**（`channel=chrome/edge`），取代脆弱的 agent-browser daemon 与手搓 CDP-over-WebSocket。
- 默认 **headed 有头模式**：登录失效时在弹出的真实窗口扫码；`HEADLESS=1` 退回无头（自动追加 `--headless=new`）。
- 浏览器**自动降级**：指定 > Chrome > Edge，同一套 Playwright 参数，对用户透明。
- **自动清理**：脚本退出（`try/finally` + `atexit`）自动关本会话并杀残余 agent-browser daemon，只杀自己人。
- **性能优化**：用 `wait_for_selector` / `wait_for_function` 精准等待元素，替代固定 `sleep`；登录检测一次会话只做一次（根治误判未登录白等 120s）。

### Changed
- 合并两个 skill，共享引擎与清理逻辑，消除重复维护。
- profile 改用独立 `WereadCDP2`；`seed` 时复制到 `<dst>/Default`（避免扁平铺平导致 Chrome 退出码 21）。

### Fixed
- Chrome 149 移除旧 headless → 显式 `--headless=new`（否则退出码 21 崩溃）。
- 中文 Windows `netstat` 输出 GBK 解码问题（cleanup 流程改用 bytes + gbk 容错）。
- 误判"未登录"白等 120s → 登录检测加会话级缓存 `_login_confirmed`。

### Known Limitations
- `extract` 的全书检索依赖微信读书前端选择器，页面改版可能需微调 `common.py` 的 JS 片段（已留多选择器兜底）。
- 加书架需微信读书网页登录态（`seed` / `login` 一次即可）；登录过期时 headed 模式停在扫码页等你扫。
- 依赖 Playwright（已装隔离 venv）；换机器需 `该venv的python -m pip install playwright`。
