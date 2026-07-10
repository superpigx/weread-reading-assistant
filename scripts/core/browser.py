# -*- coding: utf-8 -*-
"""浏览器探测 / 启动 / 清理 / profile 管理（Playwright 实现）。

设计要点（来自踩坑教训）：
- 用 Playwright 驱动系统 Chrome/Edge（channel），彻底弃用 agent-browser daemon 与手搓 CDP。
- 默认 headed（有头）模式：需要登录时直接在弹出的真实窗口里扫码，无需无头。
  仅在设置环境变量 HEADLESS=1 时退回无头（兼容无显示器/CI 环境）；无头时自动追加 --headless=new
  （Chrome 149 已移除旧 headless，传旧 --headless 会以退出码 21 崩溃）。
- 永不使用默认 user-data-dir；统一用独立的 WereadCDP 目录（Playwright 自建 Default 子目录）。
- profile 结构关键：seed 时必须复制到 <dst>/Default（而非扁平铺平），否则 Chrome 误判损坏
  profile 并退出码 21 崩溃。
- 清理只关本会话 Playwright 浏览器 + 杀残余 agent-browser daemon；不碰用户正在用的普通 Chrome/Edge。
"""
import os, shutil, time, atexit, subprocess

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]
EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
# 用 WereadCDP2 避开之前混乱的旧 WereadCDP 目录（该目录曾扁平铺平导致结构损坏、启动退出码 21）
DEFAULT_PROFILE = r"C:\Users\Administrator\AppData\Local\Google\Chrome\WereadCDP2"

# 默认有头模式，不传 --headless；仅在 HEADLESS=1 时由 launch_and_connect 追加 --headless=new。
PW_ARGS = ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]


def find_browser(prefer=None):
    if prefer == "edge":
        for p in EDGE_PATHS:
            if os.path.exists(p):
                return p, "edge"
        return None, None
    for p in CHROME_PATHS:
        if os.path.exists(p):
            return p, "chrome"
    for p in EDGE_PATHS:
        if os.path.exists(p):
            return p, "edge"
    return None, None


def launch_and_connect(browser_pref=None, port=9223, profile=None, register_atexit=True):
    from .cdp import CDP
    profile = profile or DEFAULT_PROFILE
    os.makedirs(profile, exist_ok=True)
    pref = browser_pref or os.environ.get("BROWSER")
    if pref == "edge":
        channels = ["msedge"]
    elif pref == "chrome":
        channels = ["chrome"]
    else:
        channels = ["chrome", "msedge"]
    last_err = "未知错误"
    headless = os.environ.get("HEADLESS") == "1"
    eff_args = (PW_ARGS + ["--headless=new"]) if headless else list(PW_ARGS)
    for ch in channels:
        exe, _ = find_browser(ch)
        if not exe:
            last_err = "未找到 %s 可执行文件" % ch
            continue
        try:
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            ctx = pw.chromium.launch_persistent_context(
                profile, channel=ch, headless=headless, args=eff_args)
            page = ctx.new_page()
            cdp = CDP(ctx, page, browser_name=ch, pw=pw)
            cdp.headed = (not headless)

            def _cleanup():
                try:
                    ctx.close()
                except Exception:
                    pass
                try:
                    pw.stop()
                except Exception:
                    pass
                kill_agent_browser()

            if register_atexit:
                atexit.register(_cleanup)
                cdp._cleanup = _cleanup
            return cdp, ch
        except Exception as e:
            last_err = "%s 异常: %s" % (ch, e)
            try:
                pw.stop()
            except Exception:
                pass
            continue
    raise RuntimeError("无法启动浏览器（已尝试 %s）：%s" % ("->".join(channels), last_err))


def kill_agent_browser():
    try:
        subprocess.run(["taskkill", "/F", "/IM", "agent-browser-win32-x64.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    except Exception:
        pass


def cleanup(cdp, port):
    """兼容 weread.py 旧调用：关本会话 Playwright 浏览器 + 杀 agent-browser 残余。"""
    if cdp is not None:
        try:
            cdp.close()
        except Exception:
            pass
    kill_agent_browser()


def plan_cleanup(port):
    """dry-run：返回将要清理的目标描述列表（不真正杀进程）。"""
    plan = ["agent-browser daemon: agent-browser-win32-x64.exe（若存在）"]
    return plan


def kill_strays_on_port(port):
    # Playwright 用 CDP-over-pipe 连接，不再有独立 CDP 端口残留，保留接口为空操作以兼容 cleanup 命令。
    pass


def seed_profile(src_default, dst_profile):
    """复制已登录的 Default profile 为独立 WereadCDP 目录（首次使用前调用）。

    关键：复制到 <dst_profile>/Default（Playwright 的 user_data_dir 期望含 Default 子目录），
    而非扁平铺平——扁平会让 Chrome 误判为损坏 profile 并以退出码 21 崩溃。排除锁文件。
    """
    dst_default = os.path.join(dst_profile, "Default")
    if os.path.isdir(dst_default):
        shutil.rmtree(dst_default)
    os.makedirs(dst_profile, exist_ok=True)
    shutil.copytree(
        src_default, dst_default,
        ignore=shutil.ignore_patterns("SingletonLock", "SingletonCookie",
                                      "SingletonSocket", "*.lock", "lockfile"))
    parent = os.path.dirname(src_default)
    local_state = os.path.join(parent, "Local State")
    if os.path.isfile(local_state):
        shutil.copy(local_state, os.path.join(dst_profile, "Local State"))
    return dst_profile
