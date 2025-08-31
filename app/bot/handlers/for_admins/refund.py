# app/bot/handlers/admin/refund.py

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

from app.core.config import settings
from app.logger import logger
from app.services.user_service import user_service # Используем только для проверки на админа

router = Router(name=__name__)


@router.message(Command("refund"))
async def refund_command(message: Message, command: CommandObject):
    """
    Выполняет возврат Telegram Stars по ID пользователя и ID транзакции Telegram.
    Данные берутся напрямую из аргументов команды.

    Пример использования: /refund 758107031 3256044908709981615_some_hash
    """
    # 1. Проверяем, что команду вызывает администратор
    user_db = await user_service.register_or_update_user(message)
    if not user_db.is_admin:
        logger.warning(f"Попытка несанкционированного использования /refund от {message.from_user.id}")
        return

    # 2. Проверяем наличие и количество аргументов
    args = command.args
    if not args or len(args.split()) != 2:
        await message.answer(
            "❌ **Неверный формат команды.**\n\n"
            "Используйте: <code>/refund USER_ID CHARGE_ID</code>\n\n"
            "<b>Пример:</b>\n"
            "<code>/refund 123456789 987654321_ABC...</code>"
        )
        return

    # 3. Парсим аргументы
    try:
        target_user_id_str, telegram_charge_id = args.split()
        target_user_id = int(target_user_id_str)
    except ValueError:
        await message.answer("❌ <b>Ошибка:</b> ID пользователя должен быть числом.")
        return

    # 4. Выполняем запрос к Telegram API
    try:
        await settings.BOT.refund_star_payment(
            user_id=target_user_id,
            telegram_payment_charge_id=telegram_charge_id
        )
        await message.answer(
            f"✅ Запрос на возврат для транзакции <code>{telegram_charge_id}</code> "
            f"пользователю <code>{target_user_id}</code> успешно отправлен."
        )

    except TelegramBadRequest as e:
        # Обрабатываем специфические ошибки от Telegram
        error_text = f"❌ <b>Ошибка Telegram API:</b> {e.message}"
        if "CHARGE_ALREADY_REFUNDED" in e.message:
            error_text = "⚠️ <b>Этот платеж уже был возвращен ранее.</b>"
        elif "PAYMENT_NOT_FOUND" in e.message:
            error_text = "❌ <b>Платеж с таким ID транзакции не найден в системе Telegram.</b>"
        await message.answer(error_text)

    except Exception as e:
        logger.error(f"Неожиданная ошибка при возврате платежа {telegram_charge_id}: {e}")
        await message.answer("❌ Произошла непредвиденная ошибка при выполнении возврата.")