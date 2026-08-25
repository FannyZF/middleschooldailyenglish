from pathlib import Path

from app.services import imagegen, news, pipeline


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
