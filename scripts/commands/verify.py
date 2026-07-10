# -*- coding: utf-8 -*-
"""登录态预检：打开一本已知已加架的书，看按钮是否为「已加入书架」。"""
import time
from common import log, BOOK_WAIT, read_page, open_logged_in

def run(args, cdp):
    v = args.book or "bcb32150719afe3bbcbad52"
    p = open_logged_in(cdp, "https://weread.qq.com/web/bookDetail/" + v, BOOK_WAIT, login_timeout=180)
    log("登录态预检: btn=%s title=%s" % (p.get("btn"), p.get("title")))
    if p.get("btn") == "已加入书架":
        log("✅ 登录态有效，可批量加书架。")
    else:
        log("⚠️ 登录态可能失效（btn=%s），加书架会失败，请重新 seed profile。" % p.get("btn"))
