from aiogram.types import User
from database.models import Server, Subscription, Config
from database.crud.crud_subscription import create_subscription, get_user_subscriptions, get_subscription_by_id
from database.crud.crud_server import get_least_loaded_servers
from database.crud.crud_config import create_config
from database.crud.crud_user import get_user_by_telegram_id
from database.session import get_session
from typing import List, Tuple, Optional
from bot.utils.xui_api_deepseek import XUIHandler
import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from bot.utils.logger import logger
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from bot.utils.messages import subscription_deactivated_message
from database.crud.crud_server import get_all_servers_with_load



async def create_server_config(
        server: Server,
        subscription: Subscription,
        email: str,
        uid: str
) -> Optional[str]:
    """Создает конфиг на одном сервере и возвращает результат"""
    try:
        handler = XUIHandler(
            panel_url=server.api_url,
            username=server.login,
            password=server.password
        )
        async with handler:
            await handler.add_client_vless(email, uid)
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
        logger.error(f"ERROR in create_server_config for {server.name}: {e}")
        return None


async def del_server_config(handler: XUIHandler, uid: str) -> Tuple[bool, str]:
    """Удаляет конфиг на сервере и возвращает статус выполнения"""
    try:
        async with handler:
            return await handler.delete_client_vless(uid), handler.panel_url
    except BaseException as ex:
        logger.error(f"ERROR in del_server_config: {ex}")
        return False, handler.panel_url


async def create_trial_sub(user_tg: User) -> Optional[Subscription]:
    """
    Создает пробную подписку, конфиги на серверах и возвращает ОБЪЕКТ подписки.
    """
    async with get_session() as session:
        user_db = await get_user_by_telegram_id(session, user_tg.id)
        subscription: Subscription = await create_subscription(
            session=session,
            user=user_db
        )
        servers: List[Server] = await get_least_loaded_servers(session)
        user_db = await get_user_by_telegram_id(session, user_tg.id)
        user_db.has_trial = False

        tasks = [create_server_config(
            server=server,
            subscription=subscription,
            email=subscription.service_name,
            uid=subscription.uuid_name
        ) for server in servers]

        await asyncio.gather(*tasks)
        session.add_all(servers)
        await session.commit()

        return subscription


async def get_active_user_subscription(user: User) -> List[Subscription]:
    """Находит все активные подписки пользователя, где User объект телеграмма пользователя"""
    async with get_session() as session:
        subs = await get_user_subscriptions(session, user.id)
        active_subs = [sub for sub in subs if sub.is_active]
        return active_subs


async def get_multiconfig_by_subscription(subscription_id: int) -> Optional[str]:
    """Эта функция больше не используется в основном потоке, но пусть останется."""
    async with get_session() as session:
        subscription: Subscription = await session.get(Subscription, subscription_id)
        if not subscription:
            return None
        await session.refresh(subscription, ["configs"])
        return "\n".join([config.config_data for config in subscription.configs])


async def activate_subscription(sub_id: int) -> Optional[Subscription]:
    """
    Активирует купленную подписку, создает конфиги и возвращает ОБЪЕКТ подписки.
    """
    async with get_session() as session:
        subscription: Subscription = await get_subscription_by_id(session, sub_id)
        if not subscription:
            return None

        servers: List[Server] = await get_least_loaded_servers(session)

        tasks = [create_server_config(
            server=server,
            subscription=subscription,
            email=subscription.service_name,
            uid=subscription.uuid_name
        ) for server in servers]

        await asyncio.gather(*tasks)
        session.add_all(servers)
        await session.commit()

        return subscription


async def deactivate_only_subscription(sub_id: int):
    async with get_session() as session:
        subscription: Subscription = await get_subscription_by_id(session, sub_id)
        subscription.is_active = False
        await session.commit()


async def deactivate_expired_subscriptions(bot: Bot):
    """
    Находит все просроченные подписки, уведомляет пользователей,
    деактивирует их в БД и удаляет клиентов из панелей 3x-ui.
    """
    logger.info("Scheduler: Запуск задачи по деактивации просроченных подписок...")
    now = datetime.now()

    async with get_session() as session:
        # 1. Находим все активные подписки, у которых дата окончания уже прошла,
        #    и СРАЗУ ЖЕ ("жадно") подгружаем все связанные данные.
        stmt = (
            select(Subscription)
            .options(
                # Подгружаем связанные конфиги, а для каждого конфига - связанный сервер
                selectinload(Subscription.configs).selectinload(Config.server),
                # Подгружаем связанного пользователя, чтобы знать его telegram_id
                selectinload(Subscription.user)
            )
            .where(Subscription.end_date < now, Subscription.is_active == True)
        )
        result = await session.execute(stmt)
        # .unique() нужен для избежания дубликатов из-за JOIN'ов при "жадной" загрузке
        expired_subscriptions: List[Subscription] = result.scalars().unique().all()

        if not expired_subscriptions:
            logger.info("Scheduler: Просроченные подписки не найдены.")
            return

        logger.info(f"Scheduler: Найдено {len(expired_subscriptions)} просроченных подписок для деактивации.")

        # 2. Проходимся по каждой просроченной подписке
        for sub in expired_subscriptions:
            # Теперь доступ к sub.user и sub.configs.server полностью безопасен и не вызовет ошибку
            logger.info(
                f"Scheduler: Обработка подписки ID {sub.id} (UUID: {sub.uuid_name}) для пользователя {sub.user.telegram_id}")

            # --- Удаление клиентов из панелей 3x-ui ---
            servers_to_clean = {config.server for config in sub.configs if config.server}
            tasks = []
            for server in servers_to_clean:
                try:
                    handler = XUIHandler(
                        panel_url=server.api_url,
                        username=server.login,
                        password=server.password
                    )
                    tasks.append(del_server_config(handler, sub.uuid_name))
                except Exception as e:
                    logger.error(f"Scheduler: Не удалось создать XUIHandler для сервера {server.name}: {e}")

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, Exception):
                        logger.error(f"Scheduler: Ошибка при удалении клиента {sub.uuid_name} из панели: {res}")

            # --- Обновление статуса в нашей БД ---
            sub.is_active = False
            logger.info(f"Scheduler: Подписка ID {sub.id} помечена как неактивная.")

            # --- Отправляем уведомление пользователю ПОСЛЕ успешной деактивации ---
            try:
                await bot.send_message(
                    chat_id=sub.user.telegram_id,
                    text=subscription_deactivated_message.format(sub_name=sub.service_name)
                )
                await asyncio.sleep(0.1)
            except (TelegramBadRequest, TelegramForbiddenError):
                logger.warning(
                    f"Scheduler: Не удалось отправить уведомление о деактивации пользователю {sub.user.telegram_id} (заблокировал бота).")
            except Exception as e:
                logger.error(f"Scheduler: Ошибка при отправке уведомления о деактивации: {e}")

        # Сохраняем все изменения (установку is_active = False) в БД одним коммитом
        await session.commit()

    logger.info("Scheduler: Задача по деактивации просроченных подписок завершена.")


async def update_servers_load_statistics():
    """
    Проходит по всем серверам в БД, подключается к их панелям 3x-ui,
    собирает статистику по активным клиентам и обновляет поле 'current_clients'.
    """
    logger.info("Scheduler: Запуск задачи по обновлению статистики нагрузки серверов...")

    async with get_session() as session:
        # 1. Получаем список всех наших серверов из БД
        all_servers: List[Server] = await get_all_servers_with_load(session)
        if not all_servers:
            logger.warning("Scheduler: Серверы в базе данных не найдены. Обновление статистики отменено.")
            return

        total_updated_servers = 0
        # 2. Проходим по каждому серверу
        for server in all_servers:
            if not server.is_active:
                continue

            try:
                # 3. Подключаемся к панели и получаем статистику
                handler = XUIHandler(
                    panel_url=server.api_url,
                    username=server.login,
                    password=server.password
                )
                async with handler:
                    inbounds_data = await handler.get_all_inbounds_with_client_stats()

                if inbounds_data is None:
                    logger.error(f"Scheduler: Не удалось получить статистику для сервера {server.name}.")
                    continue

                # 4. Считаем количество активных клиентов на этой панели
                active_clients_count = 0
                for inbound in inbounds_data:
                    # Убедимся, что clientStats это список
                    client_stats = inbound.get("clientStats")
                    if isinstance(client_stats, list):
                        # Считаем только включенных ('enable': true) клиентов
                        active_clients_count += sum(1 for client in client_stats if client.get("enable"))

                # 5. Обновляем значение в нашей БД
                server.current_clients = active_clients_count
                total_updated_servers += 1
                logger.info(f"Scheduler: Сервер '{server.name}' обновлен. Нагрузка: {active_clients_count} клиентов.")

            except Exception as e:
                logger.error(f"Scheduler: Непредвиденная ошибка при обработке сервера {server.name}: {e}")

        # Сохраняем все изменения в БД одним коммитом
        await session.commit()

    logger.info(f"Scheduler: Задача по обновлению статистики завершена. Обновлено {total_updated_servers} серверов.")