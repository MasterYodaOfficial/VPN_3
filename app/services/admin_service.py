# app/services/admin_service.py

from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy import select, func

from database.models import User, Subscription, Payment
from database.enums import SubscriptionStatus
from database.session import get_session

class AdminService:
    """
    Сервис для сбора и предоставления статистики для админ-панели.
    """

    async def get_general_statistics(self) -> Dict[str, Any]:
        """
        Собирает общую сводную статистику по всему боту.
        """
        async with get_session() as session:
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month_ago = now - timedelta(days=30)

            # Пользователи
            total_users_result = await session.execute(select(func.count(User.telegram_id)))
            new_today_result = await session.execute(
                select(func.count(User.telegram_id)).where(User.created_at >= today_start)
            )
            new_month_result = await session.execute(
                select(func.count(User.telegram_id)).where(User.created_at >= month_ago)
            )

            # Подписки
            active_subs_result = await session.execute(
                select(func.count(Subscription.id)).where(Subscription.status == SubscriptionStatus.ACTIVE)
            )

            # Финансы
            revenue_today_result = await session.execute(
                select(func.sum(Payment.amount)).where(
                    Payment.status == "succeeded",
                    Payment.created_at >= today_start
                )
            )
            revenue_month_result = await session.execute(
                select(func.sum(Payment.amount)).where(
                    Payment.status == "succeeded",
                    Payment.created_at >= month_ago
                )
            )

            return {
                "total_users": total_users_result.scalar_one_or_none() or 0,
                "new_users_today": new_today_result.scalar_one_or_none() or 0,
                "new_users_month": new_month_result.scalar_one_or_none() or 0,
                "active_subscriptions": active_subs_result.scalar_one_or_none() or 0,
                "revenue_today": revenue_today_result.scalar_one_or_none() or 0,
                "revenue_month": revenue_month_result.scalar_one_or_none() or 0,
            }

# --- Единственный экземпляр сервиса ---
admin_service = AdminService()