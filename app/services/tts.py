import asyncio
from pathlib import Path

import edge_tts

from ..config import settings

TTS_TIMEOUT = 30  # 单条语音合成超时（秒），防止连接挂起


def synthesize(text: str, out_path: Path, voice: str | None = None) -> None:
    """把文字合成 MP3 保存到 out_path。带超时，失败抛异常由上层捕获。"""
    voice = voice or settings.tts_voice
    text = (text or "").strip()
    if not text:
        return

    async def _run() -> None:
        communicate = edge_tts.Communicate(text, voice)
        await asyncio.wait_for(communicate.save(str(out_path)), timeout=TTS_TIMEOUT)

    asyncio.run(_run())


def generate_slang_audio(content, out_dir: Path) -> list[Path]:
    """生成网页播放用的单条语音：slang、例句、场景对话。"""
    files: list[Path] = []

    if content.slang:
        p = out_dir / "slang.mp3"
        synthesize(content.slang, p)
        files.append(p)

    for i, ex in enumerate(content.examples, start=1):
        if ex.en:
            p = out_dir / f"example-{i}.mp3"
            synthesize(ex.en, p)
            files.append(p)

    for i, sc in enumerate(content.scenarios, start=1):
        if sc.dialogue_en:
            p = out_dir / f"scenario-{i}.mp3"
            synthesize(sc.dialogue_en, p)
            files.append(p)

    return files


def generate_slang_narration(content, out_dir: Path) -> list[Path]:
    """生成视频用的 3 段旁白（纯英文，对应 3 张图）。"""
    parts = []

    s1 = []
    if content.slang:
        s1.append(f"Today's slang is {content.slang}.")
    if content.meaning_en:
        s1.append(f"It means, {content.meaning_en}.")
    parts.append(" ".join(s1))

    s2 = []
    if content.usage:
        s2.append(content.usage.replace("\n", " "))
    for i, ex in enumerate(content.examples, start=1):
        if ex.en:
            s2.append(f"Example {i}. {ex.en}")
    parts.append(" ".join(s2))

    s3 = []
    for i, sc in enumerate(content.scenarios, start=1):
        if sc.dialogue_en:
            s3.append(f"Scenario {i}. {sc.dialogue_en.replace(chr(10), ' ')}")
    parts.append(" ".join(s3))

    files: list[Path] = []
    for i, text in enumerate(parts, start=1):
        if text.strip():
            p = out_dir / f"narration-{i}.mp3"
            synthesize(text, p)
            files.append(p)
    return files
