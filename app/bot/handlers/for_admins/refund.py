from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

from app.core.config import settings
from app.logger import logger
from app.services.user_service import user_service
from database.models import Payment
from database.session import get_session

router = Router(name=__name__)


@router.message(Command("refund"))
async def refund_command(message: Message, command: CommandObject):
    """
    Выполняет возврат Telegram Stars по ID платежа в НАШЕЙ базе.
    Пример: /refund 15
    """
    user_db = await user_service.register_or_update_user(message)
    if not user_db.is_admin:
        return

    args = command.args
    if not args:
        await message.answer(
            "❌ Неверный формат команды.\n"
            "<b>Пример:</b> <code>/refund ID_платежа</code>"
        )
        return

    try:
        payment_id = int(args)
    except ValueError:
        await message.answer("❌ ID платежа должен быть числом.")
        return

    async with get_session() as session:
        payment = await session.get(Payment, payment_id)

    if not payment:
        return await message.answer(f"❌ Платеж с ID <code>{payment_id}</code> не найден в базе данных.")

    if not payment.external_payment_id or not payment.method == 'tg_stars':
        return await message.answer(f"❌ Этот платеж (ID: {payment_id}) не является платежом Telegram Stars.")

    try:
        await settings.BOT.refund_star_payment(
            user_id=payment.user_id,
            telegram_payment_charge_id=payment.external_payment_id
        )
        await message.answer(
            f"✅ Запрос на возврат для платежа <code>{payment.id}</code> "
            f"(TG Charge ID: <code>{payment.external_payment_id}</code>) "
            f"пользователю <code>{payment.user_id}</code> успешно отправлен."
        )
    except TelegramBadRequest as e:
        error_text = f"❌ Ошибка Telegram API: {e.message}"
        await message.answer(error_text)
    except Exception as e:
        logger.error(f"Неожиданная ошибка при возврате платежа {payment_id}: {e}")
        await message.answer("❌ Произошла непредвиденная ошибка.")