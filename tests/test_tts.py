from pathlib import Path

from app.schemas import SlangContent as SlangContentData
from app.services import tts


class FakeCommunicate:
    def __init__(self, text, voice):
        self.text = text
        self.voice = voice

    async def save(self, path):
        Path(path).write_bytes(b"fake-mp3")


def test_synthesize(monkeypatch, tmp_path):
    monkeypatch.setattr(tts.edge_tts, "Communicate", FakeCommunicate)
    out = tmp_path / "a.mp3"
    tts.synthesize("hello world", out, voice="en-US-JennyNeural")
    assert out.read_bytes() == b"fake-mp3"


def _content():
    return SlangContentData.model_validate(
        {
            "slang": "hit the sack",
            "phonetic": "/hɪt ðə sæk/",
            "meaning_en": "go to bed",
            "meaning_zh": "去睡觉",
            "usage": "口语。",
            "examples": [{"en": "Let's hit the sack.", "zh": "睡吧。"}],
            "scenarios": [
                {"title": "道晚安", "dialogue_en": "A: Good night!", "dialogue_zh": "A：晚安！"}
            ],
            "source": "UD",
            "source_url": "x",
            "caption": "c",
        }
    )


def test_generate_slang_audio(monkeypatch, tmp_path):
    monkeypatch.setattr(
        tts, "synthesize", lambda text, path, voice=None: Path(path).write_bytes(b"x")
    )
    tts.generate_slang_audio(_content(), tmp_path)
    assert (tmp_path / "slang.mp3").exists()
    assert (tmp_path / "example-1.mp3").exists()
    assert (tmp_path / "scenario-1.mp3").exists()


def test_generate_slang_narration(monkeypatch, tmp_path):
    monkeypatch.setattr(
        tts, "synthesize", lambda text, path, voice=None: Path(path).write_bytes(b"x")
    )
    files = tts.generate_slang_narration(_content(), tmp_path)
    assert len(files) == 3
    assert all(f.exists() for f in files)
