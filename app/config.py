import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    def __init__(self):
        self.base_dir = BASE_DIR

        self.data_dir = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
        self.font_dir = Path(os.getenv("FONT_DIR", str(BASE_DIR / "fonts")))
        self.images_dir = self.data_dir / "images"
        self.db_path = Path(os.getenv("DB_PATH", str(self.data_dir / "app.db")))

        self.secret_key = os.getenv("SECRET_KEY", "please-change-me")
        self.admin_username = os.getenv("ADMIN_USERNAME", "admin")
        self.admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

        self.schedule_cron = os.getenv("SCHEDULE_CRON", "0 6 * * *")
        self.timezone = os.getenv("TIMEZONE", "Asia/Shanghai")

        self.reddit_client_id = os.getenv("REDDIT_CLIENT_ID", "")
        self.reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
        self.reddit_username = os.getenv("REDDIT_USERNAME", "")
        self.reddit_password = os.getenv("REDDIT_PASSWORD", "")

        self.session_cookie_name = "nes_session"
        self.session_max_age = 60 * 60 * 24 * 7

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
