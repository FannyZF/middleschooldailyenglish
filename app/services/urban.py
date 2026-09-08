import random
import re
import string
import urllib.parse

from .http import fetch

UD_UA = "dailyenglish-bot/1.0 (english learning tool)"

_DEFINE_URL = "https://api.urbandictionary.com/v0/define?term="
_AUTO_URL = "https://api.urbandictionary.com/v0/autocomplete?term="
_RANDOM_URL = "https://api.urbandictionary.com/v0/random"

# 精选常用俚语/惯用语词库（约 500 条）：作为稳定、干净的基础候选
COMMON_SLANG = [
    # —— 身体/精力/作息 ——
    "hit the hay", "hit the sack", "burn the midnight oil", "pull an all-nighter",
    "catch some z's", "sleep in", "early bird", "night owl", "take a breather",
    "recharge my batteries", "crash out", "sleep on it", "doze off", "catch forty winks",
    "second wind", "get some shut-eye", "snooze", "sleep like a log",
    # —— 吃喝/日常 ——
    "grab a bite", "grab a coffee", "pig out", "hit the spot", "hangry",
    "food coma", "comfort food", "chew the fat", "bite off more than you can chew",
    "piece of cake", "cut the cheese", "spill the beans", "the icing on the cake",
    "a cup of joe", "chow down", "eat like a horse", "have a sweet tooth",
    "break bread", "in hot water", "bring home the bacon",
    # —— 情绪/心情 ——
    "in a good mood", "in a bad mood", "down in the dumps", "on cloud nine",
    "over the moon", "feel blue", "butterflies in my stomach", "walking on air",
    "in seventh heaven", "sour grapes", "green with envy", "tickled pink",
    "sick and tired", "fed up", "worn out", "on edge", "at the end of my rope",
    "in high spirits", "down to earth", "mood swings", "keep a stiff upper lip",
    "lose your cool", "cool as a cucumber", "hot under the collar", "pumped up",
    "antsy", "chipper", "gloomy", "grumpy", "mellow", "hyped",
    # —— 钱/消费 ——
    "cost an arm and a leg", "break the bank", "tight with money", "foot the bill",
    "shell out", "dip into savings", "make ends meet", "live paycheck to paycheck",
    "money talks", "pinch pennies", "rake it in", "tighten the belt",
    "born with a silver spoon", "cash cow", "deep pockets", "go dutch",
    "on a shoestring", "pay through the nose", "a pretty penny", "ballpark figure",
    "shell out big bucks", "hit the jackpot", "get your money's worth",
    # —— 时间/进度 ——
    "once in a blue moon", "in the nick of time", "beat the clock", "time flies",
    "kill time", "race against time", "high time", "about time", "in the long run",
    "down the road", "ahead of the curve", "behind the times", "around the clock",
    "on the dot", "at the eleventh hour", "a matter of time", "take your time",
    "get a move on", "crack of dawn", "long shot", "short notice", "stall for time",
    "in due course", "now or never", "overtime", "sooner or later",
    # —— 沟通/聊天 ——
    "touch base", "circle back", "loop someone in", "talk shop", "small talk",
    "cut to the chase", "beat around the bush", "get to the point", "in other words",
    "long story short", "the bottom line", "speak of the devil", "word of mouth",
    "off the record", "on the same page", "talk it out", "give a heads-up",
    "shoot the breeze", "chew the fat", "huddle up", "fill me in", "catch up on",
    "keep in the loop", "hear it from the grapevine", "straight from the horse's mouth",
    "mince words", "put in a good word", "ring a bell", "on the tip of my tongue",
    "get my point across", "read between the lines", "talking out of turn",
    # —— 工作/职场 ——
    "pull your weight", "climb the corporate ladder", "move up the ranks",
    "wear many hats", "delegate", "micromanage", "under the gun", "on the clock",
    "clock in", "clock out", "call it a day", "call it a night", "burnout",
    "grind", "hustle", "9 to 5", "the daily grind", "out of office", "deadline",
    "put out fires", "get the ball rolling", "open a can of worms", "think outside the box",
    "low-hanging fruit", "quick win", "game plan", "onboarding", "scope creep",
    "office politics", "pay your dues", "pick someone's brain", "run it up the flagpole",
    "sink or swim", "team player", "the whole nine yards", "learn the ropes",
    "get up to speed", "knock it out of the park", "raise the bar", "set the bar high",
    "go the extra mile", "buck stops here", "in the driver's seat", "move the goalposts",
    "peel the onion", "boil the ocean", "herding cats", "ducks in a row",
    "loose ends", "the elephant in the room", "win-win", "winning streak",
    # —— 人际/关系 ——
    "hit it off", "click with someone", "on the same wavelength", "two peas in a pod",
    "through thick and thin", "stand by someone", "have someone's back", "bury the hatchet",
    "make up", "patch things up", "give someone the cold shoulder", "play devil's advocate",
    "rock the boat", "stir the pot", "get along", "see eye to eye", "drift apart",
    "reconnect", "catch up with an old friend", "ghost someone", "keep in touch",
    "lose touch", "trust your gut", "blood is thicker than water",
    # —— 决定/态度 ——
    "bite the bullet", "take the plunge", "cross that bridge when you come to it",
    "weigh the pros and cons", "play it by ear", "wing it", "go with the flow",
    "take a rain check", "back to square one", "start from scratch", "turn over a new leaf",
    "give it a shot", "keep an open mind", "on the fence", "sit on the fence",
    "hedge your bets", "all in", "go for broke", "change your tune", "hold your horses",
    "jump the gun", "put the cart before the horse", "the ball is in your court",
    "take it with a grain of salt", "easier said than done", "crystal clear",
    # —— 冒险/风险 ——
    "take a risk", "live dangerously", "on thin ice", "walk a tightrope",
    "playing with fire", "dicey", "roll the dice", "all or nothing", "high stakes",
    "a leap of faith", "take a chance", "push your luck", "walk on eggshells",
    # —— 成功/失败/努力 ——
    "hit the nail on the head", "knock it out of the park", "ace it", "crush it",
    "kill it", "nail it", "on the right track", "ahead of the game", "level up",
    "fall flat", "miss the mark", "back to the drawing board", "trial and error",
    "get there", "pay off", "reap the rewards", "fingers crossed", "keep your chin up",
    "never give up", "hang in there", "keep plugging away", "keep pushing",
    # —— 表达真实/认真 ——
    "for real", "no joke", "in all seriousness", "let's be honest", "straight up",
    "lowkey", "highkey", "no cap", "deadass", "on god", "hand on heart",
    "between you and me", "the truth hurts", "let the cat out of the bag",
    # —— 常见感叹/评价 ——
    "that's fire", "that's lit", "it slaps", "dope", "sick", "awesome sauce",
    "cool beans", "no way", "you bet", "you're telling me", "tell me about it",
    "same here", "it is what it is", "so be it", "fair enough", "word",
    "bet", "facts", "period", "big deal", "no biggie", "my bad", "no sweat",
    "easy peasy", "go figure", "you name it", "hands down", "by far",
    "not my cup of tea", "up my alley", "right up my alley",
    # —— 数量/程度 ——
    "a ton of", "a bunch of", "loads of", "plenty of", "a handful of",
    "a boatload of", "tons", "heaps", "miles away", "miles better",
    "light years ahead", "worlds apart", "night and day",
    # —— 表达方向/位置 ——
    "in the middle of nowhere", "around the corner", "off the beaten path",
    "down the street", "next door", "from scratch", "from the ground up",
    # —— 天气/环境 ——
    "under the weather", "fair-weather friend", "the calm before the storm",
    "every cloud has a silver lining", "when it rains it pours", "save for a rainy day",
    "take it one day at a time", "bright and early",
    # —— 想法/理解 ——
    "lightbulb moment", "on the same page", "get the picture", "catch my drift",
    "you lost me", "follow me?", "make sense of it", "wrap my head around",
    "piece it together", "figure it out", "work it out", "sleep on it",
    # —— 常见动词短语/口语 ——
    "chill out", "hang out", "kick back", "veg out", "zone out", "spaced out",
    "show up", "flake out", "bail on", "bounce", "dip out", "scoot over",
    "cram for", "skim through", "look up to", "look down on", "come around",
    "grow on me", "warm up to", "open up", "loosen up", "perk up", "lighten up",
    "cheer up", "brush up on", "catch on", "get on board", "fall through",
    "go through with", "put up with", "make up for", "end up", "turn out",
    "pop up", "crop up", "come up with", "chime in", "pipe up", "back off",
    "back down", "hand it over", "fork over", "shell out", "toss up",
    # —— 人际形容 ——
    "green-eyed monster", "glass ceiling", "black sheep", "odd one out",
    "whipping boy", "go-to person", "jack of all trades", "people person",
    "homebody", "party animal", "morning person", "control freak", "neat freak",
    "pack rat", "night person", "worst-case scenario", "best-case scenario",
    "silver lining", "saving grace", "mixed blessing", "blessing in disguise",
    # —— 行动/状态 ——
    "on the fence about it", "in a pickle", "in a bind", "up a creek",
    "between a rock and a hard place", "stuck between a rock and a hard place",
    "caught red-handed", "in the clear", "off the hook", "get off scot-free",
    "let it slide", "turn a blind eye", "turn a deaf ear", "bury your head in the sand",
    "sweep it under the rug", "call it quits", "throw in the towel", "give up the ghost",
    "hang up your boots", "call time on", "cut your losses", "count your blessings",
    "make the most of it", "make a mountain out of a molehill", "cry over spilled milk",
    # —— 表达惊讶/提醒 ——
    "you won't believe it", "guess what", "hold your horses", "easy does it",
    "watch your step", "mind your own business", "none of your business",
    "get off my back", "give me a break", "cut me some slack", "back off",
    # —— 更多常见 ——
    "all ears", "all thumbs", "butter fingers", "fingers crossed",
    "under the thumb", "wrap someone around your finger", "play second fiddle",
    "call the shots", "calls the tune", "shot in the dark", "stab in the dark",
    "needle in a haystack", "drop in the bucket", "tip of the iceberg",
    "the whole shebang", "the full monty", "the cherry on top",
    "apple of my eye", "the bee's knees", "the cat's pajamas", "top dog",
    "underdog", "front runner", "dark horse", "fair game", "easy game",
    # —— 生活方式/习惯 ——
    "kick the habit", "quit cold turkey", "sober up", "hit rock bottom",
    "turn your life around", "get your act together", "get your ducks in a row",
    "clean slate", "fresh start", "second chance", "leap of faith",
    # —— 社交网络/年轻人 ——
    "go viral", "trending", "tag along", "dm me", "slide into the dms",
    "follow back", "like and subscribe", "hashtag", "meme", "influencer",
    "story time", "tea", "spill the tea", "clout", "ratio", "vibe check",
    "sus", "rent free in my head", "living rent free", "main character energy",
    "it's giving", "iykyk", "no pressure", "down to hang", "down to earth",
    # —— 常见 OK/确认 ——
    "sounds good", "works for me", "deal", "done deal", "say less", "copy that",
    "roger that", "got it", "understood", "all good", "no worries", "no problem",
    "happy to help", "sure thing", "you got it",
    # —— 表达辛苦/累 ——
    "dog tired", "dead tired", "beat", "wiped out", "running on empty",
    "running on fumes", "burning the candle at both ends", "in over my head",
    "up to my ears", "swamped", "slammed", "snowed under", "juggling too many things",
    # —— 常见建议/安慰 ——
    "take it easy", "hang in there", "keep your head up", "stay positive",
    "don't sweat it", "no biggie", "it happens", "tomorrow is another day",
    "chin up", "buck up", "snap out of it", "get over it", "move on",
    # —— 各类名词短语 ——
    "a quick fix", "a shortcut", "the easy way out", "the long haul",
    "a rough patch", "a hard time", "a walk in the park", "a no-brainer",
    "a game changer", "a wake-up call", "a reality check", "a rude awakening",
    "a pipe dream", "a wet blanket", "a party pooper", "a downer",
    "a people pleaser", "a pushover", "a softie", "a tough cookie",
    # —— 补充常见 ——
    "cheap and cheerful", "hit or miss", "make or break", "now or never",
    "so far so good", "better late than never", "practice makes perfect",
    "actions speak louder than words", "the sky's the limit", "don't judge a book by its cover",
]


_WORDY = re.compile(r"^[A-Za-z][A-Za-z' &.-]{1,39}$")


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


def _autocomplete_terms(prefix: str, max_out: int = 30) -> list[str]:
    """从 UD autocomplete 拉一批以 prefix 开头的真实词。"""
    try:
        resp = fetch(_AUTO_URL + urllib.parse.quote(prefix), timeout=12, user_agent=UD_UA)
        data = resp.json()
    except Exception:
        return []

    raw: list[str] = []
    if isinstance(data, list):
        raw = [x if isinstance(x, str) else "" for x in data]
    elif isinstance(data, dict):
        for key in ("result", "tags", "data", "terms", "matches", "items"):
            v = data.get(key)
            if isinstance(v, list):
                for it in v:
                    if isinstance(it, str):
                        raw.append(it)
                    elif isinstance(it, dict):
                        w = it.get("term") or it.get("word") or it.get("title")
                        if isinstance(w, str):
                            raw.append(w)

    seen: set[str] = set()
    out: list[str] = []
    for t in raw:
        s = (t or "").strip()
        if not s or not _WORDY.match(s) or s.lower() in seen:
            continue
        seen.add(s.lower())
        out.append(s)
        if len(out) >= max_out:
            break
    return out


def _define_best(term: str) -> dict | None:
    try:
        resp = fetch(
            _DEFINE_URL + urllib.parse.quote(term), timeout=12, user_agent=UD_UA
        )
        items = resp.json().get("list", [])
    except Exception:
        return None
    if not items:
        return None
    best = max(items, key=lambda it: it.get("thumbs_up") or 0)
    return _best_def(best)


def fetch_entries(limit: int = 12) -> list[dict]:
    """候选 = 精选词库 + UD 前缀枚举补充的新鲜词，保证多样且可持续。"""
    result: list[dict] = []
    seen: set[str] = set()

    def _add(cand: dict | None) -> None:
        if not cand:
            return
        key = cand["title"].lower()
        if key in seen:
            return
        seen.add(key)
        result.append(cand)

    # 1) 精选词库（基础，干净可控）
    cur_n = min(max(limit // 2, 5), len(COMMON_SLANG))
    for w in random.sample(COMMON_SLANG, cur_n):
        _add(_define_best(w))

    # 2) UD 前缀枚举补充新鲜词
    extra = limit - len(result)
    if extra > 0:
        prefixes = random.sample(string.ascii_lowercase, min(4, 26))
        random.shuffle(prefixes)
        for p in prefixes:
            if len(result) >= limit:
                break
            terms = _autocomplete_terms(p)
            random.shuffle(terms)
            for t in terms:
                if len(result) >= limit:
                    break
                _add(_define_best(t))

    # 3) 仍不足则从精选库里补（已随机样本外）
    if len(result) < limit:
        pool = list(COMMON_SLANG)
        random.shuffle(pool)
        for w in pool:
            if len(result) >= limit:
                break
            _add(_define_best(w))

    if not result:
        raise RuntimeError("Urban Dictionary 无可用词条")
    return result[:limit]
