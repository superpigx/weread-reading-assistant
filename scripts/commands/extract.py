# -*- coding: utf-8 -*-
"""提取微信读书某本书正文中《》提及的其他书籍。
v1.2.1: 改用全书搜索 API（server-side search），安全可靠，不翻页不爬虫。"""
import os, json, time, urllib.parse
from common import log, extract_books, read_reader_text, open_logged_in

SEARCH_API = "https://weread.qq.com/web/book/search"
SEARCH_COUNT = 20  # 每页搜索结果数


def _get_bookid(cdp):
    """从阅读页提取数字 bookId（如 910364）。
    优先从已加载的资源 URL 中匹配 bookId= 模式；其次从封面图片 URL（YueWen_ 前缀）提取。"""
    bid = cdp.evaluate("""(function(){
        // 1) 从 performance 资源 URL 找 bookId=<digits>
        var entries = performance.getEntriesByType('resource');
        for (var i = 0; i < entries.length; i++) {
            var m = entries[i].name.match(/bookId[=:](\\d{5,8})/);
            if (m) return m[1];
        }
        // 2) 从封面图片 src 中提取 YueWen_<digits>
        var imgs = document.querySelectorAll('img[src*="YueWen_"]');
        for (var j = 0; j < imgs.length; j++) {
            var m2 = imgs[j].src.match(/YueWen_(\\d+)/);
            if (m2) return m2[1];
        }
        return '';
    })()""")
    bid = (bid or "").strip()
    return bid


def collect_mentioned(cdp, url, self_title, max_pages, logfile):
    """用微信读书全书搜索 API 提取《书名》——服务器全量返回搜索结果，
    不需要翻页扫 DOM，零反爬风险。extract 与 expand 共用此逻辑。

    流程：打开阅读页（获取登录态 + bookId）-> 搜索《 关键词，逐页拉结果
    -> 每页 abstract 正则提取《…》-> 去重 -> 排除本书。
    """
    log("打开阅读页准备提取提及书: %s" % url, logfile)
    open_logged_in(cdp, url, 8, login_timeout=180)
    cdp.wait_selector(".readerChapterContent", timeout=20)

    book_id = _get_bookid(cdp)
    if not book_id:
        log("⚠️ 未能提取数字 bookId，降级读 DOM 首屏（结果可能不完整）", logfile)
        return sorted(set(extract_books(read_reader_text(cdp), self_title)))
    log("bookId=%s" % book_id, logfile)

    all_abstracts = []
    idx = 0
    while True:
        api_url = (SEARCH_API
                   + "?bookId=%s&keyword=%%E3%%80%%8A" % book_id  # 《 URL 编码
                   + "&maxIdx=%d&count=%d&fragmentSize=240&onlyCount=0" % (idx, SEARCH_COUNT))
        page = getattr(cdp, "page", None)
        if page is not None:
            js = "(async()=>{const r=await fetch('%s');return await r.text();})()" % api_url
            try:
                resp = page.evaluate(js)
                data = json.loads(resp)
            except Exception as e:
                log("搜索API异常(idx=%d): %s" % (idx, e), logfile)
                break
        else:
            log("⚠️ 无 page 对象，无法调用搜索 API", logfile)
            break
        results = data.get("result", [])
        if not results:
            break
        for item in results:
            abstract = item.get("abstract", "")
            if abstract:
                all_abstracts.append(abstract)
        has_more = data.get("hasMore", 0)
        log("搜索页 %d: %d 条结果, hasMore=%s" % (idx // SEARCH_COUNT, len(results), has_more), logfile)
        if not has_more:
            break
        idx += SEARCH_COUNT

    alltext = "\n".join(all_abstracts)
    books = set(extract_books(alltext, self_title))
    log("搜索 API 共提取 %d 本提及的书" % len(books), logfile)
    return sorted(books)


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
    max_pages = args.rounds or 200  # 保留兼容

    books = collect_mentioned(cdp, url, self_title, max_pages, logfile)

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
