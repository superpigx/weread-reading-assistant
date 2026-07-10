# -*- coding: utf-8 -*-
"""搜索单本书，返回候选列表（可独立使用 / 调试）。"""
import json, urllib.parse, time
from common import log, JS_SEARCH, open_logged_in

def run(args, cdp):
    q = args.query
    limit = args.limit or 10
    url = "https://weread.qq.com/web/search/books?keyword=" + urllib.parse.quote(q)
    open_logged_in(cdp, url, 7, login_timeout=120)  # 含未登录等待扫码
    cands = None
    for _ in range(3):
        c = cdp.evaluate(JS_SEARCH)
        if isinstance(c, str):
            try:
                c = json.loads(c)
            except Exception:
                c = []
        if isinstance(c, list) and c:
            cands = c
            break
        time.sleep(2.5)
    if not cands:
        log("无结果"); return
    cands = cands[:limit]
    print(json.dumps(cands, ensure_ascii=False, indent=2))
