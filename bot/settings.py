from aiogram import Dispatcher, Bot, F
from aiogram.client.default import DefaultBotProperties
from core.config import settings

from bot.handlers.start import start_command
from bot.handlers.about import about_command
from bot.handlers.profile import (profile_command, get_action_profile, get_subscription_extend,
                                  get_payment_method_extend, get_tariff_extend, get_tariff_buy, get_payment_method_buy)
from bot.handlers.referral import referral_command
from aiogram.filters import Command
from bot.utils.commands import start_bot
from bot.utils.logger import logger
from bot.utils.throttling import ThrottlingMiddleware

from bot.utils.statesforms import StepForm
from database.crud.crud_tariff import load_tariffs_from_json
from database.crud.crud_server import load_servers_from_json
from yookassa import Configuration
from pathlib import Path

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

    # Команды
    dp.message.register(start_command, Command('start'))
    dp.message.register(about_command, Command('about'))
    dp.message.register(profile_command, Command('profile'))
    dp.message.register(referral_command, Command('referral'))


    # Движения и Callbacks с /profile
    dp.callback_query.register(get_action_profile, StepForm.CHOOSE_ACTION_PROFILE) # Принимает продление, триал, или купить новую

    # Продление действующей подписки
    dp.callback_query.register(get_subscription_extend, StepForm.CHOOSE_EXTEND_SUBSCRIPTION) # Принимаем подписку для продления
    dp.callback_query.register(get_tariff_extend, StepForm.SELECT_TARIFF_EXTEND) # Принимаем тариф для продления
    dp.callback_query.register(get_payment_method_extend, StepForm.PAYMENT_METHOD_EXTEND) # Принимаем метод оплаты для продления

    # Покупка новой подписки
    dp.callback_query.register(get_tariff_buy, StepForm.SELECT_TARIFF_BUY)  # Выбор тарифа для продления
    dp.callback_query.register(get_payment_method_buy, StepForm.PAYMENT_METHOD_BUY)  # Выбор способа оплаты



    logger.info("Инициализация бота выполнена, старт...")
    await dp.start_polling(bot)