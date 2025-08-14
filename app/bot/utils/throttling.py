from collections import defaultdict
import time
from typing import Callable, Dict, Any

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from app.logger import logger



class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, limit: float = 0.5, key_prefix: str = 'antiflood_'):
        self.limit = limit
        self.key_prefix = key_prefix
        self.user_calls = defaultdict(list)
        super().__init__()

    async def __call__(
        self,
        handler: Callable,
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ):
        user_id = event.from_user.id
        current_time = time.time()

        action = "message" if isinstance(event, Message) else "callback"
        key = f"{self.key_prefix}_{user_id}_{action}"

        if key in self.user_calls:
            time_diff = current_time - self.user_calls[key][-1]
            if time_diff < self.limit:
                await self.handle_throttle(event)
                return  # пропускаем хендлер

        self.user_calls[key].append(current_time)

        # Чистим лишние записи
        if len(self.user_calls[key]) > 10:
            self.user_calls[key] = self.user_calls[key][-5:]

        return await handler(event, data)

    async def handle_throttle(self, event: Message | CallbackQuery):
        if isinstance(event, Message):
            logger.warning(f"Spam {event.from_user.id} {event.from_user.first_name}")
            await event.answer("⚠️ Слишком много запросов! Пожалуйста, подождите.")
        elif isinstance(event, CallbackQuery):
            logger.warning(f"Spam {event.from_user.id} {event.from_user.first_name}")
            await event.answer("⏳ Не так быстро! Подождите немного.", show_alert=True)