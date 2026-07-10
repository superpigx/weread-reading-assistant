# 微信读书扩展阅读助手 · weread-reading-assistant

> 一个 WorkBuddy 技能（Skill）：用 **Playwright** 驱动你系统里已装的 Chrome / Edge，把"提取书中提及的书 → 批量加书架、扩展阅读、登录态管理、后台清理"做成一站式自动化。底层稳定、默认有头（扫码方便）、自动降级与清理。

![version](https://img.shields.io/badge/version-1.0.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![engine](https://img.shields.io/badge/engine-Playwright-blue)

---

## 特性

- **一站式**：提取提及书、批量加书架、扩展阅读清单、单本搜索、登录态预检、首次扫码登录、后台清理，统一一个入口。
- **稳定引擎**：基于 Playwright（`channel=chrome/edge`），不再依赖经常卡死的 agent-browser daemon，也不再手搓脆弱的 CDP WebSocket。
- **默认有头**：登录失效时弹出真实窗口扫码；需要无头时设 `HEADLESS=1` 即可（自动 `--headless=new`）。
- **自动降级**：指定浏览器 > Chrome > Edge，对用户透明。
- **自动清理**：脚本退出自动关闭本次会话并清掉残余的 agent-browser 进程，只杀"自己人"。
- **性能好**：用 `wait_for_selector` / `wait_for_function` 精准等待，不靠死等。

---

## 为什么合并

早期拆成了 `weread-extract-mentioned` 与 `weread-add-to-shelf` 两个 skill（关注点分离 + 独立测试）。但实际**几乎总是串联使用**（extract → `books.txt` → shelf），且各自维护一份脆弱的浏览器 / 登录态 / 清理逻辑，重复又易失同步。合并后：单一入口、共享引擎、统一清理与降级，不再需要外部助手。

---

## 架构

```
weread-reading-assistant/
├── SKILL.md            # 技能清单（给 WorkBuddy 智能体读，含完整命令/踩坑文档）
├── README.md           # 本文件（给人类看的 GitHub 文档）
├── CHANGELOG.md        # 版本与升级记录（升级功能必更）
├── VERSION             # 当前版本号（SemVer）
├── LICENSE             # MIT
├── .gitignore
├── requirements.txt    # playwright
├── Makefile            # 便捷命令：install / lint / test
├── tests/
│   └── syntax_check.py # 语法 / 冒烟自检
└── scripts/
    ├── weread.py       # CLI 入口：argparse 子命令 + COMMANDS 注册表（扩展点）
    ├── common.py       # 日志、中文判定、版本优选、JS 片段、等待常量（纯标准库）
    ├── core/
    │   ├── cdp.py      # Playwright 封装的浏览器会话（navigate/evaluate/query/wait_*）
    │   └── browser.py  # Playwright 启动(channel chrome/edge，默认 headed)、cleanup、profile 管理
    └── commands/       # 各子命令实现（extract/expand/shelf/search/verify/login/cleanup/seed）
```

**扩展点**：加新功能 → 在 `commands/` 加一个模块（定义 `run(args[, cdp])`），在 `weread.py` 的 `COMMANDS` 登记一行，在 `SKILL.md` / `README.md` / `CHANGELOG.md` 补说明。**不动核心引擎**。

---

## 环境准备（一次性）

Playwright 已装入 WorkBuddy 隔离 venv。运行统一走该 venv 的 python：

```bash
VENV_PY="C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
# 如换机器或需重装：
"$VENV_PY" -m pip install -r requirements.txt
# 想用 Playwright 自带 chromium 而非系统浏览器，再跑：
"$VENV_PY" -m playwright install chromium
```

---

## 快速开始

```bash
VENV_PY="C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
SK="C:/Users/Administrator/.workbuddy/skills/weread-reading-assistant/scripts"

# 0) 首次启动：建立登录态（二选一）
"$VENV_PY" "$SK/weread.py" login          # A. 弹窗扫码（推荐）
# 或  B. 从已登录的系统 Chrome 克隆登录态（免扫码）：先关掉自己的 Chrome，再：
"$VENV_PY" "$SK/weread.py" seed

# 1) 提取某本书里提到的书
"$VENV_PY" "$SK/weread.py" extract --reader-url "https://weread.qq.com/web/reader/xxxx" --self-title "四十岁才明白的事"

# 2) 批量加书架（吃上一步的 books.txt；可分段前台跑）
"$VENV_PY" "$SK/weread.py" shelf --books-file books.txt
OFFSET=0  LIMIT=10 "$VENV_PY" "$SK/weread.py" shelf --books-file books.txt   # 前 10 本
OFFSET=10 LIMIT=10 "$VENV_PY" "$SK/weread.py" shelf --books-file books.txt   # 后 10 本
```

---

## 命令一览

| 命令 | 作用 |
|------|------|
| `extract` | 打开阅读页 → 目录栏搜《→ 多轮滚动收集 → 正则提取《…》去重 → 写 `books.txt` + `weread_mentioned_books.md` |
| `expand` | 扩展阅读：复用 extract 逻辑 → 生成带微信读书链接的「扩展阅读清单」`weread_reading_list.md`（**不自动加书架**） |
| `shelf` | 逐本搜索 → 优选中文版(推荐值最高) → 真实点击「加入书架」→ 校验 → 输出 `shelf_result.json` + `weread_added.md` |
| `search` | 搜索单本，打印候选 JSON（调试/独立用） |
| `verify` | 登录态预检（打开已知已加架的书，看按钮是否为「已加入书架」） |
| `login` | 首次启动登录：弹出窗口 → 扫码 → 确认已登录，登录态固化在 profile |
| `cleanup` | 清理后台进程（只杀自己人，详见 `SKILL.md`） |
| `seed` | 首次使用：把已登录的 Chrome `Default` profile 复制为独立 `WereadCDP2` 目录 |

> 更深的命令参数、环境变量（`HEADLESS` / `BROWSER` / `WEREAD_PROFILE` / `CDP_PORT` / `OFFSET` / `LIMIT`）、踩坑细节见 **[SKILL.md](./SKILL.md)**。

---

## 扩展阅读（expand）

针对"某本书里提到的书，想做扩展阅读"的场景：复用 `extract` 的提取逻辑（目录栏搜《→ 滚动收集 → 正则去重），但不自动加书架，而是生成一份**带微信读书链接的「扩展阅读清单」** `weread_reading_list.md`，方便逐本查看 / 决定是否读。同时仍产出 `books.txt`，后续想加书架直接 `shelf --books-file books.txt`。

---

## 开发与测试

```bash
# 语法自检（py_compile 全部模块）
make lint
# 或
"$VENV_PY" -m py_compile $(find scripts -name '*.py')

# 语法 / 冒烟自检
make test
# 或
"$VENV_PY" tests/syntax_check.py

# 安装运行依赖
make install
```

Makefile 里 `VENV_PY` 变量可覆盖：`make lint VENV_PY=/path/to/python`。

---

## 已知限制

- `extract` 的全书检索依赖微信读书前端选择器，页面改版可能需微调 `common.py` 的 JS 片段（已留多选择器兜底）。首次实跑建议先小批量试 `LIMIT=3`。
- 加书架需微信读书网页登录态（`seed` / `login` 一次即可）；登录过期时 headed 模式停在扫码页等你扫，扫完自动继续；无头模式（`HEADLESS=1`）无法扫码，需先在本机 headed 跑一次 `seed` 或手动登录。
- 依赖 Playwright（已装隔离 venv）。

---

## 版本与更新

版本号见根目录 [`VERSION`](./VERSION)，升级记录见 [`CHANGELOG.md`](./CHANGELOG.md)。

**约定**：每次升级功能，请同步更新 `VERSION` + `CHANGELOG.md`（以及对应的 `SKILL.md` / `README.md` 说明），并 `git commit && git push` 到 GitHub。

---

## 许可证

[MIT](./LICENSE)
