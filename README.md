# 微信读书扩展阅读助手 · weread-reading-assistant

> 基于 **Playwright** 的微信读书自动化工具。提取书中提及的书、批量加书架、生成推荐书单 HTML，一站式完成。

![version](https://img.shields.io/badge/version-1.3.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![engine](https://img.shields.io/badge/engine-Playwright-blue)
![tests](https://img.shields.io/badge/tests-14/14-green)

---

## 特性

- **搜索 API 驱动**：提取《书名》走微信读书官方搜索接口，服务器全量返回，零翻页、零爬虫风险，headless 完全可用。
- **一键全流程**：`pipeline` 从提取到加书架端到端自动执行。
- **精美 HTML 书单**：`recommend` 生成含封面、评分、直达链接的自包含书单页面。
- **稳定引擎**：Playwright 驱动系统 Chrome/Edge，不依赖外部 daemon，自动降级与清理。
- **默认有头**：登录失效时弹出真实窗口扫码；设 `HEADLESS=1` 可退回无头。

---

## 快速开始

```bash
VENV_PY="C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
SK="C:/Users/Administrator/.workbuddy/skills/weread-reading-assistant/scripts"

# 1) 登录（二选一）
"$VENV_PY" "$SK/weread.py" login         # 弹窗扫码
"$VENV_PY" "$SK/weread.py" seed           # 从已登录 Chrome 复制 profile

# 2) 全流程：提取 + 加书架
"$VENV_PY" "$SK/weread.py" pipeline \
  --reader-url "https://weread.qq.com/web/reader/xxxx" --self-title "书名"

# 3) 仅提取
"$VENV_PY" "$SK/weread.py" extract --reader-url "…" --self-title "书名"

# 4) 仅加书架（可分段）
"$VENV_PY" "$SK/weread.py" shelf --books-file books.txt
OFFSET=0 LIMIT=10 "$VENV_PY" "$SK/weread.py" shelf --books-file books.txt

# 5) 生成 HTML 推荐书单
"$VENV_PY" "$SK/weread.py" recommend --reader-url "…" --self-title "书名"
```

---

## 命令

| 命令 | 作用 |
|------|------|
| `extract` | 搜索 API 提取《书名》→ `books.txt` + md |
| `pipeline` | 端到端：提取 + 加书架，免手动 |
| `recommend` | 生成推荐书单 HTML（封面 / 评分 / 直达链接） |
| `expand` | 扩展阅读清单（md，不加书架） |
| `shelf` | 逐本搜索 → 优选 → 加入书架 → 校验 |
| `search` | 搜索单本，打印候选 JSON |
| `verify` | 登录态预检 |
| `login` | 首次扫码登录，固化 profile |
| `cleanup` | 清理后台进程（只杀自己人） |
| `seed` | 从已登录 Chrome 复制 profile（免扫码） |

> 环境变量：`HEADLESS=1`（无头）、`BROWSER=chrome/edge`、`WEREAD_VERIFY_BOOK`（自定义验证书）、`WEREAD_PROFILE`、`OFFSET`/`LIMIT`（分段加书架）。详见 [SKILL.md](./SKILL.md)。

---

## 架构

```
weread-reading-assistant/
├── SKILL.md             # 技能文档（给智能体读）
├── README.md            # 本文件（人类文档）
├── CHANGELOG.md         # 版本记录
├── VERSION              # 当前版本号
├── LICENSE              # MIT
├── requirements.txt
├── Makefile
├── templates/
│   └── recommend.css    # 推荐书单 HTML 样式
├── tests/
│   ├── syntax_check.py  # 全模块语法自检
│   └── test_core.py     # 核心函数单元测试（14 个）
└── scripts/
    ├── weread.py         # CLI 入口 + 命令注册表
    ├── common.py         # 日志/解析/搜索/JS 片段
    ├── core/
    │   ├── cdp.py        # Playwright 浏览器会话
    │   └── browser.py    # 启动/清理/profile 管理
    └── commands/
        ├── extract.py     ├── pipeline.py   ├── recommend.py
        ├── shelf.py       ├── expand.py     ├── search.py
        ├── verify.py      ├── login.py      ├── cleanup.py
        └── seed.py
```

**加新功能**：在 `commands/` 加模块（`run(args[, cdp])`）→ `weread.py` 的 `COMMANDS` 登记 → 更新文档。不动核心引擎。

---

## 开发与测试

```bash
# 语法自检
"$VENV_PY" tests/syntax_check.py

# 单元测试（14 个纯函数用例）
"$VENV_PY" tests/test_core.py

# 安装依赖
"$VENV_PY" -m pip install -r requirements.txt
```

---

## 已知限制

- `extract` 走搜索 API，headless 完全可用（不需真实渲染、不翻页）。
- 加书架需登录态（`seed`/`login` 一次即可）；登录过期时 headed 模式停在扫码页等你扫。
- 依赖 Playwright（隔离 venv 已装）。

---

## 许可证

[MIT](./LICENSE)
