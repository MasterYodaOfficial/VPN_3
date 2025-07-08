from aiogram import Dispatcher, Bot, F
from aiogram.client.default import DefaultBotProperties
from core.config import settings
from bot.handlers.start import start_command
from aiogram.filters import Command



dp = Dispatcher()
bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))



async def run_bot() -> None:

    dp.message.filter(F.chat.type == "private")

    # Команды
    dp.message.register(start_command, Command('start'))


    await dp.start_polling(bot)