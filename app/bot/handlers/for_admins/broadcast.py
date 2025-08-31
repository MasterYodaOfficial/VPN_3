import asyncio
from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.bot.keyboards.inlines import broadcast_confirmation_buttons
from app.bot.utils.statesforms import StepForm
from app.logger import logger
from app.services.user_service import user_service
from database.models import User
from database.session import get_session

router = Router(name=__name__)


async def _send_broadcast_task(bot: Bot, original_message: Message, user_ids: list[int], admin_id: int):
    """Приватная фоновая задача для отправки сообщения всем пользователям."""
    success_count, failed_count = 0, 0
    user_ids_to_send = [uid for uid in user_ids if uid != admin_id]

    for user_id in user_ids_to_send:
        try:
            await original_message.send_copy(chat_id=user_id)
            success_count += 1
            await asyncio.sleep(0.05)  # Защита от Flood Limits
        except Exception as e:
            failed_count += 1
            logger.warning(f"Ошибка при отправке рассылки пользователю {user_id}: {e}")
            if "Too Many Requests" in str(e):
                await asyncio.sleep(1.5)

    report_text = (
        "📢 Рассылка завершена.\n\n"
        f"✅ Успешно доставлено: {success_count}\n"
        f"❌ Ошибок: {failed_count}"
    )
    try:
        await bot.send_message(admin_id, report_text)
    except Exception as e:
        logger.error(f"Не удалось отправить отчет о рассылке админу {admin_id}: {e}")


@router.message(Command("broadcast"))
async def broadcast_command(message: Message, state: FSMContext):
    """Точка входа в режим рассылки."""
    user_db = await user_service.register_or_update_user(message)
    if not user_db.is_admin:
        return

    await message.answer(
        "📢 <b>Режим рассылки</b>\n\n"
        "Отправьте сообщение, которое вы хотите разослать всем пользователям. "
        "Можно использовать форматирование и медиа."
    )
    await state.set_state(StepForm.WAITING_BROADCAST_MESSAGE)


@router.message(StepForm.WAITING_BROADCAST_MESSAGE)
async def receive_broadcast_message(message: Message, state: FSMContext):
    """Получает сообщение от админа и просит подтверждение."""
    await state.update_data(broadcast_message=message)
    await message.reply(
        text="✅ Сообщение получено. Начать рассылку?",
        reply_markup=broadcast_confirmation_buttons()
    )
    await state.set_state(StepForm.CONFIRM_BROADCAST)


@router.callback_query(F.data.startswith("broadcast:"), StepForm.CONFIRM_BROADCAST)
async def confirm_broadcast_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """Обрабатывает подтверждение или отмену рассылки."""
    action = call.data.split(":")[1]

    if action == "start":
        data = await state.get_data()
        original_message: Message = data.get("broadcast_message")

        if not original_message:
            await call.answer("❌ Сообщение для рассылки не найдено.", show_alert=True)
            await state.clear()
            return

        async with get_session() as session:
            # Используем метод модели для получения всех ID
            user_ids = await User.get_all_telegram_ids(session)

        admin_id = call.from_user.id

        # Запускаем отправку в фоновом режиме
        asyncio.create_task(_send_broadcast_task(bot, original_message, user_ids, admin_id))

        await call.message.edit_text("📤 Рассылка запущена. Отчёт будет отправлен по завершении.")

    elif action == "cancel":
        await call.message.edit_text("❌ Рассылка отменена.")

    await state.clear()