from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.config import settings
from database.models import Subscription, Tariff
from typing import List
from database.crud.crud_tariff import get_active_tariffs



def get_config_webapp_button(webapp_url: str) -> InlineKeyboardMarkup:
    """Создает кнопку для открытия Web App с конфигурацией."""
    buttons = [
        [InlineKeyboardButton(text="📲 Получить конфигурацию", web_app=WebAppInfo(url=webapp_url))]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def profile_buttons(active_subscriptions_count: int, has_trial: bool) -> InlineKeyboardMarkup:
    """Кнопки для команды профайл"""
    kb = InlineKeyboardBuilder()
    if has_trial:
        kb.button(text="🎁 Получить промо подписку", callback_data="profile:trial")
    kb.button(text="➕ Купить новую подписку", callback_data="profile:new_sub")
    if active_subscriptions_count > 0:
        kb.button(text="🔁 Продлить подписку", callback_data="profile:extend")
        kb.button(text="⚙️ Получить действующие конфиги", callback_data="profile:get_conf")
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

def help_menu_buttons() -> InlineKeyboardMarkup:
    """Кнопки для главного меню /help."""
    kb = InlineKeyboardBuilder()
    kb.button(text="📱 Инструкции по установке", callback_data="help:install")
    kb.button(text="❓ Частые вопросы (FAQ)", callback_data="help:faq")
    kb.button(text="🗣️ Связаться с поддержкой", url=f"https://t.me/{settings.SUPPORT_NAME}")
    kb.adjust(1)
    return kb.as_markup()

def install_menu_buttons() -> InlineKeyboardMarkup:
    """Кнопки для выбора платформы в разделе инструкций."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🤖 Android", callback_data="install:android")
    kb.button(text="🍏 iOS", callback_data="install:ios")
    kb.button(text="💻 Windows / macOS", callback_data="install:desktop")
    kb.button(text="⬅️ Назад в меню помощи", callback_data="install:back_to_help")
    kb.adjust(1)
    return kb.as_markup()

def extend_subscription_button() -> InlineKeyboardMarkup:
    """Кнопка, ведущая в меню продления подписки."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔁 Продлить сейчас", callback_data="profile:extend")
    return kb.as_markup()