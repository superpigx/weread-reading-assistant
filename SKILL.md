---
name: weread-reading-assistant
description: 微信读书扩展阅读助手。一站式完成：提取书中提及的书、批量加书架（中文优先+评分最高）、生成推荐书单 HTML、单本搜索、登录态校验、后台进程清理。底层用 Playwright 驱动系统 Chrome/Edge（默认 headed 有头模式，便于登录扫码；HEADLESS=1 退回无头），不依赖外部 daemon，自动清理后台进程，Chrome 不可用自动降级 Edge。当用户提到"微信读书/weread/加书架/书单/书中提到的书/提取引用书/清理后台"时优先使用本 skill。
agent_created: true
---

# 微信读书扩展阅读助手

一站式工具集：从一本书出发，提取书中提及的其他书籍、批量加入书架、生成推荐书单 HTML 页面。

## 引擎

底层用 **Playwright** 驱动系统 Chrome/Edge（`channel="chrome"` / `channel="msedge"`），不下载浏览器、不依赖外部 daemon。登录态通过 `launch_persistent_context(user_data_dir=...)` 持久化复用。命令层只调用 `core.cdp.CDP` 的 `navigate/evaluate/close/query`，与底层解耦。

统一走隔离 venv 的 Python（已安装 Playwright）：

```bash
VENV_PY="C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
SK="C:/Users/Administrator/.workbuddy/skills/weread-reading-assistant/scripts"
"$VENV_PY" "$SK/weread.py" <子命令> ...
```

## 命令

| 命令 | 作用 |
|------|------|
| `extract` | 搜索 API 提取《书名》→ `books.txt` + md |
| `pipeline` | 端到端全流程：提取 + 加书架（免手动） |
| `recommend` | 生成推荐书单 HTML 页面（封面 / 评分 / 直达链接） |
| `expand` | 扩展阅读：提取 → 生成带链接的清单（不加书架） |
| `shelf` | 逐本搜索 → 优选中文版 → 加入书架 → 校验 |
| `search` | 搜索单本，打印候选 JSON |
| `verify` | 登录态预检 |
| `login` | 首次扫码登录，固化 profile |
| `cleanup` | 清理后台进程（只杀自己人） |
| `seed` | 从已登录 Chrome 复制 profile（免扫码） |

### 触发场景

- "把某本书里提到的书找出来 / 提取书中引用的书"
- "把这批书加入书架 / 加书架 / 收藏"
- "生成这本书的推荐书单页面"

## 快速上手

### 1. 建立登录态（login 或 seed 二选一）

加书架需要**已登录的 profile**。本 skill 用独立 profile（`WereadCDP2`），不复用你正在用的 Chrome。

- **方式 A（推荐）：`login` 扫码** — 弹出真实窗口用微信扫码，登录态写入独立 profile，此后无需再扫。
- **方式 B（免扫码）：`seed` 复制** — 已在系统 Chrome 登录微信读书时，先关 Chrome，再 `seed` 复制 `Default` 到 `WereadCDP2`。

用 Edge 时：`BROWSER=edge "$VENV_PY" weread.py seed`。

### 2. 常用命令

```bash
# 提取 + 加书架（一行搞定）
"$VENV_PY" "$SK/weread.py" pipeline --reader-url "https://weread.qq.com/web/reader/xxxx" --self-title "书名"

# 仅提取
"$VENV_PY" "$SK/weread.py" extract --reader-url "https://weread.qq.com/web/reader/xxxx" --self-title "书名"

# 仅加书架（吃上一步的 books.txt，支持分段跑）
"$VENV_PY" "$SK/weread.py" shelf --books-file books.txt
OFFSET=0  LIMIT=10 "$VENV_PY" "$SK/weread.py" shelf --books-file books.txt

# 生成推荐书单 HTML
"$VENV_PY" "$SK/weread.py" recommend --reader-url "https://weread.qq.com/web/reader/xxxx" --self-title "书名"

# 扩展阅读清单（md，不加书架）
"$VENV_PY" "$SK/weread.py" expand --reader-url "https://weread.qq.com/web/reader/xxxx" --self-title "书名"

# 其他
"$VENV_PY" "$SK/weread.py" search "原子习惯"
"$VENV_PY" "$SK/weread.py" verify
"$VENV_PY" "$SK/weread.py" login
"$VENV_PY" "$SK/weread.py" cleanup --dry-run
BROWSER=edge "$VENV_PY" "$SK/weread.py" shelf --books-file books.txt
```

## 设计要点

1. **默认 headed（有头）模式**：登录失效时需在弹出的真实窗口扫码，故默认有头。仅设 `HEADLESS=1` 时退回无头（兼容无显示器 / CI）；无头时自动追加 `--headless=new`——Chrome 149 已移除旧 headless，传旧 `--headless` 会以**退出码 21 崩溃**。
2. **profile 目录结构**：`user_data_dir` 必须是含 `Default/` 子目录的「User Data 根」。`seed` 把源 `Default` 复制到 `<dst>/Default`（不能扁平铺平，否则 Chrome 误判损坏并退出 21）。统一用 `WereadCDP2`。
3. **自动降级**：`BROWSER` 顺序 = 指定 > Chrome > Edge，同一套参数对用户透明。
4. **自动清理**：脚本退出（`try/finally` + `atexit`）自动关 Playwright 会话并杀残余 daemon，**只清自己人，不碰普通 Chrome/Edge**。
5. **精准等待**：用 `wait_for_selector` / `wait_for_function` 等元素出现即继续，不再死等固定秒数。导航用 `page.goto`，不要 eval 改 `location.href`（会销毁页面上下文）。
6. **版本优选**：标题含书名、非英文原版、推荐值最高；搜不到时用书名前两字兜底。中文正版 `web/reader/<v>`，英文原版 `web/bookDetail/<v>`。
7. **extract 走搜索 API，不扫 DOM、不翻页**：微信读书正文经虚拟化 + 懒加载，正文《书名》不进 DOM。改用阅读器"查询"功能的后端接口 `GET /web/book/search?bookId=<数字>&keyword=《`，服务器全量返回结果，正则从 abstract 片段提取书名。数字 bookId 从页面资源 URL 或封面图 `YueWen_` 前缀自动提取。零反爬风险。

## 架构

```
weread-reading-assistant/
  SKILL.md / README.md / VERSION / CHANGELOG.md
  scripts/
    weread.py              # CLI 入口：argparse + COMMANDS 注册表（扩展点）
    common.py              # 日志、中文判定、版本优选、JS 片段、等待常量
    core/
      cdp.py               # Playwright 浏览器会话封装
      browser.py            # 启动(chrome/edge, headed)、cleanup、profile
    commands/
      extract.py    expand.py    pipeline.py   recommend.py
      shelf.py      search.py    verify.py     login.py
      cleanup.py    seed.py
```

- **加新功能**：在 `commands/` 加模块（定义 `run(args[, cdp])`），在 `weread.py` 的 `COMMANDS` 登记一行，本文补一句。**不动核心引擎**。
- 所有命令共用 `core.cdp` / `core.browser`，天然继承登录态、降级、清理策略。

## 已知限制

- `extract` 走搜索 API，headless 完全可用（不需要真实渲染、不翻页）。
- 加书架需登录态（`seed`/`login` 一次即可）；登录过期时 headed 模式停在扫码页等你扫，扫完自动继续。无头模式无法扫码。
- 依赖 Playwright（隔离 venv 已装）；换机器需重装。
