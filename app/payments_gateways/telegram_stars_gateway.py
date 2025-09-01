import math
import uuid
from typing import Optional, Tuple

from aiogram.types import LabeledPrice

from app.core.config import settings
from database.models import Tariff
from .base_gateway import BaseGateway


class TelegramStarsGateway(BaseGateway):
    """Платежный шлюз для Telegram Stars."""

    @staticmethod
    def _convert_rub_to_stars(rub_price: int) -> int:
        if settings.RUB_PER_STAR <= 0:
            return rub_price * 100
        return math.ceil(rub_price / settings.RUB_PER_STAR)

    async def create_payment(
            self,
            tariff: Tariff
    ) -> Optional[Tuple[str, str]]:
        """Создает инвойс для оплаты через Telegram Stars."""
        stars_amount = self._convert_rub_to_stars(tariff.price)
        external_id = str(uuid.uuid4())

        try:
            invoice_link = await settings.BOT.create_invoice_link(
                title=f"{settings.LOGO_NAME}",
                description=f"Тариф: {tariff.name} ({tariff.duration_days} дней)",
                payload=external_id,
                currency="XTR",
                prices=[LabeledPrice(label=f"{tariff.name}", amount=stars_amount)]
            )
            return external_id, invoice_link
        except Exception as e:
            logger.error(f"Ошибка при создании инвойса для Telegram Stars: {e}")
            return None
