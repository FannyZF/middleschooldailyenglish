import requests
from requests.auth import HTTPBasicAuth

from ..config import settings
from .http import fetch, get_proxies
from .settings import get_setting

SUBREDDITS = ["EnglishLearning", "AskReddit", "AskAnAmerican", "AskUK"]
REDDIT_UA = "dailyenglish-bot/1.0 (english learning tool)"


def _creds() -> tuple[str, str, str, str] | None:
    def g(key: str, cfg: str) -> str:
        return (get_setting(key) or cfg or "").strip()

    cid = g("reddit_client_id", settings.reddit_client_id)
    secret = g("reddit_client_secret", settings.reddit_client_secret)
    username = g("reddit_username", settings.reddit_username)
    password = g("reddit_password", settings.reddit_password)
    if cid and secret and username and password:
        return cid, secret, username, password
    return None


def _get_token(creds: tuple[str, str, str, str]) -> str | None:
    cid, secret, username, password = creds
    try:
        resp = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=HTTPBasicAuth(cid, secret),
            data={"grant_type": "password", "username": username, "password": password},
            headers={"User-Agent": REDDIT_UA},
            timeout=20,
            proxies=get_proxies(),
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except Exception:
        return None


def _parse_listing(data: dict, sub: str) -> list[dict]:
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
    return out


def _fetch_subreddit(sub: str, limit: int = 10) -> tuple[list[dict], str | None]:
    creds = _creds()
    if creds:
        token = _get_token(creds)
        if not token:
            return [], f"{sub}: OAuth token 获取失败"
        try:
            resp = requests.get(
                f"https://oauth.reddit.com/r/{sub}/hot",
                params={"limit": limit},
                headers={"Authorization": f"Bearer {token}", "User-Agent": REDDIT_UA},
                timeout=20,
                proxies=get_proxies(),
            )
            resp.raise_for_status()
            return _parse_listing(resp.json(), sub), None
        except Exception as e:
            return [], f"{sub}(oauth): {type(e).__name__} {str(e)[:100]}"

    # 未配置凭证时用公开接口兜底
    try:
        resp = fetch(
            f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}",
            timeout=25,
            user_agent=REDDIT_UA,
        )
    except Exception as e:
        return [], f"{sub}: {type(e).__name__} {str(e)[:120]}"
    try:
        return _parse_listing(resp.json(), sub), None
    except ValueError:
        return [], f"{sub}: 返回内容不是 JSON"


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
