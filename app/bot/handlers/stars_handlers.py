
from aiogram.types import Message, PreCheckoutQuery


from app.logger import logger
from app.core.config import settings
from app.services.payment_service import confirm_payment_service
from app.bot.utils.messages import subscription_purchased_with_config_message
from database.crud.crud_payment import get_payment_by_external_id
from database.session import get_session


async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    """
    Подтверждает готовность к приему платежа. Telegram отправляет этот запрос
    сразу после того, как пользователь нажимает "Оплатить".
    """
    external_id = pre_checkout_query.invoice_payload
    logger.info(f"Получен PreCheckoutQuery с external_id/payload: {external_id}")
    async with get_session() as session:
        payment = await get_payment_by_external_id(session, external_id)
        if not payment:
            error_message = "Платеж не найден в системе. Пожалуйста, создайте его заново."
            logger.warning(f"PreCheckoutQuery отклонен: платеж с payload {payload} не найден.")
            await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False, error_message=error_message)
            return
        if payment.status != "pending":
            error_message = "Этот платеж уже был обработан. Пожалуйста, создайте новый."
            logger.warning(f"PreCheckoutQuery отклонен: платеж {payment.id} уже имеет статус {payment.status}.")
            await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False, error_message=error_message)
            return
    await settings.BOT.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


async def successful_payment_handler(message: Message):
    """
    Обрабатывает УСПЕШНЫЙ платеж, полученный через Telegram Stars.
    Этот хендлер вызывается ПОСЛЕ того, как пользователь завершил оплату.
    """
    payment_info = message.successful_payment
    external_id = payment_info.invoice_payload

    logger.info(
        f"Получен успешный платеж Stars на {payment_info.total_amount} {payment_info.currency} "
        f"с payload: {external_id} от пользователя {message.from_user.id}"
    )
    async with get_session() as session:
        payment = await get_payment_by_external_id(session, external_id)

        if not payment:
            logger.error(f"Критическая ошибка: не найден платеж с external_id/payload={external_id} после успешной оплаты.")
            await message.answer("Произошла ошибка при обработке вашего платежа. Пожалуйста, свяжитесь с поддержкой.")
            return
        await confirm_payment_service(payment.id)
        sub = payment.subscription
        tariff = payment.tariff
        subscription_url = f"https://{settings.DOMAIN_API}{settings.SUBSCRIPTION_PATH}/{sub.access_key}"

        await message.answer(
            text=subscription_purchased_with_config_message.format(
                tariff_name=tariff.name,
                sub_name=sub.service_name,
                subscription_url=subscription_url,
                logo_name=settings.LOGO_NAME
            ),
            message_effect_id="5159385139981059251",
            disable_web_page_preview=True
        )