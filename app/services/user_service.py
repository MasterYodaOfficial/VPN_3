import random
import string
from typing import Optional

from aiogram.types import Message
from app.core.config import settings
from app.logger import logger

from database.models import User
from database.session import get_session
from app.bot.middlewares.i18n import i18n


def _generate_referral_code(length: int = 8) -> str:
    """Вспомогательная функция для генерации реферального кода."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


class UserService:
    """
    Класс-сервис для управления бизнес-логикой, связанной с пользователями.
    Использует методы моделей (Active Record) для взаимодействия с БД.
    """

    async def register_or_update_user(
            self,
            message: Message,
            referral_code: Optional[str] = None
    ) -> User:
        """
        Регистрирует нового пользователя или обновляет данные существующего.
        Это основной метод для обработки первого контакта пользователя с ботом.

        :param message: Объект сообщения от пользователя.
        :param referral_code: Опциональный реферальный код из команды /start.
        :return: Объект User из БД (созданный или обновленный).
        """
        async with get_session() as session:
            user_from_tg = message.from_user

            # 1. Пытаемся найти пользователя в нашей БД
            user = await User.get_by_telegram_id(session, user_from_tg.id)

            if user:
                # 2. Если пользователь найден - обновляем его данные, если они изменились
                update_data = {}
                if user.username != user_from_tg.first_name:
                    update_data['username'] = user_from_tg.first_name
                if user.link != user_from_tg.username:
                    update_data['link'] = user_from_tg.username
                update_data["is_active"] = True
                if update_data:
                    logger.info(f"Обновление данных для пользователя {user.telegram_id}: {update_data}")
                    await user.update(session, **update_data)

                return user

            # 3. Если пользователь не найден - создаем нового
            logger.info(f"Регистрация нового пользователя: {user_from_tg.id} ({user_from_tg.first_name})")
            inviter_id = None
            if referral_code:
                inviter = await User.get_by_referral_code(session, referral_code)
                if inviter:
                    inviter_id = inviter.telegram_id
                    logger.info(f"Пользователь {user_from_tg.id} пришел по приглашению от {inviter_id}")

            # Генерируем уникальный реферальный код для новичка
            while True:
                new_referral_code = _generate_referral_code()
                if not await User.get_by_referral_code(session, new_referral_code):
                    break

            # Создаем пользователя, используя метод модели
            lang_code = user_from_tg.language_code
            if lang_code not in i18n.available_locales: # Проверяем по списку доступных
                lang_code = settings.DEFAULT_LANGUAGE
            new_user = await User.create(
                session=session,
                telegram_id=user_from_tg.id,
                username=user_from_tg.first_name,
                link=user_from_tg.username,
                inviter_id=inviter_id,
                referral_code=new_referral_code,
                language_code=lang_code,
                is_admin=(user_from_tg.id in settings.ADMIN_IDS),  # Сразу назначаем админа
                has_trial=(settings.TRIAL_DAYS > 0)  # Устанавливаем флаг триала на основе настроек
            )
            return new_user



user_service = UserService()