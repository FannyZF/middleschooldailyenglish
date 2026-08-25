from pathlib import Path

from app.services import imagegen, news, pipeline, reddit, urban


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


def test_generate_slang_for_date(monkeypatch):
    monkeypatch.setattr(reddit, "fetch_posts", lambda: [{"title": "p", "selftext": ""}])
    monkeypatch.setattr(
        "app.services.llm.generate_slang",
        lambda posts: {
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
        },
    )
    monkeypatch.setattr(imagegen, "render_slang_all", lambda content, out_dir: None)

    row = pipeline.generate_slang_for_date("2099-01-02")
    assert row.status == "generated"
    assert row.slang == "hit the sack"


def test_slang_source_fallback(monkeypatch):
    def boom():
        raise RuntimeError("Reddit blocked")

    monkeypatch.setattr(reddit, "fetch_posts", lambda: boom())
    monkeypatch.setattr(
        urban,
        "fetch_entries",
        lambda: [{"title": "no cap", "selftext": "for real", "subreddit": "Urban Dictionary"}],
    )

    got = pipeline._fetch_slang_candidates()
    assert got[0]["title"] == "no cap"


def test_slang_source_both_fail(monkeypatch):
    def boom():
        raise RuntimeError("blocked")

    monkeypatch.setattr(reddit, "fetch_posts", lambda: boom())
    monkeypatch.setattr(urban, "fetch_entries", lambda: boom())

    try:
        pipeline._fetch_slang_candidates()
        assert False, "should raise"
    except RuntimeError as e:
        assert "数据源" in str(e)
