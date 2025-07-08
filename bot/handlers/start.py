from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from bot.services.user_service import register_user_service
from bot.utils.messages import start_message


async def start_command(message: Message, state: FSMContext):

    referral_code = None
    if message.text and len(message.text.split()) > 1:
        referral_code = message.text.split()[1]
    await register_user_service(
        message=message,
        referral_code=referral_code
    )
    await message.answer(
        text=start_message.format(
            name=message.from_user.first_name
        )
    )
    await state.clear()