import io
import tempfile
from pathlib import Path

from PIL import Image

from app.services import imagegen, pdf_export


class FakeRow:
    def __init__(self, date, slang, image_dir):
        self.date = date
        self.slang = slang
        self.image_dir = image_dir


def test_build_slang_pdf(monkeypatch, tmp_path):
    monkeypatch.setattr(
        imagegen, "render_cover", lambda title: Image.new("RGB", (100, 100), "white")
    )
    monkeypatch.setattr(
        imagegen, "render_toc_page", lambda entries: Image.new("RGB", (100, 100), "white")
    )

    rows = []
    for day in ["2026-08-25", "2026-08-26"]:
        d = tmp_path / day
        d.mkdir(parents=True, exist_ok=True)
        for i in range(1, 4):
            Image.new("RGB", (10, 10)).save(d / f"{i:02d}.png")
        rows.append(FakeRow(day, "hit the sack", str(d)))

    data = pdf_export.build_slang_pdf(rows)
    assert data.startswith(b"%PDF")
    assert len(data) > 100
