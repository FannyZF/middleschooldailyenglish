import io
import shutil
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse

from ..auth import get_current_user
from ..db import SessionLocal
from ..models import SlangContent

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/slang/")
def index(request: Request):
    db = SessionLocal()
    try:
        rows = db.query(SlangContent).order_by(SlangContent.date.desc()).all()
    finally:
        db.close()
    return request.app.state.templates.TemplateResponse(
        request, "slang_index.html", {"contents": rows}
    )


@router.get("/slang/export")
def export(start: str = "", end: str = ""):
    db = SessionLocal()
    try:
        q = db.query(SlangContent).filter(SlangContent.status == "generated")
        if start:
            q = q.filter(SlangContent.date >= start)
        if end:
            q = q.filter(SlangContent.date <= end)
        rows = q.order_by(SlangContent.date.asc()).all()
    finally:
        db.close()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for row in rows:
            if not row.image_dir:
                continue
            img_dir = Path(row.image_dir)
            if not img_dir.exists():
                continue
            for i in range(1, 5):
                p = img_dir / f"{i:02d}.png"
                if p.exists():
                    zf.write(p, f"{row.date}/{i:02d}.png")
    buf.seek(0)

    if start and end:
        name = f"slang-{start}-to-{end}"
    elif start:
        name = f"slang-from-{start}"
    elif end:
        name = f"slang-until-{end}"
    else:
        name = "slang-all"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}.zip"'},
    )


@router.get("/slang/{day}")
def detail(request: Request, day: str):
    db = SessionLocal()
    try:
        row = db.query(SlangContent).filter(SlangContent.date == day).first()
    finally:
        db.close()
    if row is None:
        raise HTTPException(status_code=404, detail="未找到该日期的俚语内容")
    return request.app.state.templates.TemplateResponse(
        request, "slang_content.html", {"c": row}
    )


@router.get("/slang/{day}/image/{n}")
def image(day: str, n: int):
    db = SessionLocal()
    try:
        row = db.query(SlangContent).filter(SlangContent.date == day).first()
    finally:
        db.close()
    if row is None or not row.image_dir:
        raise HTTPException(status_code=404, detail="图片不存在")
    path = Path(row.image_dir) / f"{n:02d}.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(path, media_type="image/png")


@router.get("/slang/{day}/download")
def download(day: str):
    db = SessionLocal()
    try:
        row = db.query(SlangContent).filter(SlangContent.date == day).first()
    finally:
        db.close()
    if row is None or not row.image_dir:
        raise HTTPException(status_code=404, detail="内容不存在")
    img_dir = Path(row.image_dir)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i in range(1, 5):
            p = img_dir / f"{i:02d}.png"
            if p.exists():
                zf.write(p, f"{day}-{i:02d}.png")
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="slang-{day}.zip"'},
    )


@router.post("/slang/{day}/delete")
def delete(day: str):
    db = SessionLocal()
    try:
        row = db.query(SlangContent).filter(SlangContent.date == day).first()
        if row is not None:
            if row.image_dir:
                shutil.rmtree(Path(row.image_dir), ignore_errors=True)
            db.delete(row)
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/slang/", status_code=302)
