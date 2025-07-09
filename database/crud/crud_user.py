from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.models import User
from core.config import settings
from sqlalchemy.orm import selectinload



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
    inviter_id: Optional[int] = None,
    referral_code: Optional[str] = None,
) -> User:
    user = User(
        telegram_id=telegram_id,
        username=username,
        inviter_id=inviter_id,
        referral_code=referral_code
    )
    if telegram_id in settings.ADMIN_IDS:
        user.is_admin = True
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
