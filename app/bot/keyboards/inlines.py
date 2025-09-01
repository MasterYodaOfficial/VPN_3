from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.core.config import settings
from database.models import Subscription, Tariff
from typing import List
from aiogram.utils.i18n import gettext as _

def user_subscriptions_webapp_buttons(sub_list: List[Subscription]) -> InlineKeyboardMarkup:
    """
    Формирует клавиатуру со списком активных подписок пользователя.
    Для каждой подписки создается кнопка, открывающая Web App.
    """
    kb = InlineKeyboardBuilder()

    # Проходимся по каждой подписке из списка
    for sub in sub_list:

        expires_date = sub.end_date.strftime("%d.%m.%Y")
        button_text = f"📱 {sub.subscription_name} ({expires_date})"

        # Создаем и добавляем кнопку Web App в билдер
        kb.button(
            text=button_text,
            web_app=WebAppInfo(url=sub.subscription_url)
        )

    # Располагаем кнопки по одной в строке для лучшей читаемости
    kb.adjust(1)

    return kb.as_markup()
def get_config_webapp_button(webapp_url: str) -> InlineKeyboardMarkup:
    """Создает кнопку для открытия Web App с конфигурацией."""
    buttons = [
        [InlineKeyboardButton(text=_("get_configuration"), web_app=WebAppInfo(url=webapp_url))]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def profile_buttons(active_subscriptions_count: int, has_trial: bool) -> InlineKeyboardMarkup:
    """Кнопки для команды профайл"""
    kb = InlineKeyboardBuilder()
    if has_trial:
        kb.button(text=_("get_promo"), callback_data="profile:trial")
    kb.button(text=_("buy_new_sub"), callback_data="profile:new_sub")
    if active_subscriptions_count > 0:
        kb.button(text=_("extend_sub"), callback_data="profile:extend")
        kb.button(text=_("get_configs"), callback_data="profile:get_conf")
    kb.adjust(1)
    return kb.as_markup()

def referral_share_button(referral_code: str) -> InlineKeyboardMarkup:
    """Кнопка поделиться реферальной ссылкой"""
    kb = InlineKeyboardBuilder()

    link = f"https://t.me/{settings.BOT_NAME}?start={referral_code}"
    share_url = "https://t.me/share/url?url={link}&text={text}" # 🚀 Попробуй QuickVPN — анонимный и быстрый VPN. Подключи за 2 минуты!
    share_url = share_url.format(
        link=link,
        text=_("try_bot")
    )
    kb.button(text=_("share_url"), url=share_url)
    kb.adjust(1)
    return kb.as_markup()

def active_subscriptions_buttons(sub_list: List[Subscription]) -> InlineKeyboardMarkup:
    """Формирует кнопки активных подписок"""
    kb = InlineKeyboardBuilder()
    for sub in sub_list:
        subscription_name = sub.subscription_name
        expires = sub.end_date.strftime("%d.%m.%y")
        label = f"🛡️ {subscription_name} • {expires}"
        kb.button(
            text=label,
            callback_data=f"renew:{sub.id}"
        )
    kb.adjust(1)
    return kb.as_markup()

def payments_buttons() -> InlineKeyboardMarkup:
    """Формирует кнопки для оплаты подгружая фактический с .envex"""
    kb = InlineKeyboardBuilder()
    if settings.YOOKASSA_TOKEN:
        kb.button(text="💸 Card / ЮKassa / SberPay", callback_data="pay:yookassa")
    if settings.CRYPTO_TOKEN:
        kb.button(text="🧾 Crypto", callback_data="pay:crypto")
    if settings.TELEGRAM_STARS:
        kb.button(text="⭐ Telegram Stars", callback_data="pay:tg_stars")
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
    kb.button(text=_("pay"), url=url)
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
    kb.button(text=_("instructions"), callback_data="help:install")
    kb.button(text=_("FAQ"), callback_data="help:faq")
    kb.button(text=_("support"), url=f"https://t.me/{settings.SUPPORT_NAME}")
    kb.adjust(1)
    return kb.as_markup()

def install_menu_buttons() -> InlineKeyboardMarkup:
    """Кнопки для выбора платформы в разделе инструкций."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🤖 Android", callback_data="install:android")
    kb.button(text="🍏 iOS", callback_data="install:ios")
    kb.button(text="💻 Windows / macOS", callback_data="install:desktop")
    kb.button(text=_("back_menu"), callback_data="install:back_to_help")
    kb.adjust(1)
    return kb.as_markup()

def extend_subscription_button() -> InlineKeyboardMarkup:
    """Кнопка, ведущая в меню продления подписки."""
    kb = InlineKeyboardBuilder()
    kb.button(text=_("extend_now"), callback_data="profile:extend")
    return kb.as_markup()

def broadcast_confirmation_buttons() -> InlineKeyboardMarkup:
    """Кнопки для подтверждения или отмены рассылки."""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Начать рассылку", callback_data="broadcast:start")
    kb.button(text="❌ Отмена", callback_data="broadcast:cancel")
    kb.adjust(2)
    return kb.as_markup()


# app/bot/keyboards/inlines.py

# ...

def admin_panel_buttons() -> InlineKeyboardMarkup:
    """Кнопки для главной панели администратора."""
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Общая сводка", callback_data="admin:general")
    # Добавляем кнопки-заглушки
    kb.button(text="💰 Финансы", callback_data="admin:finance")
    kb.button(text="👥 Пользователи", callback_data="admin:users")
    kb.button(text="🗣️ Рефералы", callback_data="admin:referrals")
    kb.button(text="📣 Рассылка", callback_data="admin:broadcast")
    kb.adjust(1, 2, 2)
    return kb.as_markup()

def back_to_admin_panel_button() -> InlineKeyboardMarkup:
    """Кнопка для возврата в главную админ-панель."""
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад в админ-панель", callback_data="admin:back")
    return kb.as_markup()

def language_selection_buttons() -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора языка."""
    kb = InlineKeyboardBuilder()
    # callback_data содержит код языка, который мы будем сохранять
    kb.button(text="🇷🇺 Русский", callback_data="set_lang:ru")
    kb.button(text="🇬🇧 English", callback_data="set_lang:en")
    kb.adjust(2)
    return kb.as_markup()