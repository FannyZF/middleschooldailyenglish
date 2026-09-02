import json
import logging
import re
from datetime import date, datetime

from ..config import settings
from ..db import SessionLocal
from ..models import DailyContent, SlangContent
from ..schemas import Content, SlangContent as SlangContentData
from . import imagegen, lemmy, llm, news, reddit, urban

logger = logging.getLogger("pipeline")

# 候选脏话过滤（子串级，能命中 shitpost/bullshit 等复合词；ass/cock/dick 等用整词避免误伤 class/cocktail）
_VULGAR = re.compile(
    r"(?:shit|fuck|bitch|pussy|cunt|whore|slut|nigg|porn|wtf|omfg)"
    r"|\b(?:ass|arse|dick|cock|rape|fag(?:got)?)\b"
    r"|(?:asshole|kiss\s+ass|kiss\s*my\s*ass|blow\s+jobs?|handjob)",
    re.IGNORECASE,
)


def _clean_candidates(items: list[dict]) -> list[dict]:
    def _text(p: dict) -> str:
        return " ".join(
            str(p.get(k, "")) for k in ("title", "selftext", "description")
        )

    return [p for p in items if not _VULGAR.search(_text(p))]


def _norm_url(u: str) -> str:
    return (u or "").strip().rstrip("/").lower()


def _match_article(articles: list[dict], source_url: str, title: str) -> dict | None:
    target = _norm_url(source_url)
    if target:
        for a in articles:
            if _norm_url(a.get("url", "")) == target:
                return a
    t = (title or "").strip().lower()
    if t:
        for a in articles:
            if (a.get("title") or "").strip().lower() == t:
                return a
    return None


def _filter_used_articles(articles: list[dict], db, exclude_day: str | None = None) -> list[dict]:
    """排除历史已用过的新闻（按链接/标题），避免每天重复。若全用尽则回退全部。"""
    used_urls: set[str] = set()
    used_titles: set[str] = set()
    rows = (
        db.query(DailyContent)
        .filter(DailyContent.status == "generated")
        .filter(DailyContent.source_url != "")
    )
    for r in rows:
        if exclude_day and r.date == exclude_day:
            continue
        if r.source_url:
            used_urls.add(_norm_url(r.source_url))
        if r.original_title:
            used_titles.add(r.original_title.strip().lower())

    fresh = [
        a
        for a in articles
        if _norm_url(a.get("url", "")) not in used_urls
        and (a.get("title") or "").strip().lower() not in used_titles
    ]
    return fresh if fresh else articles


def generate_for_date(day: str) -> DailyContent:
    db = SessionLocal()
    try:
        row = db.query(DailyContent).filter(DailyContent.date == day).first()
        if row is None:
            row = DailyContent(date=day, status="pending")
            db.add(row)
            db.commit()

        row.status = "pending"
        row.error = ""
        db.commit()

        try:
            articles = news.fetch_articles()
            articles = _filter_used_articles(articles, db, exclude_day=day)
            data = llm.generate_content(articles)
            content = Content.model_validate(data)

            matched = _match_article(articles, content.source_url, content.title)
            content.original_title = (matched or {}).get("title", "") or content.title
            content.pub_date = (matched or {}).get("published", "") or ""

            row.status = "generated"
            row.title = content.title
            row.original_title = content.original_title
            row.pub_date = content.pub_date
            row.source_url = content.source_url
            row.source_name = content.source_name
            row.category = content.category
            row.summary_en = content.summary_en
            row.summary_zh = content.summary_zh
            row.word = content.word
            row.word_pos = content.word_pos
            row.word_phonetic = content.word_phonetic
            row.word_grade = content.word_grade
            row.definitions = json.dumps(
                [d.model_dump() for d in content.definitions], ensure_ascii=False
            )
            row.choices = json.dumps(
                [c.model_dump() for c in content.choices], ensure_ascii=False
            )
            row.translation = content.translation.model_dump_json()

            out_dir = settings.images_dir / day
            imagegen.render_all(content, out_dir)
            row.image_dir = str(out_dir)
            row.error = ""
        except Exception as e:
            row.status = "failed"
            row.error = str(e)

        db.commit()
        return row
    finally:
        db.close()


def generate_today() -> DailyContent:
    return generate_for_date(date.today().isoformat())


def list_contents():
    db = SessionLocal()
    try:
        return db.query(DailyContent).order_by(DailyContent.date.desc()).all()
    finally:
        db.close()


def _tag_origin(items: list[dict], origin: str) -> list[dict]:
    for p in items:
        p["_origin"] = origin
    return items


def _fetch_slang_candidates() -> list[dict]:
    """Lemmy → Urban Dictionary → Reddit 依次尝试，候选统一过滤脏话并标记来源。"""
    errors: list[str] = []
    for name, fn in (("Lemmy", lemmy.fetch_posts),):
        try:
            result = _tag_origin(_clean_candidates(fn()), name)
            logger.info("俚语数据源: %s 成功（%d 条候选）", name, len(result))
            if result:
                return result
        except Exception as e:
            errors.append(f"{name}: {e}")
    try:
        result = _tag_origin(_clean_candidates(urban.fetch_entries()), "Urban Dictionary")
        logger.info("俚语数据源: Urban Dictionary 成功（%d 条候选）", len(result))
        if result:
            return result
    except Exception as ue:
        errors.append(f"Urban Dictionary: {ue}")
    try:
        result = _tag_origin(_clean_candidates(reddit.fetch_posts()), "Reddit")
        logger.info("俚语数据源: Reddit 成功（%d 条候选）", len(result))
        if result:
            return result
    except Exception as re:
        errors.append(f"Reddit: {re}")
    raise RuntimeError("俚语数据源获取失败：" + "；".join(errors))


def _find_slang_candidate(slang: str, posts: list[dict]) -> dict | None:
    s = (slang or "").strip().lower()
    if not s:
        return None
    for p in posts:
        text = " ".join(
            str(p.get(k, "")) for k in ("title", "selftext", "description")
        ).lower()
        if s in text:
            return p
    return None


def _source_label(p: dict) -> str:
    """由候选的真实来源生成标签，避免模型编造来源（如 Lemmy 被写成 reddit）。"""
    origin = p.get("_origin", "")
    if origin == "Urban Dictionary":
        return "Urban Dictionary"
    sub = (p.get("subreddit") or "").strip()
    if origin and sub:
        return f"{origin} r/{sub}"
    if origin:
        return origin
    return ""


def generate_slang_for_date(day: str) -> SlangContent:
    db = SessionLocal()
    try:
        row = db.query(SlangContent).filter(SlangContent.date == day).first()
        if row is None:
            row = SlangContent(date=day, status="pending")
            db.add(row)
            db.commit()

        row.status = "pending"
        row.error = ""
        db.commit()

        try:
            posts = _fetch_slang_candidates()
            data = llm.generate_slang(posts)
            content = SlangContentData.model_validate(data)

            # 校验：俚语必须来自候选内容，否则重试一次（防止模型背默认词如 kiss ass）
            if _find_slang_candidate(content.slang, posts) is None:
                logger.warning("俚语 %r 不在候选中，重试一次", content.slang)
                data = llm.generate_slang(posts, strict=True)
                content = SlangContentData.model_validate(data)

            # 来源/链接由真实候选回填，避免模型编造（如 Lemmy 被写成 reddit）
            match = _find_slang_candidate(content.slang, posts)
            if match:
                label = _source_label(match)
                if label:
                    content.source = label
                if match.get("url"):
                    content.source_url = match["url"]

            row.status = "generated"
            row.slang = content.slang
            row.phonetic = content.phonetic
            row.meaning_en = content.meaning_en
            row.meaning_zh = content.meaning_zh
            row.usage = content.usage
            row.examples = json.dumps(
                [e.model_dump() for e in content.examples], ensure_ascii=False
            )
            row.scenarios = json.dumps(
                [s.model_dump() for s in content.scenarios], ensure_ascii=False
            )
            row.source = content.source
            row.source_url = content.source_url
            row.caption = content.caption

            out_dir = settings.images_dir / "slang" / day
            imagegen.render_slang_all(content, out_dir)
            row.image_dir = str(out_dir)
            row.error = ""
        except Exception as e:
            row.status = "failed"
            row.error = str(e)

        db.commit()
        return row
    finally:
        db.close()


def generate_slang_today() -> SlangContent:
    return generate_slang_for_date(date.today().isoformat())


def list_slang_contents():
    db = SessionLocal()
    try:
        return db.query(SlangContent).order_by(SlangContent.date.desc()).all()
    finally:
        db.close()
