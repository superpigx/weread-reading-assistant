---
name: weread-reading-assistant
description: 微信读书扩展阅读助手（合并版）。一站式完成：提取书中提及的书、批量加书架（中文优先+评分最高）、单本搜索、登录态校验、后台进程清理。底层用 Playwright 驱动系统 Chrome/Edge（默认 headed 有头模式，便于登录扫码；设置 HEADLESS=1 可退回无头），不依赖 agent-browser daemon，自动清理后台进程，Chrome 不可用自动降级 Edge。当用户提到"微信读书/weread/加书架/书单/书中提到的书/提取引用书/清理后台"时优先使用本 skill。
agent_created: true
---

# 微信读书扩展阅读助手

> 由原 `weread-extract-mentioned`（提取提及书）与 `weread-add-to-shelf`（批量加书架）合并而来。

## 为什么合并（vs 当初拆分）
- 当初拆两 skill 是为了"关注点分离 + 独立测试"，但实际**几乎总是串联使用**（extract→books.txt→shelf），且两者各自维护一份脆弱的浏览器/登录态/清理逻辑，重复且易失同步。
- 合并后：**单一入口、共享引擎、统一清理与降级**，不再需要调用 agent-browser 等外部助手。

## 底层引擎：Playwright（不是手搓 CDP，也不是 agent-browser）
这是本 skill 好用、稳定的根本原因。经历了 agent-browser daemon 卡死、`--profile` 被旧 daemon 静默忽略、手搓 WebSocket 被代理劫持等一系列坑后，最终选定 **Playwright**：
- 微软出品，驱动系统已装的 Chrome/Edge（`channel="chrome"` / `channel="msedge"`），**不需要自己下载浏览器**（除非用自带 chromium）。
- selector 友好（CSS / text / xpath），比手搓 `Runtime.evaluate` 直塞 JS 稳得多。
- 用 **CDP-over-pipe** 连接，不依赖外部长驻 daemon，脚本退出即回收，不会留孤儿进程。
- 登录态用 `launch_persistent_context(user_data_dir=...)` 持久化，复用同一份 profile。

### 环境准备（一次性）
Playwright 已装入本环境隔离 venv：`C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe`
（如需重装：`该venv的python -m pip install playwright`；想用 Playwright 自带 chromium 而非系统 Chrome，再跑一次 `该venv的python -m playwright install chromium`。）

运行统一走该 venv 的 python，例如：
```bash
VENV_PY="C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$VENV_PY" <skill>/scripts/weread.py <子命令> ...
```

## 能力一览（子命令）
| 命令 | 作用 |
|------|------|
| `extract` | 打开阅读页 → 目录栏搜《→ 多轮滚动收集 → 正则提取《…》去重 → 写 `books.txt` + `weread_mentioned_books.md` |
| `expand` | 扩展阅读：复用 extract 的提取逻辑 → 生成带微信读书链接的「扩展阅读清单」`weread_reading_list.md`（**不自动加书架**，要加把 books.txt 喂给 shelf） |
| `shelf` | 逐本搜索 → 优选中文版(推荐值最高) → 真实点击「加入书架」→ 校验 → 输出 `shelf_result.json` + `weread_added.md` |
| `search` | 搜索单本，打印候选 JSON（调试/独立用） |
| `verify` | 登录态预检（打开已知已加架的书，看按钮是否为「已加入书架」） |
| `login` | 首次启动登录：弹出浏览器窗口 → 扫码 → 确认已登录，登录态固化在 profile |
| `cleanup` | 清理后台进程（只杀自己人，详见下） |
| `seed` | 首次使用：把已登录的 Chrome `Default` profile 复制为独立 `WereadCDP2` 目录 |

## 何时使用
- "把某本书里提到的书都找出来 / 提取书中引用的书"
- "把这批书加入书架 / 加书架 / 收藏"
- "搜一下这本书在微信读书里有没有"
- "清理一下后台进程 / 关掉残留的浏览器"
- 与书单相关的扩展需求（未来可加：导出笔记、同步书单、读书统计…）

## 首次启动登录（关键一步：login 或 seed 二选一）
加书架需要**已登录的 profile**。本 skill 用独立 profile（不复用你正在用的 Chrome），有两种方式建立登录态：

**方式 A（推荐，最省事）：`login` 直接扫码**
```bash
"$VENV_PY" <skill>/scripts/weread.py login
```
弹出真实浏览器窗口 → 用微信扫二维码 → 脚本确认「已登录」后退出。**登录态写入独立 profile（默认 WereadCDP2），此后运行 shelf/extract/verify 都默认已登录，无需再扫。**
- 适合本机有显示器、能直接扫码的场景（默认 headed 有头模式，无障碍）。

**方式 B（备选，免扫码）：`seed` 复制登录态**
当你已经在系统 Chrome 里登录了微信读书、不想再扫一次码时：
1. 关闭你自己的 Chrome（否则 profile 被锁，复制不完整）。
2. 运行：`"$VENV_PY" <skill>/scripts/weread.py seed`
3. 之后脚本自启该 profile，已带登录态。

> 若用 Edge：`WEREAD_PROFILE=...WereadCDP_edge BROWSER=edge "$VENV_PY" weread.py seed`（把 Edge 的 `Default` 复制为 WereadCDP_edge）。

**两者关系**：`login` 是显式的「首次启动登录」入口；`seed` 是「从已登录的系统浏览器克隆登录态」的备选（适合已登录、懒得扫）。选一个即可，登录态都固化在独立 profile 里。

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

# 4) 首次启动登录（弹出窗口扫码，登录态固化在 profile；之后无需再扫）
"$VENV_PY" "$SK/weread.py" login

# 4.5) 扩展阅读：提取某本书提及的书 -> 生成带微信读书链接的清单（不加书架）
"$VENV_PY" "$SK/weread.py" expand --reader-url "https://weread.qq.com/web/reader/xxxx" --self-title "四十岁才明白的事"

# 5) 后台清理（只杀自己人）
"$VENV_PY" "$SK/weread.py" cleanup --dry-run     # 先看会杀什么
"$VENV_PY" "$SK/weread.py" cleanup               # 真正清理

# 6) 浏览器选择
BROWSER=edge "$VENV_PY" "$SK/weread.py" shelf --books-file books.txt   # 强制用 Edge
```

## 扩展阅读（expand）
针对「某本书里提到的书，想做扩展阅读」的场景：复用 `extract` 的提取逻辑（目录栏搜《→ 滚动收集→ 正则去重），但不自动加书架，而是生成一份**带微信读书链接的「扩展阅读清单」** `weread_reading_list.md`：

- 每本书一行，点击「微信读书」即跳到该书在微信读书的检索页（默认中文优先），方便你逐本查看/决定是否读。
- 同时仍产出 `books.txt`——若你后续想把这批书加进书架，直接 `shelf --books-file books.txt` 即可，无需重新提取。

与 `extract` 的区别：`extract` 只产出纯标题清单；`expand` 额外带上可点击的检索链接、定位为「扩展阅读」体验。两者共用 `collect_mentioned()`，逻辑只维护一处。

```bash
"$VENV_PY" "$SK/weread.py" expand --reader-url "https://weread.qq.com/web/reader/xxxx" --self-title "四十岁才明白的事"
# 产出：weread_reading_list.md（扩展阅读清单，含链接）+ books.txt（供 shelf 后续使用）
```

## 设计要点 / 踩坑（务必了解）
1. **底层 Playwright，不依赖 agent-browser daemon**：agent-browser 的 daemon 极易卡死、`--profile` 被旧 daemon 静默忽略，已彻底弃用。命令层（commands/*）只调用 `core.cdp.CDP` 的 `navigate/evaluate/close` 三个方法，与底层实现解耦。
2. **默认 headed（有头）模式**：登录态失效时需要在弹出的真实窗口里扫码，无头模式看不到二维码，故默认有头。仅当设置环境变量 `HEADLESS=1` 时退回无头（兼容无显示器/CI）；无头时自动追加 `--headless=new`（Chrome 149 已移除旧 headless，传旧 `--headless` 会以**退出码 21 崩溃**）。
3. **profile 目录结构**：`user_data_dir` 必须是含 `Default/` 子目录的"User Data 根"。`seed_profile` 会把源 `Default` 复制到 `<dst>/Default`（而非扁平铺平），扁平会让 Chrome 误判损坏 profile 并退出 21。
4. **独立非默认 user-data-dir**：默认目录拒绝远程调试。统一用 `WereadCDP2`（`WereadCDP` 旧目录曾因扁平铺平损坏，故换新名）。
5. **自动降级**：`BROWSER` 顺序 = 指定 > Chrome > Edge，同一套 Playwright 参数，对用户透明。
6. **自动清理后台进程（强需求）**：脚本退出（`try/finally` + `atexit`）自动关掉本次 Playwright 浏览器会话 + 杀残余 `agent-browser-win32-x64.exe` daemon。**只清理自己人，绝不关你正在用的普通 Chrome/Edge**。
7. **SPA 需等待渲染**：优先用 `wait_for_selector` / `wait_for_function` 精准等待元素出现（见 `core/cdp.py` 的 `wait_selector` / `wait_fn`），不再死等；`common.py` 里的 `SEARCH_WAIT/BOOK_WAIT/CLICK_WAIT` 仅作兜底上限。导航用 `page.goto`，不要用 eval 改 `location.href`（会销毁页面上下文）。
8. **版本优选**：标题含书名、非英文原版、推荐值最高；搜不到严格匹配时用书名前两字兜底。中文正版链接 `web/reader/<v>`，英文原版多为 `web/bookDetail/<v>`。

## 架构与扩展性（强需求）
```
weread-reading-assistant/
  SKILL.md
  scripts/
    weread.py          # CLI 入口：argparse 子命令 + COMMANDS 注册表（扩展点）
    common.py          # 日志、中文判定、版本优选、JS 片段、等待常量（纯标准库）
    core/
      cdp.py           # Playwright 封装的浏览器会话（navigate/evaluate/close/query）
      browser.py       # Playwright 启动(channel chrome/edge，默认 headed)、cleanup、profile 管理
    commands/
      extract.py shelf.py search.py verify.py cleanup.py seed.py
```
- **加新功能**：在 `commands/` 加一个模块（定义 `run(args[, cdp])`），在 `weread.py` 的 `COMMANDS` 登记一行，在本文补一段说明。**不动核心引擎**。
- 所有命令共用 `core.cdp` / `core.browser`，天然继承登录态、降级、清理策略。

## 已知限制
- `extract` 的全书检索依赖微信读书前端选择器，若页面改版需微调 `common.py` 里的 `JS_OPEN_SEARCH/JS_READ_RESULTS/JS_SCROLL`（已留多选择器兜底）。未做端到端联网验证，首次实跑建议先小批量试 `LIMIT=3`。
- 加书架需要微信读书网页登录态（`seed` 一次即可）；若登录过期，脚本在 headed 模式下会停在扫码页面等你扫，扫完自动继续；无头模式（HEADLESS=1）下无法扫码，需先在本机 headed 跑一次 `seed` 或手动登录后再用无头。
- 依赖 Playwright（已装隔离 venv）。若换机器，需重装：`该venv的python -m pip install playwright`。
