from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram import Bot


async def start_bot(bot: Bot) -> None:
    """
    Устанавливает команды в меню бота
    """
    await set_commands(bot)


async def set_commands(bot: Bot):
    commands = [
        BotCommand(
            command='start',
            description='Начало'
        ),
        BotCommand(
            command='profile',
            description='Мои подписки и конфиги'
        ),
        BotCommand(
            command='referral',
            description='Реферальная программа'
        ),
        BotCommand(
            command='help',
            description='Помощь в настройке подключения'
        ),
        BotCommand(
            command='about',
            description='О нас и как всё работает'
        )
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())