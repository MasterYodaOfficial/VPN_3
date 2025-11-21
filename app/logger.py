from loguru import logger
import logging
import sys
from pathlib import Path

# --- Директории ---
log_root = Path("logs")
(bot_dir := log_root / "bot").mkdir(parents=True, exist_ok=True)
(api_dir := log_root / "api").mkdir(parents=True, exist_ok=True)
(payments_dir := log_root / "payments_gateways").mkdir(parents=True, exist_ok=True)
(access_dir := log_root / "access").mkdir(parents=True, exist_ok=True)
(errors_dir := log_root / "errors").mkdir(parents=True, exist_ok=True)

(uvicorn_dir := log_root / "uvicorn").mkdir(parents=True, exist_ok=True)
(httpx_dir := log_root / "httpx").mkdir(parents=True, exist_ok=True)

logger.remove()

# Общий stdout только для INFO и выше
logger.add(sys.stdout, level="INFO", colorize=True)

# --- Файлы ---
logger.add(
    bot_dir / "bot_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="7 days",
    compression="zip",
    level="DEBUG",
    filter=lambda record: record["extra"].get("source") == "bot"
)

logger.add(
    api_dir / "api_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="7 days",
    compression="zip",
    level="DEBUG",
    filter=lambda record: record["extra"].get("source") == "api"
)

logger.add(
    payments_dir / "yookassa_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="7 days",
    compression="zip",
    level="DEBUG",
    filter=lambda record: record["extra"].get("source") == "yookassa"
)

logger.add(
    access_dir / "access_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="7 days",
    compression="zip",
    level="INFO",
    filter=lambda record: record["extra"].get("source") == "access"
)

# --- Общий errors.log для всех ERROR+ ---
logger.add(
    errors_dir / "errors_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="14 days",
    compression="zip",
    level="ERROR"
)

logger.add("logs/all_logs_{time:YYYY-MM-DD}.log",
           rotation="00:00",
           retention="7 days",
           compression="zip",
           level="DEBUG")

logger.add(
    uvicorn_dir / "uvicorn_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="7 days",
    compression="zip",
    level="DEBUG",
    filter=lambda r: r["extra"].get("source") == "uvicorn"
)

logger.add(
    httpx_dir / "httpx_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="7 days",
    compression="zip",
    level="DEBUG",
    filter=lambda r: r["extra"].get("source") == "httpx"
)

# --- Перехват стандартного logging в loguru ---
class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except Exception:
            level = record.levelno
        logger.bind(source=record.name.split(".")[0]).opt(
            depth=6, exception=record.exc_info
        ).log(level, record.getMessage())

# --- Подключаем перехватчик ---
logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
logging.getLogger("uvicorn").handlers = [InterceptHandler()]
logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]
logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
logging.getLogger("httpx").handlers = [InterceptHandler()]


logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)