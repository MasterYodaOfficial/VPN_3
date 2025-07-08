from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.models import User


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalars().first()


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
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def register_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    referral_code: Optional[str] = None,
) -> User:
    # Проверяем есть ли пользователь в базе
    user = await get_user_by_telegram_id(session, telegram_id)
    if user:
        return user

    inviter_id = None
    if referral_code:
        inviter = await get_user_by_referral_code(session, referral_code)
        if inviter:
            inviter_id = inviter.telegram_id

    # Генерация уникального referral_code для нового пользователя
    # Простая генерация, можно заменить на что-то более надежное
    import random, string
    def generate_referral_code(length=8):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    # Убедимся, что referral_code уникальный
    while True:
        new_referral_code = generate_referral_code()
        exists = await get_user_by_referral_code(session, new_referral_code)
        if not exists:
            break

    return await create_user(
        session=session,
        telegram_id=telegram_id,
        username=username,
        inviter_id=inviter_id,
        referral_code=new_referral_code
    )
