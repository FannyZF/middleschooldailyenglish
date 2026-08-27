import os

from fastapi.testclient import TestClient

os.environ["START_SCHEDULER"] = "0"

from app.db import SessionLocal
from app.main import app
from app.models import SlangContent


def _seed(day: str) -> str:
    import tempfile
    from pathlib import Path

    from PIL import Image

    base = Path(tempfile.mkdtemp(prefix="route_"))
    (base / "slang.mp3").write_bytes(b"mp3")
    (base / "video.mp4").write_bytes(b"mp4")
    Image.new("RGB", (10, 10)).save(base / "01.png")

    db = SessionLocal()
    db.add(SlangContent(date=day, status="generated", slang="hit", image_dir=str(base)))
    db.commit()
    db.close()
    return str(base)


def test_audio_video_routes():
    day = "2099-04-01"
    _seed(day)
    with TestClient(app) as client:
        client.post("/login", data={"username": "admin", "password": "admin123"})

        r = client.get(f"/slang/{day}/audio/slang.mp3")
        assert r.status_code == 200 and r.content == b"mp3"

        r = client.get(f"/slang/{day}/audio/..%2F..%2Fetc%2Fpasswd.mp3")
        assert r.status_code in (400, 404)

        r = client.get(f"/slang/{day}/audio/missing.mp3")
        assert r.status_code == 404

        r = client.get(f"/slang/{day}/video")
        assert r.status_code == 200 and r.content == b"mp4"

        r = client.get("/slang/2099-04-02/video")
        assert r.status_code == 404
