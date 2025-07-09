from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from bot.utils.messages import profile_message
from bot.utils.logger import logger
from bot.services.user_service import register_user_service
from bot.keyboards.inlines import profile_buttons



async def profile_command(message: Message, state: FSMContext):
    logger.info(f"{message.from_user.id} {message.from_user.first_name}")
    user_db = await register_user_service(message)
    await message.answer(
        text=profile_message.format(
            referral_earnings=user_db.balance,
            active_subscriptions_count=user_db.active_subscriptions_count
        ),
        reply_markup=profile_buttons(
            active_subscriptions_count=user_db.active_subscriptions_count,
            has_trial=user_db.has_trial
        )
    )
    await state.clear()