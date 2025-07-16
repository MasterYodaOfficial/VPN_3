from bot.utils.messages import subscription_renewed_message
from database.models import Payment, Tariff, Subscription
from aiogram.types import User as User_tg
from database.crud.crud_payment import create_payment
from database.crud.crud_tariff import get_tariff_by_id
from database.crud.crud_subscription import get_subscription_by_id
from database.enums import PaymentMethod
from bot.payments.yookassa import create_payment_yookassa
from database.session import get_session
from bot.utils.logger import logger
import asyncio
from yookassa import Payment as YooPayment



async def create_payment_service(
        user: User_tg,
        tariff_id: int,
        sub_id:int,
        method: str
) -> tuple[Payment, Tariff, Subscription, str] | None:

    """
    Создаёт платёж через нужную платёжную систему, сохраняет его в БД и возвращает объект и ссылку на оплату.
    """
    try:
        async with get_session() as session:
            tariff: Tariff = await get_tariff_by_id(session, tariff_id)
            subscription: Subscription = await get_subscription_by_id(session, sub_id)
            if PaymentMethod.yookassa == method:
                method = PaymentMethod(method)
                external_id, payment_url = await create_payment_yookassa(tariff.price, tariff.name)
            if PaymentMethod.crypto == method:
                raise ValueError("Need add to payment crypto") # TODO Добавить оплату криптой
            payment: Payment = await create_payment(
                session=session,
                user_id=user.id,
                amount=tariff.price,
                method=method,
                tariff_id=tariff.id,
                subscription_id=sub_id,
                external_payment_id=external_id
            )
            return payment, tariff, subscription, payment_url
    except BaseException as ex:
        logger.error(f"Ошибка в создании платежа {ex}")
        return None


async def get_payment_status(payment: Payment):
    """
    Проверяет статус платежа по его id
    """
    method = payment.method
    external_id = payment.external_payment_id

    if method == "yookassa":
        yoo_payment = await asyncio.to_thread(YooPayment.find_one, external_id)
        status = yoo_payment.status
        if status == "succeeded":
            return "paid"
        if status in ['canceled', 'failed']:
            return "failed"
    if method == "crypto":
        pass
        # TODO сделать проверку крипты