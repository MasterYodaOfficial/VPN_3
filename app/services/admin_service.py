from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy import select, func

from database.models import User, Subscription, Payment
from database.enums import SubscriptionStatus
from database.session import get_session
from app.core.config import settings
from app.logger import logger

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

    async def sinc_users_from_remna(self) -> bool:
        """
        Синхронизация юзеров с панели в БД.
        """
        try:
            async with get_session() as session:
                subscriptions_db = await Subscription.get_active(session)
                for sub in subscriptions_db:
                    subscription_from_remna = await settings.REMNA_SDK.users.get_user_by_short_uuid(sub.remnawave_short_uuid)
                    await sub.update(
                        session=session,
                        telegram_id=subscription_from_remna.telegram_id,
                        start_date=subscription_from_remna.created_at,
                        end_date=subscription_from_remna.expire_at,
                        subscription_name=subscription_from_remna.username,
                        remnawave_uuid=str(subscription_from_remna.uuid),
                        remnawave_short_uuid=subscription_from_remna.short_uuid,
                        subscription_url=subscription_from_remna.subscription_url,
                        status=subscription_from_remna.status,
                        description=subscription_from_remna.description,
                        hwidDeviceLimit=subscription_from_remna.hwidDeviceLimit,
                        first_connected=subscription_from_remna.first_connected,
                        updated_at=subscription_from_remna.updated_at
                    )
            return True
        except BaseException as ex:
            logger.warning(f"Синхронизация не выполнена{ex}")
            return False

# --- Единственный экземпляр сервиса ---
admin_service = AdminService()