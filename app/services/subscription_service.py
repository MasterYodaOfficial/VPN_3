from datetime import datetime, timedelta
from typing import Optional
from aiogram.types import User as UserTG
from app.core.config import settings
from app.logger import logger
from app.services.remnawave_service import remna_service
from database.models import Subscription, User, Tariff
from database.session import get_session
from remnawave.models import CreateUserRequestDto


class SubscriptionService:
    """
    Класс-сервис для управления бизнес-логикой, связанной с подписками.
    """

    async def create_trial_subscription(self, user_tg: UserTG) -> Optional[Subscription]:
        """
        Создает пробную подписку для пользователя.

        Этот метод выполняет следующие шаги:
        1. Проверяет, имеет ли пользователь право на пробный период.
        2. Создает нового пользователя в панели Remnawave с датой окончания триала.
        3. Сохраняет информацию о новой подписке (включая UUID из Remnawave) в локальную БД.
        4. Отмечает в локальной БД, что пользователь использовал свой триал.

        :param user_tg: Объект пользователя Aiogram.
        :return: Объект Subscription из нашей БД или None в случае неудачи.
        """
        async with get_session() as session:
            # 1. Получаем пользователя из нашей БД
            user_db = await User.get_by_telegram_id(session, user_tg.id)

            if not user_db or not user_db.has_trial:
                logger.warning(f"Пользователь {user_tg.id} запросил триал, но право на него отсутствует.")
                return None
            # 2. Готовим данные для Remnawave.
            # Генерируем уникальное имя подписки для пользователя в панели, чтобы избежать конфликтов
            sub_count = user_db.total_subscriptions_count + 1
            subscription_name = f"{user_db.username}-{settings.LOGO_NAME}-{sub_count}"
            expire_date = datetime.now() + timedelta(days=settings.TRIAL_DAYS)
            # 3. Вызываем сервис для создания пользователя в Remnawave
            remna_user = await remna_service.create_user_subscription(
                telegram_id=user_db.telegram_id,
                subscription_name=subscription_name,
                expire_date=expire_date
            )
            if not remna_user:
                logger.error(f"Не удалось создать пользователя в Remnawave для триала пользователя {user_db.telegram_id}")
                return None
            # 4. Создаем запись о подписке в НАШЕЙ базе, используя метод модели
            new_subscription = await Subscription.create(
                session=session,
                telegram_id=user_db.telegram_id,
                end_date=expire_date,
                subscription_name=subscription_name,
                remnawave_uuid=remna_user.uuid,
                remnawave_short_uuid=remna_user.short_uuid,
                subscription_url=remna_user.subscription_url,
                is_active=True
            )
            # 5. Обновляем статус триала у пользователя в нашей БД
            await user_db.update(session, has_trial=False)

            logger.info(f"Успешно создана пробная подписка ID:{new_subscription.id} для пользователя "
                        f"{user_db.username}|{user_db.telegram_id}")
            return new_subscription

    async def create_pending_subscription(
            self,
            user_db: User,
            tariff: Optional[Tariff]
    ) -> Optional[Subscription]:
        """
        Создает неактивную подписку в Remnawave и в локальной БД перед оплатой.
        Это "заготовка", которая будет активирована после успешного платежа.
        """
        async with get_session() as session:
            sub_count = user_db.total_subscriptions_count + 1
            subscription_name = f"{user_db.username}-{settings.LOGO_NAME}-{sub_count}"
            expire_date = datetime.now() - timedelta(days=1)
            # Создаем пользователя в Remnawave с датой окончания "в прошлом",
            # чтобы он был неактивен до момента оплаты.
            remna_user = await remna_service.create_user_subscription(
                telegram_id=user_db.telegram_id,
                subscription_name=subscription_name,
                expire_date=expire_date
            )
            if not remna_user:
                logger.error(f"Не удалось создать пользователя в Remnawave для заготовки {user_db.telegram_id}")
                return None

            subscription = await Subscription.create(
                session=session,
                telegram_id=user_db.telegram_id,
                end_date=expire_date,
                subscription_name=subscription_name,
                remnawave_uuid=remna_user.uuid,
                remnawave_short_uuid=remna_user.short_uuid,
                subscription_url=remna_user.subscription_url,
                is_active=False,
                tariff_id=tariff.id
            )
            return subscription



    # Здесь в будущем будут другие методы:
    # async def extend_subscription(self, sub_id: int, tariff_id: int) -> Optional[Subscription]: ...
    # async def deactivate_expired_subscriptions(self, bot: Bot): ...


# --- Создаем единственный экземпляр сервиса для всего приложения ---
subscription_service = SubscriptionService()