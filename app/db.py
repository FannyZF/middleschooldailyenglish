from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)
Base = declarative_base()


def _migrate() -> None:
    from sqlalchemy import text

    with engine.begin() as conn:
        cols = {r[1] for r in conn.execute(text("PRAGMA table_info(daily_content)"))}
        if not cols:
            return
        if "word_grade" not in cols:
            conn.execute(
                text("ALTER TABLE daily_content ADD COLUMN word_grade VARCHAR(50) DEFAULT ''")
            )
        if "original_title" not in cols:
            conn.execute(
                text("ALTER TABLE daily_content ADD COLUMN original_title TEXT DEFAULT ''")
            )
        if "pub_date" not in cols:
            conn.execute(
                text("ALTER TABLE daily_content ADD COLUMN pub_date VARCHAR(20) DEFAULT ''")
            )
        if "choices" not in cols:
            if "choice" in cols:
                conn.execute(text("ALTER TABLE daily_content RENAME COLUMN choice TO choices"))
            elif "fill_blank" in cols:
                conn.execute(text("ALTER TABLE daily_content RENAME COLUMN fill_blank TO choices"))
        if "translation" not in cols and "sentence" in cols:
            conn.execute(text("ALTER TABLE daily_content RENAME COLUMN sentence TO translation"))

        s_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(slang_content)"))}
        if s_cols and "caption" not in s_cols:
            conn.execute(
                text("ALTER TABLE slang_content ADD COLUMN caption TEXT DEFAULT ''")
            )


def init_db() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(engine)
    _migrate()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
