import os
import logging
import pathlib
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime


def _load_dotenv_if_missing():
    if os.getenv("BOT_TOKEN"):
        return

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    dotenv_path = repo_root / ".env"
    if not dotenv_path.exists():
        return

    try:
        for raw in dotenv_path.read_text(encoding="utf8").splitlines():
            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            if "=" not in s:
                continue
            key, val = s.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            os.environ.setdefault(key, val)
    except Exception:
        return


_load_dotenv_if_missing()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
    
    TAPO_EMAIL = os.getenv("TAPO_EMAIL")
    TAPO_PASSWORD = os.getenv("TAPO_PASSWORD")
    DEVICE_IP = os.getenv("DEVICE_IP")
    
    CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "30"))
    CONFIRMATION_CHECKS = int(os.getenv("CONFIRMATION_CHECKS", "2"))
    TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
    TIMEZONE = os.getenv("TIMEZONE", "Europe/Kyiv")
    
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "powerbot")
    DB_USER = os.getenv("DB_USER", "powerbot")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "powerbot")

    # Sentry configuration
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", "production")
    SENTRY_TRACES_SAMPLE_RATE = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))

# Logging setup with daily rotation
def setup_logging():
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    log_dir = repo_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Format: bot_YYYY-MM-DD.log
    log_file = log_dir / f"bot_{datetime.now().strftime('%Y-%m-%d')}.log"
    
    # Formatting setup
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File handler with daily rotation
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when='midnight',
        interval=1,
        backupCount=30,  # Keep logs for 30 days
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Root logger setup
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

setup_logging()
logger = logging.getLogger(__name__)
