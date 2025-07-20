from database.models import Payment, Tariff, Subscription
from aiogram.types import User as User_tg
from database.crud.crud_payment import create_payment, get_payment_by_id
from database.crud.crud_tariff import get_tariff_by_id
from database.crud.crud_subscription import get_subscription_by_id, create_subscription
from database.enums import PaymentMethod
from bot.payments.yookassa import create_payment_yookassa, cancel_yookassa_payment
from database.session import get_session
from bot.utils.logger import logger
import asyncio
from yookassa import Payment as YooPayment
from datetime import timedelta



async def create_payment_service(
        user: User_tg,
        tariff_id: int,
        method: str,
        sub_id: int = None,
) -> tuple[Payment, Tariff, Subscription, str] | None:

    """
    Создаёт платёж через нужную платёжную систему, сохраняет его в БД и возвращает объект и ссылку на оплату.
    """
    try:
        async with get_session() as session:
            tariff: Tariff = await get_tariff_by_id(session, tariff_id)
            if sub_id:
                subscription: Subscription = await get_subscription_by_id(session, sub_id)
            else:
                subscription: Subscription = await create_subscription(
                    session=session,
                    telegram_id=user.id,
                    tariff_id=tariff_id
                )
                sub_id = subscription.id

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
            await session.commit()
            await session.refresh(payment)
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


async def confirm_payment_service(payment_id: int) -> bool:
    """
    Подтверждает оплату, продлевает подписку на количество дней согласно тарифу.
    :param payment_id: ID платежа
    :return: True, если операция успешна, иначе False
    """
    async with get_session() as session:
        # Получаем платеж
        payment: Payment = await get_payment_by_id(session, payment_id)
        payment.status = "success"
        subscription = payment.subscription
        tariff = payment.tariff
        subscription.end_date += timedelta(days=tariff.duration_days)
        await session.commit()
        return True

async def error_payment_service(payment_id: int) -> bool:
    """
    Сменяет статус платежа на ошибку.
    :param payment_id:
    :return:
    """
    async with get_session() as session:
        payment: Payment = await get_payment_by_id(session, payment_id)
        # Отмена в зависимости от метода оплаты в платежной системе
        if payment.method == PaymentMethod.yookassa:
            try:
                if payment.external_payment_id:
                    await cancel_yookassa_payment(payment.external_payment_id)
            except Exception as e:
                logger.error(f"Ошибка при отмене платежа {payment_id} в ЮKassa: {e}")
                return False
        if payment.method == PaymentMethod.crypto:
            # TODO Сделать отмену для крипты
            pass
        payment.status = "failed"
        await session.commit()
        return True