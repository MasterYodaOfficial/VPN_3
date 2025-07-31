from aiogram import Dispatcher, Bot, F
from aiogram.client.default import DefaultBotProperties
from core.config import settings
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.handlers.start import start_command
from bot.handlers.about import about_command
from bot.handlers.profile import (profile_command, get_action_profile, get_subscription_extend,
                                  get_payment_method_extend, get_tariff_extend, get_tariff_buy, get_payment_method_buy)
from bot.handlers.referral import referral_command
from bot.handlers.help import help_command, navigate_help_menu, show_install_guide
from bot.handlers.for_admins import statistics, broadcast
from aiogram.filters import Command
from bot.utils.commands import start_bot
from bot.utils.logger import logger
from bot.utils.throttling import ThrottlingMiddleware
from bot.services.generator_subscriptions import deactivate_expired_subscriptions, update_servers_load_statistics
from bot.services.payment_service import send_expiration_warnings
from bot.utils.statesforms import StepForm
from database.crud.crud_tariff import load_tariffs_from_json
from database.crud.crud_server import load_servers_from_json
from yookassa import Configuration

Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_TOKEN
dp = Dispatcher()
bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))



async def run_bot() -> None:
    try:
        await load_tariffs_from_json("database/tariffs.json")
        logger.info("Тарифы успешно загружены/обновлены")
    except BaseException as e:
        logger.debug(f"Ошибка при загрузке тарифов: {e}")

    try:
        await load_servers_from_json("database/servers.json")
        logger.info("Сервера загружены и обновлены")
    except BaseException as e:
        logger.debug(f"Ошибка пр  загрузке серверов: {e}")

    logger.info("Инициализация бота")
    dp.message.filter(F.chat.type == "private")
    dp.startup.register(start_bot)

    # Антиспам
    dp.message.middleware(ThrottlingMiddleware(limit=1.5))
    dp.callback_query.middleware(ThrottlingMiddleware(limit=1.0))

    # Команды юзеров
    dp.message.register(start_command, Command('start'))
    dp.message.register(about_command, Command('about'))
    dp.message.register(profile_command, Command('profile'))
    dp.message.register(referral_command, Command('referral'))
    dp.message.register(help_command, Command('help'))

    # Админки
    dp.message.register(broadcast.broadcast_command, Command('broadcast'))
    dp.message.register(statistics.admin_command, Command('admin'))
    dp.callback_query.register(broadcast.broadcast_command, F.data == "admin_broadcast_start")
    dp.message.register(broadcast.receive_broadcast_message, StepForm.WAITING_BROADCAST_MESSAGE)
    dp.callback_query.register(broadcast.confirm_broadcast_handler, StepForm.CONFIRM_BROADCAST)
    dp.callback_query.register(statistics.navigate_admin_panel, F.data.startswith("admin_stats:"))


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



    # --- Настройка и запуск планировщиков ---
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(deactivate_expired_subscriptions, 'cron', hour=2, minute=0) # Удаление конфигов
    scheduler.add_job(send_expiration_warnings, 'cron', hour=11, minute=0, args=[bot]) # Уведомление с просьбой оплатить
    scheduler.add_job(update_servers_load_statistics, 'interval', hours=1) # Активные пользователи каждый час
    scheduler.start()

    logger.info("Инициализация бота выполнена, старт...")
    await dp.start_polling(bot)