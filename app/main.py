from contextlib import asynccontextmanager
from fastapi import FastAPI
from yookassa import Configuration

from app.core.config import settings
from app.core.limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler


from app.api.bot_api import router as bot_router
from app.api.subscription import router as subscription_router
from app.api.head import head_router
from app.api.payment_webhooks.yookassa import yookassa_router
from app.bot.bot_logic import setup_bot_logic
from app.logger import logger
from database.crud.crud_tariff import load_tariffs_from_json
from database.crud.crud_server import load_servers_from_json


Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_TOKEN


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await load_tariffs_from_json("database/tariffs.json")
        logger.info("Тарифы успешно загружены/обновлены")
    except Exception as e:
        logger.debug(f"Ошибка при загрузке тарифов: {e}")

    try:
        await load_servers_from_json("database/servers.json")
        logger.info("Сервера загружены и обновлены")
    except Exception as e:
        logger.debug(f"Ошибка при загрузке серверов: {e}")

    setup_bot_logic(settings.DP_BOT, settings.BOT)

    await settings.BOT.set_webhook(url=settings.WEBHOOK_BOT_URL, secret_token=settings.WEBHOOK_SECRET)
    logger.info(f"Вебхук установлен на: {settings.WEBHOOK_BOT_URL}")

    yield

    logger.info("Остановка приложения... Удаление вебхука.")
    await settings.BOT.delete_webhook()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


app.include_router(head_router, tags=["Head"]) # TODO можно сделать одностраничник
app.include_router(bot_router, tags=["Telegram Bot"]) # Бот
app.include_router(subscription_router, prefix=settings.SUBSCRIPTION_PATH, tags=["Subscription"]) # Подписки
app.include_router(yookassa_router, tags=["Payment Yookassa"])
