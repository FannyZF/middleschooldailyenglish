import shutil
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from ..auth import get_current_user
from ..config import settings
from ..db import SessionLocal
from ..models import DailyContent, SlangContent
from ..scheduler import cron_to_time, reload_scheduler, time_to_cron
from ..services import pipeline
from ..services.settings import get_setting, set_setting

router = APIRouter(dependencies=[Depends(get_current_user)])


def _model(module: str):
    return DailyContent if module == "news" else SlangContent


def _has_generated(module: str, day: str) -> bool:
    db = SessionLocal()
    try:
        model = _model(module)
        row = db.query(model).filter(model.date == day, model.status == "generated").first()
        return row is not None
    finally:
        db.close()


@router.post("/admin/generate-range")
def generate_range(request: Request, module: str = Form(...), start: str = Form(...), end: str = Form(...)):
    try:
        d0 = date.fromisoformat(start)
        d1 = date.fromisoformat(end)
    except ValueError:
        return RedirectResponse("/admin", status_code=302)

    results: list[dict] = []
    if d1 >= d0:
        cur = d0
        while cur <= d1:
            day = cur.isoformat()
            if _has_generated(module, day):
                results.append({"day": day, "status": "已存在，跳过"})
            else:
                try:
                    if module == "news":
                        pipeline.generate_for_date(day)
                    else:
                        pipeline.generate_slang_for_date(day)
                    results.append({"day": day, "status": "生成成功"})
                except Exception as e:
                    results.append({"day": day, "status": f"失败：{e}"})
            cur += timedelta(days=1)

    return request.app.state.templates.TemplateResponse(
        request,
        "range_result.html",
        {"module": module, "results": results},
    )


@router.post("/admin/delete-range")
def delete_range(request: Request, module: str = Form(...), start: str = Form(...), end: str = Form(...)):
    model = _model(module)
    db = SessionLocal()
    count = 0
    try:
        rows = (
            db.query(model)
            .filter(model.date >= start, model.date <= end)
            .all()
        )
        for r in rows:
            if r.image_dir:
                shutil.rmtree(r.image_dir, ignore_errors=True)
            db.delete(r)
            count += 1
        db.commit()
    finally:
        db.close()
    return request.app.state.templates.TemplateResponse(
        request,
        "delete_result.html",
        {"module": module, "start": start, "end": end, "count": count},
    )


@router.get("/admin")
def admin_page(request: Request):
    cron = get_setting("schedule_cron", settings.schedule_cron)
    keys = {
        "deepseek_api_key": get_setting("deepseek_api_key", settings.deepseek_api_key),
        "schedule_time": cron_to_time(cron),
        "reddit_client_id": get_setting("reddit_client_id", settings.reddit_client_id),
        "reddit_client_secret": get_setting("reddit_client_secret", settings.reddit_client_secret),
        "reddit_username": get_setting("reddit_username", settings.reddit_username),
        "reddit_password": get_setting("reddit_password", settings.reddit_password),
    }
    return request.app.state.templates.TemplateResponse(
        request, "admin.html", {"keys": keys, "today": date.today().isoformat()}
    )


@router.post("/admin/generate")
def generate_now(request: Request, day: str = Form(default="")):
    target = day.strip() or date.today().isoformat()
    pipeline.generate_for_date(target)
    return RedirectResponse(f"/content/{target}", status_code=302)


@router.post("/admin/generate-slang")
def generate_slang_now(request: Request, day: str = Form(default="")):
    target = day.strip() or date.today().isoformat()
    pipeline.generate_slang_for_date(target)
    return RedirectResponse(f"/slang/{target}", status_code=302)


@router.post("/admin/settings")
def save_settings(
    request: Request,
    deepseek_api_key: str = Form(default=""),
    schedule_time: str = Form(default=""),
    reddit_client_id: str = Form(default=""),
    reddit_client_secret: str = Form(default=""),
    reddit_username: str = Form(default=""),
    reddit_password: str = Form(default=""),
):
    set_setting("deepseek_api_key", deepseek_api_key.strip())
    set_setting("reddit_client_id", reddit_client_id.strip())
    set_setting("reddit_client_secret", reddit_client_secret.strip())
    set_setting("reddit_username", reddit_username.strip())
    set_setting("reddit_password", reddit_password.strip())
    cron = time_to_cron(schedule_time)
    if cron:
        set_setting("schedule_cron", cron)
        try:
            reload_scheduler()
        except Exception:
            pass
    return RedirectResponse("/admin", status_code=302)
