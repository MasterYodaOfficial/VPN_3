from aiogram import Dispatcher, Bot, F
from aiogram.client.default import DefaultBotProperties
from core.config import settings

from bot.handlers.start import start_command
from bot.handlers.about import about_command
from bot.handlers.profile import (profile_command, get_action_profile)
from bot.handlers.referral import referral_command
from aiogram.filters import Command
from bot.utils.commands import start_bot
from bot.utils.logger import logger
from bot.utils.throttling import ThrottlingMiddleware

from bot.utils.statesforms import StepForm


dp = Dispatcher()
bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))



async def run_bot() -> None:
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
    dp.callback_query.register(get_action_profile, StepForm.CHOOSE_ACTION_PROFILE)


    logger.info("Инициализация бота выполнена, старт...")
    await dp.start_polling(bot)