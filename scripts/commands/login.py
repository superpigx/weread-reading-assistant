# -*- coding: utf-8 -*-
"""首次启动登录：开浏览器 -> 等扫码 -> 确认已登录 -> 退出。登录态固化在 profile。

与把扫码逻辑藏在 shelf 里不同，login 是一个独立、显式的「首次启动」步骤：
用户跑一次 login 扫完码，后续 shelf/extract/search/verify 都默认已登录、无需再扫。
"""
import os, time
from common import log, open_logged_in


def _still_need_login(cdp):
    st = cdp.evaluate(
        "(function(){var b=document.body?document.body.innerText:'';"
        "return {need:/登录/.test(b)||/微信扫码/.test(b)||/二维码/.test(b)};})()")
    return isinstance(st, dict) and bool(st.get("need"))


def run(args, cdp):
    profile = os.environ.get("WEREAD_PROFILE") or "WereadCDP2"
    log("👉 打开微信读书首页，请在弹出的浏览器窗口中扫码登录（首次启动）…")
    # open_logged_in 会导航到首页；headed 模式下若检测到未登录，会阻塞等待扫码完成
    open_logged_in(cdp, "https://weread.qq.com/", wait=8, login_timeout=180)
    # 再确认一次：轮询页面是否已无「登录/扫码」字样（兜底：若 open_logged_in 因渲染慢错过等待窗口）
    deadline = time.time() + 60
    ok = False
    while time.time() < deadline:
        if not _still_need_login(cdp):
            ok = True
            break
        time.sleep(2)
    if ok:
        log("✅ 登录成功！登录态已固化在 profile（%s）中。" % profile)
        log("   后续运行 shelf / extract / search / verify 时，若该 profile 登录未过期，将不再需要扫码。")
    else:
        log("⚠️ 仍未检测到已登录状态，请确认扫码已完成且页面已刷新；可重跑 `login`。")
