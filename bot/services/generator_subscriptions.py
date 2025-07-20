from aiogram.types import  User
from database.models import Server, Subscription
from database.crud.crud_subscription import create_subscription, get_user_subscriptions, get_subscription_by_id
from database.crud.crud_server import get_least_loaded_servers
from database.crud.crud_config import create_config
from database.crud.crud_user import get_user_by_telegram_id
from database.session import get_session
from typing import List, Tuple, Optional
from bot.utils.xui_api_deepseek import XUIHandler
import asyncio
from core.config import settings



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
            config = await handler.get_conf_user_vless(email, server.name)
            if config:
                async with get_session() as ses:
                    await create_config(
                        session=ses,
                        subscription_id=subscription.id,
                        server_id=server.id,
                        config_data=config
                    )
                    server.current_clients += 1
                    await ses.commit()
                return config
            return None
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



async def create_trial_sub(user_tg: User) -> str | None:
    async with get_session() as session:
        # Создаем подписку и получаем серверы
        subscription: Subscription = await create_subscription(
            session=session,
            telegram_id=user_tg.id
        )
        servers: List[Server] = await get_least_loaded_servers(session)
        # Убираем флаг промо версии
        user_db = await get_user_by_telegram_id(session, user_tg.id)
        user_db.has_trial = False

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
        await asyncio.gather(*tasks)
        session.add_all(servers)
        await session.commit()
        return f"https://{settings.DOMAIN_API}/subscription/{subscription.service_name}"



async def get_active_user_subscription(user: User) -> List[Subscription]:
    """Находит все активные подписки пользователя, где User объект телеграмма пользователя"""
    async with get_session() as session:
        subs = await get_user_subscriptions(session, user.id)
        active_subs = [sub for sub in subs if sub.is_active]
        return active_subs


async def get_multiconfig_by_subscription(subscription_id: int) -> Optional[str]:
    async with get_session() as session:
        # Получаем подписку и связанные конфиги
        subscription: Subscription = await session.get(Subscription, subscription_id)
        if not subscription:
            return None

        # Убедимся, что конфиги загружены
        await session.refresh(subscription, ["configs"])

        # Собираем непустые конфиги с подписями сервера (если есть)
        return "\n".join([config.config_data for config in subscription.configs])


async def activate_subscription(sub_id) -> str | None:
    async with get_session() as session:
        # Создаем подписку и получаем серверы
        subscription: Subscription = await get_subscription_by_id(session, sub_id)
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
        await asyncio.gather(*tasks)
        session.add_all(servers)
        await session.commit()
        return f"https://{settings.DOMAIN_API}/subscription/{subscription.service_name}"



async def deactivate_only_subscription(sub_id):
    async with get_session() as session:
        # Создаем подписку и получаем серверы
        subscription: Subscription = await get_subscription_by_id(session, sub_id)
        subscription.is_active = False
        await session.commit()



