from abc import ABC, abstractmethod
from typing import Tuple, Optional
from database.models import Tariff


class BaseGateway(ABC):
    """
    Абстрактный базовый класс для всех платежных шлюзов.
    Определяет единый интерфейс для создания и отмены платежей.
    """

    @abstractmethod
    async def create_payment(
        self,
        tariff: Tariff
    ) -> Optional[Tuple[str, str]]:
        """
        Создает платеж во внешней системе.

        :param tariff: Объект тарифа, который оплачивается.
        :param user_id: Telegram ID пользователя для возможной идентификации.
        :return: Кортеж (external_id, payment_url) или None в случае ошибки.
        """
        pass
