import random
import string
from typing import Optional
from aiogram.types import Message
from database.session import get_session
from database.models import User
from database.crud.crud_user import get_user_by_telegram_id, get_user_by_referral_code, create_user


def generate_referral_code(length: int = 8) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


async def register_user_service(
    message: Message,
    referral_code: Optional[str] = None
) -> User:
    async with get_session() as session:
        telegram_id = message.from_user.id
        username = message.from_user.first_name

        # Проверяем, есть ли пользователь в базе
        user = await get_user_by_telegram_id(session, telegram_id)
        if user:
            return user

        inviter_id = None
        if referral_code:
            inviter = await get_user_by_referral_code(session, referral_code)
            if inviter:
                inviter_id = inviter.telegram_id

        # Генерируем уникальный referral_code для нового пользователя
        while True:
            new_referral_code = generate_referral_code()
            exists = await get_user_by_referral_code(session, new_referral_code)
            if not exists:
                break

        # Создаем пользователя
        user = await create_user(
            session=session,
            telegram_id=telegram_id,
            username=username,
            inviter_id=inviter_id,
            referral_code=new_referral_code,
        )
        return user
