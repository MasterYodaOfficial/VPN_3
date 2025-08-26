from aiogram.types import Message
from aiogram.filters import CommandObject
from aiogram.exceptions import TelegramBadRequest
from app.services.user_service import register_user_service  # Для проверки на админа
from app.logger import logger
from app.core.config import settings

async def refund_command(message: Message, command: CommandObject):
    """
    Выполняет возврат Telegram Stars по ID пользователя и ID платежа в НАШЕЙ базе.
    Пример: /refund 12345678 15
    """
    user_db = await register_user_service(message)
    if not user_db.is_admin:
        logger.debug(f"Попытка не админа {message.from_user.id} {message.from_user.first_name}")
        return
    args = command.args
    if not args or len(args.split()) != 2:
        await message.answer(
            "❌ Неверный формат команды.\n"
            "<b>Пример:</b> <code>/refund ID_пользователя ID_платежа</code>"
        )
        return
    try:
        target_user_id = int(args.split()[0])
        telegram_charge_id = args.split()[1]
    except ValueError:
        await message.answer("❌ ID пользователя и ID платежа должны быть числами.")
        return
    try:
        await settings.BOT.refund_star_payment(
            user_id=target_user_id,  # ID пользователя, которому возвращаем
            telegram_payment_charge_id=telegram_charge_id  # ID транзакции из нашей БД
        )
        await message.answer(
            f"✅ Возврат для платежа <code>{telegram_charge_id}</code> пользователю <code>{target_user_id}</code> успешно выполнен.")

    except TelegramBadRequest as e:
        error_text = "❌ Произошла неизвестная ошибка при возврате."
        if "CHARGE_ALREADY_REFUNDED" in e.message:
            error_text = "⚠️ Этот платеж уже был возвращен ранее."
        elif "PAYMENT_NOT_FOUND" in e.message:
            error_text = "❌ Платеж с таким ID транзакции не найден в системе Telegram."

        await message.answer(error_text)
    except Exception as e:
        logger.error(f"Неожиданная ошибка при возврате платежа {telegram_charge_id}: {e}")
        await message.answer("❌ Произошла непредвиденная ошибка при возврате.")