import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database.models import Subscription, Tariff, User
from typing import Optional, List
from app.core.config import settings
from sqlalchemy.orm import selectinload
import secrets


def generate_access_key() -> str:
    """Генерирует уникальный и криптографически случайный ключ доступа."""
    return secrets.token_urlsafe(16)

def generate_service_name(user: User) -> str:
    """Генерирует красивое, человекочитаемое имя подписки."""
    # Считаем, сколько у пользователя уже есть подписок, чтобы сделать имя уникальным
    sub_count = len(user.subscriptions) + 1
    # Убираем пробелы из имени пользователя, если они есть
    username = user.username.replace(" ", "") if user.username else str(user.telegram_id)
    return f"QuickVPN-{username}-{sub_count}"



def generate_uuid_name() -> str:
    """Генерация UUID, используемого в качестве идентификатора VLESS-клиента."""
    return str(uuid.uuid4())


async def create_subscription(
    session: AsyncSession,
    user: User,
    tariff_id: int = None,
    uuid_name: str = None,
    promo_id: Optional[int] = None
) -> Subscription:
    start_date = datetime.now()
    if tariff_id:
        result = await session.execute(select(Tariff).where(Tariff.id == tariff_id))
        tariff = result.scalar_one_or_none()
        if not tariff:
            raise ValueError("Тариф не найден")
        end_date = start_date
    else:
        end_date = start_date + timedelta(days=settings.TRIAL_DAYS)

    if not uuid_name:
        uuid_name = generate_uuid_name()
    new_subscription = Subscription(
        telegram_id=user.telegram_id,
        start_date=start_date,
        end_date=end_date,
        is_active=True,
        service_name=generate_service_name(user),
        access_key=generate_access_key(),
        uuid_name=uuid_name,
        tariff_id=tariff_id,
        promo_id=promo_id,
    )

    session.add(new_subscription)
    await session.commit()
    await session.refresh(new_subscription)

    return new_subscription


async def delete_subscription(session: AsyncSession, subscription_id: int):
    subscription = await session.get(Subscription, subscription_id)
    if subscription:
        await session.delete(subscription)
        await session.commit()


async def get_user_subscriptions(session: AsyncSession, telegram_id: int) -> List[Subscription]:
    """Возвращает все подписки пользователя по telegram_id."""
    result = await session.execute(
        select(Subscription).where(Subscription.telegram_id == telegram_id)
    )
    return result.scalars().all()


async def get_subscription_by_id(session: AsyncSession, subscription_id: int) -> Subscription | None:
    """Получает подписку по его id"""
    result = await session.execute(select(Subscription).where(Subscription.id == subscription_id))
    subscription = result.scalars().first()
    return subscription

async def get_subscription_with_configs_by_access_key(session: AsyncSession, access_key: str) -> Optional[Subscription]:
    """Находит подписку и ее конфиги по секрет key."""
    stmt = (
        select(Subscription)
        .options(selectinload(Subscription.configs))
        .where(Subscription.access_key == access_key)
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def count_active_subscriptions(session: AsyncSession) -> int:
    """Считает общее количество активных подписок."""
    result = await session.execute(
        select(func.count(Subscription.id)).where(Subscription.is_active == True)
    )
    return result.scalar_one()