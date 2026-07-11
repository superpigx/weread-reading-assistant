# -*- coding: utf-8 -*-
"""扩展阅读：提取某本书中《》提及的其他书籍，生成带微信读书链接的「扩展阅读清单」。
不自动加书架（如需加书架，把生成的 books.txt 喂给 shelf 即可）。"""
import os, urllib.parse
from common import log
from commands.extract import collect_mentioned


def run(args, cdp):
    url = args.reader_url
    if not url and args.v:
        url = "https://weread.qq.com/web/reader/" + args.v
    if not url:
        log("需提供 --reader-url 或 --v"); return
    out_dir = args.out_dir or os.getcwd()
    os.makedirs(out_dir, exist_ok=True)
    logfile = os.path.join(out_dir, "expand_log.txt")
    self_title = (args.self_title or "").strip()
    max_pages = args.rounds or 300  # rounds 复用作最大翻页数

    books = collect_mentioned(cdp, url, self_title, max_pages, logfile)

    # 仍产出 books.txt（方便后续 shelf 一条龙），但本命令不自动加书架
    books_file = os.path.join(out_dir, "books.txt")
    with open(books_file, "w", encoding="utf-8") as f:
        f.write("\n".join(books))

    # 生成「扩展阅读清单」：每本带微信读书搜索链接（点击即在网页端检索，中文优先）
    md = os.path.join(out_dir, "weread_reading_list.md")
    head = self_title or "本书"
    lines = ["# 《%s》扩展阅读清单（共 %d 本）" % (head, len(books)), ""]
    lines.append("> 以下为书中《》提及的其他书籍。点击「微信读书」可在网页端检索该书（默认中文优先）。")
    lines.append("")
    if books:
        lines.append("| # | 书名 | 微信读书 |")
        lines.append("|---|------|---------|")
        for i, b in enumerate(books, 1):
            q = urllib.parse.quote(b)
            link = "https://weread.qq.com/web/search/books?keyword=" + q
            lines.append("| %d | 《%s》 | [搜索](%s) |" % (i, b, link))
    else:
        lines.append("_未提取到提及的书（可增大 --rounds 翻页数，或确认该书正文含《书名》引用）_")
    lines.append("")
    lines.append("---")
    lines.append("生成时间见日志。如需把以上书加入书架，运行：")
    lines.append("")
    lines.append("    python weread.py shelf --books-file books.txt")
    lines.append("")
    with open(md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log("📚 扩展阅读清单已生成：%d 本 -> %s" % (len(books), md), logfile)
    log("   （未自动加书架；如需加，把 books.txt 喂给 shelf 即可）", logfile)
