from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from bot.services.user_service import register_user_service
from bot.utils.messages import start_message
from bot.utils.logger import logger


async def start_command(message: Message, state: FSMContext):
    logger.info(f"{message.from_user.id} {message.from_user.first_name}")
    referral_code = None
    welcome_image = FSInputFile("bot/media/welcome.jpg")
    if message.text and len(message.text.split()) > 1:
        referral_code = message.text.split()[1]
    await register_user_service(
        message=message,
        referral_code=referral_code
    )
    await message.answer_photo(
        photo=welcome_image,
        caption=start_message.format(
            name=message.from_user.first_name
        )
    )
    await state.clear()
