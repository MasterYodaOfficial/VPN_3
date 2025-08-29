from typing import Dict, Any
from app.logger import logger
from database.session import get_session
from app.core.config import settings
from app.bot.utils.messages import subscription_deactivated_message, subscription_expiration_warning_message
from app.services.subscription_service import subscription_service



class UserEventsHandler:
    """
    Класс для обработки всех событий, связанных с пользователями (user.*).
    """

    async def user_expired(self, payload: Dict[str, Any]):
        user_data = payload.get("data", {})
        remna_uuid = user_data.get("shortUuid")
        telegram_id = user_data.get("telegramId")
        subscription_name = user_data.get("username")
        logger.info(f"WEBHOOK: Получено событие 'user.expired' для подписки {subscription_name} ({telegram_id})")

        # Логика: деактивируем подписку в нашей БД и отправляем уведомление
        subscription = await subscription_service.get_by_remna_uuid(remna_uuid)
        if not subscription:
            logger.warning(f"Получен вебхук 'user.expired', но подписка с remna_uuid={remna_uuid} не найдена в локальной БД.")
            return
        if subscription and subscription.is_active:
            async with get_session() as session:
                await subscription.update(session, is_active=False)
        try:
            await settings.BOT.send_message(
                chat_id=subscription.telegram_id,
                text=subscription_deactivated_message.format(
                    sub_name=subscription.subscription_name)
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление о 'user.expired' пользователю {telegram_id}: {e}")

    async def user_expires_in_24_hours(self, payload: Dict[str, Any]):
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
            await settings.BOT.send_message(
                chat_id=subscription.telegram_id,
                text=subscription_expiration_warning_message.format(sub_name=subscription.subscription_name)
            )
        except Exception as e:
            logger.warning(
                f"Не удалось отправить уведомление о 'user.expires_in_24_hours' пользователю {telegram_id}: {e}")

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