from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Payment
from database.enums import PaymentMethod


async def create_payment(
        session: AsyncSession,
        user_id: int,
        amount: int,
        subscription_id: int,
        tariff_id: int,
        currency: str = "RUB",
        method: PaymentMethod = PaymentMethod.yookassa,
        external_payment_id: str | None = None,
) -> Payment:
    """
    Создаёт запись об оплате в БД.

    :param session: Асинхронная сессия SQLAlchemy
    :param user_id: Telegram ID пользователя
    :param amount: Сумма оплаты
    :param currency: Валюта (по умолчанию RUB)
    :param method: Метод оплаты (enum PaymentMethod)
    :param subscription_id: Id на которой продлиться подписка
    :param tariff_id: Id тарифа
    :param external_payment_id: ID оплаты в сторонней системе (если есть)
    :return: Объект Payment
    """

    payment = Payment(
        user_id=user_id,
        amount=amount,
        currency=currency,
        method=method,
        tariff_id=tariff_id,
        external_payment_id=external_payment_id,
        subscription_id=subscription_id,
        status="pending",
    )

    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment
