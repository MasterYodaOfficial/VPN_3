from typing import Dict, Any, Optional
from app.logger import logger
from database.session import get_session
from app.core.config import settings
from app.services.subscription_service import subscription_service
from database.models import User, Subscription
from app.services.user_service import _generate_referral_code
from app.bot.keyboards.inlines import get_config_webapp_button
from app.bot.middlewares.i18n import i18n
from aiogram.utils.i18n import gettext as _
from database.enums import SubscriptionStatus


class UserEventsHandler:
    """
    Класс для обработки всех событий, связанных с пользователями (user.*).
    """

    async def created(self, payload: Dict[str, Any]):
        user_data = payload.get("data", {})
        remna_uuid = user_data.get("uuid")

        if not remna_uuid:
            logger.warning("Вебхук 'user.created' пришел с неполными данными. Обработка невозможна.")
            return

        async with get_session() as session:
            existing_sub = await Subscription.get_by_remna_uuid(session, remna_uuid)
            if existing_sub:
                logger.info(f"Подписка с remna_uuid={remna_uuid} уже существует. Синхронизация не требуется.")
                return
            subscription_from_remna = await settings.REMNA_SDK.users.get_user_by_uuid(remna_uuid)
            logger.info(f"WEBHOOK: 'user.created' для {subscription_from_remna.username}")
            if not subscription_from_remna.telegram_id:
                logger.info(f"Подписка с remna_uuid={remna_uuid} без телеграмма")
                return
            user_db = await User.get_by_telegram_id(session, subscription_from_remna.telegram_id)
            if not user_db:
                logger.info(f"Пользователь с tg_id={subscription_from_remna.telegram_id} не найден. Создаем нового.")
                while True:
                    new_ref_code = _generate_referral_code()
                    if not await User.get_by_referral_code(session, new_ref_code): break

                user_db = await User.create(
                    session=session, telegram_id=subscription_from_remna.telegram_id,
                    username=subscription_from_remna.username, referral_code=new_ref_code,
                    is_admin=(subscription_from_remna.telegram_id in settings.ADMIN_IDS)
                )
            new_subscription = await Subscription.create(
                session=session, telegram_id=subscription_from_remna.telegram_id,
                start_date=subscription_from_remna.created_at,
                end_date=subscription_from_remna.expire_at,
                subscription_name=subscription_from_remna.username,
                remnawave_uuid=str(subscription_from_remna.uuid),
                remnawave_short_uuid=subscription_from_remna.short_uuid,
                subscription_url=subscription_from_remna.subscription_url,
                status=SubscriptionStatus.ACTIVE
            )
            logger.info(f"Создана локальная подписка ID:{new_subscription.id} для синхронизации с Remnawave.")

            try:
                i18n.current_locale = user_db.language_code
                with i18n.context():
                    await settings.BOT.send_message(
                        chat_id=subscription_from_remna.telegram_id,
                        text=_("welcome_message_universal").format(
                            logo_name=settings.LOGO_NAME
                        ),
                        reply_markup=get_config_webapp_button(subscription_from_remna.subscription_url)
                    )
                    logger.info(f"Отправлено приветственное сообщение пользователю {subscription_from_remna.telegram_id}.")
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение пользователю {subscription_from_remna.telegram_id}: {e}")


    async def modified(self, payload: Dict[str, Any]):
        user_data = payload.get("data", {})
        remna_uuid = user_data.get("uuid")
        subscription_from_remna = await settings.REMNA_SDK.users.get_user_by_uuid(remna_uuid)
        logger.info(f"WEBHOOK: Получено событие 'user.modified' для подписки {subscription_from_remna.username} ({subscription_from_remna.telegram_id})")
        async with get_session() as session:
            subscription_from_db = await Subscription.get_by_remna_uuid(session, remna_uuid)
            if subscription_from_db:
                await subscription_from_db.update(
                    session=session,
                    end_date=subscription_from_remna.expire_at
                )
                logger.info(f"Данные обновлены {subscription_from_remna.username} {subscription_from_remna.expire_at}")


    async def expired(self, payload: Dict[str, Any]):
        user_data = payload.get("data", {})
        remna_uuid = user_data.get("shortUuid")
        telegram_id = user_data.get("telegramId")
        subscription_name = user_data.get("username")
        logger.info(f"WEBHOOK: Получено событие 'user.expired' для подписки {subscription_name} ({telegram_id})")

        # Логика: деактивируем подписку в нашей БД и отправляем уведомление
        async with get_session() as session:  # <-- Открываем сессию ОДИН РАЗ
            subscription = await Subscription.get_by_remna_uuid(session, remna_uuid)

            if not subscription:
                logger.warning(f"Получен вебхук 'user.expired', но подписка с remna_uuid={remna_uuid} не найдена.")
                return

            if subscription.status == SubscriptionStatus.ACTIVE:
                await subscription.update(session, status=SubscriptionStatus.DISABLED)
                try:
                    i18n.current_locale = subscription.user.language_code
                    with i18n.context():
                        await settings.BOT.send_message(
                            chat_id=subscription.telegram_id,
                            text=_("subscription_deactivated_message").format(
                                sub_name=subscription.subscription_name)
                        )
                except Exception as e:
                    logger.warning(f"Не удалось отправить уведомление о 'user.expired' пользователю {telegram_id}: {e}")

    async def expires_in_24_hours(self, payload: Dict[str, Any]):
        user_data = payload.get("data", {})
        remna_uuid = user_data.get("shortUuid")
        telegram_id = user_data.get("telegramId")
        subscription_name = user_data.get("username")
        logger.info(f"WEBHOOK: Получено событие 'user.expires_in_24_hours' для {subscription_name} ({telegram_id})")

        # Логика: отправляем уведомление о скором окончании
        subscription = await subscription_service.get_by_remna_uuid(remna_uuid)
        if not subscription:
            logger.warning(f"Получен вебхук 'user.expires_in_24_hours', но подписка с remna_uuid={remna_uuid} не найдена в локальной БД.")
            return
        try:
            i18n.current_locale = subscription.user.language_code
            with i18n.context():
                await settings.BOT.send_message(
                    chat_id=subscription.telegram_id,
                    text=("subscription_expiration_warning_message").format(sub_name=subscription.subscription_name)
                )
        except Exception as e:
            logger.warning(
                f"Не удалось отправить уведомление о 'user.expires_in_24_hours' пользователю {subscription.telegram_id}: {e}")

    async def _unhandled_event(self, event_name: str, payload: Dict[str, Any]):
        """Обрабатывает любое другое событие пользователя, для которого нет метода."""
        logger.debug(f"Получено необработанное событие пользователя: {event_name}")


class WebhookService:
    """
    Сервис-диспетчер, который принимает вебхуки и направляет их
    в соответствующий обработчик.
    """

    def __init__(self):
        self.user_handler = UserEventsHandler()
        # В будущем:
        # self.node_handler = NodeEventsHandler()
        # self.service_handler = ServiceEventsHandler()

    async def process_webhook(self, payload: Dict[str, Any]):
        event_name = payload.get("event")
        if not event_name:
            logger.warning("Получен вебхук без поля 'event'.")
            return

        try:
            event_category, event_action = event_name.split('.', 1)
        except ValueError:
            logger.warning(f"Некорректный формат события в вебхуке: {event_name}")
            return

        handler = None
        if event_category == "user":
            handler = self.user_handler
        # elif event_category == "node":
        #     handler = self.node_handler
        else:
            logger.info(f"Получен вебхук для неподдерживаемой категории: {event_category}")
            return

        # Пытаемся найти метод, который точно соответствует имени события
        # (например, для 'user.expires_in_24_hours' ищем метод 'user_expires_in_24_hours')
        method_name = event_action.replace('.', '_')
        handler_method = getattr(handler, method_name, None)

        if handler_method and callable(handler_method):
            # Если метод найден, вызываем его с одним аргументом
            await handler_method(payload)
        else:
            # Если конкретный метод не найден, вызываем общий обработчик _unhandled_event
            # с ДВУМЯ аргументами
            await handler._unhandled_event(event_name, payload)


# --- Единственный экземпляр сервиса ---
webhook_service = WebhookService()