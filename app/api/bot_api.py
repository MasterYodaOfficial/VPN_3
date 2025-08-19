from fastapi import APIRouter, Request, Response
from aiogram import types
from app.logger import logger
from app.core.config import settings


router = APIRouter()


@router.post(settings.WEBHOOK_BOT_PATH)
async def bot_webhook(update: dict, request: Request):
    """
    Принимает вебхуки от Telegram, проверяет секретный токен
    и передает обновление в диспетчер aiogram.
    """
    telegram_secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    if telegram_secret_token != settings.WEBHOOK_SECRET:
        logger.bind(source="bot").warning(
            f"Запрос с неправильным токеном! IP={request.client.host}"
        )
        return Response(status_code=403)
    logger.bind(source="bot").info(
        f"Webhook: update_id={update.get('update_id')}, from={update.get('message', {}).get('from')}"
    )
    logger.bind(source="bot").debug(f"Полный update: {update}")
    telegram_update = types.Update(**update)
    await settings.DP_BOT.feed_update(bot=settings.BOT, update=telegram_update)

    return Response(status_code=200)