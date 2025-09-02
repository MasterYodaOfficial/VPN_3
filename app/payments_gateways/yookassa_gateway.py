from functools import partial
import asyncio
from typing import Optional, Tuple

from yookassa import Payment

from app.logger import logger
from app.core.config import settings
from database.models import Tariff
from .base_gateway import BaseGateway


class YooKassaGateway(BaseGateway):
    """Платежный шлюз для YooKassa."""

    async def create_payment(self, tariff: Tariff) -> Optional[Tuple[str, str]]:
        """Создает платеж в ЮKassa."""
        payload = {
            "amount": {
                "value": str(tariff.price),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": f"https://t.me/{settings.BOT_NAME}"
            },
            "capture": True,
            "description": f"Оплата подписки '{tariff.name}'"
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