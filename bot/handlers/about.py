from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from bot.utils.messages import about_message
from bot.utils.logger import logger
from core.config import settings


async def about_command(message: Message, state: FSMContext):
    logger.info(f"{message.from_user.id} {message.from_user.first_name}")
    logo_image = FSInputFile("bot/media/logo.jpg")
    await message.answer_photo(
        photo=logo_image,
        caption=about_message.format(
            support=settings.SUPPORT_NAME,
            owner=settings.OWNER_NAME
        )
    )
    await state.clear()
