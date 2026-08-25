import hashlib
import hmac
import os

from fastapi import Request
from fastapi.responses import RedirectResponse

from .config import settings


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt), stored)


def check_credentials(username: str, password: str) -> bool:
    if username != settings.admin_username:
        return False
    # 支持明文密码（来自 env）或预置哈希（可选）
    env_hash = os.getenv("ADMIN_PASSWORD_HASH", "")
    if env_hash:
        return verify_password(password, env_hash)
    return hmac.compare_digest(password, settings.admin_password)


class NotAuthenticated(Exception):
    pass


def get_current_user(request: Request) -> str:
    user = request.session.get("user")
    if not user:
        raise NotAuthenticated()
    return user


async def not_authenticated_handler(request: Request, exc: NotAuthenticated):
    return RedirectResponse("/login", status_code=303)
