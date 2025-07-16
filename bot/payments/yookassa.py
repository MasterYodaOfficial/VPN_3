from yookassa import Payment
from functools import partial
import asyncio
from bot.utils.logger import logger
from core.config import settings


async def create_payment_yookassa(price: str, description: str) -> tuple[str, str] | None:
    """
    Создает платеж юкасса.
    """
    payload = {
    "amount": {
        "value": f"{price}",
        "currency": "RUB"
    },
    "confirmation": {
        "type": "redirect",
        "return_url": f"https://t.me/{settings.BOT_NAME}" # https://t.me/ImageTester_bot
    },
    "capture": True,
    "description": f" Оплата тарифа {description}"
    }
    try:
        payment = await asyncio.to_thread(
            partial(
            Payment.create,
            payload
            )
        )
        external_id = payment.id
        payment_url = payment.confirmation.confirmation_url

        return external_id, payment_url
    except BaseException as ex:
        logger.exception(ex)
        return None