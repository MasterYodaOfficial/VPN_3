from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from bot.utils.messages import referral_message
from bot.keyboards.inlines import referral_share_button
from bot.utils.logger import logger
from bot.services.user_service import register_user_service
from core.config import settings



async def referral_command(message: Message, state: FSMContext):
    logger.info(f"{message.from_user.id} {message.from_user.first_name}")
    user_db = await register_user_service(message)
    referral_image = FSInputFile("bot/media/referral.jpg")
    await message.answer_photo(
        caption=referral_message.format(
            referrals_count=user_db.invited_users_count,
            earned=user_db.balance,
            bot_name=settings.BOT_NAME,
            referral_code=user_db.referral_code,
            commission_precent=settings.REFERRAL_COMMISSION_PERCENT

        ),
        reply_markup=referral_share_button(
            referral_code=user_db.referral_code
        ),
        photo=referral_image
    )
    await state.clear()
