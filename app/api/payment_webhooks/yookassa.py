from fastapi import APIRouter, Request, Response, Header
from yookassa.domain.notification import WebhookNotification
import json

from app.logger import logger
from app.services.payment_service import confirm_payment_service, error_payment_service
from database.crud.crud_payment import get_payment_by_external_id
from database.session import get_session
from app.bot.utils.messages import (subscription_purchased_with_config_message, payment_cancelled_message)
from app.core.config import settings


yookassa_router = APIRouter(prefix=settings.PAYMENTS_PATH)

@yookassa_router.post("/yookassa")
async def yookassa_webhook(request: Request):
    """
    Принимает и обрабатывает вебхуки от ЮKassa.
    """
    try:
        event_json = await request.json()
        notification = WebhookNotification(event_json)
    except json.JSONDecodeError:
        logger.bind(source="payments").error("Ошибка декодирования JSON от ЮKassa")
        return Response(status_code=400)
    except Exception as e:
        logger.bind(source="payments").error(f"Невалидный объект уведомления от ЮKassa: {e}")
        return Response(status_code=400)

    payment_status = notification.object.status
    external_payment_id = notification.object.id

    logger.bind(source="payments").info(f"Получен вебхук от ЮKassa: ID={external_payment_id}, Статус={payment_status}")

    async with get_session() as session:
        # Находим наш внутренний платеж по внешнему ID
        internal_payment = await get_payment_by_external_id(session, external_payment_id)

        if not internal_payment:
            logger.bind(source="payments").error(f"Не найден платеж с external_id={external_payment_id} в нашей БД.")
            return Response(status_code=200)

        if internal_payment.status != "pending":
            logger.bind(source="payments").warning(f"Платеж {internal_payment.id} уже был обработан. Текущий статус: {internal_payment.status}")
            return Response(status_code=200)
        sub = internal_payment.subscription
        tariff = internal_payment.tariff
        if payment_status == 'succeeded':
            await confirm_payment_service(internal_payment.id)
            try:
                subscription_url = f"https://{settings.DOMAIN_API}{settings.SUBSCRIPTION_PATH}/{sub.access_key}"

                await settings.BOT.send_message(
                    chat_id=internal_payment.user_id,
                    text=subscription_purchased_with_config_message.format(
                        tariff_name=tariff.name,
                        sub_name=sub.service_name,
                        subscription_url=subscription_url,
                        logo_name=settings.LOGO_NAME
                    ),
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.bind(source="payments").error(f"Не удалось отправить уведомление об оплате пользователю {internal_payment.user_id}: {e}")

        elif payment_status in ['canceled', 'failed']:
            try:
                await error_payment_service(internal_payment.id)
                await settings.BOT.send_message(
                    chat_id=internal_payment.user_id,
                    text=payment_cancelled_message.format(
                        tariff_name=tariff.name
                    )
                )
            except Exception as e:
                logger.bind(source="payments").error(f"Не удалось отправить уведомление об оплате пользователю {internal_payment.user_id}: {e}")
    return Response(status_code=200)