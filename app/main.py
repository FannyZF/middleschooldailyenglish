import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .auth import NotAuthenticated, not_authenticated_handler
from .config import settings
from .db import init_db
from .routes import admin, auth, content

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if os.getenv("START_SCHEDULER", "1") == "1":
        from .scheduler import start_scheduler

        start_scheduler()
    yield
    if os.getenv("START_SCHEDULER", "1") == "1":
        from .scheduler import stop_scheduler

        stop_scheduler()


app = FastAPI(title="每日英语学习", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie=settings.session_cookie_name,
    max_age=settings.session_max_age,
)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.state.templates = templates

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.add_exception_handler(NotAuthenticated, not_authenticated_handler)

app.include_router(auth.router)
app.include_router(content.router)
app.include_router(admin.router)
