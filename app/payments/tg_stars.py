from database.models import Tariff
from app.core.config import settings
from aiogram.types import LabeledPrice
import math
import uuid


def convert_rub_to_stars(rub_price: int) -> int:
    """
    Конвертирует цену в рублях в Telegram Stars по курсу из настроек.
    Округляет результат до ближайшего целого числа вверх.
    """
    if settings.RUB_PER_STAR <= 0:
        return rub_price * 100
    stars_float = rub_price / settings.RUB_PER_STAR
    return math.ceil(stars_float)


async def create_payment_tg_stars(tariff: Tariff):
    """Формирует ссылку на оплату звездами"""
    stars_amount = convert_rub_to_stars(tariff.price)
    external_id= str(uuid.uuid4())
    invoice_link = await settings.BOT.create_invoice_link(
        title=f"{settings.LOGO_NAME}",
        description=f"Тариф: {tariff.name} ({tariff.duration_days} дней)",
        payload=external_id,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"Telegram Stars", amount=stars_amount)]
    )
    return external_id, invoice_link