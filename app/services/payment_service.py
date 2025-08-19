from app.services.generator_subscriptions import activate_subscription
from database.models import Payment, Tariff, Subscription, User
from aiogram.types import User as User_tg
from database.crud.crud_payment import create_payment, get_payment_by_id
from database.crud.crud_tariff import get_tariff_by_id
from database.crud.crud_subscription import get_subscription_by_id, create_subscription
from database.crud.crud_user import get_user_by_telegram_id
from database.enums import PaymentMethod
from app.payments.yookassa import create_payment_yookassa, cancel_yookassa_payment
from database.session import get_session
from app.logger import logger
import asyncio
from yookassa import Payment as YooPayment
from app.core.config import settings
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from app.bot.utils.messages import subscription_expiration_warning_message
from typing import List



async def create_payment_service(
        user: User_tg,
        tariff_id: int,
        method: str,
        sub_id: int = None,
) -> tuple[Payment, Tariff, Subscription, str] | None:

    """
    Создаёт платёж через нужную платёжную систему, сохраняет его в БД и возвращает объект и ссылку на оплату.
    """
    try:
        async with get_session() as session:
            tariff: Tariff = await get_tariff_by_id(session, tariff_id)
            if sub_id:
                subscription: Subscription = await get_subscription_by_id(session, sub_id)
            else:
                user_db = await get_user_by_telegram_id(session, user.id)
                subscription: Subscription = await create_subscription(
                    session=session,
                    user=user_db,
                    tariff_id=tariff_id,
                    is_active_status=False
                )
                sub_id = subscription.id

            if PaymentMethod.yookassa == method:
                method = PaymentMethod(method)
                external_id, payment_url = await create_payment_yookassa(tariff.price, tariff.name)
            if PaymentMethod.crypto == method:
                raise ValueError("Need add to payment crypto") # TODO Добавить оплату криптой
            payment: Payment = await create_payment(
                session=session,
                user_id=user.id,
                amount=tariff.price,
                method=method,
                tariff_id=tariff.id,
                subscription_id=sub_id,
                external_payment_id=external_id
            )
            await session.commit()
            await session.refresh(payment)
            return payment, tariff, subscription, payment_url
    except BaseException as ex:
        logger.error(f"Ошибка в создании платежа {ex}")
        return None


async def get_payment_status(payment: Payment):
    """
    Проверяет статус платежа по его id
    """
    method = payment.method
    external_id = payment.external_payment_id

    if method == "yookassa":
        yoo_payment = await asyncio.to_thread(YooPayment.find_one, external_id)
        status = yoo_payment.status
        if status == "succeeded":
            return "paid"
        if status in ['canceled', 'failed']:
            return "failed"
    if method == "crypto":
        pass
        # TODO сделать проверку крипты


async def confirm_payment_service(payment_id: int) -> bool:
    """
    Подтверждает оплату, продлевает подписку на количество дней согласно тарифу.
    Начисляет реферальное вознаграждение
    за ПЕРВУЮ покупку
    Активирует конфиги
    :param payment_id: ID платежа
    :return: True, если операция успешна, иначе False
    """
    async with get_session() as session:
        payment: Payment = await get_payment_by_id(session, payment_id)
        payment.status = "success"
        # генерим конфиги
        await activate_subscription(payment.subscription_id)
        # Получаем пользователя, который совершил покупку
        buyer: User = await get_user_by_telegram_id(session, payment.user_id)
        if buyer.inviter_id and not buyer.had_first_purchase:
            # Находим пригласившего
            inviter: User = await get_user_by_telegram_id(session, buyer.inviter_id)
            if inviter:
                # Рассчитываем вознаграждение
                commission_amount = int(payment.amount * (settings.REFERRAL_COMMISSION_PERCENT / 100))
                # Начисляем на баланс пригласившего
                inviter.balance += commission_amount
                logger.info(
                    f"Начислено реферальное вознаграждение: {commission_amount} RUB "
                    f"пользователю {inviter.telegram_id} за первую покупку от {buyer.telegram_id}"
                )
        buyer.had_first_purchase = True
        subscription = payment.subscription
        tariff = payment.tariff

        subscription.end_date += timedelta(days=tariff.duration_days)
        await session.commit()
        return True

async def error_payment_service(payment_id: int) -> bool:
    """
    Сменяет статус платежа на ошибку.
    :param payment_id:
    :return:
    """
    async with get_session() as session:
        payment: Payment = await get_payment_by_id(session, payment_id)
        # Отмена в зависимости от метода оплаты в платежной системе
        # if payment.method == PaymentMethod.yookassa:
        #     try:
        #         if payment.external_payment_id:
        #             await cancel_yookassa_payment(payment.external_payment_id)
        #     except Exception as e:
        #         logger.error(f"Ошибка при отмене платежа {payment_id} в ЮKassa: {e}")
        #         return False
        # if payment.method == PaymentMethod.crypto:
        #     # TODO Сделать отмену для крипты
        #     pass
        payment.status = "failed"
        await session.commit()
        return True


async def send_expiration_warnings(bot: Bot):
    """
    Находит подписки, истекающие на следующий день, и отправляет пользователям
    уведомление с предложением продлить.
    """
    logger.info("Scheduler: Запуск задачи по отправке уведомлений об окончании подписки...")

    now = datetime.now()
    tomorrow_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    day_after_tomorrow_start = (now + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)

    async with get_session() as session:
        stmt = (
            select(Subscription)
            .options(selectinload(Subscription.user))  # Подгружаем пользователя, чтобы знать его telegram_id
            .where(
                Subscription.end_date >= tomorrow_start,
                Subscription.end_date < day_after_tomorrow_start,
                Subscription.is_active == True
            )
        )
        result = await session.execute(stmt)
        subscriptions_to_notify: List[Subscription] = result.scalars().all()

        if not subscriptions_to_notify:
            logger.info("Scheduler: Не найдено подписок для отправки уведомлений.")
            return

        logger.info(f"Scheduler: Найдено {len(subscriptions_to_notify)} подписок для уведомления.")

        sent_count = 0
        for sub in subscriptions_to_notify:
            try:
                await bot.send_message(
                    chat_id=sub.user.telegram_id,
                    text=subscription_expiration_warning_message.format(sub_name=sub.service_name)
                )
                sent_count += 1
                await asyncio.sleep(0.1)
            except (TelegramBadRequest, TelegramForbiddenError) as e:
                logger.warning(f"Scheduler: Не удалось отправить уведомление пользователю {sub.user.telegram_id}: {e}")
            except Exception as e:
                logger.error(
                    f"Scheduler: Непредвиденная ошибка при отправке уведомления пользователю {sub.user.telegram_id}: {e}")

    logger.info(f"Scheduler: Успешно отправлено {sent_count} из {len(subscriptions_to_notify)} уведомлений.")