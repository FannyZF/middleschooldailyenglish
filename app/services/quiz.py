import json
import logging
import random

from ..config import settings
from ..db import SessionLocal
from ..models import SlangContent, WeeklyQuiz
from . import imagegen, llm, urban

logger = logging.getLogger("quiz")

MIN_SELECT = 2
MAX_SELECT = 12
QUESTIONS = 2


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _validate_questions(questions: list[dict], week_words: set[str]) -> bool:
    if not questions or len(questions) > QUESTIONS:
        return False
    used_correct: set[str] = set()
    for q in questions:
        opts = q.get("options") or []
        if len(opts) < 3:
            return False
        if len({_norm(o) for o in opts}) != len(opts):
            return False
        try:
            idx = int(q.get("answer_index"))
        except (TypeError, ValueError):
            return False
        if not (0 <= idx < len(opts)):
            return False
        correct = _norm(opts[idx])
        if not correct or correct not in week_words:
            return False
        if correct in used_correct:
            return False
        used_correct.add(correct)
        q["options"] = opts[:4]
        q["answer_index"] = idx
        q["answer_slang"] = opts[idx]
    return True


def _distractor_pool(week_words: set[str], n: int = 12) -> list[str]:
    pool = [
        w.strip()
        for w in urban.COMMON_SLANG
        if w.strip() and _norm(w) not in week_words
    ]
    random.shuffle(pool)
    return pool[:n]


def create_quiz(dates: list[str]) -> WeeklyQuiz:
    dates = [d for d in dict.fromkeys(dates) if d]
    db = SessionLocal()
    try:
        row = WeeklyQuiz(status="pending", source_dates=json.dumps(dates))
        db.add(row)
        db.commit()
        row_id = row.id

        try:
            if not (MIN_SELECT <= len(dates) <= MAX_SELECT):
                raise RuntimeError(f"请选择 {MIN_SELECT}-{MAX_SELECT} 条本周内容")

            contents = (
                db.query(SlangContent)
                .filter(SlangContent.date.in_(dates), SlangContent.status == "generated")
                .order_by(SlangContent.date.asc())
                .all()
            )
            if len(contents) < MIN_SELECT:
                raise RuntimeError("选中的内容中可用的不足 2 条")

            week_slangs = []
            week_words: set[str] = set()
            for c in contents:
                word = _norm(c.slang)
                week_words.add(word)
                scene = ""
                sc = c.scenarios_list()
                if sc:
                    scene = sc[0].get("dialogue_zh") or sc[0].get("dialogue_en", "")
                week_slangs.append(
                    {
                        "slang": c.slang,
                        "meaning_zh": c.meaning_zh or "",
                        "scene": (c.hook or scene or c.meaning_zh or "")[:200],
                    }
                )

            distractors = _distractor_pool(week_words)

            questions: list[dict] | None = None
            for _ in range(3):
                data = llm.generate_quiz(week_slangs, distractors)
                qs = data.get("questions") or []
                if _validate_questions(qs, week_words):
                    questions = qs
                    break

            if questions is None:
                raise RuntimeError("周测题目生成不合法，请重试")

            row.questions = json.dumps(questions, ensure_ascii=False)
            row.title = "本周小测 · 情境选俚语"

            out_dir = settings.images_dir / "quiz" / str(row_id)
            imagegen.render_quiz_all(questions, out_dir)
            row.image_dir = str(out_dir)
            row.status = "generated"
            row.error = ""
        except Exception as e:
            row.status = "failed"
            row.error = str(e)
            logger.exception("周测生成失败: %s", e)

        db.commit()
        return row
    finally:
        db.close()


def list_quizzes():
    db = SessionLocal()
    try:
        return db.query(WeeklyQuiz).order_by(WeeklyQuiz.id.desc()).all()
    finally:
        db.close()
