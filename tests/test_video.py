from pathlib import Path

from PIL import Image

from app.schemas import SlangContent as SlangContentData
from app.services import video


def _content():
    return SlangContentData.model_validate(
        {
            "slang": "hit the sack",
            "phonetic": "",
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


def test_build_slang_video(monkeypatch, tmp_path):
    # 准备 3 张图
    for i in range(1, 4):
        Image.new("RGB", (10, 10), "white").save(tmp_path / f"{i:02d}.png")

    def fake_narration(content, out_dir):
        for i in range(1, 4):
            (out_dir / f"narration-{i}.mp3").write_bytes(b"x")
        return list(out_dir.glob("narration-*.mp3"))

    monkeypatch.setattr(video.tts, "generate_slang_narration", fake_narration)

    calls = []

    def fake_ffmpeg(args):
        calls.append(args)

    monkeypatch.setattr(video, "_run_ffmpeg", fake_ffmpeg)

    out = video.build_slang_video(_content(), tmp_path)
    assert out == tmp_path / "video.mp4"
    assert len(calls) == 4  # 3 段片段 + 1 次拼接


def test_build_slang_video_missing_image(monkeypatch, tmp_path):
    # 没有图片
    def fake_narration(content, out_dir):
        (out_dir / "narration-1.mp3").write_bytes(b"x")
        return [out_dir / "narration-1.mp3"]

    monkeypatch.setattr(video.tts, "generate_slang_narration", fake_narration)
    monkeypatch.setattr(video, "_run_ffmpeg", lambda args: None)

    try:
        video.build_slang_video(_content(), tmp_path)
        assert False, "should raise"
    except RuntimeError:
        pass
