from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
from database.session import get_session
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



async def load_servers_from_json(file_path: str):
    """Загружает, обновляет, добавляет, деактивирует серверы из json"""
    async with get_session() as session:
        with open(file_path, "r", encoding="utf-8") as f:
            json_servers = json.load(f)

        # Получаем все текущие серверы
        existing_servers = await session.execute(select(Server))
        existing_servers = existing_servers.scalars().all()
        existing_servers_dict = {s.name: s for s in existing_servers}

        # Обновление или добавление серверов
        for json_server in json_servers:
            if json_server["name"] in existing_servers_dict:
                server = existing_servers_dict[json_server["name"]]
                server.api_url = json_server["api_url"]
                server.link_ip = json_server.get("link_ip")
                server.login = json_server.get("login")
                server.password = json_server.get("password")
                server.max_clients = json_server.get("max_clients", server.max_clients)
                server.current_clients = json_server.get("current_clients", server.current_clients)
                server.is_active = json_server.get("is_active", True)
            else:
                server = Server(**json_server)
                session.add(server)

        # Деактивация серверов, которых нет в JSON
        json_server_names = {s["name"] for s in json_servers}
        for server in existing_servers:
            if server.name not in json_server_names:
                server.is_active = False

        await session.commit()

