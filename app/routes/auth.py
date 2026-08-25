from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from starlette.status import HTTP_302_FOUND

from ..auth import check_credentials

router = APIRouter()


@router.get("/login")
def login_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/", status_code=HTTP_302_FOUND)
    return request.app.state.templates.TemplateResponse(
        request, "login.html", {"error": None}
    )


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if check_credentials(username, password):
        request.session["user"] = username
        return RedirectResponse("/", status_code=HTTP_302_FOUND)
    return request.app.state.templates.TemplateResponse(
        request, "login.html", {"error": "用户名或密码错误"}
    )


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=HTTP_302_FOUND)
