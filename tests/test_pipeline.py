from pathlib import Path

from app.db import SessionLocal
from app.models import DailyContent, SlangContent
from app.services import imagegen, lemmy, news, pipeline, reddit, urban


def test_wrap_text_ascii():
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (100, 100))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    lines = imagegen.wrap_text(draw, "hello world foo", font, 40)
    assert len(lines) >= 1


def test_generate_for_date(monkeypatch):
    monkeypatch.setattr(
        news,
        "fetch_articles",
        lambda: [{"title": "t", "description": "d"}],
    )
    monkeypatch.setattr(
        "app.services.llm.generate_content",
        lambda articles: {
            "title": "Test News",
            "summary_en": "This is a test.",
            "summary_zh": "这是一条测试。",
            "word": "test",
            "word_pos": "n.",
            "word_phonetic": "/test/",
            "word_grade": "八年级（初二）",
            "definitions": [
                {
                    "meaning_en": "an exam",
                    "meaning_zh": "测验",
                    "example_en": "We have a test.",
                    "example_zh": "我们有测验。",
                }
            ],
            "choices": [
                {
                    "question": "We have a ____ today.",
                    "options": ["test", "rest", "best", "nest"],
                    "answer": "A",
                },
                {
                    "question": "I want to ____ my English.",
                    "options": ["improve", "waste", "test", "break"],
                    "answer": "A",
                },
            ],
            "translation": {"question": "我们今天有测验。", "answer": "We have a test today."},
        },
    )
    monkeypatch.setattr(imagegen, "render_all", lambda content, out_dir: None)

    row = pipeline.generate_for_date("2099-01-01")
    assert row.status == "generated"
    assert row.word == "test"


def test_clean_candidates_filters_compound_vulgar():
    items = [
        {"title": "shitposting in r/main is a hobby", "selftext": ""},
        {"title": "lowkey flex but ok", "selftext": ""},
        {"title": "best apple pie recipe", "selftext": ""},
    ]
    out = pipeline._clean_candidates(items)
    assert len(out) == 2
    assert "apple pie" in out[0]["title"] or "apple pie" in out[1]["title"]


def test_filter_used_articles():
    db = SessionLocal()
    db.add(
        DailyContent(
            date="2026-08-01",
            status="generated",
            source_url="https://x.com/old",
            original_title="Old News Story",
        )
    )
    db.commit()
    db.close()

    articles = [
        {"url": "https://x.com/old", "title": "Old News Story"},
        {"url": "https://x.com/new", "title": "Brand New Story"},
    ]
    db = SessionLocal()
    fresh = pipeline._filter_used_articles(articles, db, exclude_day="2099-12-31")
    db.close()
    assert len(fresh) == 1
    assert fresh[0]["url"] == "https://x.com/new"


def test_generate_slang_for_date(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "_fetch_slang_candidates",
        lambda: [{"title": "p", "selftext": "hit the sack means go to bed"}],
    )
    monkeypatch.setattr(
        "app.services.llm.generate_slang",
        lambda posts, strict=False, avoid=None: {
            "slang": "hit the sack",
            "phonetic": "/hɪt ðə sæk/",
            "meaning_en": "go to bed",
            "meaning_zh": "去睡觉",
            "usage": "口语常用。",
            "examples": [{"en": "Let's hit the sack.", "zh": "我们睡觉吧。"}],
            "scenarios": [
                {
                    "title": "道晚安",
                    "dialogue_en": "A: Time to hit the sack.\nB: Good night!",
                    "dialogue_zh": "A：该睡了。\nB：晚安！",
                }
            ],
            "source": "Reddit r/EnglishLearning",
            "source_url": "https://www.reddit.com/x",
            "caption": "你是否有过很累的经历？不要再说 go to bed 了，用 hit the sack 吧！",
            "hook": "累到睁不开眼却还想再刷一会儿手机？",
            "theme": "日常生活",
        },
    )
    monkeypatch.setattr(imagegen, "render_slang_all", lambda content, out_dir: None)

    row = pipeline.generate_slang_for_date("2099-01-02")
    assert row.status == "generated"
    assert row.slang == "hit the sack"
    assert row.caption
    assert row.theme == "日常生活"
    assert row.hook


def test_slang_not_in_candidates_triggers_retry(monkeypatch):
    calls = {"n": 0}

    def fake_llm(posts, strict=False, avoid=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "slang": "kiss ass",
                "phonetic": "",
                "meaning_en": "suck up",
                "meaning_zh": "拍马屁",
                "usage": "u",
                "examples": [{"en": "x", "zh": "y"}],
                "scenarios": [{"title": "t", "dialogue_en": "A: b", "dialogue_zh": "A：b"}],
                "source": "s",
                "source_url": "",
                "caption": "c",
            }
        return {
            "slang": "lowkey",
            "phonetic": "",
            "meaning_en": "secretly",
            "meaning_zh": "低调地",
            "usage": "u",
            "examples": [{"en": "x", "zh": "y"}],
            "scenarios": [{"title": "t", "dialogue_en": "A: b", "dialogue_zh": "A：b"}],
            "source": "s",
            "source_url": "",
            "caption": "c",
        }

    monkeypatch.setattr(
        pipeline,
        "_fetch_slang_candidates",
        lambda: [{"title": "lowkey", "selftext": "means secretly"}],
    )
    monkeypatch.setattr("app.services.llm.generate_slang", fake_llm)
    monkeypatch.setattr(imagegen, "render_slang_all", lambda content, out_dir: None)

    row = pipeline.generate_slang_for_date("2099-01-04")
    assert row.status == "generated"
    assert row.slang == "lowkey"
    assert calls["n"] == 2


def test_slang_source_corrected_from_candidates(monkeypatch):
    cand = [
        {
            "title": "lowkey means chill",
            "selftext": "",
            "subreddit": "asklemmy",
            "url": "https://lemmy.world/post/9",
            "_origin": "Lemmy",
        }
    ]

    def fake_llm(posts, strict=False, avoid=None):
        return {
            "slang": "lowkey",
            "phonetic": "",
            "meaning_en": "secretly",
            "meaning_zh": "低调地",
            "usage": "u",
            "examples": [{"en": "x", "zh": "y"}],
            "scenarios": [{"title": "t", "dialogue_en": "A: b", "dialogue_zh": "A：b"}],
            "source": "Reddit r/main",  # 模型编造
            "source_url": "https://reddit.com/fake",
            "caption": "c",
        }

    monkeypatch.setattr(pipeline, "_fetch_slang_candidates", lambda: cand)
    monkeypatch.setattr("app.services.llm.generate_slang", fake_llm)
    monkeypatch.setattr(imagegen, "render_slang_all", lambda content, out_dir: None)

    row = pipeline.generate_slang_for_date("2099-01-05")
    assert row.status == "generated"
    assert row.source == "Lemmy r/asklemmy"
    assert row.source_url == "https://lemmy.world/post/9"


def test_slang_source_fallback(monkeypatch):
    def boom():
        raise RuntimeError("Reddit blocked")

    monkeypatch.setattr(reddit, "fetch_posts", lambda: boom())
    monkeypatch.setattr(lemmy, "fetch_posts", lambda: boom())
    monkeypatch.setattr(
        urban,
        "fetch_entries",
        lambda: [{"title": "no cap", "selftext": "for real", "subreddit": "Urban Dictionary"}],
    )

    got = pipeline._fetch_slang_candidates()
    assert got[0]["title"] == "no cap"


def test_slang_source_lemmy_first(monkeypatch):
    def boom():
        raise RuntimeError("blocked")

    monkeypatch.setattr(lemmy, "fetch_posts", lambda: [{"title": "lemmy top"}])
    monkeypatch.setattr(urban, "fetch_entries", lambda: boom())
    monkeypatch.setattr(reddit, "fetch_posts", lambda: boom())

    got = pipeline._fetch_slang_candidates()
    assert got[0]["title"] == "lemmy top"


def test_slang_source_all_fail(monkeypatch):
    def boom():
        raise RuntimeError("blocked")

    monkeypatch.setattr(reddit, "fetch_posts", lambda: boom())
    monkeypatch.setattr(lemmy, "fetch_posts", lambda: boom())
    monkeypatch.setattr(urban, "fetch_entries", lambda: boom())

    try:
        pipeline._fetch_slang_candidates()
        assert False, "should raise"
    except RuntimeError as e:
        assert "数据源" in str(e)


def test_slang_source_urban_only(monkeypatch):
    monkeypatch.setattr(pipeline.settings, "slang_source", "urban")
    monkeypatch.setattr(
        urban, "fetch_entries", lambda: [{"title": "lowkey", "selftext": "secret"}]
    )

    def not_called():
        raise AssertionError("lemmy/reddit 不应被调用")

    monkeypatch.setattr(lemmy, "fetch_posts", lambda: not_called())
    monkeypatch.setattr(reddit, "fetch_posts", lambda: not_called())

    got = pipeline._fetch_slang_candidates()
    assert got[0]["title"] == "lowkey"
    assert got[0]["_origin"] == "Urban Dictionary"


def test_slang_skip_already_used(monkeypatch):
    # 造一条历史已发布过的俚语 lowkey
    db = SessionLocal()
    db.add(SlangContent(date="2099-02-01", status="generated", slang="lowkey"))
    db.commit()
    db.close()

    def fake_fetch():
        return [
            {"title": "lowkey", "selftext": "secret", "_origin": "Urban Dictionary", "url": "x"},
            {"title": "no cap", "selftext": "really", "_origin": "Urban Dictionary", "url": "y"},
        ]

    monkeypatch.setattr(pipeline, "_fetch_slang_candidates", fake_fetch)

    seen = []

    def fake_llm(posts, strict=False, avoid=None):
        seen.append([p["title"] for p in posts])
        return {
            "slang": "no cap",
            "phonetic": "",
            "meaning_en": "for real",
            "meaning_zh": "真的",
            "usage": "u",
            "examples": [{"en": "x", "zh": "y"}],
            "scenarios": [{"title": "t", "dialogue_en": "A: b", "dialogue_zh": "A：b"}],
            "source": "s",
            "source_url": "",
            "caption": "c",
        }

    monkeypatch.setattr("app.services.llm.generate_slang", fake_llm)
    monkeypatch.setattr(imagegen, "render_slang_all", lambda content, out_dir: None)

    row = pipeline.generate_slang_for_date("2099-02-02")
    assert row.slang == "no cap"
    # 传给模型做选择的候选不应包含已发布过的 lowkey
    assert all("lowkey" not in titles for titles in seen)
    assert "no cap" in seen[0]
