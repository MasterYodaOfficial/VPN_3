from typing import Dict, Any, Callable, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.utils.i18n import I18n

from app.core.config import settings
from database.models import User
from database.session import get_session

i18n = I18n(path=settings.LOCALES_DIR, default_locale=settings.DEFAULT_LANGUAGE, domain="messages")


class I18nMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")

        if not user:
            user_locale = settings.DEFAULT_LANGUAGE
        else:
            async with get_session() as session:
                db_user = await User.get_by_telegram_id(session, user.id)
                user_locale = db_user.language_code if db_user else user.language_code

        if user_locale not in i18n.available_locales:
            user_locale = settings.DEFAULT_LANGUAGE

        # 1. Устанавливаем текущую локаль для объекта i18n
        i18n.current_locale = user_locale
        # 2. Передаем сам объект i18n в хендлеры
        data["i18n"] = i18n
        # 3. Активируем контекст БЕЗ аргументов
        with i18n.context():
            return await handler(event, data)


i18n_middleware = I18nMiddleware()