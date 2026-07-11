# -*- coding: utf-8 -*-
"""生成推荐书单精美 HTML 页面：提取《书名》→ 逐本搜索微信读书获取详情 → 出品自包含 HTML。"""
import os, re, json, time, urllib.parse, datetime
from common import log, extract_books, open_logged_in, pick, JS_SEARCH, _safe_json_parse, _search_candidates

# ---------- 图书详情解析 ----------

def _search_book_detail(cdp, cdp_page, name):
    """搜索一本书并返回最匹配结果的详细信息。"""
    cands = _search_candidates(cdp, name, retries=2)
    if not cands:
        return None
    best = pick(cands, name)
    if not best:
        best = cands[0]

    # 解析 t 字段: "书名 作者 X人今日阅读 推荐值 XX% 简介..."
    t = best.get("t", "")
    info = _parse_book_t(t)

    # 尝试从 DOM 取封面图
    cover = ""
    if cdp_page is not None:
        js = r"""(function(){
          var imgs=document.querySelectorAll('.wr_bookList_item img');
          for(var i=0;i<imgs.length;i++){if(imgs[i].src) return imgs[i].src;}
          return '';
        })()"""
        try:
            cover = cdp_page.evaluate(js) or ""
        except Exception:
            pass

    return {
        "title": info.get("title", name),
        "author": info.get("author", ""),
        "rating": best.get("rec", -1),
        "readers": info.get("readers", ""),
        "desc": info.get("desc", ""),
        "cover": cover,
        "url": "https://weread.qq.com/web/bookDetail/" + best.get("v", ""),
        "v": best.get("v", ""),
    }


def _parse_book_t(t):
    """从微信读书搜索结果字符串稳健解析：书名、作者、读者数、简介。
    用正则逐字段提取（不依赖空格分隔顺序），格式变化时各字段独立退化。"""
    info = {}
    t = t.replace("\n", " ").strip()
    # 推荐值（最可靠，格式稳定）
    rm = re.search(r"推荐值\s*([\d.]+)%", t)
    if rm:
        info["rating_str"] = rm.group(0)
    # 读者数
    rm2 = re.search(r"(\d+人今日阅读)", t)
    if rm2:
        info["readers"] = rm2.group(1)
    # 简介：推荐值 % 之后的部分
    idx_pct = t.find("%")
    if idx_pct > 0 and idx_pct < len(t) - 6:
        desc = t[idx_pct + 1:].strip()
        if len(desc) > 8:
            info["desc"] = desc[:80]
    # 作者：在书名和读者数之间（最脆弱部分，多策略叠加）
    author = ""
    if "人今日阅读" in t:
        prefix = t[:t.index("人今日阅读")]
        # 去掉末尾数字（如"5"来自"5人今日阅读"）
        prefix = re.sub(r"\d+\s*$", "", prefix).strip()
        # 找最后一个双空格/中文标点之后的部分
        m_author = re.search(r"(?:[^\u4e00-\u9fffA-Za-z0-9·\u300a\u300b]|\s{2,})([^\u4e00-\u9fffA-Za-z0-9·\u300a\u300b][\s\S]+?)$", prefix)
        if m_author:
            candidate = m_author.group(1).strip()
            # 过滤：太短不是作者，太长可能是书名残留
            if 2 <= len(candidate) <= 40 and not re.match(r"^[\d\s.]+$", candidate):
                author = candidate
        if not author:
            parts = [p for p in re.split(r"\s{2,}", prefix) if p]
            if len(parts) >= 2 and len(parts[-1]) < 30:
                author = re.sub(r"\d+\s*$", "", parts[-1]).strip()
    # 书名：排除作者和前缀后的首段
    if author:
        t2 = t[:t.find(author)].strip() if author in t else t
    else:
        t2 = t
    m_title = re.match(r"^(.+?)(?:\s{2,}|\s+\d|\s*$)", t2)
    info["title"] = m_title.group(1).strip() if m_title else t2.split()[0] if t2.split() else t2[:40]
    info["author"] = author
    return info


# ---------- HTML 生成 ----------

_HERE = os.path.dirname(os.path.abspath(__file__))
_CSS_FILE = os.path.join(_HERE, "..", "..", "templates", "recommend.css")
try:
    with open(_CSS_FILE, "r", encoding="utf-8") as f:
        REC_CSS = f.read()
except Exception:
    REC_CSS = ""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>《{self_title}》推荐书单</title>
<style>
""" + REC_CSS + """
</style>
</head>
<body>
<div class="container">
<div class="hero">
  <h1>📚 《<em>{self_title}</em>》推荐书单</h1>
  <p class="subtitle">书中提及的所有书籍，整理为结构化阅读清单</p>
</div>
<div class="stats">
  <div class="stat"><div class="num">{book_count}</div><div class="label">推荐书籍</div></div>
  <div class="stat"><div class="num">{avg_rating:.0f}%</div><div class="label">平均推荐值</div></div>
</div>
<div class="grid">
{cards}
</div>
<div class="footer">
  由 <a href="https://github.com/superpigx/weread-reading-assistant">微信读书扩展阅读助手</a> 生成 · {gen_time}<br>
  数据来源 <a href="{source_url}">微信读书</a>
</div>
</div>
</body>
</html>"""


def _rating_class(r):
    if r >= 75: return "high"
    if r >= 50: return "mid"
    return "low"


def _build_card(book):
    title = book.get("title", "")
    author = book.get("author", "")
    rating = book.get("rating", -1)
    desc = book.get("desc", "")
    cover = book.get("cover", "")
    url = book.get("url", "")
    readers = book.get("readers", "")
    rating_str = "%.1f%%" % rating if rating >= 0 else "N/A"

    cover_html = ""
    if cover:
        cover_html = '<img src="%s" alt="%s" loading="lazy">' % (cover, title)
    else:
        cover_html = '📖'

    return """<div class="card">
  <div class="card-cover">%s</div>
  <div class="card-body">
    <h3 title="%s">%s</h3>
    <div class="author">%s</div>
    <div class="desc">%s</div>
    <div class="meta">
      <span class="rating %s">%s</span>
      <span class="readers">%s</span>
    </div>
    <a class="btn" href="%s" target="_blank" rel="noopener">📖 在微信读书中查看</a>
  </div>
</div>""" % (cover_html, title, title, author or "&nbsp;", desc, _rating_class(rating), rating_str, readers, url)


# ---------- 主入口 ----------

def run(args, cdp):
    url = args.reader_url
    if not url and args.v:
        url = "https://weread.qq.com/web/reader/" + args.v
    if not url:
        log("需提供 --reader-url 或 --v"); return
    out_dir = args.out_dir or os.getcwd()
    os.makedirs(out_dir, exist_ok=True)
    logfile = os.path.join(out_dir, "recommend_log.txt")
    self_title = args.self_title or "本书"

    from commands.extract import collect_mentioned

    def L(m):
        log(m, logfile)

    L("═══ 生成推荐书单 HTML ═══")
    L("【阶段1】提取书中提及的书: %s" % url)
    books = collect_mentioned(cdp, url, self_title, 200, logfile)
    if not books:
        L("未提取到书"); return
    L("提取到 %d 本" % len(books))

    L("【阶段2】逐本搜索微信读书获取详情")
    book_details = []
    page = getattr(cdp, "page", None)
    for i, name in enumerate(books):
        L("  [%d/%d] %s" % (i + 1, len(books), name))
        detail = _search_book_detail(cdp, page, name)
        if detail:
            book_details.append(detail)
        else:
            book_details.append({"title": name, "author": "", "rating": -1,
                                 "desc": "", "cover": "", "url": "", "readers": ""})

    # 计算统计
    ratings = [b["rating"] for b in book_details if b.get("rating", -1) >= 0]
    avg = sum(ratings) / len(ratings) if ratings else 0

    # 生成 HTML
    cards_html = "\n".join(_build_card(b) for b in book_details)
    gen_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    source_url = "https://weread.qq.com/web/reader/%s" % (args.v or url.split("/")[-1])
    html = HTML_TEMPLATE.format(
        self_title=self_title, book_count=len(books), avg_rating=avg,
        cards=cards_html, gen_time=gen_time, source_url=source_url,
    )

    out = os.path.join(out_dir, "recommend_books.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    L("✅ 推荐书单 HTML 已生成: %s" % out)
