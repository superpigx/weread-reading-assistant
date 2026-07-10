# -*- coding: utf-8 -*-
"""Playwright 驱动的浏览器会话封装。

对外保持与原 hand-rolled CDP 类完全兼容的 API：navigate / evaluate / close / query，
因此 commands/* 里所有调用方一行都不用改。

底层用 Playwright（channel=chrome/edge）：
- 默认 headed（有头）模式，需要登录时直接在真实窗口扫码；设置 HEADLESS=1 可退回无头。
- 彻底摆脱 agent-browser 的脆弱 daemon（卡死、--profile 被旧 daemon 静默忽略）；
- 不再手搓 WebSocket 协议（之前各种环境坑：urllib 被 HTTP_PROXY 劫持卡死、headless 长驻进程会悄悄死）；
- Playwright 用 CDP-over-pipe 连接，稳定且对用户透明。

已验证：本沙箱 `channel="chrome"` 可正常启动系统 Chrome、访问微信读书、解析 DOM
（search / read / click 全部 OK）。无头模式仅在 HEADLESS=1 时启用。
"""
import time

NAV_TIMEOUT = 60

class CDP:
    def __init__(self, ctx, page, browser_name="", pw=None):
        self.ctx = ctx
        self.page = page
        self.browser_name = browser_name
        self._pw = pw
        self._closed = False
        self.headed = False  # 由 launch_and_connect 根据 HEADLESS 设置

    def navigate(self, url):
        # domcontentloaded 即返回；SPA 渲染由调用方 sleep 补偿（兼容命令模块的等待节奏）
        self.page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT * 1000)

    def evaluate(self, js, timeout=30):
        try:
            return self.page.evaluate(js)
        except Exception as e:
            return {"__error__": str(e)}

    def wait_selector(self, sel, timeout=10, state="attached"):
        """等价 Playwright page.wait_for_selector，元素一出现就返回 True（不再死等）。
        state 默认 attached：SPA 元素入 DOM 即认为可解析，比 visible 更快更稳。"""
        try:
            self.page.wait_for_selector(sel, timeout=timeout * 1000, state=state)
            return True
        except Exception:
            return False

    def wait_fn(self, expr, timeout=10, arg=None):
        """等价 Playwright page.wait_for_function，JS 条件成立即返回 True。"""
        try:
            self.page.wait_for_function(expr, arg=arg, timeout=timeout * 1000)
            return True
        except Exception:
            return False

    def query(self, sel):
        return self.page.query_selector(sel)

    def click(self, sel):
        el = self.page.query_selector(sel)
        if el:
            try:
                el.click(timeout=3000)
                return True
            except Exception:
                return False
        return False

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.ctx.close()
        except Exception:
            pass
        try:
            if self._pw is not None:
                self._pw.stop()
        except Exception:
            pass

    def wait_for_login(self, timeout=180, poll=5):
        """headed 模式下，若当前页面要求登录（显示登录/扫码二维码），阻塞等待用户扫码。
        返回 True=已登录或本就无需登录；False=超时仍未登录。无头模式直接返回 True（无法扫码）。"""
        if not self.headed:
            return True
        deadline = time.time() + timeout
        while time.time() < deadline:
            state = self.evaluate(
                "(function(){var b=document.body?document.body.innerText:'';"
                "return {need: /登录/.test(b)||/微信扫码/.test(b)||/二维码/.test(b)};})()")
            if isinstance(state, dict) and not state.get("need"):
                return True
            time.sleep(poll)
        return False

def connect_browser(host="127.0.0.1", port=9223, timeout=30, browser_pref=None, profile=None):
    """兼容旧签名；实际委托 browser.launch_and_connect 启动 Playwright 会话。"""
    from .browser import launch_and_connect
    cdp, _name = launch_and_connect(browser_pref=browser_pref, port=port,
                                    profile=profile, register_atexit=True)
    return cdp
