from aiogram.types import  User
from database.models import Server, Subscription
from database.crud.crud_subscription import create_subscription, get_user_subscriptions
from database.crud.crud_server import get_least_loaded_servers
from database.crud.crud_config import create_config
from database.session import get_session
from typing import List, Tuple, Optional
from bot.utils.xui_api_deepseek import XUIHandler
import asyncio



async def create_server_config(
        server: Server,
        subscription: Subscription,
        email: str,
        uid: str
) -> Optional[str | None]:
    """Создает конфиг на одном сервере и возвращает результат"""
    try:
        handler = XUIHandler(
            panel_url=server.api_url,
            username=server.login,
            password=server.password
        )
        async with handler:
            # Создаем клиента
            await handler.add_client_vless(email, uid)
            # Получаем конфигурацию
            config = await handler.get_conf_user_vless(email)
            async with get_session() as ses:
                await create_config(
                    session=ses,
                    subscription_id=subscription.id,
                    server_id=server.id,
                    config_data=config
                )
            server.current_clients += 1
            return config
    except Exception as e:
        print(e)
        return None


async def del_server_config(handler: XUIHandler, uid: str) -> Tuple[bool, str]:
    """Удаляет конфиг на сервере и возвращает статус выполнения"""
    try:
        async with handler:
            return await handler.delete_client_vless(uid), handler.panel_url
    except BaseException as ex:
        print(ex)
        return False, handler.panel_url



async def create_trial_sub(user: User) -> str:
    async with get_session() as session:
        # Создаем подписку и получаем серверы
        subscription: Subscription = await create_subscription(
            session=session,
            telegram_id=user.id
        )
        servers: List[Server] = await get_least_loaded_servers(session)
        # Создаем задачи для параллельного выполнения
        tasks = []
        for server in servers:
            tasks.append(
                create_server_config(
                    server=server,
                    subscription=subscription,
                    email=subscription.service_name,
                    uid=subscription.uuid_name
                )
            )
        # Запускаем все задачи параллельно
        results: List[str] = await asyncio.gather(*tasks)
        session.add_all(servers)
        await session.commit()
        return "\n".join(results)


async def get_active_user_subscription(user: User) -> List[Subscription]:
    """Находит все активные подписки пользователя, где User объект телеграмма пользователя"""
    async with get_session() as session:
        subs = await get_user_subscriptions(session, user.id)
        active_subs = [sub for sub in subs if sub.is_active]
        return active_subs



