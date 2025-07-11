from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.utils.messages import profile_message
from bot.utils.logger import logger
from bot.services.user_service import register_user_service
from bot.keyboards.inlines import profile_buttons
from bot.utils.statesforms import StepForm
from bot.services.generator_subscriptions import create_trial_sub



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
    await state.set_state(StepForm.CHOOSE_ACTION_PROFILE)


async def get_action_profile(call: CallbackQuery, state: FSMContext):

    """Принимает кнопки после команды профайл. Продлить подписку, купить подписку, пробная версия и так далее"""

    logger.info(f"{call.from_user.id}, {call.from_user.first_name}")
    if call.data.startswith("profile"):
        _, profile_action = call.data.split(":")
        if profile_action == "trial":
            await call.message.edit_text("Генерируем...")
            config = await create_trial_sub(call.from_user)
            await call.message.answer(config)
            await call.message.delete()
            # TODO make method getting sub_config
            await state.clear()
            pass
        if profile_action == "new_sub":
            pass
        if profile_action == "extend":
            # Продление подписки
            pass
        if profile_action == "refresh":
            pass
    else:
        await call.message.delete()
