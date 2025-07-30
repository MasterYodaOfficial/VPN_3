from aiogram.types import Message, CallbackQuery
from aiogram import Bot
from aiogram.fsm.context import FSMContext

from bot.database.crud.crud_user import is_admin, get_all_telegram_ids

from bot.utils.messages import broadcast_message
from bot.utils.statesforms import StepForm
from bot.keyboards.inlines import continue_broadcast_buttons

import asyncio
from bot.logger import logger

async def send_broadcast(bot: Bot, original_message: Message, user_ids: list[int], admin_id: int):
    """Фоновая задача для отправки всем пользователям"""
    success, failed = 0, 0

    for user_id in user_ids:
        try:
            await original_message.send_copy(chat_id=user_id)
            success += 1
            await asyncio.sleep(0.05)  # пауза, чтобы не ловить Flood
        except Exception as e:
            failed += 1
            logger.warning(f"Ошибка при отправке {user_id}: {e}")
            if "Too Many Requests" in str(e):
                await asyncio.sleep(1.5)
            else:
                await asyncio.sleep(0.05)

    text = (
        "📢 Рассылка завершена.\n"
        f"✅ Успешно доставлено: {success}\n"
        f"❌ Ошибок: {failed}\n"
        f"👥 Всего: {len(user_ids)}"
    )

    # Отправляем лог админу
    try:
        await bot.send_message(admin_id, text)
    except Exception as e:
        logger.error(f"Не удалось отправить лог админу: {e}")


async def broadcast_command(message: Message, state: FSMContext):
    """
    Запуск команды для рассылки пользователям
    """
    logger.info(f"{message.from_user.id}, {message.from_user.first_name}")
    if await is_admin(message.from_user):
        await message.answer(broadcast_message)
        await state.set_state(StepForm.WAITING_BROADCAST_MESSAGE)


async def receive_broadcast_message(message: Message, state: FSMContext):
    """Ждем сообщение для отправки"""
    logger.info(f"{message.from_user.id}, {message.from_user.first_name}")
    await state.update_data(broadcast_message=message)
    await message.reply(
        text="✅ Получено! Проверьте это сообщение и подтвердите рассылку или отмените.",
        reply_markup=continue_broadcast_buttons()
    )
    await state.set_state(StepForm.CONFIRM_BROADCAST)


async def confirm_broadcast(call: CallbackQuery, state: FSMContext):
    """
    Принимаем кнопку согласия на отправку и отправляем
    """

    if call.data.startswith("broadcast"):
        _, answer = call.data.split(":")
        if answer == "start":
            data = await state.get_data()
            original_message: Message = data.get("broadcast_message")
            if not original_message:
                await call.answer("❌ Сообщение не найдено. Начните сначала.", show_alert=True)
                await state.clear()
                return

            user_ids = await get_all_telegram_ids()
            admin_id = call.from_user.id

            # Запуск фоновой задачи правильно
            await asyncio.create_task(send_broadcast(call.bot, original_message, user_ids, admin_id))

            await call.message.edit_text("📤 Рассылка запущена. Отчёт придёт сюда после завершения.")
            await state.clear()
        else:
            await call.message.answer("Отменил.")
            await call.message.delete()
            await state.clear()
            return