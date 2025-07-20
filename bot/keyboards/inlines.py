from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.config import settings
from database.models import Subscription, Tariff
from typing import List
from database.crud.crud_tariff import get_active_tariffs



def profile_buttons(active_subscriptions_count: int, has_trial: bool) -> InlineKeyboardMarkup:
    """Кнопки для команды профайл"""
    kb = InlineKeyboardBuilder()
    if has_trial:
        kb.button(text="🎁 Получить промо подписку", callback_data="profile:trial")
    kb.button(text="➕ Купить новую подписку", callback_data="profile:new_sub")
    if active_subscriptions_count > 0:
        kb.button(text="🔁 Продлить подписку", callback_data="profile:extend")
        kb.button(text="⚙️ Получить действующий конфиг", callback_data="profile:get_conf")
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

def active_subscriptions_buttons(sub_list: List[Subscription]) -> InlineKeyboardMarkup:
    """Формирует кнопки активных подписок"""
    kb = InlineKeyboardBuilder()
    for sub in sub_list:
        server_name = sub.service_name
        expires = sub.end_date.strftime("%d.%m.%y")
        label = f"🛡️ {server_name} • до {expires}"
        kb.button(
            text=label,
            callback_data=f"renew:{sub.id}"
        )
    kb.adjust(1)
    return kb.as_markup()

def payments_buttons() -> InlineKeyboardMarkup:
    """Формирует кнопки для оплаты подгружая фактический с .env"""
    kb = InlineKeyboardBuilder()
    if settings.YOOKASSA_TOKEN:
        kb.button(text="💸 Оплата ЮKassa", callback_data="pay:yookassa")
    if settings.CRYPTO_TOKEN:
        kb.button(text="🧾 Крипто-оплата", callback_data="pay:crypto")
    kb.adjust(1)
    return kb.as_markup()

def tariff_buttons(tariffs: List[Tariff]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for tariff in tariffs:
        button_text = f"{tariff.name} — {tariff.price}₽"
        kb.button(
            text=button_text,
            callback_data=f"choose_tariff:{tariff.id}"
        )
    kb.adjust(1)
    return kb.as_markup()

def make_pay_link_button(url: str) -> InlineKeyboardMarkup:
    """Кнопка оплатить"""
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Оплатить", url=url)
    return kb.as_markup()

def tariff_buttons_buy(tariffs: List[Tariff]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for tariff in tariffs:
        button_text = f"{tariff.name} — {tariff.price}₽"
        kb.button(
            text=button_text,
            callback_data=f"buy_tariff:{tariff.id}"
        )
    kb.adjust(1)
    return kb.as_markup()