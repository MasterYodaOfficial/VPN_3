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
        user_from_tg = message.from_user

        # Проверяем, есть ли пользователь в базе
        user = await get_user_by_telegram_id(session, telegram_id)
        if user:
            # ---> ЛОГИКА ОБНОВЛЕНИЯ ДЛЯ СУЩЕСТВУЮЩЕГО ПОЛЬЗОВАТЕЛЯ <---
            should_commit = False
            # Обновляем first_name, если он изменился
            if user.username != user_from_tg.first_name:
                user.username = user_from_tg.first_name
                should_commit = True
            # Обновляем @username (link), если он изменился
            if user.link != user_from_tg.username:
                user.link = user_from_tg.username
                should_commit = True

            if should_commit:
                await session.commit()

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
            link=user_from_tg.username,
            inviter_id=inviter_id,
            referral_code=new_referral_code
        )
        return user
