from contextlib import asynccontextmanager
from fastapi import FastAPI
from yookassa import Configuration

from app.core.config import settings
from app.core.limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler


from app.api.bot_api import router as bot_router
from app.api.head import head_router
from app.api.media import media_router
from app.api.payment_webhooks.yookassa import yookassa_router
from app.api.remnawave_webhook import remna_webhook_router
from app.bot.bot_logic import setup_bot_logic
from app.logger import logger
from app.services.tariff_service import tariff_service


Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_TOKEN


@asynccontextmanager
async def lifespan(app: FastAPI):

    await tariff_service.load_and_sync_tariffs("database/tariffs.json")

    setup_bot_logic(settings.DP_BOT, settings.BOT)

    await settings.BOT.set_webhook(
        url=settings.WEBHOOK_BOT_URL,
        secret_token=settings.WEBHOOK_SECRET,
        allowed_updates=[
            "message",
            "callback_query",
            "pre_checkout_query",
            "chat_member",
            "my_chat_member"
        ]
    )
    logger.bind(source="bot").info(f"Вебхук установлен на: {settings.WEBHOOK_BOT_PATH} + secret")
    stats = await settings.REMNA_SDK.system.get_stats()
    # Если запрос успешен, выводим полезную информацию
    total_users = stats.users.total_users
    total_nodes = stats.nodes.total_online
    logger.info(f"✅ Успешное подключение к Remnawave. "
                f"Всего пользователей в панели: {total_users}\n"
                f"Нод онлайн: {total_nodes}")

    yield

    logger.bind(source="bot").info("Остановка приложения... Удаление вебхука.")
    await settings.BOT.delete_webhook()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


app.include_router(head_router, tags=["Head"]) # TODO.md можно сделать одностраничник
app.include_router(bot_router, tags=["Telegram Bot"]) # Бот
app.include_router(yookassa_router, tags=["Payment Yookassa"])
app.include_router(media_router)
app.include_router(remna_webhook_router, tags=["Remnawave Webhooks"])
