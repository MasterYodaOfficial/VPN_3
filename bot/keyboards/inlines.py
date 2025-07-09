from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder



def profile_buttons(active_subscriptions_count: int, has_trial: bool) -> InlineKeyboardMarkup:
    """Кнопки для команды профайл"""
    kb = InlineKeyboardBuilder()
    if has_trial:
        kb.button(text="🎁 Получить промо подписку", callback_data="profile:trial")
    kb.button(text="➕ Купить новую подписку", callback_data="profile:new_sub")
    if active_subscriptions_count > 0:
        kb.button(text="🔁 Продлить подписку", callback_data="profile:extend")
        kb.button(text="♻️ Обновить конфиги", callback_data="profile:refresh")
    kb.adjust(1)
    return kb.as_markup()