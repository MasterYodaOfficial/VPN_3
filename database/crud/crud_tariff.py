import json
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Tariff
from database.session import get_session
from typing import List
from sqlalchemy import select



async def load_tariffs_from_json(file_path: str):
    """Загружает, обновляет, добавляет, деактивирует тарифы из json"""
    async with get_session() as session:
        with open(file_path, "r", encoding="utf-8") as f:
            json_tariffs = json.load(f)

        # Получаем все существующие тарифы из БД
        existing_tariffs = await session.execute(select(Tariff))
        existing_tariffs = existing_tariffs.scalars().all()

        # Создаем словарь для быстрого поиска по имени
        existing_tariffs_dict = {t.name: t for t in existing_tariffs}

        # Обрабатываем тарифы из JSON
        for json_tariff in json_tariffs:
            if json_tariff["name"] in existing_tariffs_dict:
                # Обновляем существующий тариф
                tariff = existing_tariffs_dict[json_tariff["name"]]
                tariff.duration_days = json_tariff["duration_days"]
                tariff.price = json_tariff["price"]
                tariff.currency = json_tariff["currency"]
                tariff.is_active = json_tariff["is_active"]
            else:
                # Добавляем новый тариф
                tariff = Tariff(**json_tariff)
                session.add(tariff)

        # Деактивируем тарифы, которых нет в JSON
        json_tariff_names = {t["name"] for t in json_tariffs}
        for tariff in existing_tariffs:
            if tariff.name not in json_tariff_names:
                tariff.is_active = False

        await session.commit()



async def get_active_tariffs() -> List[Tariff]:
    """
    Получает список активных тарифов из базы данных
    :return: Список объектов Tariff с is_active=True
    """
    async with get_session() as session:
        query = select(Tariff).where(Tariff.is_active == True).order_by(Tariff.price)
        result = await session.execute(query)
        return result.scalars().all()


async def get_tariff_by_id(session: AsyncSession, tariff_id: int) -> Tariff | None:
    """Получает тариф по его id"""
    stmt = select(Tariff).where(Tariff.id == tariff_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()