from fastapi import APIRouter, Request, Response, Header
from yookassa.domain.notification import WebhookNotification
import json

from app.logger import logger
from app.services.payment_service import confirm_payment_service, error_payment_service
from database.crud.crud_payment import get_payment_by_external_id
from database.session import get_session
from app.bot.utils.messages import subscription_purchased_with_config_message
from app.core.config import settings


yookassa_router = APIRouter(prefix=settings.PAYMENTS_PATH)

@yookassa_router.post("/yookassa")
async def yookassa_webhook(request: Request):
    """
    Принимает и обрабатывает вебхуки от ЮKassa.
    """
    # Проверка IP-адреса (рекомендуется ЮKassa для безопасности)
    # x_real_ip = request.headers.get("x-real-ip")
    # yookassa_ips = ["185.71.76.0/27", "185.71.77.0/27", "77.75.153.0/25", "77.75.154.128/25", "2a02:5180::/32"]
    # if x_real_ip not in yookassa_ips: # Упрощенная проверка, нужна реализация проверки подсети
    #     logger.warning(f"Получен вебхук с недоверенного IP: {x_real_ip}")
    #     return Response(status_code=403)

    try:
        event_json = await request.json()
        notification = WebhookNotification(event_json)
    except json.JSONDecodeError:
        logger.error("Ошибка декодирования JSON от ЮKassa")
        return Response(status_code=400)
    except Exception as e:
        logger.error(f"Невалидный объект уведомления от ЮKassa: {e}")
        return Response(status_code=400)

    payment_status = notification.object.status
    external_payment_id = notification.object.id

    logger.info(f"Получен вебхук от ЮKassa: ID={external_payment_id}, Статус={payment_status}")

    async with get_session() as session:
        # Находим наш внутренний платеж по внешнему ID
        internal_payment = await get_payment_by_external_id(session, external_payment_id)

        if not internal_payment:
            logger.error(f"Не найден платеж с external_id={external_payment_id} в нашей БД.")
            return Response(status_code=200)  # Отвечаем 200, чтобы ЮKassa не повторяла запрос

        # Обрабатываем только если статус еще 'pending'
        if internal_payment.status != "pending":
            logger.warning(f"Платеж {internal_payment.id} уже был обработан. Текущий статус: {internal_payment.status}")
            return Response(status_code=200)

        if payment_status == 'succeeded':
            await confirm_payment_service(internal_payment.id)

            # --- Отправка уведомления пользователю ---
            try:
                sub = internal_payment.subscription
                tariff = internal_payment.tariff
                subscription_url = f"https://{settings.DOMAIN_API}{settings.SUBSCRIPTION_PATH}/{sub.access_key}"

                await settings.BOT.send_message(
                    chat_id=internal_payment.user_id,
                    text=subscription_purchased_with_config_message.format(
                        tariff_name=tariff.name,
                        sub_name=sub.service_name,
                        subscription_url=subscription_url,
                        logo_name=settings.LOGO_NAME
                    )
                )
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление об оплате пользователю {internal_payment.user_id}: {e}")

        elif payment_status in ['canceled', 'failed']:
            await error_payment_service(internal_payment.id)
            # Здесь можно отправить уведомление о неудачной оплате, но это не обязательно

    return Response(status_code=200)