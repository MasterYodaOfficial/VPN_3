from aiogram.types import Message, CallbackQuery
from datetime import datetime
from app.bot.utils.admin_messages import admin_panel_start_message
from app.bot.keyboards.inlines import admin_panel_buttons, back_to_admin_panel_button
from app.services.user_service import register_user_service
from database.session import get_session
from database.crud import crud_user, crud_payment, crud_subscription, crud_server


async def admin_command(message: Message):
    """Точка входа в админ-панель. /admin"""
    user_db = await register_user_service(message)
    if not user_db.is_admin:
        return

    await message.answer(admin_panel_start_message, reply_markup=admin_panel_buttons())


async def navigate_admin_panel(call: CallbackQuery):
    """Обрабатывает навигацию по кнопкам админ-панели."""
    action = call.data.split(":")[1]

    async with get_session() as session:
        if action == "back":
            await call.message.edit_text(admin_panel_start_message, reply_markup=admin_panel_buttons())
            return

        # --- Сбор данных ---
        if action == "general":
            total_users = await crud_user.count_users(session)
            new_users_today = await crud_user.count_new_users_for_period(session, days=1)
            new_users_month = await crud_user.count_new_users_for_period(session, days=30)
            active_subs = await crud_subscription.count_active_subscriptions(session)
            revenue_today = await crud_payment.get_revenue_for_period(session, days=1)
            revenue_month = await crud_payment.get_revenue_for_period(session, days=30)

            text = (
                f"<b>📊 Общая сводка на {datetime.now().strftime('%d.%m.%Y %H:%M')}</b>\n\n"
                f"<b>Пользователи:</b>\n"
                f"  - Всего: <code>{total_users}</code>\n"
                f"  - Новых сегодня: <code>{new_users_today}</code>\n"
                f"  - Новых за 30 дней: <code>{new_users_month}</code>\n\n"
                f"<b>Подписки:</b>\n"
                f"  - Активных сейчас: <code>{active_subs}</code>\n\n"
                f"<b>Финансы:</b>\n"
                f"  - Доход сегодня: <code>{revenue_today} ₽</code>\n"
                f"  - Доход за 30 дней: <code>{revenue_month} ₽</code>"
            )

        elif action == "finance":
            revenue_today = await crud_payment.get_revenue_for_period(session, days=1)
            revenue_week = await crud_payment.get_revenue_for_period(session, days=7)
            revenue_month = await crud_payment.get_revenue_for_period(session, days=30)
            revenue_total = await crud_payment.get_revenue_for_period(session)

            text = (
                f"<b>💰 Статистика по финансам</b>\n\n"
                f"  - Доход сегодня: <code>{revenue_today} ₽</code>\n"
                f"  - Доход за 7 дней: <code>{revenue_week} ₽</code>\n"
                f"  - Доход за 30 дней: <code>{revenue_month} ₽</code>\n"
                f"  - Доход за все время: <code>{revenue_total} ₽</code>"
            )

        elif action == "servers":
            servers = await crud_server.get_all_servers_with_load(session)
            server_lines = []
            for server in servers:
                status_icon = "✅" if server.is_active else "❌"
                load_percent = (server.current_clients / server.max_clients * 100) if server.max_clients else 0
                server_lines.append(
                    f"  - {status_icon} <b>{server.name}</b>: <code>{server.current_clients}/{server.max_clients}</code> ({load_percent:.1f}%)"
                )

            text = "<b>🖥️ Состояние серверов</b>\n\n" + "\n".join(server_lines)

        elif action == "referrals":
            top_referrers = await crud_user.get_top_referrers(session, limit=5)
            referrer_lines = []
            for i, user in enumerate(top_referrers):
                referrer_lines.append(
                    f"  {i + 1}. <code>{user.telegram_id}</code> ({user.username}) - пригласил(а) <b>{len(user.invited_users)}</b> чел."
                )

            text = "<b>🗣️ Топ-5 рефералов (по кол-ву приглашенных)</b>\n\n" + "\n".join(referrer_lines)

        else:
            text = "Раздел в разработке."

        await call.message.edit_text(text, reply_markup=back_to_admin_panel_button())