import re
from datetime import datetime
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from .database import connect, log_collection

# Start with one public event index that visibly lists event dates, locations and detail links.
# Add other sources only after checking their terms, robots rules and page stability.
SOURCES = [
    {
        "name": "长沙本地宝·活动汇总",
        "url": "https://m.cs.bendibao.com/xiuxian/",
        "allowed_domains": {"m.cs.bendibao.com", "cs.bendibao.com"},
    },
    {
        "name": "长沙本地宝·活动资讯",
        "url": "https://cs.bendibao.com/xiuxian/huodongnews/",
        "allowed_domains": {"m.cs.bendibao.com", "cs.bendibao.com"},
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ChangshaEventRadar/1.0; +local personal event guide)"
}
TIMEOUT = 18
CITY_TERMS = ("长沙", "岳麓", "芙蓉", "天心", "开福", "雨花", "望城", "长沙县", "浏阳", "宁乡")
DATE_RE = re.compile(r"(20\d{2})[年./-](\d{1,2})[月./-](\d{1,2})日?")
SHORT_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})[月./-](\d{1,2})日?")
RANGE_RE = re.compile(r"(\d{1,2})[月./-](\d{1,2})日?\s*[-至~—]\s*(?:(\d{1,2})[月./-])?(\d{1,2})日?")
PRICE_RE = re.compile(r"(免费|免门票|无需门票|票价\s*[：:]?\s*\d+元|\d{1,4}(?:-\d{1,4})?元(?:起)?|¥\s*\d+(?:-\d+)?(?:起)?)")
CATEGORY_MAP = {
    "演出": ("演出", "音乐会", "演唱会", "livehouse", "话剧", "舞剧", "音乐节"),
    "展览": ("展览", "美术馆", "艺术展", "摄影展", "特展"),
    "市集": ("市集", "集市", "面包节", "文创", "摊位"),
    "电影": ("电影", "放映", "观影"),
    "运动": ("跑", "徒步", "骑行", "马拉松", "赛事", "运动"),
}

def category_for(text):
    low = text.lower()
    for cat, words in CATEGORY_MAP.items():
        if any(w.lower() in low for w in words):
            return cat
    return "其他"

def normalize_date(text):
    """Extract dates as ISO strings where possible; ambiguous dates are left blank."""
    today = datetime.now()
    m = DATE_RE.search(text)
    if m:
        try:
            return date_parser.parse(f"{m.group(1)}-{m.group(2)}-{m.group(3)}").date().isoformat()
        except Exception:
            pass
    m = SHORT_DATE_RE.search(text)
    if m:
        try:
            d = date_parser.parse(f"{today.year}-{m.group(1)}-{m.group(2)}")
            # If the inferred date is far in the past, it may refer to next year.
            if (today.date() - d.date()).days > 180:
                d = d.replace(year=today.year + 1)
            return d.date().isoformat()
        except Exception:
            pass
    return ""

def extract_event(text, title, url, source_name):
    combined = f"{title} {text}"
    if not any(term in combined for term in CITY_TERMS):
        return None
    # Exclude generic navigation or unrelated content.
    if len(title.strip()) < 5 or any(x in title for x in ("登录", "注册", "首页", "排行榜")):
        return None
    dates = [normalize_date(m.group(0)) for m in RANGE_RE.finditer(combined)]
    start_date = dates[0] if dates else normalize_date(combined)
    end_date = ""
    rm = RANGE_RE.search(combined)
    if rm:
        try:
            year = datetime.now().year
            end_month = int(rm.group(3) or rm.group(1))
            end_day = int(rm.group(4))
            end_date = date_parser.parse(f"{year}-{end_month}-{end_day}").date().isoformat()
        except Exception:
            pass
    pm = PRICE_RE.search(combined)
    price = pm.group(0) if pm else "待确认"
    venue = ""
    for line in [x.strip() for x in re.split(r"[。；\n]", text) if x.strip()]:
        if any(k in line for k in ("地址", "地点", "在长沙", "举办", "举行")) and len(line) < 100:
            venue = line[:100]
            break
    description = re.sub(r"\s+", " ", text).strip()[:500]
    return {
        "title": title.strip()[:160],
        "category": category_for(combined),
        "description": description,
        "start_date": start_date,
        "end_date": end_date,
        "venue": venue,
        "price": price,
        "signup_url": url,
        "source_name": source_name,
        "source_url": url,
        "verification": "待核实",
    }

def collect_source(source):
    name, index_url = source["name"], source["url"]
    try:
        response = requests.get(index_url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
        candidates = []
        seen = set()
        for a in soup.select("a[href]"):
            href = urljoin(index_url, a.get("href", "").strip())
            parsed = urlparse(href)
            title = " ".join(a.get_text(" ", strip=True).split())
            if parsed.netloc not in source["allowed_domains"] or not title or href in seen:
                continue
            if not any(k in href for k in ("/xiuxian/", "/tour/", "huodong", "activity")):
                continue
            if len(title) < 6:
                continue
            seen.add(href)
            candidates.append((title, href))
        inserted = 0
        # Visit a limited number of likely article/detail pages to keep requests polite.
        for title, href in candidates[:35]:
            try:
                page = requests.get(href, headers=HEADERS, timeout=TIMEOUT)
                page.raise_for_status()
                page.encoding = page.apparent_encoding or "utf-8"
                detail = BeautifulSoup(page.text, "html.parser")
                for node in detail(["script", "style", "nav", "footer", "header"]):
                    node.decompose()
                text = " ".join(detail.get_text(" ", strip=True).split())[:12000]
                h1 = detail.find("h1")
                actual_title = h1.get_text(" ", strip=True) if h1 else title
                event = extract_event(text, actual_title, href, name)
                if not event:
                    continue
                with connect() as db:
                    cur = db.execute("""
                    INSERT INTO events
                    (title,category,description,start_date,end_date,venue,price,signup_url,
                     source_name,source_url,verification,updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP) ON CONFLICT (source_url) DO NOTHING
                    """, tuple(event[k] for k in (
                        "title","category","description","start_date","end_date","venue",
                        "price","signup_url","source_name","source_url","verification")))
                    inserted += cur.rowcount
                    db.commit()
            except Exception:
                continue
        msg = f"扫描链接 {len(candidates)} 个，新增活动 {inserted} 个"
        log_collection(name, index_url, "success", msg)
        return {"source": name, "status": "success", "message": msg}
    except Exception as exc:
        msg = f"{type(exc).__name__}: {str(exc)[:250]}"
        log_collection(name, index_url, "error", msg)
        return {"source": name, "status": "error", "message": msg}

def collect_all():
    return [collect_source(source) for source in SOURCES]
