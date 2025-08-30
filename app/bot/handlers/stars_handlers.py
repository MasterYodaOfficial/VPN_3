from aiogram.types import Message, PreCheckoutQuery
from app.logger import logger
from app.core.config import settings
from app.services.payment_service import payment_service
from app.bot.keyboards.inlines import get_config_webapp_button
from aiogram.utils.i18n import gettext as _

async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    """
    Подтверждает готовность к приему платежа. Telegram отправляет этот запрос
    сразу после того, как пользователь нажимает "Оплатить".
    """
    external_id = pre_checkout_query.invoice_payload
    logger.info(f"Получен PreCheckoutQuery с external_id/payload: {external_id}")
    payment = await payment_service.get_by_external_id(external_id)
    if not payment:
        # "Платеж не найден в системе. Пожалуйста, создайте его заново."
        error_payment_not_found = _("payment_not_found")
        logger.warning(f"PreCheckoutQuery отклонен: платеж с payload {payload} не найден.")
        await settings.BOT.answer_pre_checkout_query(pre_checkout_query.id, ok=False, error_message=error_payment_not_found)
        return
    if payment.status != "pending":
        # "Этот платеж уже был обработан. Пожалуйста, создайте новый."
        error_payment_done = _("payment_done")
        logger.warning(f"PreCheckoutQuery отклонен: платеж {payment.id} уже имеет статус {payment.status}.")
        await settings.BOT.answer_pre_checkout_query(pre_checkout_query.id, ok=False, error_message=error_payment_done)
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

    payment = await payment_service.get_by_external_id(external_id)

    if not payment:
        logger.error(f"Критическая ошибка: не найден платеж с external_id/payload={external_id} после успешной оплаты.")
        # Произошла ошибка при обработке вашего платежа. Пожалуйста, свяжитесь с поддержкой.
        await message.answer(_("error_payment"))
        return
    await payment_service.confirm_payment(payment.id)
    subscription = payment.subscription
    tariff = payment.tariff

    await message.answer(
        text=_("subscription_purchased_with_config_message").format(
            tariff_name=tariff.name,
            sub_name=subscription.subscription_name,
            logo_name=settings.LOGO_NAME
        ),
        message_effect_id="5159385139981059251",
        reply_markup=get_config_webapp_button(subscription.subscription_url)
    )
