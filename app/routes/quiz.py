import io
import shutil
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse

from ..auth import get_current_user
from ..db import SessionLocal
from ..models import WeeklyQuiz
from ..services import quiz as quiz_service

router = APIRouter(dependencies=[Depends(get_current_user)])


def _get(id: int):
    db = SessionLocal()
    try:
        row = db.query(WeeklyQuiz).filter(WeeklyQuiz.id == id).first()
    finally:
        db.close()
    return row


@router.get("/slang/quizzes")
def list_page(request: Request):
    rows = quiz_service.list_quizzes()
    return request.app.state.templates.TemplateResponse(
        request, "quiz_list.html", {"quizzes": rows}
    )


@router.post("/slang/quiz/create")
def create(request: Request, dates: list[str] = Form(default=[])):
    row = quiz_service.create_quiz(dates)
    return RedirectResponse(f"/slang/quiz/{row.id}", status_code=302)


@router.get("/slang/quiz/{qid}")
def detail(request: Request, qid: int):
    row = _get(qid)
    if row is None:
        raise HTTPException(status_code=404, detail="未找到该周测")
    questions = row.questions_list()
    n = len(questions)
    return request.app.state.templates.TemplateResponse(
        request, "quiz_view.html", {"q": row, "n": n}
    )


@router.get("/slang/quiz/{qid}/image/{name}")
def image(qid: int, name: str):
    import re

    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.png", name):
        raise HTTPException(status_code=400, detail="非法文件名")
    row = _get(qid)
    if row is None or not row.image_dir:
        raise HTTPException(status_code=404, detail="图片不存在")
    path = (Path(row.image_dir) / name).resolve()
    base = Path(row.image_dir).resolve()
    if not str(path).startswith(str(base)) or not path.exists():
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(path, media_type="image/png")


@router.get("/slang/quiz/{qid}/download")
def download(qid: int):
    row = _get(qid)
    if row is None or not row.image_dir:
        raise HTTPException(status_code=404, detail="内容不存在")
    img_dir = Path(row.image_dir)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(img_dir.glob("*.png")):
            zf.write(p, p.name)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="quiz-{qid}.zip"'},
    )


@router.post("/slang/quiz/{qid}/delete")
def delete(qid: int):
    db = SessionLocal()
    try:
        row = db.query(WeeklyQuiz).filter(WeeklyQuiz.id == qid).first()
        if row is not None:
            if row.image_dir:
                shutil.rmtree(Path(row.image_dir), ignore_errors=True)
            db.delete(row)
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/slang/quizzes", status_code=302)
