from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Type

from aiogram.types import User as UserTG
from alembic.util import status

from app.core.config import settings
from app.logger import logger

# --- Импортируем наши шлюзы и сервисы ---
from app.payments_gateways.base_gateway import BaseGateway
from app.payments_gateways.yookassa_gateway import YooKassaGateway
from app.payments_gateways.telegram_stars_gateway import TelegramStarsGateway
from app.services.subscription_service import subscription_service

# --- Импортируем модели напрямую ---
from database.enums import PaymentMethod, SubscriptionStatus
from database.models import Payment, Subscription, Tariff, User
from database.session import get_session
from app.services.remnawave_service import remna_service

class PaymentService:
    """
    Класс-сервис для управления бизнес-логикой, связанной с платежами.
    """

    def __init__(self):
        self.gateways: Dict[PaymentMethod, Type[BaseGateway]] = {}
        if settings.YOOKASSA_TOKEN and settings.YOOKASSA_SHOP_ID:
            self.gateways[PaymentMethod.yookassa] = YooKassaGateway
        if settings.TELEGRAM_STARS:
            self.gateways[PaymentMethod.tg_stars] = TelegramStarsGateway
        logger.info(f"Зарегистрированные платежные шлюзы: {[gw.name for gw in self.gateways.keys()]}")

    def _get_gateway(self, method: PaymentMethod) -> Optional[BaseGateway]:
        gateway_class = self.gateways.get(method)
        return gateway_class() if gateway_class else None

    async def get_by_external_id(self, external_id: str) -> Optional[Payment]:
        """
        Находит платеж в базе данных по его внешнему идентификатору
        (ID из ЮKassa или payload из Telegram Stars).

        Этот метод "жадно" подгружает связанные данные (подписку, тариф, пользователя),
        чтобы избежать дополнительных запросов к БД после.

        :param external_id: Внешний ID платежа.
        :return: Объект Payment или None, если платеж не найден.
        """
        async with get_session() as session:
            payment = await Payment.get_by_external_id(session, external_id)
            if not payment:
                logger.warning(f"Попытка найти платеж с несуществующим external_id: {external_id}")
            return payment


    async def create_payment_link(
            self,
            user_tg: UserTG,
            tariff_id: int,
            method_str: str,
            sub_id_to_extend: Optional[int] = None,
    ) -> Optional[Tuple[Payment, Tariff, Subscription, str]]:
        """
        Основной метод для создания платежа.
        1. Находит или создает подписку.
        2. Выбирает нужный платежный шлюз.
        3. Создает платеж во внешней системе и возвращает ссылку на оплату.
        4. Сохраняет запись о платеже в нашей БД.
        """
        try:
            method = PaymentMethod(method_str)
            gateway = self._get_gateway(method)
            if not gateway:
                logger.error(f"Платежный шлюз '{method_str}' не настроен.")
                return None

            async with get_session() as session:
                tariff = await Tariff.get_by_id(session, tariff_id)
                user_db = await User.get_by_telegram_id(session, user_tg.id)
                if not tariff or not user_db:
                    logger.error("Тариф или пользователь не найдены при создании платежа.")
                    return None

                if sub_id_to_extend:
                    subscription = await Subscription.get_by_id(session, sub_id_to_extend)
                    if not subscription or subscription.telegram_id != user_tg.id:
                        logger.error("Подписка для продления не найдена.")
                        return None
                else:
                    subscription = await subscription_service.create_pending_subscription(user_db, tariff)

                payment_details = await gateway.create_payment(tariff)
                if not payment_details:
                    logger.error(f"Шлюз '{method_str}' не смог создать платеж.")
                    return None

                external_id, payment_url = payment_details

                payment = await Payment.create(
                    session=session,
                    user_id=user_tg.id, amount=tariff.price, method=method,
                    tariff_id=tariff.id, subscription_id=subscription.id,
                    external_payment_id=external_id
                )
                return payment, tariff, subscription, payment_url

        except Exception as e:
            logger.error(f"Ошибка при создании ссылки на оплату для пользователя {user_tg.id}: {e}")
            return None

    async def confirm_payment(self, payment_id: int) -> Optional[Payment]:
        """
        Подтверждает оплату, продлевает подписку и начисляет реферальные бонусы.
        Вызывается из вебхуков (ЮKassa) или хендлеров (Telegram Stars).
        """
        async with get_session() as session:
            payment = await Payment.get_by_id_with_relations(session, payment_id)
            if not payment or payment.status != "pending":
                logger.warning(f"Попытка подтвердить уже обработанный или несуществующий платеж ID: {payment_id}")
                return None

            # 1. Обновляем подписку
            subscription: Subscription = payment.subscription
            tariff: Tariff = payment.tariff
            current_end_date = subscription.end_date if subscription.status == SubscriptionStatus.ACTIVE and subscription.end_date > datetime.now() else datetime.now()
            new_end_date = current_end_date + timedelta(days=tariff.duration_days)

            # Обновляем дату в Remnawave
            await remna_service.update_user_expiration(subscription.remnawave_uuid, new_end_date)

            # Обновляем дату и статус в нашей БД
            await subscription.update(session, end_date=new_end_date, status=SubscriptionStatus.ACTIVE)

            # 2. Обновляем статус платежа
            payment.status = "succeeded"  # Используем succeeded для консистентности с YooKassa

            # 3. Начисляем реферальный бонус (если это первая покупка)
            buyer: User = payment.user
            if buyer.inviter_id and not buyer.had_first_purchase:
                inviter = await User.get_by_telegram_id(session, buyer.inviter_id)
                if inviter:
                    commission = int(payment.amount * (settings.REFERRAL_COMMISSION_PERCENT / 100))
                    await inviter.update(session, balance=inviter.balance + commission)
                    logger.info(f"Начислен реф. бонус {commission}р. пользователю {inviter.telegram_id}")

            await buyer.update(session, had_first_purchase=True)

            await session.commit()
            logger.info(f"Платеж ID:{payment.id} успешно подтвержден.")
            return payment

    async def fail_payment(self, payment_id: int) -> Optional[Payment]:
        """Отмечает платеж как отмененный или неудачный."""
        async with get_session() as session:
            payment = await session.get(Payment, payment_id)
            if not payment or payment.status != "pending":
                logger.error("Платеж не найден или статус не в ожидании оплаты")
                return None

            await payment.update(session, status="canceled")
            logger.warning(f"Платеж ID:{payment.id} отмечен как отмененный.")
            return payment


# --- Создаем единственный экземпляр сервиса ---
payment_service = PaymentService()