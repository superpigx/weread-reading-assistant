# -*- coding: utf-8 -*-
"""提取微信读书某本书正文中《》提及的其他书籍。"""
import os, json, time
from common import log, BOOK_RE, JS_OPEN_SEARCH, JS_READ_RESULTS, JS_SCROLL, open_logged_in


def collect_mentioned(cdp, url, self_title, rounds, logfile):
    """打开阅读页 -> 目录栏搜《 -> 多轮滚动收集 -> 正则提取《…》去重 -> 排除本书。
    返回去重后的书名列表。extract 与 expand 共用此逻辑，避免重复维护。"""
    log("打开阅读页: %s" % url, logfile)
    open_logged_in(cdp, url, 8, login_timeout=180)  # 含未登录等待扫码
    res = cdp.evaluate(JS_OPEN_SEARCH)
    log("打开目录检索框: %s" % res, logfile)
    time.sleep(3)

    seen = set()
    books = []
    no_new_streak = 0
    for r_i in range(rounds):
        r = cdp.evaluate(JS_READ_RESULTS)
        txt = ""
        if isinstance(r, str):
            try:
                r = json.loads(r)
            except Exception:
                r = {}
        if isinstance(r, dict):
            txt = r.get("txt", "")
        found = BOOK_RE.findall(txt or "")
        new = 0
        for t in found:
            t2 = t.strip()
            if t2 and t2 not in seen and t2 != self_title:
                seen.add(t2)
                books.append(t2)
                new += 1
        cdp.evaluate(JS_SCROLL)
        time.sleep(2)
        if new == 0:
            no_new_streak += 1
            if no_new_streak >= 2 and books:
                log("连续 %d 轮无新增，判定到底，停止收集" % no_new_streak, logfile)
                break
        else:
            no_new_streak = 0
    return books


def run(args, cdp):
    url = args.reader_url
    if not url and args.v:
        url = "https://weread.qq.com/web/reader/" + args.v
    if not url:
        log("需提供 --reader-url 或 --v"); return
    out_dir = args.out_dir or os.getcwd()
    os.makedirs(out_dir, exist_ok=True)
    logfile = os.path.join(out_dir, "extract_log.txt")
    self_title = (args.self_title or "").strip()
    rounds = args.rounds or 12

    books = collect_mentioned(cdp, url, self_title, rounds, logfile)

    books_file = os.path.join(out_dir, "books.txt")
    with open(books_file, "w", encoding="utf-8") as f:
        f.write("\n".join(books))
    md = os.path.join(out_dir, "weread_mentioned_books.md")
    lines = ["# 书中提及的书（去重 %d 本）" % len(books), ""]
    for b in books:
        lines.append("- 《%s》" % b)
    with open(md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log("提取完成：%d 本 -> %s（可直接喂给 shelf 的 --books-file）" % (len(books), books_file), logfile)
