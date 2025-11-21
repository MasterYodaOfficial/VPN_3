from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from app.bot.keyboards.inlines import admin_panel_buttons, back_to_admin_panel_button
from app.services.user_service import user_service
from app.services.admin_service import admin_service
from aiogram.fsm.context import FSMContext

router = Router(name=__name__)


@router.message(Command("admin"))
async def admin_command(message: Message, state: FSMContext):
    """Точка входа в админ-панель."""
    user_db = await user_service.register_or_update_user(message)
    if not user_db.is_admin:
        return
    await state.clear()
    await message.answer(
        "<b>👑 Панель администратора</b>\nВыберите раздел для просмотра.",
        reply_markup=admin_panel_buttons()
    )


@router.callback_query(F.data.startswith("admin:"))
async def navigate_admin_panel(call: CallbackQuery):
    """Обрабатывает навигацию по кнопкам админ-панели."""
    action = call.data.split(":")[1]

    if action == "back":
        await call.message.edit_text(
            "<b>👑 Панель администратора</b>\nВыберите раздел для просмотра.",
            reply_markup=admin_panel_buttons()
        )
        return

    text = "🚧 Раздел в разработке."  # Сообщение-заглушка по умолчанию

    if action == "general":
        stats = await admin_service.get_general_statistics()
        text = (
            f"<b>📊 Общая сводка на {datetime.now().strftime('%d.%m.%Y %H:%M')}</b>\n\n"
            f"<b>Пользователи:</b>\n"
            f"  - Всего: <code>{stats['total_users']}</code>\n"
            f"  - Новых сегодня: <code>{stats['new_users_today']}</code>\n"
            f"  - Новых за 30 дней: <code>{stats['new_users_month']}</code>\n\n"
            f"<b>Подписки:</b>\n"
            f"  - Активных сейчас: <code>{stats['active_subscriptions']}</code>\n\n"
            f"<b>Финансы:</b>\n"
            f"  - Доход сегодня: <code>{stats['revenue_today']} ₽</code>\n"
            f"  - Доход за 30 дней: <code>{stats['revenue_month']} ₽</code>"
        )
    if action == "sinc":
        await call.message.edit_text("Запуск синхронизации...")
        status = await admin_service.sinc_users_from_remna()
        text = "✅ Синхронизация выполнена" if status else "‼️ Ошибка синхронизации"

    # Для всех остальных кнопок (finance, users и т.д.) будет использовано сообщение-заглушка

    await call.message.edit_text(text, reply_markup=back_to_admin_panel_button())
    await call.answer()