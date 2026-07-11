# -*- coding: utf-8 -*-
"""批量把书加入微信读书书架：搜索 -> 优选中文版 -> 真实点击 -> 校验。"""
import os, json, time, urllib.parse, datetime
from common import (log, pick, JS_SEARCH, JS_READ, JS_CLICK, _search_candidates,
                    SEARCH_WAIT, BOOK_WAIT, CLICK_WAIT, read_page, open_logged_in, _safe_json_parse)

VERIFY_BOOK = os.environ.get("WEREAD_VERIFY_BOOK", "bcb32150719afe3bbcbad52")  # 用于登录态预检，可通过环境变量覆盖

def add_one(cdp, name, L):
    cands = _search_candidates(cdp, name)
    if not isinstance(cands, list):
        L("    搜索解析异常"); cands = []
    pc = pick(cands, name)
    if not pc:
        L("    ✗ 未找到中文版本"); return {"name": name, "status": "未找到", "url": ""}
    v = pc["v"]
    burl = "https://weread.qq.com/web/bookDetail/" + v
    L("    选定: %s | 推荐值%s" % (pc["t"][:40], pc["rec"]))
    page = open_logged_in(cdp, burl, BOOK_WAIT, login_timeout=120)
    btn = page.get("btn", "")
    landed = page.get("title", "")
    xiajia = page.get("xiajia", False)
    if xiajia:
        L("    → 已下架"); return {"name": name, "status": "已下架", "url": burl, "landed": landed}
    if btn == "已加入书架":
        L("    → 已在书架"); return {"name": name, "status": "已在书架", "url": burl, "landed": landed}
    if btn == "加入书架":
        cdp.evaluate("(function(){var b=document.querySelector('button.bookInfo_right_header_addShelfBtn'); if(b) b.click();})()")
        # 等「已加入书架」文本出现即继续（替代固定 sleep）
        cdp.wait_fn(
            "(function(){var b=document.querySelector('button.bookInfo_right_header_addShelfBtn');"
            "return b && /已加入/.test(b.textContent);})()", timeout=CLICK_WAIT)
        after = read_page(cdp)
        if after.get("btn") == "已加入书架":
            L("    → 加入成功"); return {"name": name, "status": "加入成功", "url": burl, "landed": landed}
        cdp.evaluate(JS_CLICK)
        cdp.wait_fn(
            "(function(){var b=document.querySelector('button.bookInfo_right_header_addShelfBtn');"
            "return b && /已加入/.test(b.textContent);})()", timeout=CLICK_WAIT)
        after2 = read_page(cdp)
        if after2.get("btn") == "已加入书架":
            L("    → 加入成功(兜底)"); return {"name": name, "status": "加入成功", "url": burl, "landed": landed}
        L("    → 加入失败(仍为:%s)" % after.get("btn"))
        return {"name": name, "status": "加入失败", "url": burl, "landed": landed}
    L("    → 异常(无按钮:%s)" % btn)
    return {"name": name, "status": "异常", "url": burl, "landed": landed}

def run(args, cdp):
    books = []
    if args.books_file and os.path.exists(args.books_file):
        with open(args.books_file, encoding="utf-8") as f:
            books = [l.strip().strip("《》").strip() for l in f if l.strip()]
    if args.titles:
        books += [t.strip().strip("《》").strip() for t in args.titles]
    OFFSET = int(os.environ.get("OFFSET", "0") or "0")
    LIMIT = int(os.environ.get("LIMIT", "0") or "0")
    if OFFSET:
        books = books[OFFSET:]
    if LIMIT > 0:
        books = books[:LIMIT]
    total = len(books)
    if total == 0:
        log("无书可加"); return

    out_dir = args.out_dir or os.getcwd()
    os.makedirs(out_dir, exist_ok=True)
    logfile = os.path.join(out_dir, "shelf_log.txt")
    def L(m):
        log(m, logfile)

    L("=== 批量加书架：%d 本 (OFFSET=%d) ===" % (total, OFFSET))
    chk = open_logged_in(cdp, "https://weread.qq.com/web/bookDetail/" + VERIFY_BOOK, BOOK_WAIT, login_timeout=180)
    L("【登录预检】掌控习惯 btn=%s title=%s" % (chk.get("btn"), chk.get("title")))
    if chk.get("btn") != "已加入书架":
        L("⚠️ 登录态可能失效（未显示「已加入书架」），结果可能全失败，请检查 profile。")

    results = []
    added = already = failed = 0
    for i, name in enumerate(books):
        L(">>> [%d/%d] %s （剩余%d）" % (i + 1, total, name, total - i - 1))
        r = add_one(cdp, name, L)
        st = r["status"]
        if st == "加入成功":
            added += 1
        elif st == "已在书架":
            already += 1
        else:
            failed += 1
        r["idx"] = OFFSET + i + 1
        results.append(r)
        L("    | 已加%d 已在%d 失败%d 剩余%d" % (added, already, failed, total - i - 1))

    RJ = os.path.join(out_dir, "shelf_result.json")
    RM = os.path.join(out_dir, "weread_added.md")
    summary = {"total": total, "offset": OFFSET, "added": added, "already": already, "failed": failed,
               "failed_books": [r["name"] for r in results if r["status"] not in ("加入成功", "已在书架")],
               "results": results, "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    with open(RJ, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    lines = ["# 加书架结果", ""]
    lines.append("- 本次新加入：**%d** | 之前已在：**%d** | 失败/下架/未找到：**%d**" % (added, already, failed))
    lines.append("")
    lines.append("| # | 书名 | 状态 | 落点书名 |")
    lines.append("|---|---|---|---|")
    for r in results:
        lines.append("| %s | %s | %s | %s |" % (r.get("idx", ""), r["name"], r["status"], r.get("landed", "")[:24]))
    with open(RM, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    L("=== 完成：新加%d 已在%d 失败%d ===" % (added, already, failed))
    if summary["failed_books"]:
        L("需关注: " + "；".join(summary["failed_books"]))
