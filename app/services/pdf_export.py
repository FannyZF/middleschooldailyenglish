import io
from datetime import datetime
from pathlib import Path

from PIL import Image

from . import imagegen

SLANG_IMAGE_COUNT = 3
TOC_PER_PAGE = 15


def _month_day(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{d.month}月{d.day}日"


def build_slang_pdf(rows) -> bytes:
    """把多天俚语内容合成为 PDF：封面 + 目录 + 每天 3 张图。rows 需按日期升序。"""
    if not rows:
        raise ValueError("没有可导出的内容")

    start = rows[0].date
    d = datetime.strptime(start, "%Y-%m-%d")
    title = f"{d.year}年{d.month}月俚语集合"

    n = len(rows)
    toc_pages = max(1, (n + TOC_PER_PAGE - 1) // TOC_PER_PAGE)

    entries: list[tuple[str, int]] = []
    for i, row in enumerate(rows):
        page = toc_pages + 2 + i * SLANG_IMAGE_COUNT
        label = f"{_month_day(row.date)} · {row.slang or ''}"
        entries.append((label, page))

    pages = [imagegen.render_cover(title)]
    for p in range(toc_pages):
        chunk = entries[p * TOC_PER_PAGE:(p + 1) * TOC_PER_PAGE]
        if chunk:
            pages.append(imagegen.render_toc_page(chunk))

    for row in rows:
        img_dir = Path(row.image_dir)
        for i in range(1, SLANG_IMAGE_COUNT + 1):
            p = img_dir / f"{i:02d}.png"
            if p.exists():
                pages.append(Image.open(p).convert("RGB"))

    buf = io.BytesIO()
    pages[0].save(buf, "PDF", save_all=True, append_images=pages[1:])
    buf.seek(0)
    return buf.getvalue()
