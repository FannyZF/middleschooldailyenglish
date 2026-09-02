import random
import urllib.parse

from .http import fetch

UD_UA = "dailyenglish-bot/1.0 (english learning tool)"

_RANDOM_URL = "https://api.urbandictionary.com/v0/random"
_DEFINE_URL = "https://api.urbandictionary.com/v0/define?term="

# 常用地道俚语种子词表：每天随机抽若干，保证候选既有质量又多样
COMMON_SLANG = [
    "hit the sack", "hit the hay", "piece of cake", "break a leg",
    "spill the beans", "under the weather", "once in a blue moon",
    "bite the bullet", "let the cat out of the bag", "burn the midnight oil",
    "call it a day", "get the ball rolling", "miss the boat",
    "beat around the bush", "speak of the devil", "when pigs fly",
    "on the same page", "hang in there", "shoot the breeze", "cut corners",
    "back to square one", "hit the nail on the head", "cost an arm and a leg",
    "a blessing in disguise", "cry over spilled milk", "no cap", "lowkey",
    "highkey", "spill the tea", "vibe check", "flex", "sus", "bet", "fire",
    "lit", "chill out", "hangry", "salty", "savage", "shook", "GOAT",
    "hang out", "catch up", "hit the books", "twist someone's arm",
    "take it easy", "pull an all-nighter", "spill the beans",
]


def _best_def(item: dict) -> dict | None:
    word = (item.get("word") or "").strip()
    if not word:
        return None
    definition = (item.get("definition") or "").strip()[:500]
    example = (item.get("example") or "").strip()[:250]
    selftext = definition
    if example:
        selftext += "\n例：" + example
    return {
        "title": word,
        "selftext": selftext[:600],
        "subreddit": "Urban Dictionary",
        "url": item.get("permalink") or "",
        "score": item.get("thumbs_up") or 0,
    }


def fetch_entries(limit: int = 8) -> list[dict]:
    """以常用俚语种子为主，random 补充，保证返回的候选多样且适合学习。"""
    result: list[dict] = []
    seen: set[str] = set()

    def _add(item: dict) -> None:
        cand = _best_def(item)
        if not cand or cand["title"].lower() in seen:
            return
        seen.add(cand["title"].lower())
        result.append(cand)

    # 1) 常用俚语种子：每天随机抽 limit 个，取该词最热门释义
    seeds = random.sample(COMMON_SLANG, min(limit, len(COMMON_SLANG)))
    for w in seeds:
        try:
            resp = fetch(
                _DEFINE_URL + urllib.parse.quote(w), timeout=15, user_agent=UD_UA
            )
            items = resp.json().get("list", [])
            if items:
                best = max(items, key=lambda it: it.get("thumbs_up") or 0)
                _add(best)
        except Exception:
            continue

    # 2) random 补充（若种子不足或想加入新词）
    attempts = 0
    while len(result) < limit and attempts < 4:
        attempts += 1
        try:
            resp = fetch(_RANDOM_URL, timeout=15, user_agent=UD_UA)
            for item in resp.json().get("list", []):
                _add(item)
        except Exception:
            continue

    if not result:
        raise RuntimeError("Urban Dictionary 无可用词条")
    return result[:limit]
