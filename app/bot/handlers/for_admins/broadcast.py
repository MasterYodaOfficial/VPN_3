from aiogram.types import Message, CallbackQuery
from aiogram import Bot
from aiogram.fsm.context import FSMContext
import asyncio
from app.bot.utils.admin_messages import broadcast_start_message
from app.bot.utils.statesforms import StepForm
from app.bot.keyboards.inlines import broadcast_confirmation_buttons
from app.services.user_service import register_user_service
from database.crud.crud_user import get_all_telegram_ids
from database.session import get_session
from app.logger import logger


async def send_broadcast_task(bot: Bot, original_message: Message, user_ids: list[int], admin_id: int):
    """Фоновая задача для отправки сообщения всем пользователям."""
    success_count, failed_count = 0, 0

    # Отправляем сообщение всем, кроме самого админа
    user_ids_to_send = [uid for uid in user_ids if uid != admin_id]

    for user_id in user_ids_to_send:
        try:
            await original_message.send_copy(chat_id=user_id)
            success_count += 1
            await asyncio.sleep(0.05)  # Пауза 50мс между отправками для защиты от Flood Limits
        except Exception as e:
            failed_count += 1
            logger.bind(source="bot").warning(f"Ошибка при отправке рассылки пользователю {user_id}: {e}")
            if "Too Many Requests" in str(e):
                await asyncio.sleep(1.5)  # Если ловим флуд, ждем подольше

    report_text = (
        "📢 Рассылка завершена.\n\n"
        f"✅ Успешно доставлено: {success_count}\n"
        f"❌ Ошибок: {failed_count}\n"
        f"👥 Всего пользователей (без админа): {len(user_ids_to_send)}"
    )

    try:
        await bot.send_message(admin_id, report_text)
    except Exception as e:
        logger.bind(source="bot").error(f"Не удалось отправить отчет о рассылке админу {admin_id}: {e}")


async def broadcast_command(message: Message, state: FSMContext):
    """
    Точка входа в режим рассылки. /broadcast
    """
    user_db = await register_user_service(message)
    if not user_db.is_admin:
        logger.bind(source="bot").warning(f"{message.from_user.id}, {message.from_user.first_name} нет админки игнор")
        await state.clear()
        return

    await message.answer(broadcast_start_message)
    await state.set_state(StepForm.WAITING_BROADCAST_MESSAGE)


async def receive_broadcast_message(message: Message, state: FSMContext):
    """
    Получает сообщение от админа для рассылки и просит подтверждение.
    """
    await state.update_data(broadcast_message=message)
    await message.reply(
        text="✅ Сообщение получено. Вот как оно будет выглядеть. Начать рассылку?",
        reply_markup=broadcast_confirmation_buttons()
    )
    await state.set_state(StepForm.CONFIRM_BROADCAST)


async def confirm_broadcast_handler(call: CallbackQuery, state: FSMContext):
    """
    Обрабатывает подтверждение или отмену рассылки.
    """
    action = call.data.split(":")[1]

    if action == "start":
        data = await state.get_data()
        original_message: Message = data.get("broadcast_message")

        if not original_message:
            await call.answer("❌ Сообщение для рассылки не найдено. Попробуйте снова.")
            await state.clear()
            return

        async with get_session() as session:
            user_ids = await get_all_telegram_ids(session)

        admin_id = call.from_user.id

        # Запускаем отправку в фоновой задаче, чтобы не блокировать бота
        asyncio.create_task(send_broadcast_task(call.bot, original_message, user_ids, admin_id))

        await call.message.edit_text("📤 Рассылка запущена. Отчёт о доставке придёт сюда после завершения.")

    elif action == "cancel":
        await call.message.edit_text("❌ Рассылка отменена.")

    await state.clear()