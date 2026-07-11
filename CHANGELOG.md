# Changelog

本文件记录每次功能升级。**规则（与根目录 `VERSION` 同步）：**

- 新增 / 变更功能 → 在此**追加一个版本条目**，并同步修改根目录 `VERSION`。
- 升级后若已配置 GitHub remote → `git add -A && git commit -m "..." && git push`。
- 升级后记得同步更新 `SKILL.md`（命令说明）与 `README.md`（用户文档）。

格式参考 [Keep a Changelog](https://keepachangelog.com/)，版本号采用 [SemVer](https://semver.org/)。

---

## [1.3.0] - 2026-07-11

### Added
- **`pipeline` 全流程管道命令**：提取 + 加书架端到端自动执行，免手动步骤。注册 `commands/pipeline.py`。
- **`recommend` 推荐书单命令**：提取 → 逐本搜索微信读书获取详情（封面/作者/评分/读者数/简介）→ 生成自包含精美 HTML 页面。
- `command-audit.md` 审计报告（10 命令无废弃项）。

### Changed
- `weread.py` COMMANDS 扩展：新增 pipeline / recommend 子命令。
- VERSION → 1.3.0。SKILL.md 同步。

### Fixed
- 清理 `common.py` 死代码（-100行）、`extract.py` 无用导入、`weread-zhifu/` 50+调试脚本。

---

## [1.2.1] - 2026-07-11

### Changed
- **extract 改用全书搜索 API（server-side search），彻底摒弃翻页/DOM 扫描**：
  `GET /web/book/search?bookId=<数字>&keyword=《` 是微信读书阅读器"查询"功能的后端接口。
  服务器全量返回搜索结果，正则从 abstract 片段提取《书名》即可。无需翻页、无需拦截章节接口、零反爬风险。
- 新增 `_get_bookid()` 从页面自动提取数字 bookId（performance 资源 URL 或 YueWen_ 前缀）。
- `--rounds` 默认 200，收敛阈值 12（保留兼容，搜索方案不依赖翻页）。
- **废弃** 1.2.0 的章节接口拦截方案（headless 无法触发章节加载）。

### Fixed
- 解决数字 bookId 不在 reader URL 中的提取瓶颈。

---

## [1.2.0] - 2026-07-11（已废弃，被 1.2.1 取代）

### Fixed
- **extract 提取全书提及书的根本方案修正**：经完整排查，旧版（含 1.1.0 的 DOM 方案）读 `document.body.innerText` 或 `.readerChapterContent` 都拿不到正文——微信读书阅读器对正文做了**虚拟化 + 懒加载**，正文《书名》根本不进 DOM（headless/无真实渲染下 `.readerChapterContent` 恒为简介+第一章开头，翻页/滚动/点目录都不加载新章）。
- 改为**拦截阅读器原生章节接口 `web/book/chapter/e_N` 的回包**来取全本正文：打开阅读页 → 挂响应监听器 → `PageDown` 正常翻页（等同正常阅读，非爬虫）→ 每章把 base64 编码的 XHTML/正文解码、剥标签 → 正则提取《…》去重 → 排除本书。这是阅读器自己加载正文用的数据通道，安全且能拿全本。
- 新增 `common.decode_chapter_body()`：稳健解码回包（实测格式 `= [hex 哈希][可选分隔][base64(XHTML/正文)]`），自动识别 XHTML / 纯中文正文 / 样式章节，多偏移试解选取合理结果，最后剥标签/实体。

### Changed
- `collect_mentioned` 重写：响应拦截 + `PageDown` 翻页遍历，连续 5 页无新章节即判定遍历完成；无 `page` 对象时降级读 DOM 首屏。
- `extract` / `expand` 共用新逻辑；`BOOK_RE` 与 `extract_books` / `read_reader_text` 保留为清洗层。

### Known Limitations
- **提取依赖真实渲染**：章节是按需懒加载，headless / 无真实渲染的环境里阅读器只预载少量章节、翻页不触发加载，故 extract 在**无头/沙箱环境只能拿到少量章节（可能 0 本）**。**请在本机 headed 模式（真实阅读、随翻页加载各章）下运行 extract** 才能拿全本——这是平台虚拟化限制，非代码缺陷。
- 章节接口 `c` 签名与章节绑定，且 `c` 哈希不在任何公开接口下发，故无法离线重放全部章节（会触发反爬 500）；坚持走阅读器原生加载通道。

---

## [1.1.0] - 2026-07-11（已废弃，被 1.2.0 取代）

> 该版本尝试用 DOM（`.readerChapterContent` + `Space` 翻页）提取，但后续排查证实微信读书正文不进 DOM，方案不成立，已由 1.2.0 的章节接口拦截方案取代。

### Changed（当时尝试，现已弃用）
- 读取 `.readerChapterContent.textContent` + `Space` 翻页遍历全书。
- 新增 `extract_books` / `read_reader_text` / 收紧 `BOOK_RE`。

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
