from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import Server


async def get_least_loaded_servers(session: AsyncSession, limit: int = 10) -> list[Server]:
    """Достает 10 менее загруженных серверов"""
    stmt = (
        select(Server)
        .where(Server.is_active == True)
        .order_by(Server.current_clients.asc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    servers: list[Server] = result.scalars().all()
    return servers


async def get_server_by_id(session: AsyncSession, server_id: int) -> Server | None:
    """Возвращает сервер по его ID или None, если не найден."""
    result = await session.execute(
        select(Server).where(Server.id == server_id)
    )
    return result.scalar_one_or_none()
