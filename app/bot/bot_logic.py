from aiogram import Dispatcher, Bot, F, Router
from app.bot.handlers.start import start_command
from app.bot.handlers.about import about_command
from app.bot.handlers.profile import (profile_command, get_action_profile, get_subscription_extend,
                              get_payment_method_extend, get_tariff_extend, get_tariff_buy, get_payment_method_buy)
from app.bot.handlers.referral import referral_command
from app.bot.handlers.help import help_command, navigate_help_menu, show_install_guide
from aiogram.filters import Command
from app.bot.utils.commands import start_bot
from app.logger import logger
from app.bot.utils.throttling import ThrottlingMiddleware
from app.bot.utils.statesforms import StepForm
from app.bot.handlers.stars_handlers import pre_checkout_handler, successful_payment_handler
from app.bot.middlewares.i18n import i18n_middleware
from app.bot.handlers.language import router as language_router
from app.bot.handlers.for_admins import broadcast, refund, statistics


def setup_bot_logic(dp: Dispatcher, bot: Bot) -> None:

    logger.info("Инициализация бота")
    dp.message.filter(F.chat.type == "private")
    dp.startup.register(start_bot)

    # Антиспам
    dp.message.middleware(ThrottlingMiddleware(limit=0.2))
    dp.callback_query.middleware(ThrottlingMiddleware(limit=0.2))
    # Переводчик
    dp.update.middleware(i18n_middleware)

    # Команды юзеров
    dp.message.register(start_command, Command('start'))
    dp.message.register(about_command, Command('about'))
    dp.message.register(profile_command, Command('profile'))
    dp.message.register(referral_command, Command('referral'))
    dp.message.register(help_command, Command('help'))
    # Смена языка
    dp.include_router(language_router)

    # --- Админские команды ---
    admin_router = Router(name="admin_commands")
    admin_router.include_router(broadcast.router)
    admin_router.include_router(refund.router)
    admin_router.include_router(statistics.router)

    dp.include_router(admin_router)


    # Движения и Callbacks с /profile
    dp.callback_query.register(get_action_profile, StepForm.CHOOSE_ACTION_PROFILE) # Принимает продление, триал, или купить новую

    # Продление действующей подписки
    dp.callback_query.register(get_subscription_extend, StepForm.CHOOSE_EXTEND_SUBSCRIPTION) # Принимаем подписку для продления
    dp.callback_query.register(get_tariff_extend, StepForm.SELECT_TARIFF_EXTEND) # Принимаем тариф для продления
    dp.callback_query.register(get_payment_method_extend, StepForm.PAYMENT_METHOD_EXTEND) # Принимаем метод оплаты для продления

    # Покупка новой подписки
    dp.callback_query.register(get_tariff_buy, StepForm.SELECT_TARIFF_BUY)  # Выбор тарифа для продления
    dp.callback_query.register(get_payment_method_buy, StepForm.PAYMENT_METHOD_BUY)  # Выбор способа оплаты

    # Обработка кнопок помощи
    dp.callback_query.register(navigate_help_menu, F.data.startswith("help:"))
    dp.callback_query.register(show_install_guide, F.data.startswith("install:"))

    # Обработка покупки звездами
    dp.pre_checkout_query.register(pre_checkout_handler)
    dp.message.register(successful_payment_handler, F.successful_payment)


    # --- Настройка и запуск планировщиков ---


    logger.info("Инициализация бота выполнена, старт...")
