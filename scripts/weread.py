# -*- coding: utf-8 -*-
"""
微信读书扩展阅读助手 — 统一 CLI 入口。

子命令（命令注册表 COMMANDS 分发，新增功能只需加模块 + 登记）：
  extract  提取书中提及的书 -> books.txt + weread_mentioned_books.md
  shelf    批量加书架（吃 books.txt 或直接给书名）
  search   搜索单本，返回候选（调试/独立用）
  verify   登录态预检
  login    首次启动登录（弹出窗口扫码，登录态固化在 profile）
  cleanup  清理后台进程（只杀自己人）
  seed     复制登录态 profile（从已登录的 Chrome/Edge 复制，备选方案）

特点：
  - 纯标准库，不依赖 agent-browser。
  - 脚本自启独立 profile 的 headless 浏览器（Chrome 失败自动降级 Edge），跑完自清。
  - 通过环境变量可配：CHROME / WEREAD_PROFILE / CDP_PORT / BROWSER(=auto|chrome|edge)。

示例：
  python weread.py seed
  python weread.py extract --reader-url "https://weread.qq.com/web/reader/xxxx" --self-title "四十岁才明白的事"
  python weread.py shelf --books-file books.txt
  OFFSET=0 LIMIT=10 python weread.py shelf --books-file books.txt
  python weread.py verify
  python weread.py cleanup --dry-run
"""
import os, sys, argparse

# 脚本所在目录（scripts/）自动在 sys.path[0]，故可直接 import common / core / commands
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from common import log
import core.browser as browser

def parse():
    ap = argparse.ArgumentParser(prog="weread", description="微信读书扩展阅读助手")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pe = sub.add_parser("extract", help="提取书中提及的书")
    pe.add_argument("--reader-url", help="微信读书阅读页 URL（web/reader/<v>）")
    pe.add_argument("--v", help="reader 页 bookId")
    pe.add_argument("--self-title", help="本书标题，用于排除自身")
    pe.add_argument("--out-dir", default=os.getcwd())
    pe.add_argument("--rounds", type=int, default=200, help="翻页遍历全书上限")

    pexp = sub.add_parser("expand", help="扩展阅读：提取提及的书并生成带链接的清单（不加书架）")
    pexp.add_argument("--reader-url", help="微信读书阅读页 URL（web/reader/<v>）")
    pexp.add_argument("--v", help="reader 页 bookId")
    pexp.add_argument("--self-title", help="本书标题，用于排除自身")
    pexp.add_argument("--out-dir", default=os.getcwd())
    pexp.add_argument("--rounds", type=int, default=200, help="翻页遍历全书上限")

    ps = sub.add_parser("shelf", help="批量加书架")
    ps.add_argument("--books-file", help="书名列表（每行一本，无书名号）")
    ps.add_argument("--out-dir", default=os.getcwd())
    ps.add_argument("titles", nargs="*", help="直接给书名也可")

    pq = sub.add_parser("search", help="搜索单本返回候选")
    pq.add_argument("query")
    pq.add_argument("--limit", type=int, default=10)

    pv = sub.add_parser("verify", help="登录态预检")
    pv.add_argument("--book", default="bcb32150719afe3bbcbad52")

    pl = sub.add_parser("login", help="首次启动登录（弹出窗口扫码）")
    pl.add_argument("--home", default="https://weread.qq.com/", help="登录页 URL")

    pc = sub.add_parser("cleanup", help="清理后台进程（只杀自己人）")
    pc.add_argument("--dry-run", action="store_true", help="仅列出将要清理的目标，不真正杀")
    pc.add_argument("--port", type=int)

    pseed = sub.add_parser("seed", help="复制登录态 profile（首次使用）")
    pseed.add_argument("--src", help="源 Default profile 路径")
    pseed.add_argument("--dst", help="目标 WereadCDP 目录")

    return ap.parse_args()

# 命令注册表（扩展点）：name -> (module, func, needs_browser)
COMMANDS = {
    "extract": ("commands.extract", "run", True),
    "expand":  ("commands.expand", "run", True),
    "shelf":   ("commands.shelf", "run", True),
    "search":  ("commands.search", "run", True),
    "verify":  ("commands.verify", "run", True),
    "login":   ("commands.login", "run", True),
    "cleanup": ("commands.cleanup", "run", False),
    "seed":    ("commands.seed", "run", False),
}

def main():
    args = parse()
    spec = COMMANDS.get(args.cmd)
    if not spec:
        print("未知命令: %s" % args.cmd)
        sys.exit(1)
    modname, funcname, needs_browser = spec

    if not needs_browser:
        mod = __import__(modname, fromlist=[funcname])
        getattr(mod, funcname)(args)
        return

    # 需要浏览器的命令：自启 + 连接（Chrome 失败自动降级 Edge），结束自动清理
    port = int(os.environ.get("CDP_PORT", "9223"))
    profile = os.environ.get("WEREAD_PROFILE") or browser.DEFAULT_PROFILE
    pref = os.environ.get("BROWSER")  # auto | chrome | edge
    try:
        cdp, bname = browser.launch_and_connect(browser_pref=pref, port=port, profile=profile)
    except Exception as e:
        log("❌ 浏览器启动失败: %s" % e)
        sys.exit(1)
    mode = "有头" if getattr(cdp, "headed", False) else "无头"
    log("✅ 已用 %s（%s模式）启动浏览器（Playwright，profile=%s）" % (bname, mode, profile))
    try:
        mod = __import__(modname, fromlist=[funcname])
        getattr(mod, funcname)(args, cdp)
    finally:
        browser.cleanup(cdp, port)
        log("🧹 已清理本次浏览会话。")

if __name__ == "__main__":
    main()
