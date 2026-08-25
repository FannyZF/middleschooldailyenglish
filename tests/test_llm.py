import json

from app.services import llm


class FakeCompletions:
    def __init__(self, payload):
        self.payload = payload

    def create(self, **kwargs):
        return FakeResponse(self.payload)


class FakeChat:
    def __init__(self, payload):
        self.completions = FakeCompletions(payload)


class FakeClient:
    def __init__(self, payload):
        self.chat = FakeChat(payload)


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeResponse:
    def __init__(self, payload):
        self.choices = [FakeChoice(json.dumps(payload, ensure_ascii=False))]


def test_generate_content_returns_dict(monkeypatch):
    payload = {"title": "News", "summary_en": "Hello.", "summary_zh": "你好。"}
    monkeypatch.setattr(llm, "_client", lambda: FakeClient(payload))

    result = llm.generate_content([{"title": "x", "description": "y"}])
    assert result["title"] == "News"
