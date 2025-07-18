from yookassa import Payment
from functools import partial
import asyncio
from bot.utils.logger import logger
from core.config import settings
from yookassa.domain.exceptions import BadRequestError



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



async def cancel_yookassa_payment(payment_id: str) -> bool:
    """
    Отменяет платеж в ЮKassa через официальный SDK
    :param payment_id: ID платежа в ЮKassa
    :return: True если отмена успешна, False если ошибка
    """
    try:
        canceled_payment = await asyncio.to_thread(
            partial(Payment.cancel, payment_id)
        )
        return canceled_payment.status == 'canceled'
    except BadRequestError as e:
        logger.error(f"Ошибка YooKassa при отмене {payment_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отмене {payment_id}: {e}")
        return False
