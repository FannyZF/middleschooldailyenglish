import html
import re
import time

import feedparser

from .http import fetch

CATEGORY_LABELS = {
    "technology": "科技",
    "sports": "体育",
    "business": "财经",
}

# 科技 / 财经 / 体育 三类，BBC + CNN 各一份，互为备份
FEEDS = [
    ("technology", "https://feeds.bbci.co.uk/news/technology/rss.xml", "BBC"),
    ("business", "https://feeds.bbci.co.uk/news/business/rss.xml", "BBC"),
    ("sports", "https://feeds.bbci.co.uk/sport/rss.xml", "BBC"),
    ("technology", "https://rss.cnn.com/rss/edition_technology.rss", "CNN"),
    ("business", "https://rss.cnn.com/rss/money_news_international.rss", "CNN"),
    ("sports", "https://rss.cnn.com/rss/edition_sport.rss", "CNN"),
]

# 明显不适合初中生/存在争议的新闻关键词（整词匹配，避免误伤 software/studies 等）
BLOCKED_PATTERN = re.compile(
    r"\b(?:war|killed|death|deaths|die|dies|died|shooting|shootings|crime|"
    r"attack|attacks|sex|porn|gambling|rape|murder|massacre|bomb|bombs)\b",
    re.IGNORECASE,
)

_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    text = _TAG_RE.sub(" ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _pub_date(entry) -> str:
    dt = entry.get("published_parsed") or entry.get("updated_parsed")
    if dt:
        try:
            return time.strftime("%Y-%m-%d", dt)
        except (TypeError, ValueError):
            return ""
    return ""


def _fetch_feed(cat: str, url: str, source: str) -> tuple[list[dict], str | None]:
    try:
        resp = fetch(url)
        feed = feedparser.parse(resp.content)
    except Exception as e:
        return [], f"网络请求失败({source} {cat}): {e}"

    if not feed.entries:
        return [], f"RSS 无内容({source} {cat})"

    out: list[dict] = []
    for e in feed.entries:
        title = _clean(e.get("title", ""))
        if not title:
            continue
        desc = _clean(e.get("summary") or e.get("description", ""))
        if not desc:
            desc = title

        out.append(
            {
                "title": title,
                "description": desc,
                "url": e.get("link", ""),
                "source": source,
                "category": cat,
                "category_label": CATEGORY_LABELS.get(cat, cat),
                "published": _pub_date(e),
            }
        )
    return out, None


def fetch_articles(limit: int = 30) -> list[dict]:
    articles: list[dict] = []
    seen: set[str] = set()
    errors: list[str] = []

    for cat, url, source in FEEDS:
        items, err = _fetch_feed(cat, url, source)
        if err:
            errors.append(err)
            continue

        for a in items:
            if BLOCKED_PATTERN.search(a["title"] + " " + a["description"]):
                continue
            if a["title"] in seen:
                continue
            seen.add(a["title"])
            articles.append(a)

    if not articles:
        if errors:
            raise RuntimeError("RSS 获取失败：" + "；".join(errors))
        raise RuntimeError("RSS 返回的新闻都被过滤或内容为空")

    return articles[:limit]
