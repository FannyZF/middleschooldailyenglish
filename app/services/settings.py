from .. import models
from ..db import SessionLocal


def get_setting(key: str, default: str = "") -> str:
    db = SessionLocal()
    try:
        row = db.query(models.Setting).filter(models.Setting.key == key).first()
        return row.value if row else default
    finally:
        db.close()


def set_setting(key: str, value: str) -> None:
    db = SessionLocal()
    try:
        row = db.query(models.Setting).filter(models.Setting.key == key).first()
        if row:
            row.value = value
        else:
            db.add(models.Setting(key=key, value=value))
        db.commit()
    finally:
        db.close()


def get_all_settings() -> dict:
    db = SessionLocal()
    try:
        return {r.key: r.value for r in db.query(models.Setting).all()}
    finally:
        db.close()
