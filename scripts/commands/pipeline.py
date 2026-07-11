# -*- coding: utf-8 -*-
"""全流程管道：提取书中提及的书 → 批量加入书架。端到端自动执行，零手动步骤。"""
import os, time
from common import log, open_logged_in
from commands.extract import collect_mentioned
from commands.shelf import add_one


def run(args, cdp):
    url = args.reader_url
    if not url and args.v:
        url = "https://weread.qq.com/web/reader/" + args.v
    if not url:
        log("需提供 --reader-url 或 --v")
        return
    out_dir = args.out_dir or os.getcwd()
    os.makedirs(out_dir, exist_ok=True)
    logfile = os.path.join(out_dir, "pipeline_log.txt")
    self_title = (args.self_title or "").strip()
    max_pages = args.rounds or 200

    # === 阶段1：提取 ===
    def L(m):
        log(m, logfile)
    L("═══ 全流程管道：提取 → 加书架 ═══")
    L("【阶段1】提取书中提及的书: %s" % url)
    books = collect_mentioned(cdp, url, self_title, max_pages, logfile)
    if not books:
        L("未提取到任何书，结束。")
        return
    L("提取完成：%d 本" % len(books))

    # 仍产出 books.txt（方便后续独立使用）
    books_file = os.path.join(out_dir, "books.txt")
    with open(books_file, "w", encoding="utf-8") as f:
        f.write("\n".join(books))
    L("已写入 %s" % books_file)

    # === 阶段2：加书架 ===
    L("【阶段2】逐本加入书架")
    results = []
    added = already = failed = 0
    for i, name in enumerate(books):
        L(">>> [%d/%d] %s" % (i + 1, len(books), name))
        r = add_one(cdp, name, L)
        st = r["status"]
        if st == "加入成功":
            added += 1
        elif st == "已在书架":
            already += 1
        else:
            failed += 1
        r["idx"] = i + 1
        results.append(r)
        L("    | 已加%d 已在%d 失败%d 剩余%d" % (added, already, failed, len(books) - i - 1))

    L("═══ 全流程完成：新加%d / 已在%d / 失败%d ═══" % (added, already, failed))
    failed_names = [r["name"] for r in results if r["status"] not in ("加入成功", "已在书架")]
    if failed_names:
        L("需关注: " + "；".join(failed_names))
