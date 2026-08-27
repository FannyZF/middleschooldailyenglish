import io
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw

from . import imagegen

SLANG_IMAGE_COUNT = 3


def _month_day(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{d.month}月{d.day}日"


def _toc_rows_per_page() -> int:
    """按实际字体度量计算每页目录能放多少行，避免压到落款。"""
    img = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(img)
    row_h = imagegen._line_height(imagegen._font(imagegen.REGULAR, 34)) + 16
    top = imagegen.HEADER_H + imagegen.TOP_PAD
    heading_h = imagegen._line_height(imagegen._font(imagegen.BOLD, 46)) + 8 + 46
    bottom = imagegen.H - imagegen.FOOTER_H - 20
    return max(1, int((bottom - top - heading_h) // row_h))


def _add_page_number(img: Image.Image, num: int) -> Image.Image:
    img = img.convert("RGB").copy()
    draw = ImageDraw.Draw(img)
    font = imagegen._font(imagegen.REGULAR, 24)
    text = str(num)
    tw = draw.textlength(text, font=font)
    x = imagegen.W - imagegen.MARGIN - tw
    y = imagegen.H - 60
    draw.text((x, y), text, font=font, fill=imagegen.MUTED)
    return img


def build_slang_pdf(rows) -> bytes:
    """把多天俚语内容合成为 PDF：封面 + 目录（可多页）+ 每天 3 张图 + 每页页码。rows 需按日期升序。"""
    if not rows:
        raise ValueError("没有可导出的内容")

    start = rows[0].date
    d = datetime.strptime(start, "%Y-%m-%d")
    title = f"{d.year}年{d.month}月俚语集合"

    per_page = _toc_rows_per_page()
    n = len(rows)
    toc_pages = max(1, (n + per_page - 1) // per_page)

    entries: list[tuple[str, int]] = []
    for i, row in enumerate(rows):
        page = toc_pages + 2 + i * SLANG_IMAGE_COUNT
        label = f"{_month_day(row.date)} · {row.slang or ''}"
        entries.append((label, page))

    pages = [imagegen.render_cover(title)]
    for p in range(toc_pages):
        chunk = entries[p * per_page:(p + 1) * per_page]
        if chunk:
            pages.append(imagegen.render_toc_page(chunk))

    for row in rows:
        img_dir = Path(row.image_dir)
        for i in range(1, SLANG_IMAGE_COUNT + 1):
            p = img_dir / f"{i:02d}.png"
            if p.exists():
                pages.append(Image.open(p).convert("RGB"))

    numbered = [_add_page_number(pg, idx + 1) for idx, pg in enumerate(pages)]

    buf = io.BytesIO()
    numbered[0].save(buf, "PDF", save_all=True, append_images=numbered[1:])
    buf.seek(0)
    return buf.getvalue()
