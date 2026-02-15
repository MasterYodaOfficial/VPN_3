from datetime import datetime, timedelta
from typing import Optional, List
from aiogram.types import User as UserTG
from app.core.config import settings
from app.logger import logger
from app.services.remnawave_service import remna_service
from database.models import Subscription, User, Tariff
from database.session import get_session
import re
from transliterate import translit
from database.enums import SubscriptionStatus
import uuid


class SubscriptionService:
    """
    Класс-сервис для управления бизнес-логикой, связанной с подписками.
    """


    @staticmethod
    def normalize_username(name: str, fallback: str = "QuickVPNUser") -> str:
        """
        Приводит Telegram first_name к допустимому username для Remnawave.
        """
        if not name:
            return fallback
        try:
            name = translit(name, "ru", reversed=True)
        except Exception as ex:
            logger.error(ex)
        name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
        name = re.sub(r"_+", "_", name)
        name = name[:30]
        if not name.strip("_"):
            return fallback
        return name


    async def get_active_user_subscriptions(self, user_tg: UserTG) -> Optional[List[Subscription]]:
        """
        Возвращает список всех АКТИВНЫХ подписок для указанного пользователя.

        Этот метод идеально подходит для формирования клавиатур и отображения
        информации в профиле пользователя.

        :param user_tg: Telegram объект пользователя.
        :return: Список объектов Subscription или пустой список, если ничего не найдено.
        """
        async with get_session() as session:
            user = await User.get_by_telegram_id(session, user_tg.id)
            if not user:
                logger.warning(f"Пользователь не найден {user_tg.username} {user_tg.id}")
                return None
            if user.active_subscriptions_count == 0:
                logger.warning(f"У пользователя нет активных подписок {user_tg.username} {user_tg.id}")
                return None
            return user.active_subscriptions


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
            unique_suffix = uuid.uuid4().hex[:6]
            tg_user_name = self.normalize_username(user_db.username)
            subscription_name = f"{tg_user_name}-{settings.LOGO_NAME}-{unique_suffix}"
            expire_date = datetime.now() + timedelta(days=settings.TRIAL_DAYS)
            # 3. Вызываем сервис для создания пользователя в Remnawave
            remna_user = await remna_service.create_user_subscription(
                telegram_id=user_db.telegram_id,
                subscription_name=subscription_name,
                expire_date=expire_date,
                status=SubscriptionStatus.ACTIVE
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
                remnawave_uuid=str(remna_user.uuid),
                remnawave_short_uuid=str(remna_user.short_uuid),
                subscription_url=remna_user.subscription_url,
                status=SubscriptionStatus.ACTIVE
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
            unique_suffix = uuid.uuid4().hex[:6]
            tg_user_name = self.normalize_username(user_db.username)
            subscription_name = f"{tg_user_name}-{settings.LOGO_NAME}-{unique_suffix}"
            expire_date = datetime.now()
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
                remnawave_uuid=str(remna_user.uuid),
                remnawave_short_uuid=str(remna_user.short_uuid),
                subscription_url=remna_user.subscription_url,
                status = SubscriptionStatus.DISABLED,
                tariff_id=tariff.id
            )
            return subscription

    async def get_by_remna_uuid(self, remna_uuid: str) -> Optional[Subscription]:
        """
        Находит локальную запись о подписке по ее UUID из Remnawave.

        :param remna_uuid: Полный или короткий UUID пользователя из Remnawave.
        :return: Объект Subscription или None.
        """
        async with get_session() as session:
            subscription = await Subscription.get_by_remna_uuid(session, remna_uuid)
            if not subscription:
                logger.warning(f"Попытка найти подписку по несуществующему remna_uuid: {remna_uuid}")
            return subscription

    # Здесь в будущем будут другие методы:
    # async def extend_subscription(self, sub_id: int, tariff_id: int) -> Optional[Subscription]: ...
    # async def deactivate_expired_subscriptions(self, bot: Bot): ...


# --- Создаем единственный экземпляр сервиса для всего приложения ---
subscription_service = SubscriptionService()