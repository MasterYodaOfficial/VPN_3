from typing import Optional
from app.logger import logger
from database.models import Subscription, SubscriptionStatus
from remnawave.models.users import UserResponseDto


def map_user_dto_to_subscription(dto: UserResponseDto, sub: Subscription) -> Optional[Subscription]:
    """
    Безопасно обновляет Subscription по данным из Remnawave UserResponseDto,
    только если они пришли не None.
    """
    try:
        if dto.telegram_id is not None:
            sub.telegram_id = dto.telegram_id

        if dto.created_at is not None:
            sub.start_date = dto.created_at

        if dto.expire_at is not None:
            sub.end_date = dto.expire_at

        if dto.uuid is not None:
            sub.remnawave_uuid = str(dto.uuid)
        if dto.short_uuid is not None:
            sub.remnawave_short_uuid = dto.short_uuid

        if dto.username is not None:
            sub.subscription_name = dto.username
        if dto.subscription_url is not None:
            sub.subscription_url = dto.subscription_url

        if getattr(dto, "description", None) is not None:
            sub.description = dto.description

        if getattr(dto, "hwidDeviceLimit", None) is not None:
            sub.hwidDeviceLimit = dto.hwidDeviceLimit

        if getattr(dto, "first_connected", None) is not None:
            sub.first_connected = dto.first_connected

        if getattr(dto, "updated_at", None) is not None:
            sub.updated_at = dto.updated_at

        if getattr(dto, "status", None) is not None:
            try:
                sub.status = SubscriptionStatus(dto.status.value)
            except ValueError:
                logger.warning(f"Несовпадение статуса, нужно добавить: {dto.status.value}")
                pass

        return sub
    except BaseException as ex:
        logger.error(f"Ошибка обновления Subscription из Remnawave UserResponseDto {ex}")
        return None