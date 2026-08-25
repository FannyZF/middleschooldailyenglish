import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import settings
from .services.pipeline import generate_today
from .services.settings import get_setting

logger = logging.getLogger("scheduler")

_scheduler: BackgroundScheduler | None = None

DEFAULT_CRON = "0 6 * * *"


def time_to_cron(time_str: str) -> str:
    try:
        h, m = time_str.strip().split(":")
        h, m = int(h), int(m)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return f"{m} {h} * * *"
    except (ValueError, AttributeError):
        pass
    return ""


def cron_to_time(cron: str) -> str:
    parts = (cron or "").split()
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        return f"{int(parts[1]):02d}:{int(parts[0]):02d}"
    return "06:00"


def is_valid_cron(cron: str) -> bool:
    try:
        CronTrigger.from_crontab(cron.strip())
        return True
    except Exception:
        return False


def _job() -> None:
    try:
        generate_today()
        logger.info("每日内容生成完成")
    except Exception as e:
        logger.exception("每日内容生成失败: %s", e)


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return

    cron = (get_setting("schedule_cron") or settings.schedule_cron or DEFAULT_CRON).strip()
    if not is_valid_cron(cron):
        logger.warning("无效的 cron 表达式 %r，回退到默认 %s", cron, DEFAULT_CRON)
        cron = DEFAULT_CRON

    try:
        _scheduler = BackgroundScheduler(timezone=settings.timezone)
        _scheduler.add_job(
            _job, CronTrigger.from_crontab(cron, timezone=settings.timezone)
        )
        _scheduler.start()
        logger.info("定时任务已启动: %s (%s)", cron, settings.timezone)
    except Exception:
        _scheduler = None
        logger.exception("定时任务启动失败")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None


def reload_scheduler() -> None:
    stop_scheduler()
    start_scheduler()
