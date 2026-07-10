---
name: weread-reading-assistant
description: 微信读书扩展阅读助手（合并版）。一站式完成：提取书中提及的书、批量加书架（中文优先+评分最高）、单本搜索、登录态校验、后台进程清理。底层用 Playwright 驱动系统 Chrome/Edge（默认 headed 有头模式，便于登录扫码；设置 HEADLESS=1 可退回无头），不依赖 agent-browser daemon，自动清理后台进程，Chrome 不可用自动降级 Edge。当用户提到"微信读书/weread/加书架/书单/书中提到的书/提取引用书/清理后台"时优先使用本 skill。
agent_created: true
---

# 微信读书扩展阅读助手

> 由 `weread-extract-mentioned`（提取提及书）与 `weread-add-to-shelf`（批量加书架）合并而来，统一为一站式入口、共享引擎。

## 引擎与运行环境

底层用 **Playwright** 驱动系统已装的 Chrome/Edge（`channel="chrome"` / `channel="msedge"`），不下载浏览器、不依赖外部长驻 daemon；登录态通过 `launch_persistent_context(user_data_dir=...)` 持久化复用。命令层（`commands/*`）只调用 `core.cdp.CDP` 的 `navigate/evaluate/close/query` 方法，与底层解耦。

运行统一走隔离 venv 的 python（已安装 Playwright）：

```bash
VENV_PY="C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$VENV_PY" <skill>/scripts/weread.py <子命令> ...
# 重装依赖（换机器时）：该 venv 的 python -m pip install -r requirements.txt
# 改用 Playwright 自带 chromium：该 venv 的 python -m playwright install chromium
```

## 能力一览（子命令）

| 命令 | 作用 |
|------|------|
| `extract` | 打开阅读页 → 目录栏搜《→ 多轮滚动收集 → 正则提取《…》去重 → 写 `books.txt` + `weread_mentioned_books.md` |
| `expand` | 扩展阅读：复用 `extract` 提取逻辑 → 生成带微信读书链接的「扩展阅读清单」`weread_reading_list.md`（**不自动加书架**，要加把 `books.txt` 喂给 `shelf`） |
| `shelf` | 逐本搜索 → 优选中文版（推荐值最高）→ 真实点击「加入书架」→ 校验 → 输出 `shelf_result.json` + `weread_added.md` |
| `search` | 搜索单本，打印候选 JSON（调试/独立用） |
| `verify` | 登录态预检（打开已知已加架的书，看按钮是否为「已加入书架」） |
| `login` | 首次启动登录：弹出浏览器窗口 → 扫码 → 确认已登录，登录态固化在 profile |
| `cleanup` | 清理后台进程（只杀自己人） |
| `seed` | 首次使用：把已登录的 Chrome `Default` profile 复制为独立 `WereadCDP2` 目录 |

## 何时使用

- "把某本书里提到的书都找出来 / 提取书中引用的书"
- "把这批书加入书架 / 加书架 / 收藏"
- "搜一下这本书在微信读书里有没有"
- "清理一下后台进程 / 关掉残留的浏览器"

## 首次启动登录（login 或 seed 二选一）

加书架需要**已登录的 profile**。本 skill 用独立 profile（不复用你正在用的 Chrome），两种建立登录态的方式：

- **方式 A（推荐）：`login` 直接扫码** — 弹出真实窗口用微信扫码，登录态写入独立 profile（默认 `WereadCDP2`），此后 `shelf/extract/verify` 默认已登录、无需再扫。适合本机能直接扫码的场景。
- **方式 B（免扫码）：`seed` 复制登录态** — 已在系统 Chrome 登录微信读书时：先关闭自己的 Chrome（否则 profile 被锁），再 `seed` 把 `Default` 复制为 `WereadCDP2`。

两者选一即可，登录态都固化在独立 profile 里。用 Edge 时：`WEREAD_PROFILE=...WereadCDP_edge BROWSER=edge "$VENV_PY" weread.py seed`。

## 用法示例

```bash
VENV_PY="C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
SK="C:/Users/Administrator/.workbuddy/skills/weread-reading-assistant/scripts"

# 1) 提取书中提及的书
"$VENV_PY" "$SK/weread.py" extract --reader-url "https://weread.qq.com/web/reader/xxxx" --self-title "四十岁才明白的事"

# 2) 批量加书架（吃上一步的 books.txt；可分段前台跑）
"$VENV_PY" "$SK/weread.py" shelf --books-file books.txt
OFFSET=0  LIMIT=10 "$VENV_PY" "$SK/weread.py" shelf --books-file books.txt   # 前 10 本
OFFSET=10 LIMIT=10 "$VENV_PY" "$SK/weread.py" shelf --books-file books.txt   # 后 10 本

# 3) 单本搜索 / 登录态校验
"$VENV_PY" "$SK/weread.py" search "原子习惯"
"$VENV_PY" "$SK/weread.py" verify

# 4) 首次启动登录（弹出窗口扫码，登录态固化在 profile）
"$VENV_PY" "$SK/weread.py" login

# 5) 扩展阅读：提取某本书提及的书 -> 生成带微信读书链接的清单（不加书架）
"$VENV_PY" "$SK/weread.py" expand --reader-url "https://weread.qq.com/web/reader/xxxx" --self-title "四十岁才明白的事"

# 6) 后台清理（只杀自己人）
"$VENV_PY" "$SK/weread.py" cleanup --dry-run     # 先看会杀什么
"$VENV_PY" "$SK/weread.py" cleanup               # 真正清理

# 7) 浏览器选择
BROWSER=edge "$VENV_PY" "$SK/weread.py" shelf --books-file books.txt   # 强制用 Edge
```

## 扩展阅读（expand）

针对「某本书里提到的书，想做扩展阅读」的场景：复用 `extract` 的提取逻辑（目录栏搜《→ 滚动收集 → 正则去重），但**不自动加书架**，而是生成一份带微信读书链接的「扩展阅读清单」`weread_reading_list.md`（每本书一行，点击即跳到该书在微信读书的检索页，默认中文优先）。同时仍产出 `books.txt`，后续想加书架直接 `shelf --books-file books.txt` 即可，无需重新提取。两者共用 `collect_mentioned()`，逻辑只维护一处。

## 设计要点与踩坑

1. **默认 headed（有头）模式**：登录失效时需在弹出的真实窗口扫码，故默认有头。仅设 `HEADLESS=1` 时退回无头（兼容无显示器/CI）；无头时自动追加 `--headless=new`——Chrome 149 已移除旧 headless，传旧 `--headless` 会以**退出码 21 崩溃**。
2. **profile 目录结构**：`user_data_dir` 必须是含 `Default/` 子目录的「User Data 根」。`seed_profile` 把源 `Default` 复制到 `<dst>/Default`（而非扁平铺平），扁平会让 Chrome 误判损坏 profile 并退出 21。统一用独立 `WereadCDP2`（`WereadCDP` 旧目录曾因扁平铺平损坏，故换新名）。
3. **自动降级**：`BROWSER` 顺序 = 指定 > Chrome > Edge，同一套 Playwright 参数，对用户透明。
4. **自动清理后台进程**：脚本退出（`try/finally` + `atexit`）自动关掉本次 Playwright 会话 + 杀残余 `agent-browser-win32-x64.exe` daemon，**只清理自己人，绝不关你正在用的普通 Chrome/Edge**。
5. **SPA 需等待渲染**：优先用 `wait_for_selector` / `wait_for_function` 精准等待（见 `core/cdp.py` 的 `wait_selector` / `wait_fn`），不再死等；`common.py` 的 `SEARCH_WAIT/BOOK_WAIT/CLICK_WAIT` 仅作兜底上限。导航用 `page.goto`，不要用 eval 改 `location.href`（会销毁页面上下文）。
6. **版本优选**：标题含书名、非英文原版、推荐值最高；搜不到严格匹配时用书名前两字兜底。中文正版链接 `web/reader/<v>`，英文原版多为 `web/bookDetail/<v>`。

## 架构与扩展性

```
weread-reading-assistant/
  SKILL.md
  scripts/
    weread.py          # CLI 入口：argparse 子命令 + COMMANDS 注册表（扩展点）
    common.py          # 日志、中文判定、版本优选、JS 片段、等待常量（纯标准库）
    core/
      cdp.py           # Playwright 封装的浏览器会话（navigate/evaluate/close/query/wait_*）
      browser.py       # Playwright 启动(channel chrome/edge，默认 headed)、cleanup、profile 管理
    commands/
      extract.py expand.py shelf.py search.py verify.py login.py cleanup.py seed.py
```

- **加新功能**：在 `commands/` 加一个模块（定义 `run(args[, cdp])`），在 `weread.py` 的 `COMMANDS` 登记一行，在本文补一段说明。**不动核心引擎**。
- 所有命令共用 `core.cdp` / `core.browser`，天然继承登录态、降级、清理策略。

## 已知限制

- `extract` 的全书检索依赖微信读书前端选择器，页面改版可能需微调 `common.py` 的 JS 片段（已留多选择器兜底）；首次实跑建议先小批量试 `LIMIT=3`。
- 加书架需微信读书网页登录态（`seed`/`login` 一次即可）；登录过期时 headed 模式停在扫码页等你扫，扫完自动继续；无头模式（`HEADLESS=1`）无法扫码，需先在本机 headed 跑一次 `seed` 或手动登录。
- 依赖 Playwright（已装隔离 venv）；换机器需重装：`该venv的python -m pip install playwright`。
