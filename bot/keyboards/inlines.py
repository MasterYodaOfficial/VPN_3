from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.config import settings


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

def referral_share_button(referral_code: str) -> InlineKeyboardMarkup:
    """Кнопка поделиться реферальной ссылкой"""
    kb = InlineKeyboardBuilder()

    link = f"https://t.me/{settings.BOT_NAME}?start={referral_code}"
    share_url = f"https://t.me/share/url?url={link}&text=🚀 Попробуй QuickVPN — анонимный и быстрый VPN. Подключи за 2 минуты!"

    kb.button(text="📲 Поделиться ссылкой", url=share_url)
    kb.adjust(1)
    return kb.as_markup()