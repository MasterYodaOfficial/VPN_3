from fastapi import APIRouter, Request, Response, Header
from yookassa.domain.notification import WebhookNotification
import json

from app.logger import logger
from app.services.payment_service import payment_service
from database.session import get_session
from app.bot.utils.messages import (subscription_purchased_with_config_message, payment_cancelled_message)
from app.core.config import settings
from app.bot.keyboards.inlines import get_config_webapp_button


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
        logger.bind(source="payments_gateways").error("Ошибка декодирования JSON от ЮKassa")
        return Response(status_code=400)
    except Exception as e:
        logger.bind(source="payments_gateways").error(f"Невалидный объект уведомления от ЮKassa: {e}")
        return Response(status_code=400)

    payment_status = notification.object.status
    external_payment_id = notification.object.id

    logger.bind(source="payments_gateways").info(f"Получен вебхук от ЮKassa: ID={external_payment_id}, Статус={payment_status}")
    # Находим наш внутренний платеж по внешнему ID
    internal_payment = await payment_service.get_by_external_id(external_payment_id)

    if not internal_payment:
        logger.bind(source="payments_gateways").error(f"Не найден платеж с external_id={external_payment_id} в нашей БД.")
        return Response(status_code=200)
    if internal_payment.status != "pending":
        logger.bind(source="payments_gateways").warning(f"Платеж {internal_payment.id} уже был обработан. Текущий статус: {internal_payment.status}")
        return Response(status_code=200)
    subscription = internal_payment.subscription
    tariff = internal_payment.tariff
    if payment_status == 'succeeded':
        await payment_service.confirm_payment(internal_payment.id)
        try:
            await settings.BOT.send_message(
                chat_id=internal_payment.user_id,
                text=subscription_purchased_with_config_message.format(
                    tariff_name=tariff.name,
                    sub_name=subscription.subscription_name,
                    logo_name=settings.LOGO_NAME
                ),
                message_effect_id="5159385139981059251",
                reply_markup=get_config_webapp_button(subscription.subscription_url)
            )
        except Exception as e:
            logger.bind(source="payments_gateways").error(f"Не удалось отправить уведомление об оплате пользователю {internal_payment.user_id}: {e}")

    elif payment_status in ['canceled', 'failed']:
        try:
            await payment_service.fail_payment(internal_payment.id)
            await settings.BOT.send_message(
                chat_id=internal_payment.user_id,
                text=payment_cancelled_message.format(
                    tariff_name=tariff.name
                )
            )
        except Exception as e:
            logger.bind(source="payments_gateways").error(f"Не удалось отправить уведомление об оплате пользователю {internal_payment.user_id}: {e}")
    return Response(status_code=200)