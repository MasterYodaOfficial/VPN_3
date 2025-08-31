# app/bot/utils/commands.py

from aiogram.types import BotCommand, BotCommandScopeDefault
# from aiogram import Bot
from app.core.config import settings
from app.bot.middlewares.i18n import i18n  # <-- Импортируем наш i18n объект


async def start_bot() -> None:
    """
    Устанавливает команды в меню бота при его старте.
    """
    await set_commands()


async def set_commands():
    """
    Устанавливает локализованные команды для каждого поддерживаемого языка.
    """
    commands = {
        "start": "command-start-description",
        "profile": "command-profile-description",
        "referral": "command-referral-description",
        "help": "command-help-description",
        "about": "command-about-description",
        "language": "command-language-description",
    }

    # Устанавливаем команды для каждого языка из нашего списка
    for lang_code in i18n.available_locales:
        # Устанавливаем контекст для функции _()
        with i18n.context(lang_code):
            # Создаем список объектов BotCommand с переведенными описаниями
            localized_commands = [
                BotCommand(
                    command=command_name,
                    description=i18n.gettext(description_key)
                )
                for command_name, description_key in commands.items()
            ]

            # Устанавливаем команды для конкретного языка
            await settings.BOT.set_my_commands(
                commands=localized_commands,
                scope=BotCommandScopeDefault(),
                language_code=lang_code
            )

    # Опционально: можно установить команды для языка по умолчанию (для тех, у кого нет нашего языка)
    # with i18n.context(settings.DEFAULT_LANGUAGE):
    #     default_commands = [ ... ]
    #     await bot.set_my_commands(commands=default_commands, scope=BotCommandScopeDefault())