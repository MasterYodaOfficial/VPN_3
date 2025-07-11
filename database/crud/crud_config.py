from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Config
from sqlalchemy import delete

async def create_config(
    session: AsyncSession,
    subscription_id: int,
    server_id: int,
    config_data: str
) -> Config:
    """Создание конфига для подписки на конкретном сервере."""
    new_config = Config(
        subscription_id=subscription_id,
        server_id=server_id,
        config_data=config_data
    )
    session.add(new_config)
    await session.commit()
    await session.refresh(new_config)
    return new_config


async def delete_config_by_id(session: AsyncSession, config_id: int) -> None:
    stmt = delete(Config).where(Config.id == config_id)
    await session.execute(stmt)
    await session.commit()


async def delete_configs_by_subscription_id(session: AsyncSession, subscription_id: int) -> None:
    stmt = delete(Config).where(Config.subscription_id == subscription_id)
    await session.execute(stmt)
    await session.commit()

