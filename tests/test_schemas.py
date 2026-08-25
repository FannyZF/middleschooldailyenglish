from app.schemas import Content


def test_content_validation():
    data = {
        "title": "Test News",
        "summary_en": "This is a test. It has two sentences.",
        "summary_zh": "这是一条测试新闻。",
        "word": "test",
        "word_pos": "n.",
        "word_phonetic": "/test/",
        "word_grade": "八年级（初二）",
        "definitions": [
            {
                "meaning_en": "an exam",
                "meaning_zh": "测验",
                "example_en": "We have a test today.",
                "example_zh": "我们今天有测验。",
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
        "translation": {"question": "我们今天有个测验。", "answer": "We have a test today."},
    }
    c = Content.model_validate(data)
    assert c.word == "test"
    assert len(c.definitions) == 1
    assert len(c.choices) == 2
    assert c.choices[0].answer == "A"
    assert c.word_grade == "八年级（初二）"


def test_choice_option_prefix_stripped():
    from app.schemas import ChoiceQuestion

    q = ChoiceQuestion.model_validate(
        {
            "question": "q",
            "options": ["A. improve", "B) waste", "C、forget", "D. break"],
            "answer": "B) waste",
        }
    )
    assert q.options == ["improve", "waste", "forget", "break"]
    assert q.answer == "B"
