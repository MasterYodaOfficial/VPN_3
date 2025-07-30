from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Payment
from database.enums import PaymentMethod
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, and_
from datetime import datetime, timedelta



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


async def get_payment_by_id(session: AsyncSession, payment_id):
    """
    Получает платеж из БД по его id
    :param session:
    :param payment_id:
    :return: Payment из БД
    """
    result = await session.execute(
        select(Payment)
        .options(selectinload(Payment.subscription))
        .options(selectinload(Payment.tariff))
        .where(Payment.id == payment_id)
    )
    return result.scalars().first()


async def get_revenue_for_period(session: AsyncSession, days: int = None) -> int:
    """Считает доход за период (None = за все время)."""
    stmt = select(func.sum(Payment.amount)).where(Payment.status == "success")
    if days:
        start_date = datetime.now() - timedelta(days=days)
        stmt = stmt.where(Payment.created_at >= start_date)

    result = await session.execute(stmt)
    return result.scalar_one_or_none() or 0


async def count_successful_payments_for_period(session: AsyncSession, days: int = None) -> int:
    """Считает количество успешных платежей за период."""
    stmt = select(func.count(Payment.id)).where(Payment.status == "success")
    if days:
        start_date = datetime.now() - timedelta(days=days)
        stmt = stmt.where(Payment.created_at >= start_date)

    result = await session.execute(stmt)
    return result.scalar_one_or_none() or 0