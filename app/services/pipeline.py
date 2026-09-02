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

# 候选脏话过滤（防止把粗俗词喂给模型，也避免模型总是选脏词）
_VULGAR = re.compile(
    r"\b(?:ass|arse|asshole|bitch|shit|fuck|fucking|dick|cock|pussy|cunt|whore|"
    r"slut|nigga|nigger|fag(?:got)?|rape|porn|blowjob|boner|milf|hentai|wtf|omfg)\b"
    r"|kiss\s+ass|suck\s+(?:my|your|his|her|it)",
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


def _fetch_slang_candidates() -> list[dict]:
    """Lemmy → Urban Dictionary → Reddit 依次尝试，候选统一过滤脏话。"""
    errors: list[str] = []
    for name, fn in (("Lemmy", lemmy.fetch_posts),):
        try:
            result = _clean_candidates(fn())
            logger.info("俚语数据源: %s 成功（%d 条候选）", name, len(result))
            if result:
                return result
        except Exception as e:
            errors.append(f"{name}: {e}")
    try:
        result = _clean_candidates(urban.fetch_entries())
        logger.info("俚语数据源: Urban Dictionary 成功（%d 条候选）", len(result))
        if result:
            return result
    except Exception as ue:
        errors.append(f"Urban Dictionary: {ue}")
    try:
        result = _clean_candidates(reddit.fetch_posts())
        logger.info("俚语数据源: Reddit 成功（%d 条候选）", len(result))
        if result:
            return result
    except Exception as re:
        errors.append(f"Reddit: {re}")
    raise RuntimeError("俚语数据源获取失败：" + "；".join(errors))


def _slang_in_candidates(slang: str, posts: list[dict]) -> bool:
    s = (slang or "").strip().lower()
    if not s:
        return True
    for p in posts:
        text = " ".join(
            str(p.get(k, "")) for k in ("title", "selftext", "description")
        ).lower()
        if s in text:
            return True
    return False


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
            if not _slang_in_candidates(content.slang, posts):
                logger.warning("俚语 %r 不在候选中，重试一次", content.slang)
                data = llm.generate_slang(posts, strict=True)
                content = SlangContentData.model_validate(data)

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
