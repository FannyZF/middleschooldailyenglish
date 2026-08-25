from .http import fetch

SUBREDDITS = ["EnglishLearning", "AskReddit", "AskAnAmerican", "AskUK"]
REDDIT_UA = "dailyenglish-bot/1.0 (english learning tool)"


def _fetch_subreddit(sub: str, limit: int = 10) -> tuple[list[dict], str | None]:
    url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}"
    try:
        resp = fetch(url, timeout=25, user_agent=REDDIT_UA)
    except Exception as e:
        return [], f"{sub}: {type(e).__name__} {str(e)[:120]}"

    if resp.status_code != 200:
        return [], f"{sub}: HTTP {resp.status_code}"

    try:
        data = resp.json()
    except ValueError:
        return [], f"{sub}: 返回内容不是 JSON"

    out: list[dict] = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        title = (d.get("title") or "").strip()
        if not title:
            continue
        selftext = (d.get("selftext") or "").strip()[:600]
        out.append(
            {
                "title": title,
                "selftext": selftext,
                "subreddit": d.get("subreddit") or sub,
                "url": "https://www.reddit.com" + (d.get("permalink") or ""),
                "score": d.get("score") or 0,
            }
        )
    return out, None


def fetch_posts(limit: int = 30) -> list[dict]:
    posts: list[dict] = []
    seen: set[str] = set()
    errors: list[str] = []

    for sub in SUBREDDITS:
        items, err = _fetch_subreddit(sub)
        if err:
            errors.append(err)
            continue
        for p in items:
            key = p["title"][:60]
            if key in seen:
                continue
            seen.add(key)
            posts.append(p)

    if not posts:
        if errors:
            raise RuntimeError("Reddit 获取失败：" + "；".join(errors[:3]))
        raise RuntimeError("Reddit 无可用帖子")

    posts.sort(key=lambda p: p["score"], reverse=True)
    return posts[:limit]
