from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.models import User
from app.core.config import settings
from sqlalchemy.orm import selectinload, aliased
from typing import List
from sqlalchemy import func
from datetime import datetime, timedelta



async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(
        select(User)
        .options(
            selectinload(User.subscriptions),
            selectinload(User.invited_users),
            selectinload(User.inviter),
        )
        .where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()



async def get_user_by_referral_code(session: AsyncSession, referral_code: str) -> Optional[User]:
    result = await session.execute(select(User).where(User.referral_code == referral_code))
    return result.scalars().first()


async def create_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    link: Optional[str] = None,
    inviter_id: Optional[int] = None,
    referral_code: Optional[str] = None,
    has_trial: bool = True
) -> User:
    if settings.TRIAL_DAYS == 0:
        has_trial = False
    user = User(
        telegram_id=telegram_id,
        username=username,
        inviter_id=inviter_id,
        referral_code=referral_code,
        has_trial=has_trial
    )
    if telegram_id in settings.ADMIN_IDS:
        user.is_admin = True
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_all_telegram_ids(session: AsyncSession) -> List[int]:
    """Возвращает список всех telegram_id пользователей из базы данных."""
    stmt = select(User.telegram_id)
    result = await session.execute(stmt)
    return result.scalars().all()

async def is_admin(user: User) -> bool:
    """Проверяет, является ли пользователь админом."""
    return user.is_admin


async def count_users(session: AsyncSession) -> int:
    """Считает общее количество пользователей."""
    result = await session.execute(select(func.count(User.telegram_id)))
    return result.scalar_one()

async def count_new_users_for_period(session: AsyncSession, days: int) -> int:
    """Считает новых пользователей за последние N дней."""
    start_date = datetime.now() - timedelta(days=days)
    result = await session.execute(
        select(func.count(User.telegram_id)).where(User.created_at >= start_date)
    )
    return result.scalar_one()


async def get_top_referrers(session: AsyncSession, limit: int = 5) -> List[User]:
    """Возвращает топ N пользователей по количеству приглашенных."""

    # ---> ИСПРАВЛЕННАЯ ЛОГИКА ЗАПРОСА <---

    # Создаем псевдоним (alias) для таблицы User, чтобы различать приглашающих и приглашенных
    InvitedUser = aliased(User)

    # Формируем запрос
    stmt = (
        select(
            User,
            func.count(InvitedUser.telegram_id).label('referral_count')
        )
        .outerjoin(InvitedUser, User.telegram_id == InvitedUser.inviter_id)
        .group_by(User.telegram_id)
        .order_by(func.count(InvitedUser.telegram_id).desc())
        .limit(limit)
    )

    result = await session.execute(stmt)
    # result теперь содержит кортежи (User, referral_count), нам нужен только User
    top_users = [user for user, count in result.all()]

    # Дополнительно загружаем relationship, чтобы в хендлере len(user.invited_users) работало
    for user in top_users:
        await session.refresh(user, ['invited_users'])

    return top_users