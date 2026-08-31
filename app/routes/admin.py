from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from ..auth import get_current_user
from ..config import settings
from ..scheduler import cron_to_time, reload_scheduler, time_to_cron
from ..services import pipeline
from ..services.settings import get_setting, set_setting

router = APIRouter(dependencies=[Depends(get_current_user)])


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
