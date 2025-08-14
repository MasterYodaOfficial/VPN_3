from loguru import logger
import sys
from pathlib import Path


log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logger.remove()


logger.add(sys.stdout, level="DEBUG")


logger.add(
    log_dir / "bot_log_{time:YYYY-MM-DD}.log",
    rotation="00:00",           # каждый день в полночь
    retention="7 days",         # хранить минимум 7 дней
    compression="zip",          # архивировать старые логи
    level="DEBUG"
)