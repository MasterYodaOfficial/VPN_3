from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from app.bot.utils.messages import about_message
from app.logger import logger
from app.core.config import settings


async def about_command(message: Message, state: FSMContext):
    logger.bind(source="bot").info(f"{message.from_user.id} {message.from_user.first_name}")
    logo_image = FSInputFile("app/bot/media/logo.jpg")
    await message.answer_photo(
        photo=logo_image,
        caption=about_message.format(
            support=settings.SUPPORT_NAME,
            owner=settings.OWNER_NAME
        )
    )
    await state.clear()
