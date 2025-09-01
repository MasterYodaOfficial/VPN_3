from datetime import datetime
from typing import Optional, List

from app.core.config import settings
from app.logger import logger
from remnawave.models import (
    CreateUserRequestDto,
    UpdateUserRequestDto,
    UserResponseDto,
)


class RemnaService:
    """
    Класс-сервис для инкапсуляции всей логики взаимодействия с Remnawave API.
    Предоставляет простые методы для других частей приложения.
    """

    async def _get_all_squad_uuids(self) -> List[str]:
        """Приватный метод для получения UUID всех отрядов в панели."""
        if not settings.REMNA_SDK:
            return []
        try:
            response = await settings.REMNA_SDK.internal_squads.get_internal_squads()
            if response and response.internal_squads:
                return [str(squad.uuid) for squad in response.internal_squads]
        except Exception as e:
            logger.error(f"Не удалось получить список отрядов из Remnawave: {e}")
        return []

    async def create_user_subscription(
        self,
        telegram_id: int,
        subscription_name: str,
        expire_date: datetime
    ) -> Optional[UserResponseDto]:
        """
        Создает нового пользователя в Remnawave и сразу добавляет его во все отряды.
        Это основной метод для создания новой подписки.
        """
        if not settings.REMNA_SDK:
            logger.critical("Попытка создать пользователя Remnawave, но SDK не инициализирован.")
            return None

        try:
            all_squads = await self._get_all_squad_uuids()
            if not all_squads:
                logger.warning("В Remnawave не найдено ни одного отряда (squad). Пользователь будет создан без доступа к серверам.")

            create_dto = CreateUserRequestDto(
                username=subscription_name,
                telegram_id=telegram_id,
                description=f"Bot user, tg_id: {telegram_id}",
                expire_at=expire_date,
                active_internal_squads=all_squads
            )

            response = await settings.REMNA_SDK.users.create_user(create_dto)

            if response:
                logger.info(f"Успешно создан пользователь в Remnawave: {response.username} (uuid: {response.uuid})")
                return response
            return None

        except Exception as e:
            logger.error(f"Ошибка при создании пользователя Remnawave для tg_id={telegram_id}: {e}")
            return None

    async def update_user_expiration(
        self,
        remna_uuid: str,
        new_expire_date: datetime
    ) -> Optional[UserResponseDto]:
        """
        Обновляет (продлевает) дату окончания подписки для существующего пользователя.
        """
        if not settings.REMNA_SDK:
            logger.critical("Попытка обновить пользователя Remnawave, но SDK не инициализирован.")
            return None

        try:
            update_dto = UpdateUserRequestDto(
                uuid=remna_uuid,
                expire_at=new_expire_date
            )
            response = await settings.REMNA_SDK.users.update_user(update_dto)

            if response:
                logger.info(f"Успешно обновлена дата подписки для Remnawave uuid={remna_uuid}")
                return response
            return None
        except Exception as e:
            logger.error(f"Ошибка при обновлении подписки для Remnawave uuid={remna_uuid}: {e}")
            return None

# --- Создаем единственный экземпляр сервиса ---
remna_service = RemnaService()