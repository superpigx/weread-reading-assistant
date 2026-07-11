# -*- coding: utf-8 -*-
"""微信读书扩展阅读助手 — 共享工具：日志、中文判定、版本优选、JS 片段、等待常量。"""
import datetime, re, time, base64, json

# 这些常量现在作为「兜底超时上限」：页面元素一旦渲染完成（wait_selector/wait_fn）
# 会立即继续，不再死等满。真实网络下通常 1~3 秒就走完，远小于以下上限。
SEARCH_WAIT = 8.0
BOOK_WAIT = 12.0
CLICK_WAIT = 5.0
NAV_TIMEOUT = 60

def log(msg, logfile=None):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = "[%s] %s" % (ts, msg)
    print(line, flush=True)
    if logfile:
        try:
            with open(logfile, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

def has_cn(t):
    return any('\u4e00' <= c <= '\u9fff' for c in t)

def is_eng(t):
    if "英文原版" in t:
        return True
    if not has_cn(t):
        return True
    return False

def pick(cands, name):
    """在搜索候选里优选：标题含书名、非英文原版、推荐值最高；兜底用书名前两字。"""
    if not cands:
        return None
    matched = [c for c in cands if (name in c["t"]) and not is_eng(c["t"])]
    if not matched:
        matched = [c for c in cands if name in c["t"]]
    if not matched and len(name) >= 3:
        prefix = name[:2]
        matched = [c for c in cands if (prefix in c["t"]) and not is_eng(c["t"])]
    if not matched:
        return None
    matched.sort(key=lambda c: (-c["rec"], len(c["t"])))
    return matched[0]

BOOK_RE = re.compile(r"\u300a([^\u300a\u300b\n]{1,40})\u300b")  # 匹配《...》，排除嵌套书名号与超长（跨页截断）


def extract_books(txt, self_title=""):
    """从正文文本提取《...》书名。清洗规则：去掉跨页截断噪声（含 .. ）、
    仍含书名号的嵌套脏数据、过短（<2字）、以及本书自身标题。返回列表（不去重，调用方去重）。"""
    out = []
    if not txt:
        return out
    for m in BOOK_RE.findall(txt):
        t = m.strip()
        if not t:
            continue
        if ".." in t or "..." in t:        # 跨页截断噪声，如「世界上最伟..」
            continue
        if "\u300a" in t or "\u300b" in t:  # 仍有书名号（嵌套），丢弃
            continue
        if len(t) < 2:
            continue
        if self_title and t == self_title:
            continue
        out.append(t)
    return out


def read_reader_text(cdp):
    """读取微信读书阅读器正文全文：优先 .readerChapterContent 真实正文容器，
    缺失（极少数书用不同结构）时回退 document.body.textContent。返回字符串。"""
    txt = cdp.evaluate("(function(){var el=document.querySelector('.readerChapterContent');return el?el.textContent:'';})()")
    if isinstance(txt, str) and len(txt.strip()) > 50:
        return txt
    body = cdp.evaluate("(function(){return document.body?document.body.textContent:'';})()")
    return body if isinstance(body, str) else ""


def _is_sane_text(txt):
    """判断解码后的文本是否为有效章节内容（XML/CSS/中文正文）。"""
    t = txt.strip()
    if t.startswith("<?xml") or t.startswith("<"):
        return True
    if re.search(r"<[a-zA-Z!]", t[:60]):
        return True
    if "width" in t[:60] or "body{" in t[:60] or ".class" in t[:60] or t[:1] == "{":
        return True
    head = t[:200]
    if head:
        cjk = sum(1 for c in head if "\u4e00" <= c <= "\u9fff")
        if cjk / len(head) > 0.2:
            return True
    return False


def decode_chapter_body(raw):
    """解码 web/book/chapter/e_N 的回包正文 -> 清理后的纯文本。

    微信读书章节接口回包格式（已实测）：
      可选 JSON 包裹 -> 否则为 [hex哈希串][base64编码的 XHTML 或 正文]。
    hex 哈希长度不固定，其后紧跟 base64；base64 解码后或以 <?xml 开头（XHTML 章节），
    或为纯中文正文，或为 CSS（样式章节）。采用「去 hex 前缀 + 多偏移试解」策略，
    选取解码后内容合理的那一份，最后剥标签/实体。
    """
    if not raw:
        return ""
    s = raw.strip()
    # 1) 已是文本（极少数情况）
    if s.startswith("<?xml") or s.lstrip().startswith("<"):
        return _strip_tags(s)
    # 2) JSON 包裹：取其中的字符串字段再递归
    try:
        j = json.loads(s)
        if isinstance(j, dict):
            for k in ("p", "content", "data", "text", "body", "html"):
                if isinstance(j.get(k), str):
                    return decode_chapter_body(j[k])
    except Exception:
        pass
    # 3) 去 hex 前缀，然后多偏移试解 base64
    m = re.match(r"^[0-9A-Fa-f]+", s)
    start = m.end() if m else 0
    cand = s[start:]
    best = None
    for off in range(0, 4):
        sub = cand[off:]
        if len(sub) < 8:
            continue
        try:
            raw_b = base64.b64decode(sub)
            txt = raw_b.decode("utf-8", "ignore")
        except Exception:
            continue
        if _is_sane_text(txt):
            best = txt
            break
    if best is None:
        best = cand  # 兜底：返回原串（下次正则自然无匹配）
    return _strip_tags(best)


def _strip_tags(txt):
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"&[a-zA-Z#0-9]+;", " ", txt)
    txt = re.sub(r"\s+", " ", txt)
    return txt.strip()


# ---- 加书架相关 JS ----
JS_SEARCH = r"""(function(){
  var items=[].slice.call(document.querySelectorAll('.wr_bookList_item'));
  var out=[];
  for(var i=0;i<items.length;i++){
    var it=items[i];
    var a=it.querySelector('a[href*="web/reader/"]')||it.querySelector('a[href*="web/bookDetail/"]');
    if(!a) continue;
    var href=a.getAttribute('href')||'';
    var m=href.match(/\/(?:web\/reader|web\/bookDetail)\/([A-Za-z0-9]+)/);
    if(!m) continue;
    var v=m[1];
    var t=(it.innerText||'').replace(/\s+/g,' ').trim();
    var rm=t.match(/推荐值\s*([\d.]+)%/);
    var rec=rm?parseFloat(rm[1]):-1;
    out.push({v:v, t:t.slice(0,70), rec:rec});
  }
  return JSON.stringify(out);
})();"""

JS_READ = r"""(function(){
  var b=document.querySelector('button.bookInfo_right_header_addShelfBtn');
  var h=document.querySelector('h1')||document.querySelector('.readerBookInfo_head');
  var body=(document.body?document.body.innerText:'').replace(/\s+/g,' ');
  return JSON.stringify({url:location.href, btn:b?b.textContent.trim():'NO_BTN', title:h?h.textContent.trim():'', xiajia:(body.indexOf('下架')>=0||body.indexOf('已下架')>=0)});
})();"""

JS_CLICK = r"""(function(){
  var els=[].slice.call(document.querySelectorAll('button,div,span,a')).filter(function(e){
    var x=(e.innerText||'').trim();
    return x==='加入书架'||(x.indexOf('加入书架')>=0 && x.indexOf('已加入')<0);
  });
  els.sort(function(a,b){return (a.tagName==='BUTTON'?0:1)-(b.tagName==='BUTTON'?0:1);});
  var b=els[0];
  if(!b) return JSON.stringify({clicked:false});
  b.click();
  return JSON.stringify({clicked:true, tag:b.tagName});
})();"""

# ---- 提取提及书相关 JS ----
JS_OPEN_SEARCH = r"""(function(){
  var inp=document.querySelector('input[placeholder*="搜索"]');
  if(!inp) return JSON.stringify({ok:false, reason:'no search input'});
  inp.focus();
  inp.value='《';
  inp.dispatchEvent(new Event('input',{bubbles:true}));
  inp.dispatchEvent(new KeyboardEvent('keydown',{key:'《',bubbles:true}));
  return JSON.stringify({ok:true});
})();"""

JS_READ_RESULTS = r"""(function(){
  var sel=['.readerCatalog_searchResult','.searchResult','.app_searchResult','.readerCatalog_item'];
  var box=null;
  for(var i=0;i<sel.length;i++){box=document.querySelector(sel[i]); if(box) break;}
  var txt=box?box.innerText:document.body.innerText;
  return JSON.stringify({len:(txt||'').length, txt:(txt||'').slice(0,20000)});
})();"""

JS_SCROLL = r"""(function(){
  var sel=['.readerCatalog_searchResult','.searchResult','.app_searchResult','.readerCatalog_item'];
  var box=null;
  for(var i=0;i<sel.length;i++){box=document.querySelector(sel[i]); if(box) break;}
  if(box){ box.scrollTop=box.scrollHeight; }
  else { window.scrollBy(0,4000); }
  return JSON.stringify({scrolled:!!box});
})();"""

def read_page(cdp):
    page = cdp.evaluate(JS_READ)
    if isinstance(page, str):
        try:
            page = json.loads(page)
        except Exception:
            page = {}
    if isinstance(page, dict) and page.get("url"):
        return page
    # 第一次没读到有效页：等一下关键元素再读一次（替代固定重试 sleep）
    cdp.wait_selector("button.bookInfo_right_header_addShelfBtn, h1", timeout=5)
    page = cdp.evaluate(JS_READ)
    if isinstance(page, str):
        try:
            page = json.loads(page)
        except Exception:
            page = {}
    return page if isinstance(page, dict) else {"url": "", "btn": "READ_FAIL", "title": "", "xiajia": False}

def open_logged_in(cdp, url, wait, login_timeout=180):
    """导航到 url 并等待渲染；若处于 headed 模式且检测到未登录（页面出现登录/扫码二维码），
    阻塞等待用户在弹出的真实窗口中扫码，扫完继续。无头模式不等待（无法扫码）。
    返回 read_page(cdp) 的结果。

    性能优化：
    - 用 wait_selector 等页面关键元素出现即继续（不再死等 wait 秒）。
    - 登录态**本会话只检测一次**（_login_confirmed 缓存），避免已登录会话里偶发
      body 含「登录」字样导致误判、每次白等 login_timeout 秒。
    """
    cdp.navigate(url)
    # 登录态：本会话仅检测一次
    if getattr(cdp, "headed", False) and not getattr(cdp, "_login_confirmed", False):
        st = cdp.evaluate(
            "(function(){var b=document.body?document.body.innerText:'';"
            "return {need:/登录/.test(b)||/微信扫码/.test(b)||/二维码/.test(b)};})()")
        need = isinstance(st, dict) and st.get("need")
        if need:
            log("⏳ 检测到未登录，请在弹出的浏览器窗口中扫码登录（最多等待 %d 秒）…" % login_timeout)
            if cdp.wait_for_login(timeout=login_timeout):
                log("✅ 登录成功，继续操作。")
            else:
                log("⚠️ 等待登录超时，本次操作可能失败。")
        cdp._login_confirmed = True  # 无论是否登录，本次会话不再重复检测
    # 等页面关键元素渲染（替代固定 sleep；元素出现即继续）
    if "/web/search/" in url:
        cdp.wait_selector(".wr_bookList_item", timeout=wait)
    elif "/web/bookDetail/" in url or "/web/reader/" in url:
        cdp.wait_selector("button.bookInfo_right_header_addShelfBtn, h1", timeout=wait)
    else:
        time.sleep(min(wait, 2.0))
    return read_page(cdp)

import json
