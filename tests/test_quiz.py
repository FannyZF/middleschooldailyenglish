from app.db import SessionLocal
from app.models import SlangContent
from app.services import imagegen, llm, quiz


def _seed_slang(dates):
    db = SessionLocal()
    for i, d in enumerate(dates):
        db.add(
            SlangContent(
                date=d,
                status="generated",
                slang=f"slang{i}",
                meaning_zh=f"释义{i}",
                scenarios='[{"title":"t","dialogue_zh":"A：x","dialogue_en":"A: x"}]',
            )
        )
    db.commit()
    db.close()


def test_validate_questions():
    week = {"slang0", "slang1", "slang2"}
    q = {
        "options": ["slang0", "slang1", "slang2", "outsider"],
        "answer_index": 0,
        "answer_slang": "slang0",
        "situation": "情境",
        "explanation": "解析",
    }
    assert quiz._validate_questions([q], week)
    bad = dict(q)
    bad["answer_index"] = 3  # 答案是外来词
    assert not quiz._validate_questions([bad], week)


def test_create_quiz(monkeypatch):
    _seed_slang(["2099-05-01", "2099-05-02", "2099-05-03"])

    def fake_gen(week, dist):
        return {
            "questions": [
                {
                    "situation": "加班到很晚还要开会？",
                    "options": ["slang0", "slang1", "slang2", "distractorX"],
                    "answer_index": 0,
                    "answer_slang": "slang0",
                    "explanation": "slang0 表示这个意思。",
                },
                {
                    "situation": "朋友吹牛怎么办？",
                    "options": ["slang1", "slang2", "slang0", "distractorY"],
                    "answer_index": 1,
                    "answer_slang": "slang2",
                    "explanation": "slang2 表示这个意思。",
                },
            ]
        }

    monkeypatch.setattr(llm, "generate_quiz", fake_gen)
    monkeypatch.setattr(imagegen, "render_quiz_all", lambda questions, out_dir: None)

    row = quiz.create_quiz(["2099-05-01", "2099-05-02", "2099-05-03"])
    assert row.status == "generated"
    qs = row.questions_list()
    assert len(qs) == 2
    assert row.source_dates_list() == ["2099-05-01", "2099-05-02", "2099-05-03"]


def test_create_quiz_insufficient():
    _seed_slang(["2099-05-11"])
    row = quiz.create_quiz(["2099-05-11"])
    assert row.status == "failed"
