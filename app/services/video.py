import logging
import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from . import tts

logger = logging.getLogger("video")

IMAGE_COUNT = 3
NARRATION_COUNT = 3


def _run_ffmpeg(args: list[str]) -> None:
    exe = get_ffmpeg_exe()
    cmd = [exe, "-y"] + args
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg 执行失败: {proc.stderr[-500:] if proc.stderr else 'unknown'}"
        )


def build_slang_video(content, out_dir: Path) -> Path:
    """把当天 3 张图 + 3 段旁白合成竖屏 MP4。"""
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. 旁白音频：已有则复用，否则生成
    narrations = [
        out_dir / f"narration-{i}.mp3" for i in range(1, NARRATION_COUNT + 1)
    ]
    if not all(p.exists() for p in narrations):
        narrations = tts.generate_slang_narration(content, out_dir)
    narrations = [p for p in narrations if p.exists()]
    if not narrations:
        raise RuntimeError("无旁白内容")

    segments: list[Path] = []
    for i in range(1, IMAGE_COUNT + 1):
        img = out_dir / f"{i:02d}.png"
        if not img.exists():
            raise RuntimeError(f"缺少图片 {img.name}")
        audio = out_dir / f"narration-{i}.mp3"
        if not audio.exists():
            continue
        seg = out_dir / f"_seg-{i}.mp4"
        # 静态图 + 音频 → 片段（图像时长 = 音频时长）
        _run_ffmpeg(
            [
                "-loop", "1",
                "-i", str(img),
                "-i", str(audio),
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-pix_fmt", "yuv420p",
                "-r", "24",
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
                "-fflags", "+genpts",
                str(seg),
            ]
        )
        segments.append(seg)

    if not segments:
        raise RuntimeError("没有可合成的片段")

    # 2. 拼接所有片段
    list_file = out_dir / "_concat.txt"
    list_file.write_text(
        "\n".join(f"file '{s.name}'" for s in segments) + "\n", encoding="utf-8"
    )
    video_path = out_dir / "video.mp4"
    _run_ffmpeg(
        [
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            "-movflags", "+faststart",
            str(video_path),
        ]
    )

    # 清理临时文件
    for seg in segments:
        try:
            seg.unlink()
        except OSError:
            pass
    try:
        list_file.unlink()
    except OSError:
        pass

    logger.info("俚语视频已生成: %s", video_path)
    return video_path
