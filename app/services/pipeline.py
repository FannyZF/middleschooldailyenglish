import json
from datetime import date, datetime

from ..config import settings
from ..db import SessionLocal
from ..models import DailyContent
from ..schemas import Content
from . import imagegen, llm, news


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
