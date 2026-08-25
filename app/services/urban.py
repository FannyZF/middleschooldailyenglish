from .http import fetch

UD_UA = "dailyenglish-bot/1.0 (english learning tool)"


def fetch_entries(limit: int = 8) -> list[dict]:
    entries: list[dict] = []
    seen: set[str] = set()
    errors: list[str] = []

    attempts = 0
    while len(entries) < limit and attempts < limit * 3:
        attempts += 1
        try:
            resp = fetch(
                "https://api.urbandictionary.com/v0/random",
                timeout=20,
                user_agent=UD_UA,
            )
            data = resp.json()
        except Exception as e:
            errors.append(str(e)[:100])
            continue

        for w in data.get("list", []):
            word = (w.get("word") or "").strip()
            if not word or word in seen:
                continue
            seen.add(word)

            definition = (w.get("definition") or "").strip()[:500]
            example = (w.get("example") or "").strip()[:250]
            selftext = definition
            if example:
                selftext += "\n例：" + example

            entries.append(
                {
                    "title": word,
                    "selftext": selftext[:600],
                    "subreddit": "Urban Dictionary",
                    "url": w.get("permalink") or "",
                    "score": w.get("thumbs_up") or 0,
                }
            )

    if not entries:
        if errors:
            raise RuntimeError("Urban Dictionary 获取失败：" + "；".join(errors[:3]))
        raise RuntimeError("Urban Dictionary 无可用词条")

    entries.sort(key=lambda e: e["score"], reverse=True)
    return entries
