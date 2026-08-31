from .http import fetch

INSTANCES = ["lemmy.world", "sh.itjust.works", "lemmy.ml"]
LEMMY_UA = "dailyenglish-bot/1.0 (english learning tool)"


def _fetch_instance(instance: str, limit: int = 10) -> tuple[list[dict], str | None]:
    url = f"https://{instance}/api/v3/post/list?sort=Hot&limit={limit}"
    try:
        resp = fetch(url, timeout=25, user_agent=LEMMY_UA)
    except Exception as e:
        return [], f"{instance}: {type(e).__name__} {str(e)[:120]}"

    try:
        data = resp.json()
    except ValueError:
        return [], f"{instance}: 返回内容不是 JSON"

    out: list[dict] = []
    for item in data.get("posts", []):
        post = item.get("post", {})
        title = (post.get("name") or "").strip()
        if not title:
            continue
        body = (post.get("body") or "").strip()[:600]
        community = item.get("community", {}).get("name", "") or instance
        score = item.get("counts", {}).get("score") or 0
        out.append(
            {
                "title": title,
                "selftext": body,
                "subreddit": community,
                "url": f"https://{instance}/post/{post.get('id')}",
                "score": score,
            }
        )
    return out, None


def fetch_posts(limit: int = 30) -> list[dict]:
    posts: list[dict] = []
    seen: set[str] = set()
    errors: list[str] = []

    for inst in INSTANCES:
        items, err = _fetch_instance(inst)
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
            raise RuntimeError("Lemmy 获取失败：" + "；".join(errors[:3]))
        raise RuntimeError("Lemmy 无可用帖子")

    posts.sort(key=lambda p: p["score"], reverse=True)
    return posts[:limit]
