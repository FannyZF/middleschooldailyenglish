import os

from fastapi.testclient import TestClient

os.environ["START_SCHEDULER"] = "0"

from app.db import SessionLocal
from app.main import app
from app.models import SlangContent
from app.routes import admin as admin_mod


def test_generate_range_skips_existing(monkeypatch):
    db = SessionLocal()
    db.add(SlangContent(date="2099-03-01", status="generated", slang="x"))
    db.add(SlangContent(date="2099-03-03", status="failed", slang=""))
    db.commit()
    db.close()

    calls = []

    def fake_slang(day):
        calls.append(day)
        db = SessionLocal()
        db.add(SlangContent(date=day, status="generated", slang=f"word-{day}"))
        db.commit()
        db.close()

    def fake_news(day):
        raise AssertionError("should not call news")

    monkeypatch.setattr(admin_mod.pipeline, "generate_slang_for_date", fake_slang)
    monkeypatch.setattr(admin_mod.pipeline, "generate_for_date", fake_news)

    with TestClient(app) as client:
        client.post("/login", data={"username": "admin", "password": "admin123"})
        r = client.post(
            "/admin/generate-range",
            data={"module": "slang", "start": "2099-03-01", "end": "2099-03-03"},
        )
        assert r.status_code == 200
        # 03-01 已生成跳过；03-02/03-03 调用（03-03 之前 failed 不算已生成）
        assert calls == ["2099-03-02", "2099-03-03"]
        assert "生成成功" in r.text


def test_delete_range_removes_rows(monkeypatch):
    from pathlib import Path

    import tempfile
    from PIL import Image

    from app.models import DailyContent

    base = Path(tempfile.mkdtemp(prefix="del_"))
    db = SessionLocal()
    db.add(SlangContent(date="2099-04-01", status="generated", slang="x", image_dir=str(base / "a")))
    db.add(SlangContent(date="2099-04-03", status="generated", slang="y", image_dir=str(base / "b")))
    db.add(SlangContent(date="2099-04-05", status="generated", slang="z", image_dir=str(base / "c")))
    db.add(DailyContent(date="2099-04-02", status="generated", title="n"))
    db.commit()
    db.close()

    with TestClient(app) as client:
        client.post("/login", data={"username": "admin", "password": "admin123"})
        r = client.post(
            "/admin/delete-range",
            data={"module": "slang", "start": "2099-04-01", "end": "2099-04-04"},
        )
        assert r.status_code == 200
        assert "2" in r.text  # 删了 04-01、04-03 两条，04-05 保留

    db = SessionLocal()
    left = [x.date for x in db.query(SlangContent).all()]
    news_left = [x.date for x in db.query(DailyContent).all()]
    db.close()
    assert "2099-04-01" not in left and "2099-04-03" not in left
    assert "2099-04-05" in left
    assert "2099-04-02" in news_left
