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
